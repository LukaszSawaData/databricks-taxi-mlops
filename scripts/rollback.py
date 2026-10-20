"""Rollback: point @champion at an existing version and roll the endpoint to it (no retraining)."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from databricks.sdk import WorkspaceClient  # noqa: E402

from taxi_mlops.model import CHAMPION_ALIAS  # noqa: E402
from taxi_mlops.serving import deploy_version  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--env", required=True, choices=["dev", "prod"])
    p.add_argument("--version", type=int, required=True)
    p.add_argument("--catalog", default="workspace")
    args = p.parse_args()

    schema = f"taxi_{args.env}"
    model = f"{args.catalog}.{schema}.taxi_fare_model"
    w = WorkspaceClient()
    w.model_versions.get(full_name=model, version=args.version)  # fails if it does not exist
    w.registered_models.set_alias(full_name=model, alias=CHAMPION_ALIAS, version_num=args.version)
    print(f"{model}@{CHAMPION_ALIAS} -> v{args.version}")
    deploy_version(
        w, f"taxi-fare-{args.env}", model, str(args.version), args.env, args.catalog, schema
    )


if __name__ == "__main__":
    main()
