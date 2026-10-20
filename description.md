# Databricks MLOps Quickstart (NYC Taxi, Free Edition)

A very basic but complete MLOps setup on **Databricks Free Edition**
(`https://dbc-b7edd512-cbb9.cloud.databricks.com`). The goal is the **MLOps plumbing**, not the model.

## Scope (as requested)
- Data from a dataset already inside Databricks: `samples.nyctaxi.trips` (about 22k rows).
- **Terraform**: platform layer (service principals + secrets, UC schemas, grants, GitHub environments/secrets).
- **DAB (Declarative Automation Bundles)**: workload layer (pipeline, jobs, experiment, model) deployed per target.
- **Lakeflow Spark Declarative Pipeline**: data tests (expectations) + feature computation.
- **Feature Store** (UC feature table with a PK) + `FeatureEngineeringClient.create_training_set`.
- **MLflow 3 tracking** + models registered in **Unity Catalog**.
- **Lakeflow Jobs**: training runs in each environment on that environment's own data (prod trains on prod data).
- **MLflow deployment job** with `@champion`: evaluation → approval → deployment → batch inference.
- **Model Serving** (scale-to-zero CPU endpoint) + smoke test + rollback.
- **Monitoring**: own RMSE/PSI table + Databricks Data Quality Monitoring + endpoint inference table (best effort).
- **GitHub Actions**: PR CI (lint, tests, terraform validate, deploy+run on dev), CD to prod with approval.
- **One workspace**: dev artifacts in dev, prod in prod (schema, folder, experiment, jobs, model, endpoint, SP).
- Training must be **very fast** on **very little data** (3k rows in dev).

## Constraints discovered
- Free Edition: serverless only, no account console/APIs (so no GitHub OIDC federation → SP OAuth secret),
  1 active pipeline per type, 5 concurrent job tasks, limited serving endpoints, **no online tables**.
- No online feature store → serving cannot look features up in real time. The tiny zip-feature table is
  embedded in the model at training time (see `src/taxi_mlops/model.py::FarePredictor`). No Lakebase needed.

## Out of scope (for now)
Separate workspaces, GPU, online feature store, LLM/agents.
