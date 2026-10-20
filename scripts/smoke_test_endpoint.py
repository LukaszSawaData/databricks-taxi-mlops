"""Smoke test a serving endpoint: the expected version is served and predictions look sane."""

import argparse
import sys
import time

from databricks.sdk import WorkspaceClient

# Raw request columns only - zip features are added inside the model.
SAMPLE = [
    {"trip_distance": 1.2, "pickup_hour": 8.0, "pickup_dow": 2.0, "pickup_zip": 10001.0},
    {"trip_distance": 8.5, "pickup_hour": 18.0, "pickup_dow": 6.0, "pickup_zip": 10019.0},
    {"trip_distance": 3.0, "pickup_hour": 1.0, "pickup_dow": 7.0, "pickup_zip": 99999.0},
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--endpoint", required=True)
    p.add_argument("--expected-version", required=True)
    p.add_argument("--retries", type=int, default=10)
    args = p.parse_args()

    w = WorkspaceClient()
    ep = w.serving_endpoints.get(args.endpoint)
    served = {e.entity_version for e in ep.config.served_entities}
    print(f"{args.endpoint}: ready={ep.state.ready} served_versions={served}")
    if args.expected_version not in served:
        sys.exit(f"Expected version {args.expected_version}, endpoint serves {served}")

    # Scale-to-zero endpoints may need a few minutes to wake up.
    for attempt in range(1, args.retries + 1):
        try:
            resp = w.serving_endpoints.query(name=args.endpoint, dataframe_records=SAMPLE)
            break
        except Exception as e:
            print(f"attempt {attempt}/{args.retries} failed: {e}", flush=True)
            time.sleep(30)
    else:
        sys.exit("Endpoint did not answer")

    preds = resp.predictions
    print(f"predictions={preds}")
    if len(preds) != len(SAMPLE) or not all(0 < x < 500 for x in preds):
        sys.exit("Predictions out of the expected range")
    if not preds[1] > preds[0]:
        sys.exit("A longer trip should cost more")


if __name__ == "__main__":
    main()
