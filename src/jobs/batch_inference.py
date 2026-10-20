"""Batch inference job: score trips_scoring with @champion, write predictions, compute monitoring metrics.

Monitoring has two layers:
  1. taxi_model_metrics - our own RMSE/MAE + PSI drift table (always works, cheap).
  2. Databricks Data Quality monitor (inference profile) on taxi_predictions - best effort.
Drift or a quality drop can trigger the train job (closed loop), still gated by the deployment job.
"""

import argparse
import sys
from datetime import UTC, datetime


def ensure_quality_monitor(w, predictions_table: str, schema_full: str, assets_dir: str) -> None:
    from databricks.sdk.errors import NotFound
    from databricks.sdk.service.dataquality import (
        DataProfilingConfig,
        InferenceLogConfig,
        InferenceProblemType,
        Monitor,
        Refresh,
    )

    table_id = w.tables.get(predictions_table).table_id
    try:
        w.data_quality.get_monitor(object_type="table", object_id=table_id)
    except NotFound:
        schema_id = w.schemas.get(schema_full).schema_id
        w.data_quality.create_monitor(
            Monitor(
                object_type="table",
                object_id=table_id,
                data_profiling_config=DataProfilingConfig(
                    output_schema_id=schema_id,
                    assets_dir=assets_dir,
                    inference_log=InferenceLogConfig(
                        problem_type=InferenceProblemType.INFERENCE_PROBLEM_TYPE_REGRESSION,
                        timestamp_column="pickup_ts",
                        granularities=["1 day"],
                        prediction_column="prediction",
                        model_id_column="model_version",
                        label_column="fare_amount",
                    ),
                ),
            )
        )
        print(f"created data quality monitor on {predictions_table}")
    w.data_quality.create_refresh(object_type="table", object_id=table_id, refresh=Refresh())


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--model_name", required=True, help="short name, e.g. taxi_fare_model")
    p.add_argument("--monitor_assets_dir", required=True)
    p.add_argument("--train_job_name", required=True)
    p.add_argument("--retrain_on_drift", default="false")
    p.add_argument("--max_psi", type=float, default=0.2)
    p.add_argument("--max_rmse", type=float, default=6.0)
    p.add_argument("--src_dir", required=True)
    args = p.parse_args()

    sys.path.insert(0, args.src_dir)
    import mlflow
    import pandas as pd
    from databricks.sdk import WorkspaceClient
    from pyspark.sql import SparkSession

    from taxi_mlops.model import CHAMPION_ALIAS, REQUEST_COLUMNS, TARGET, evaluate, psi

    mlflow.set_registry_uri("databricks-uc")
    spark = SparkSession.builder.getOrCreate()
    w = WorkspaceClient()
    ns = f"{args.catalog}.{args.schema}"
    full_name = f"{ns}.{args.model_name}"

    version = mlflow.MlflowClient().get_model_version_by_alias(full_name, CHAMPION_ALIAS).version
    model = mlflow.pyfunc.load_model(f"models:/{full_name}@{CHAMPION_ALIAS}")

    # Data is tiny -> pandas is simpler than spark_udf. Switch to spark_udf for real volumes.
    scoring = spark.table(f"{ns}.trips_scoring").toPandas()
    scoring["prediction"] = model.predict(scoring[REQUEST_COLUMNS])
    scoring["model_version"] = str(version)
    scoring["scored_at"] = datetime.now(UTC)

    predictions_table = f"{ns}.taxi_predictions"
    cols = [
        "trip_id",
        "pickup_ts",
        *REQUEST_COLUMNS,
        TARGET,
        "prediction",
        "model_version",
        "scored_at",
    ]
    # Idempotent: re-running for the same version replaces its rows instead of duplicating them.
    writer = spark.createDataFrame(scoring[cols]).write.mode("overwrite")
    if spark.catalog.tableExists(predictions_table):
        writer = writer.option("replaceWhere", f"model_version = '{version}'")
    writer.saveAsTable(predictions_table)

    # Layer 1: own metrics (label is known here because the data is historical).
    train = spark.table(f"{ns}.trips_train").select(*REQUEST_COLUMNS).toPandas()
    quality = evaluate(model, scoring[REQUEST_COLUMNS], scoring[TARGET])
    drift = {f"psi_{c}": psi(train[c], scoring[c]) for c in ["trip_distance", "pickup_hour"]}
    row = {"model_version": str(version), "measured_at": datetime.now(UTC), "rows": len(scoring)}
    row |= quality | drift
    spark.createDataFrame(pd.DataFrame([row])).write.mode("append").saveAsTable(
        f"{ns}.taxi_model_metrics"
    )
    print(f"monitoring: {row}")

    # Layer 2: Databricks Data Quality Monitoring (dashboard + profile/drift tables).
    try:
        ensure_quality_monitor(w, predictions_table, ns, args.monitor_assets_dir)
    except Exception as e:
        print(f"WARN: data quality monitor not available: {e}")

    drifted = max(drift.values()) > args.max_psi or quality["rmse"] > args.max_rmse
    if drifted and args.retrain_on_drift.lower() == "true":
        # Matched by suffix so a name_prefix preset would not break it.
        jobs = [j for j in w.jobs.list() if j.settings.name.endswith(args.train_job_name)]
        if jobs:
            run = w.jobs.run_now(job_id=jobs[0].job_id)
            print(f"drift/quality alert -> started retraining run {run.run_id}")
    elif drifted:
        print("drift/quality alert (retrain_on_drift=false, not retraining)")


if __name__ == "__main__":
    main()
