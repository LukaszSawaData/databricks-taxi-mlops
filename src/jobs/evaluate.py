"""Deployment job, task `evaluation`: candidate vs @champion on the same out-of-time data.

Fails the task (so the version is not deployed) when the candidate is not good enough.
"""

import argparse
import sys


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model_name", required=True, help="catalog.schema.model (job parameter)")
    p.add_argument("--model_version", required=True)
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--max_rmse", type=float, default=6.0)
    p.add_argument("--tolerance", type=float, default=0.0)
    p.add_argument("--auto_approve", default="false")
    p.add_argument("--approval_tag", default="approval_check")
    p.add_argument("--src_dir", required=True)
    args = p.parse_args()

    sys.path.insert(0, args.src_dir)
    import mlflow
    from mlflow.exceptions import MlflowException
    from pyspark.sql import SparkSession

    from taxi_mlops.model import (
        CHAMPION_ALIAS,
        REQUEST_COLUMNS,
        TARGET,
        evaluate,
        promotion_decision,
    )

    mlflow.set_registry_uri("databricks-uc")
    client = mlflow.MlflowClient()
    spark = SparkSession.builder.getOrCreate()

    # Out-of-time evaluation: trips after split_date, never seen in training.
    pdf = spark.table(f"{args.catalog}.{args.schema}.trips_scoring").toPandas()
    X, y = pdf[REQUEST_COLUMNS], pdf[TARGET]

    # Loading from UC also proves the version is loadable before it reaches serving.
    candidate = mlflow.pyfunc.load_model(f"models:/{args.model_name}/{args.model_version}")
    cand = evaluate(candidate, X, y)
    print(f"candidate v{args.model_version}: {cand}")

    champion_rmse = None
    try:
        champ_v = client.get_model_version_by_alias(args.model_name, CHAMPION_ALIAS).version
        if str(champ_v) != str(args.model_version):
            champion = mlflow.pyfunc.load_model(f"models:/{args.model_name}@{CHAMPION_ALIAS}")
            champion_rmse = evaluate(champion, X, y)["rmse"]
            print(f"champion v{champ_v}: rmse={champion_rmse:.3f}")
    except MlflowException:
        print("no champion yet")

    promote, reason = promotion_decision(cand["rmse"], champion_rmse, args.max_rmse, args.tolerance)
    for key, value in {"eval_rmse": f"{cand['rmse']:.4f}", "eval_decision": reason}.items():
        client.set_model_version_tag(args.model_name, args.model_version, key, value)

    if not promote:
        raise SystemExit(f"Not promoting v{args.model_version}: {reason}")
    if args.auto_approve.lower() == "true":
        # dev only: the same tag the Approve button sets in the UI.
        client.set_model_version_tag(
            args.model_name, args.model_version, args.approval_tag, "Approved"
        )
        print("auto-approved (dev)")


if __name__ == "__main__":
    main()
