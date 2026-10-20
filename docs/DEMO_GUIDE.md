# Demo guide: Databricks MLOps quickstart (NYC Taxi, Free Edition)

A presenter runbook. **Part 0** is done before the audience arrives. **Part 1** is the live show, about 45 minutes.
Each step has: **Do** (what you click or type), **Show** (what the audience sees), **Say** (the point to make).

> Serverless start-up + pipeline + training + endpoint rollout takes 15–25 minutes end to end.
> Never wait for it live. Pre-run everything in Part 0, show finished runs, and trigger one fresh
> run (the PR in step 9) at the start so it finishes while you talk.

Workspace: `https://dbc-b7edd512-cbb9.cloud.databricks.com`

---

## Part 0: Preparation (the day before, about 1.5 h)

### 0.1 Tools
```bash
# Databricks CLI >= 1.21 (the ~/.local/bin/databricks 0.18 is the deprecated legacy CLI - replace it)
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
databricks --version
terraform version        # >= 1.9
sudo apt-get install -y jq   # used in step 4
rm ~/.local/bin/databricks   # remove the legacy 0.18 CLI that shadows the new one in $PATH
gh auth status           # GitHub CLI logged in
python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
```

### 0.2 Your admin login (PAT, local only)
Databricks → Settings → Developer → Access tokens → Generate (lifetime: 30 days).
```bash
databricks configure --host https://dbc-b7edd512-cbb9.cloud.databricks.com --profile free   # paste the PAT
databricks current-user me --profile free
```

### 0.3 GitHub repo + platform (Terraform)
```bash
git init -b main && git add . && git commit -m "Databricks MLOps quickstart"
gh repo create databricks-taxi-mlops --private --source . --push

cd infra/platform
cp terraform.tfvars.example terraform.tfvars     # set github_owner / github_repo
# Free GitHub + private repo: add `prod_required_reviewers = false` (or make the repo public)
export GITHUB_TOKEN=<fine-grained PAT for that repo: Administration, Environments, Secrets, Variables = RW>
terraform init && terraform apply
terraform output service_principals
terraform output -json sp_secrets
cd ../..
# GitHub Free: environment secrets + reviewers need a PUBLIC repo (or Pro/Team for private)
```
If `databricks_service_principal_secret` is rejected: create the secrets in the UI
(Settings → Identity and access → Service principals → `sp-taxi-mlops-dev` → Secrets → Generate), then run again with
`create_sp_secrets = false` and `manual_sp_secrets = { dev = "...", prod = "..." }`.

### 0.4 SP profiles (bundle commands always run as the env SP, never as you)
Add to `~/.databrickscfg`:
```
[dev-sp]
host          = https://dbc-b7edd512-cbb9.cloud.databricks.com
client_id     = <service_principals.dev>
client_secret = <sp_secrets.dev>

[prod-sp]
host          = https://dbc-b7edd512-cbb9.cloud.databricks.com
client_id     = <service_principals.prod>
client_secret = <sp_secrets.prod>
```
Why: `run_as` covers jobs and pipelines, but the registered model is owned by **whoever deploys**.
If you deploy as yourself, the SP's deployment job can't move `@champion`.

### 0.5 Dry run: full flow on dev, then prod
```bash
databricks bundle validate -t dev --profile dev-sp
databricks bundle deploy   -t dev --profile dev-sp
databricks bundle run train -t dev --profile dev-sp       # pipeline + training -> v1 -> deployment job
```
Wait until the deployment job **`taxi-deployment-dev`** finishes (Jobs UI), then:
```bash
DATABRICKS_CONFIG_PROFILE=dev-sp python scripts/smoke_test_endpoint.py --endpoint taxi-fare-dev --expected-version 1
```
Run `train` a **second time** so dev has v1 and v2 (needed for the rollback step).
Then push to `main` once, so `cd` runs prod: approve the GitHub `prod` environment, wait for prod training,
open `workspace.taxi_prod.taxi_fare_model` → newest version → **Approve**. Check `taxi-fare-prod` is Ready.

### 0.6 Things to check, and their fallbacks
| Check | If it fails |
|---|---|
| Deployment job started by itself after `train` | Preview not enabled → CI's `wait_for_deployment.py` starts it anyway; in a manual run: Jobs → `taxi-deployment-dev` → Run now with `model_name`, `model_version` |
| Endpoint `taxi-fare-dev` Ready | Free Edition endpoint limit → set `serving_enabled: "false"` in dev, demo serving on prod only |
| `taxi_predictions` → Quality tab shows a monitor | Not on Free Edition → show `taxi_model_metrics` (always written) |
| `taxi_fare_payload` inference table exists | Skipped (log says WARN) → show the endpoint's built-in Metrics tab instead |
| Free Edition daily quota | Don't re-run on the demo day before the show; everything you show must already be finished |

### 0.7 Browser tabs to open before you start (in this order)
1. GitHub repo (Code tab) 2. GitHub Actions 3. Databricks Catalog Explorer → `workspace` 4. Jobs & Pipelines
5. Experiments 6. Serving 7. A SQL editor with the queries from step 8 pasted in 8. The terminal in the repo folder

---

## Part 1: Live demo (about 45 min)

### Step 1: The problem and the architecture (3 min)
**Do:** open `README.md` on GitHub and scroll to the architecture diagram.
**Say:** "One Free Edition workspace with two environments that can't touch each other. Terraform builds the platform,
a bundle builds the workload, GitHub Actions moves code. A model reaches prod only after two approvals:
one for the code, one for the model."
**Show:** the isolation table: identity, schema, folder, data volume, approval and endpoint per environment.

### Step 2: Kick off a live change first (2 min, it runs in the background)
**Do:**
```bash
git switch -c demo/change-comment
sed -i 's/NYC taxi fare regressor/NYC taxi fare regressor (demo)/' resources/ml.yml
git commit -am "demo: change model comment" && git push -u origin demo/change-comment
gh pr create --fill
```
**Say:** "This PR will prove itself on dev while we walk through the pieces. We'll come back to it in step 9."

### Step 3: Platform layer: Terraform (4 min)
**Do:** open `infra/platform/identities.tf`, `unity_catalog.tf`, `github.tf`. In the terminal:
`cd infra/platform && terraform plan` → *No changes*.
**Show:** Catalog Explorer → `workspace.taxi_dev` → Permissions: `sp-taxi-mlops-dev` has ALL PRIVILEGES and the prod SP has nothing.
GitHub → Settings → Environments → `prod` (reviewer + `main` only).
**Say:** "Isolation is decided here, once, by an admin. Dev's identity physically can't write to prod's schema."

### Step 4: Workload layer: Declarative Automation Bundle (4 min)
**Do:** open `databricks.yml`, then compare the targets in the terminal:
```bash
databricks bundle validate -t dev  -o json --profile dev-sp  | jq '.resources.jobs.train.name, .variables.max_rows.value, .workspace.root_path'
databricks bundle validate -t prod -o json --profile prod-sp | jq '.resources.jobs.train.name, .variables.max_rows.value, .workspace.root_path'
```
**Show:** `"taxi-train-dev"` / `3000` vs `"taxi-train-prod"` / `0` (all rows), and each root path in that SP's own home
(`/Workspace/Users/<app id>/...`), because `/Workspace/Shared` is writable by every user.
**Say:** "Same code, two deployments. Prod trains on prod data. We don't copy dev's model into prod.
'Deploy code, not models' is the Databricks-recommended pattern."

### Step 5: Lakeflow pipeline: data tests + features (5 min)
**Do:** Jobs & Pipelines → `taxi-features-dev` → last update → graph.
**Show:**
- graph `trips_raw → trips_clean → trips_train / trips_scoring → pickup_zip_features`;
- click `trips_clean` → **Data quality**: rows dropped per expectation (`valid_fare`, `valid_distance`, `has_zip`);
- `src/pipelines/features.py`: `@dp.expect_or_drop` vs `@dp.expect_or_fail`;
- Catalog Explorer → `pickup_zip_features` → primary key `pickup_zip` = a **Feature Store** table.
**Say:** "Data tests run in the pipeline. Bad rows are dropped and counted. A broken feature table fails the update,
so training never starts on bad features."

### Step 6: Training job: Feature Store + MLflow 3 (6 min)
**Do:** Jobs → `taxi-train-dev` → last run.
**Show:**
- tasks `refresh_features → train`, all on serverless; point out how short the train task is;
- `src/jobs/train.py`: `create_training_set(... FeatureLookup ...)`, `log_model(name=...)`, `log_metrics(model_id=...)`;
- Experiments → `/Users/<dev SP app id>/taxi-fare-experiment-dev` → run: params, `training_set` input, `git_sha` tag;
- Catalog Explorer → `taxi_fare_model` → version: metrics on the version page (MLflow 3 LoggedModel), lineage.
**Say:** "Every version tells us which commit, which data and which metrics produced it.
There's no online feature store on Free Edition, so the small zip-feature table is packed inside the model.
Batch and real-time use the same artifact, so there's no training/serving skew."

### Step 7: MLflow deployment job with @champion (6 min)
**Do:** Catalog Explorer → `taxi_fare_model` → Overview → **Deployment job** panel. Open the last run of `taxi-deployment-dev`.
**Show:**
- the run started **automatically** when the version was created (job parameters `model_name`, `model_version`);
- `evaluation`: candidate vs `@champion` on `trips_scoring` (out-of-time); tags `eval_rmse`, `eval_decision` on the version;
- `approval_check`: auto-approved in dev (tag `approval_check = Approved`);
- `deployment`: `@champion` moved, endpoint updated; `batch_inference` triggered;
- prod model `workspace.taxi_prod.taxi_fare_model`: the run that **stopped at approval_check** and the **Approve** button you used in prep.
**Say:** "Promotion is data, not a person editing YAML. A version that doesn't beat the champion never gets deployed,
and in prod a human has to approve it."

### Step 8: Serving + monitoring (6 min)
**Do:** Serving → `taxi-fare-dev` → served version = `@champion`. Query it live:
```bash
DATABRICKS_CONFIG_PROFILE=dev-sp python scripts/smoke_test_endpoint.py --endpoint taxi-fare-dev --expected-version <champion>
```
(If it was idle, the first call wakes it up from zero, so narrate the retries.)
Then in the SQL editor:
```sql
SELECT model_version, measured_at, rows, rmse, mae, psi_trip_distance, psi_pickup_hour
FROM workspace.taxi_dev.taxi_model_metrics ORDER BY measured_at DESC;

SELECT model_version, COUNT(*) n, ROUND(AVG(ABS(prediction - fare_amount)), 2) mae
FROM workspace.taxi_dev.taxi_predictions GROUP BY model_version;
```
**Show:** predictions for 3 trips (the unknown zip `99999` still gets a price), the metrics history, and the
Quality tab of `taxi_predictions` if the monitor exists.
**Say:** "Two monitoring layers: our own metrics table, which always works and is cheap, plus Databricks Data Quality
Monitoring. Drift can start retraining (`retrain_on_drift`), but the new model still goes through evaluation and approval."

### Step 9: CI/CD: the PR from step 2 (6 min)
**Do:** GitHub → Actions → `ci` run for the PR.
**Show:** `checks` (ruff, pytest, terraform validate) → `dev / deploy`: validate → deploy → train → wait for the deployment job → smoke test.
In Databricks, the job's *Run as* is `sp-taxi-mlops-dev`, not you.
Merge the PR → `cd`: dev again → **prod waits for review** → click *Review deployments → Approve*.
**Say:** "Nobody deploys prod from a laptop. Code gate in GitHub, model gate in Unity Catalog. Prod training uses prod data,
and the new prod version waits for approval in Catalog Explorer."
(Prod training takes minutes. Show the approval moment from your prep run and let the live one finish in the background.)

### Step 10: Rollback (2 min)
**Do:** GitHub → Actions → `rollback` → Run workflow → target `dev`, version `1`.
**Show:** `@champion` → v1, endpoint serving v1, smoke test green.
**Say:** "Rollback means moving the alias and rolling the endpoint. No retraining, about a minute."

### Step 11 (optional, 3 min): a failure on purpose
**Do:** in a branch, change `sane_avg_fare` in `src/pipelines/features.py` to `zip_avg_fare BETWEEN 2.5 AND 5`, push, open a PR.
**Show:** CI → `bundle run train` fails in `refresh_features`; the expectation failure in the pipeline event log; no new model version.
**Say:** "Bad data stops the line before a model is ever trained."

### Wrap-up (1 min)
Recap the chain: Terraform (platform) → Bundle (workload) → Lakeflow pipeline (tested features) → Lakeflow Job
(MLflow 3 + Feature Store) → deployment job (`@champion`, approval) → Model Serving → monitoring → GitHub CI/CD.

---

## After the demo: teardown
```bash
databricks bundle destroy -t dev  --profile dev-sp  --auto-approve
databricks bundle destroy -t prod --profile prod-sp --auto-approve
databricks serving-endpoints delete taxi-fare-dev  --profile free
databricks serving-endpoints delete taxi-fare-prod --profile free
cd infra/platform && terraform destroy
```
Then revoke the PAT (Settings → Developer → Access tokens).

## Likely audience questions
- **Why not separate workspaces?** That would be best practice. Free Edition allows one workspace, so isolation here
  is by identity + schema + folder. The bundle targets would point at different hosts with no code change.
- **Why Terraform *and* bundles?** Terraform owns long-lived platform objects that an admin sets up once.
  Bundles own the workload, which changes with every commit.
- **Why is the endpoint not managed in the bundle?** The served version changes per model approval, not per code
  deploy. If the bundle owned it, the next `bundle deploy` would revert the version.
- **Why not `fe.log_model` with automatic feature lookup?** Real-time lookup needs an online store (Lakebase).
  Free Edition doesn't support it, and it isn't needed for a static feature table this small.

## Sources
- [From Laptop Prototype to Scheduled Job (Oct 2026)](https://hovinh.github.io/blog/2026-10-10-databricks-ml-setup/): Free Edition, `samples.nyctaxi.trips`, schema-per-env, serverless jobs, gotchas
- [kkarki7120/databricks-mlops-platform](https://github.com/kkarki7120/databricks-mlops-platform): champion/challenger, bundle targets via GitHub Actions
- [DAB → Declarative Automation Bundles](https://community.databricks.com/t5/mvp-articles/databricks-asset-bundles-is-now-declarative-automation-bundles/td-p/151594)
- [Aliases in bundle config not applied (community)](https://community.databricks.com/t5/data-engineering/dab-registered-model-aliases-not-being-applied-to-unity-catalog/m-p/140509/highlight/true)
- Fact checks only: [MLflow 3 deployment jobs](https://docs.databricks.com/aws/en/mlflow/deployment-job), [Free Edition limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
