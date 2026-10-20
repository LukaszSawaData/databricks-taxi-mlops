"""Deployment job, task `approval_check`: passes only when the version tag <approval_check>=Approved.

The task name must start with "approval" so the UC model page shows an Approve button.
The first prod run fails here by design; Approve sets the tag and repairs the run.
"""

import argparse


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model_name", required=True)
    p.add_argument("--model_version", required=True)
    p.add_argument("--approval_tag", default="approval_check")
    args = p.parse_args()

    import mlflow

    mlflow.set_registry_uri("databricks-uc")
    mv = mlflow.MlflowClient().get_model_version(args.model_name, args.model_version)
    value = (mv.tags or {}).get(args.approval_tag, "")
    if value.lower() != "approved":
        raise SystemExit(
            f"v{args.model_version} is not approved (tag {args.approval_tag}={value!r}). "
            "Approve it on the UC model version page, then repair this run."
        )
    print(f"v{args.model_version} approved")


if __name__ == "__main__":
    main()
