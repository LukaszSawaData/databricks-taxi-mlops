"""Deployment job, task `deployment`: move @champion and roll the serving endpoint to that version."""

import argparse
import sys


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model_name", required=True)
    p.add_argument("--model_version", required=True)
    p.add_argument("--endpoint", required=True)
    p.add_argument("--env", required=True)
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--serving_enabled", default="true")
    p.add_argument("--src_dir", required=True)
    args = p.parse_args()

    sys.path.insert(0, args.src_dir)
    import mlflow
    from databricks.sdk import WorkspaceClient

    from taxi_mlops.model import CHAMPION_ALIAS
    from taxi_mlops.serving import deploy_version

    mlflow.set_registry_uri("databricks-uc")
    mlflow.MlflowClient().set_registered_model_alias(
        args.model_name, CHAMPION_ALIAS, args.model_version
    )
    print(f"@{CHAMPION_ALIAS} -> v{args.model_version}")

    if args.serving_enabled.lower() == "true":
        deploy_version(
            WorkspaceClient(),
            args.endpoint,
            args.model_name,
            args.model_version,
            args.env,
            args.catalog,
            args.schema,
        )
    else:
        print("serving disabled for this target (batch scoring only)")


if __name__ == "__main__":
    main()
