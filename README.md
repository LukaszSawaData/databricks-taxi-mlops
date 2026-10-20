# Databricks MLOps Quickstart: NYC Taxi on Free Edition

End-to-end MLOps on one Databricks Free Edition workspace with dev and prod isolated from each other.
The model is deliberately trivial (fare regression, a few seconds to train). The lesson is the plumbing.

## Architecture

```
                      GitHub
  PR ──► ci.yml: ruff + pytest + terraform validate ──► _deploy.yml(dev)
  main ─► cd.yml: _deploy.yml(dev) ──► [GitHub approval] ──► _deploy.yml(prod)
                                                    │  auth: SP OAuth secret per environment
───────────────────────────────────────────────────┼────────────────────────────────────────
  Databricks Free Edition (one workspace)           ▼   databricks bundle deploy -t <env>
                                                        databricks bundle run train -t <env>
  ┌─ Terraform (infra/platform, run once by you) ─────────────────────────────────────┐
  │ sp-taxi-mlops-dev / -prod · workspace.taxi_dev / taxi_prod · GitHub envs + secrets     │
  └───────────────────────────────────────────────────────────────────────────────────┘
  ┌─ Bundle target <env> (runs as sp-taxi-mlops-<env>) ───────────────────────────────┐
  │ Lakeflow pipeline taxi-features-<env>                                             │
  │   samples.nyctaxi.trips → trips_raw → trips_clean (expectations = data tests)     │
  │                           → trips_train / trips_scoring                           │
  │                           → pickup_zip_features (PK = Feature Store table)        │
  │ Job taxi-train-<env>: refresh_features → train (FeatureLookup, MLflow 3, UC model)│
  │        │ new version of workspace.taxi_<env>.taxi_fare_model                      │
  │        ▼ (auto trigger: MLflow deployment job)                                    │
  │ Job taxi-deployment-<env>: evaluation → approval_check → deployment → batch       │
  │        vs @champion        dev: auto   @champion +    taxi_predictions,           │
  │        on trips_scoring    prod: human endpoint       taxi_model_metrics,         │
  │                                        taxi-fare-<env> data quality monitor       │
  └───────────────────────────────────────────────────────────────────────────────────┘
```

Two gates protect prod. **Code gate**: the GitHub `prod` environment approval before `bundle deploy -t prod`.
**Model gate**: the MLflow deployment job's `approval_check` task, approved in Catalog Explorer.

## Isolation: what is separate per environment

| Artifact | dev | prod |
|---|---|---|
| Identity (deploys + runs) | `sp-taxi-mlops-dev` | `sp-taxi-mlops-prod` |
| UC schema (tables, features, model, monitoring) | `workspace.taxi_dev` | `workspace.taxi_prod` |
| Workspace folder (bundle files, experiment, dashboards) | `/Users/<dev SP id>/` | `/Users/<prod SP id>/` |
| Data volume | 3k rows | all rows (~22k) |
| Approval of a new model | automatic | human |
| Endpoint | `taxi-fare-dev` | `taxi-fare-prod` |

## Repository layout

```
infra/platform/          Terraform: SPs + secrets, schemas, grants, GitHub envs/secrets
databricks.yml           Bundle: variables, run_as, targets dev/prod
resources/               Bundle resources: pipeline, 3 jobs, experiment, registered model
src/pipelines/           Lakeflow declarative pipeline (data tests + features)
src/jobs/                train / evaluate / approval / deploy / batch_inference
src/taxi_mlops/          pure model logic (unit-tested), MLflow pyfunc wrapper, serving helper
scripts/                 CI helpers: wait_for_deployment, smoke_test_endpoint, rollback
tests/                   pytest (no Databricks needed)
.github/workflows/       ci.yml (PR), cd.yml (main), _deploy.yml (reusable), rollback.yml
docs/DEMO_GUIDE.md       step-by-step guide for presenting this to an audience
```

## Quick start (full presenter runbook: docs/DEMO_GUIDE.md)

```bash
# 0. tools: Databricks CLI >= 1.21 (the `databricks` in ~/.local/bin is the deprecated 0.18 - replace it)
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
databricks configure --host https://dbc-b7edd512-cbb9.cloud.databricks.com --profile free   # paste your PAT (admin, local only)

# 1. GitHub repo + platform (once)
git init && gh repo create databricks-taxi-mlops --private --source . --push
cd infra/platform && cp terraform.tfvars.example terraform.tfvars   # edit
export GITHUB_TOKEN=...; terraform init && terraform apply

# 2. local checks
pip install -r requirements-dev.txt && ruff check . && pytest -q

# 3. open a PR -> CI deploys + runs dev; merge -> CD deploys prod (approve twice)
```

Bundle commands always run **as the environment SP** (CI, or local profiles `dev-sp`/`prod-sp`; see docs/DEMO_GUIDE.md, step 0.4).
Your PAT is only for Terraform. If you deploy as yourself, you own the model and the SP can't move `@champion`.

Teardown: `databricks bundle destroy -t dev --profile dev-sp` (and prod), delete endpoints `taxi-fare-*`,
then `terraform destroy` in `infra/platform`.

## What is new in 2026 and how this repo uses it

- **Declarative Automation Bundles** is the new name for Databricks Asset Bundles (Mar 2026, CLI 0.287+).
  CLI 1.x uses the **direct deployment engine** by default (no Terraform under the hood).
- **MLflow 3**: `LoggedModel` (`log_model(name=...)`, `log_metrics(model_id=...)`). Metrics show on the
  UC model version page. **Deployment jobs** (Public Preview) are triggered by a new UC version.
- **Lakeflow Spark Declarative Pipelines** (`from pyspark import pipelines as dp`) replace `import dlt`.
- **Data Quality Monitoring API** (`w.data_quality`) replaces the deprecated `quality_monitors` API.
- **Online feature store** now runs on Lakebase. It isn't available on Free Edition and isn't needed here.

## Sources (what each part is built from)

Practitioner sources:
- [From Laptop Prototype to Scheduled Job (Oct 2026)](https://hovinh.github.io/blog/2026-10-10-databricks-ml-setup/):
  Free Edition + `samples.nyctaxi.trips`, one schema per env in one workspace, serverless `environment_version`,
  gotchas (MLflow 3 tracking URI, `__file__` in jobs, `pip_requirements`, casting, grants follow identity).
- [kkarki7120/databricks-mlops-platform](https://github.com/kkarki7120/databricks-mlops-platform):
  champion/challenger aliases, bundle targets dev/prod deployed by GitHub Actions.
- [DAB is now Declarative Automation Bundles (community MVP article)](https://community.databricks.com/t5/mvp-articles/databricks-asset-bundles-is-now-declarative-automation-bundles/td-p/151594)
- [Community thread: aliases in bundle config not applied](https://community.databricks.com/t5/data-engineering/dab-registered-model-aliases-not-being-applied-to-unity-catalog/m-p/140509/highlight/true):
  the reason aliases are moved by the deployment job, not declared in YAML.
- [databricks/terraform-provider-databricks docs (GitHub)](https://github.com/databricks/terraform-provider-databricks/tree/main/docs)

Vendor pages used only to check facts and limits, not as course material:
[MLflow 3 deployment jobs](https://docs.databricks.com/aws/en/mlflow/deployment-job) (parameters, `approval*` task naming, permissions),
[Free Edition limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations),
[Online feature store](https://docs.databricks.com/aws/en/machine-learning/feature-store/online-feature-store).
