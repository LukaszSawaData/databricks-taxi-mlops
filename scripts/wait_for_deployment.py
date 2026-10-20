"""CI helper: find the MLflow deployment-job run for the newest model version and wait for it.

The deployment job is triggered automatically by UC when train.py registers a version.
If no run shows up (e.g. preview disabled), it is started manually with the same parameters.
Writes model_version=<v> to $GITHUB_OUTPUT for the smoke test.
"""

import argparse
import os
import sys
import time
from datetime import timedelta

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import RunResultState


def find_run(w: WorkspaceClient, job_id: int, version: str):
    for run in w.jobs.list_runs(job_id=job_id, limit=25):
        params = {p.name: p.value for p in (run.job_parameters or [])}
        if params.get("model_version") == version:
            return run.run_id
    return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--deployment-job-id", type=int, required=True)
    p.add_argument("--model", required=True, help="catalog.schema.model")
    p.add_argument("--trigger-after-s", type=int, default=180)
    p.add_argument("--timeout-min", type=int, default=45)
    args = p.parse_args()

    w = WorkspaceClient()
    version = str(max(int(v.version) for v in w.model_versions.list(full_name=args.model)))
    print(f"newest version: {args.model} v{version}")

    deadline = time.time() + args.trigger_after_s
    run_id = find_run(w, args.deployment_job_id, version)
    while run_id is None and time.time() < deadline:
        time.sleep(15)
        run_id = find_run(w, args.deployment_job_id, version)
    if run_id is None:
        print("no automatic run found -> triggering the deployment job manually")
        run_id = w.jobs.run_now(
            job_id=args.deployment_job_id,
            job_parameters={"model_name": args.model, "model_version": version},
        ).run_id

    print(f"deployment run: {w.jobs.get_run(run_id).run_page_url}", flush=True)
    run = w.jobs.wait_get_run_job_terminated_or_skipped(
        run_id=run_id, timeout=timedelta(minutes=args.timeout_min)
    )
    for task in run.tasks or []:
        print(f"  {task.task_key}: {task.state.result_state if task.state else None}")

    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a") as f:
            f.write(f"model_version={version}\n")
    if run.state.result_state != RunResultState.SUCCESS:
        sys.exit(f"deployment job finished with {run.state.result_state}")


if __name__ == "__main__":
    main()
