"""Train job, task `train`: Feature Store training set -> sklearn -> MLflow 3 -> new UC model version.

Registering the version auto-triggers the MLflow deployment job linked to the model.
"""

import argparse
import os
import sys


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--model_name", required=True)
    p.add_argument("--experiment", required=True)
    p.add_argument("--deployment_job_id", required=True)
    p.add_argument("--src_dir", required=True)
    p.add_argument("--git_sha", default="local")
    args = p.parse_args()

    # __file__ is not defined in spark_python_task, so the bundle passes the code folder.
    sys.path.insert(0, args.src_dir)
    import mlflow
    from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup
    from mlflow.models import infer_signature
    from pyspark.sql import SparkSession

    from taxi_mlops.model import (
        REQUEST_COLUMNS,
        TARGET,
        ZIP_FEATURES,
        ZIP_KEY,
        FarePredictor,
        build_model,
        evaluate,
        split,
    )
    from taxi_mlops.pyfunc import TaxiFareModel

    spark = SparkSession.builder.getOrCreate()
    ns = f"{args.catalog}.{args.schema}"
    full_model_name = f"{ns}.{args.model_name}"
    feature_table = f"{ns}.pickup_zip_features"

    # MLflow 3 silently uses a local store if the URIs are not set.
    mlflow.set_tracking_uri("databricks")
    mlflow.set_registry_uri("databricks-uc")
    mlflow.set_experiment(args.experiment)
    client = mlflow.MlflowClient()

    # Link the deployment job once (idempotent). Without it, a new version triggers nothing.
    client.update_registered_model(full_model_name, deployment_job_id=args.deployment_job_id)

    # Feature Store: labels + lookup key from trips_train, features joined from the feature table.
    fe = FeatureEngineeringClient()
    training_set = fe.create_training_set(
        df=spark.table(f"{ns}.trips_train").select("trip_id", *REQUEST_COLUMNS, TARGET),
        feature_lookups=[
            FeatureLookup(table_name=feature_table, lookup_key=ZIP_KEY, feature_names=ZIP_FEATURES)
        ],
        label=TARGET,
        exclude_columns=["trip_id"],
    )
    train_pdf = training_set.load_df().toPandas()
    zip_pdf = spark.table(feature_table).toPandas()

    X_train, X_test, y_train, y_test = split(train_pdf)

    with open(os.path.join(args.src_dir, "requirements-job.txt")) as f:
        pip_requirements = [
            line.strip() for line in f if line.strip() and "feature-engineering" not in line
        ]

    with mlflow.start_run(run_name=f"train-{args.schema}") as run:
        mlflow.set_tags({"git_sha": args.git_sha, "schema": args.schema})
        mlflow.log_params(
            {"rows_train": len(X_train), "rows_test": len(X_test), "zips": len(zip_pdf)}
        )
        mlflow.log_input(
            mlflow.data.from_pandas(train_pdf, name="training_set"), context="training"
        )

        sk_model = build_model().fit(X_train, y_train)
        predictor = FarePredictor(sk_model, zip_pdf)
        sample = X_test[REQUEST_COLUMNS].head(5)

        info = mlflow.pyfunc.log_model(
            name="model",
            python_model=TaxiFareModel(predictor),
            code_paths=[os.path.join(args.src_dir, "taxi_mlops")],
            signature=infer_signature(sample, predictor.predict(sample)),
            input_example=sample,
            pip_requirements=pip_requirements,
            registered_model_name=full_model_name,
        )
        metrics = {f"holdout_{k}": v for k, v in evaluate(predictor, X_test, y_test).items()}
        # MLflow 3: metrics on the LoggedModel show up on the UC model version page.
        mlflow.log_metrics(metrics, model_id=info.model_id)

    version = str(info.registered_model_version)
    client.set_model_version_tag(full_model_name, version, "git_sha", args.git_sha)
    print(f"run={run.info.run_id} {full_model_name} v{version} {metrics}")


if __name__ == "__main__":
    main()
