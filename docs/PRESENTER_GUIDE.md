| Databricks workspace | https://dbc-b7edd512-cbb9.cloud.databricks.com |
| GitHub repo | https://github.com/LukaszSawaData/databricks-taxi-mlops |
| GitHub Actions | https://github.com/LukaszSawaData/databricks-taxi-mlops/actions |
| Local folder | `~/learning/MLops_azure/Databricks` |



1. Pokazemy databricks usluge: 
   - katalogi
   - modele
   - feature
   - experimenty 
   - joby
   - models
   - serving



2. Przechodzimy do vs code: 

   - terraform
   - bundles  wraz z fodlerem resources.
   - biblioteki
   - oraz pipeline cicd



3. przechodzimy do githuba: 

      - omawiamy cicd 
      - omawiamy cd
      - Krok po kroku co sie odbywa












15. uruchomic moze cicd 
      

















**Say:** "Terraform builds the platform. The bundle builds the workload. The pipeline tests the data.
MLflow tracks every model. The deployment job promotes only better models, with a human gate in prod.
Serving makes it an API, monitoring watches it, and GitHub automates all of it."
Optionally show **Serving** → `taxi-fare-prod`, now Ready.
**Start here (entry point = the code on your laptop):**
1. Create a branch and change the code.
2. Push the branch and open a pull request.
3. GitHub starts `ci`: lint + tests.
4. `ci` deploys the code to **dev** (bundle).
5. Dev pipeline: builds the data and features.
6. Dev training: a new model version.
7. Dev deployment job: check → auto-approve → `@champion` → endpoint `taxi-fare-dev`.
8. `ci` tests the endpoint. The PR is green.
9. Merge the PR.
10. GitHub starts `cd`: dev again (steps 4–8).
11. `cd` waits. **You click Approve** in GitHub (Review deployments).
12. `cd` deploys the code to **prod**.
13. Prod pipeline + training on prod data: a new prod model version.
14. Prod deployment job: check → **stops, waits for approval**.
15. **You click Approve** in Databricks (Catalog → `taxi_prod.taxi_fare_model` → version).
16. Prod: `@champion` → endpoint **`taxi-fare-prod` is published**.
17. Batch inference + monitoring run.



Model used: 
1. We predict the **price of a NYC taxi trip** (`fare_amount`) from distance, pickup hour, weekday and pickup zip code.
2. **Source data:** `samples.nyctaxi.trips`, the built-in dataset 

**Say:** "Two different people can own two different gates: an engineer approves code, a model owner approves the model.
Creating the prod endpoint takes about 15 minutes, so we'll check it at the end."




1. show workspace
2. Show 2 schemas: workspace.taxi_dev, workspace.taxi_prod
3. Jobs list i rodzaje: 

      1 Lakeflow pipeline: `taxi-features-<env>`
            - `trips_raw`: a sample of the source (dev: 3,000 rows, prod: all rows)
            - `trips_clean`: the data tests run here; bad rows are dropped
            - `trips_train`: trips before 2016-02-15, used for training
            - `trips_scoring`: trips from 2016-02-15, the "new" data used for evaluation and scoring
            - `pickup_zip_features`: the Feature Store table (key `pickup_zip`), computed from `trips_train`
            https://dbc-b7edd512-cbb9.cloud.databricks.com/pipelines/c8dc1740-b712-452e-a4c9-359124914a71/updates/d1655c9a-1d2f-4e27-b618-f8d38164ba18?w=7474659274314955&o=7474659274314955



            https://dbc-b7edd512-cbb9.cloud.databricks.com/pipelines/ae08b94c-e4db-4d5a-840b-bae49efcd0f6?w=7474659274314955
               Pokazac joba z featureami + w jaki sposób mozna historyziwać dane cechy.


            Pokazac to ze jest Expectations w jobach features.

            | 7 | Feature Store table | **Catalog** → `workspace` → `taxi_dev` → `pickup_zip_features` (see **primary key** `pickup_zip`) | – |  Do czego to sluzy




      3 jobs: `taxi-train-<env>`, `taxi-batch-inference-<env>`
         | Training data | 3,000 sampled trips | all trips (~22k) |
            **Job `taxi-train-<env>`:**
               - task `refresh_features` runs the pipeline
               - task `train` trains the model and registers a new version in `workspace.taxi_<env>.taxi_fare_model`

               | 8 | Train job (dev) | **Jobs & Pipelines** → `taxi-train-dev` → **Runs** | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/jobs/219390601285598?w=7474659274314955) |
               | 9 | Train job (prod) | `taxi-train-prod` | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/jobs/935896757180582?w=7474659274314955) |



               train joby a ffeatures store ????





      `taxi-deployment-<env>`, 

         Start when Every training run saves the model again with a new number: v1, v2, v3… The old versions are kept too. A "new version" is simply the model that was just trained.

         `taxi-deployment-<env>`:**
            - `evaluation`: compares the new version with `@champion` on `trips_scoring`; it stops if the new version is worse
            - `approval_check`: automatic in dev, needs a human in prod
            - `deployment`: points `@champion` at the new version and updates the endpoint `taxi-fare-<env>`
            - `batch_inference`: scores `trips_scoring` and writes the monitoring tables




      1 MLflow experiment and 1 registered model `taxi_fare_model`

4. How bundles works
5.  Github repository with CICD
 **GitHub Actions** (`.github/workflows/`):
   - `ci.yml`: on a pull request, runs tests, then deploys and runs everything on dev
   - `cd.yml`: on a push to `main`, deploys dev, waits for human approval, then deploys prod
   - `rollback.yml`: started manually, serves an older model version again

**"Deploy code, not models":** prod is **not** a copy of dev's model. The same code is deployed to prod, and prod trains its own model on prod data.



MODELS: 

1. dev: https://dbc-b7edd512-cbb9.cloud.databricks.com/explore/data/models/workspace/taxi_dev/taxi_fare_model?o=7474659274314955&activeTab=overview&sortingColumn=name&sortingOrder=asc
2. prd: 
https://dbc-b7edd512-cbb9.cloud.databricks.com/explore/data/models/workspace/taxi_prod/taxi_fare_model?o=7474659274314955

@champion - co to jest . na devie z auotmatu na prodzie trzeba approva ??


 Endpoint - trrzeba zrobic appova !!!? zeb

Features - jak historie pokazac ????




ROLLBACK: 

### Step 11: Rollback in one click (2 min)
**Click:** **Actions** → `rollback` → **Run workflow** → target `dev`, version `2` → **Run workflow**.
**Show:** after about a minute, `@champion` = v2, the endpoint serves v2, the smoke test is green.
**Say:** "If something goes wrong, we move a label back. No retraining, about one minute."



REJESTROWANIE MODELU ??????

| 10 | MLflow experiment (dev) | **Experiments** → `taxi-fare-experiment-dev` → newest run | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/ml/experiments/3879132776008438?w=7474659274314955) |
| 11 | MLflow experiment (prod) | **Experiments** → `taxi-fare-experiment-prod` | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/ml/experiments/1726300016789788?w=7474659274314955) |


| 12 | Model (dev) | **Catalog** → `workspace` → `taxi_dev` → **Models** → `taxi_fare_model` | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/explore/data/models/workspace/taxi_dev/taxi_fare_model?w=7474659274314955) |
| 13 | Model (prod) | same, `taxi_prod` | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/explore/data/models/workspace/taxi_prod/taxi_fare_model?w=7474659274314955) |





| 14 | Deployment job (dev) | `taxi-deployment-dev` → **Runs** | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/jobs/110536595814426?w=7474659274314955) |
| 15 | Deployment job (prod), waiting for approval | `taxi-deployment-prod` → **Runs** | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/jobs/420972634839066?w=7474659274314955) |








| 16 | Endpoint (dev) | **Serving** → `taxi-fare-dev` | – |




| 17 | Batch inference job (dev) | `taxi-batch-inference-dev` | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/jobs/413380434300039?w=7474659274314955) |



| 18 | Predictions + metrics tables | **Catalog** → `taxi_dev` → `taxi_predictions`, `taxi_model_metrics` | – |







| 19 | Data quality monitor | **Catalog** → `taxi_dev` → `taxi_predictions` → tab **Quality** | – |

GITHUB:
## Part 4: GitHub: how the process works and how to start it

### 4.1 The four workflow files

| File | Starts when | What it does |
|---|---|---|
| `ci.yml` | A **pull request** to `main` is opened or updated | 1) `checks`: lint (ruff), unit tests (pytest), terraform fmt/validate. 2) `dev`: deploy the PR's code to dev and run everything |
| `cd.yml` | A **push to `main`** (e.g. merging a PR), or manually | 1) `dev`: same as above. 2) `prod`: **waits for a human**, then deploys to prod and trains on prod data |
| `_deploy.yml` | Never by itself: `ci` and `cd` call it | The shared deploy steps (below) |
| `rollback.yml` | **Manually** (button) | Points `@champion` back to an older version and updates the endpoint |

### 4.2 What `_deploy.yml` does, step by step (what you see in the run log)

| Step in GitHub | What happens in Databricks | Typical time |
|---|---|---|
| Set up job, checkout, setup-python, setup-cli | Prepares a fresh Linux machine with the Databricks CLI 1.21 | 1 min |
| Log in | Uses environment secrets `DATABRICKS_CLIENT_ID/SECRET`, so GitHub **is** the robot of that environment | – |
| **Validate bundle** | Checks the YAML against the workspace | 10 s |
| **Deploy bundle** | Uploads `src/`, creates or updates pipeline, jobs, experiment, model | 30 s |
| **Train on <env> data** | Runs job `taxi-train-<env>`: pipeline refresh, then training. A new model version appears | 3 min (up to 45 min if Free Edition queues it) |
| **Wait for MLflow deployment job** (dev only) | The new version auto-starts `taxi-deployment-<env>`, and GitHub waits until it ends | 5–15 min |
| **Smoke test serving endpoint** (dev only) | Sends 3 trips to `taxi-fare-dev`, checks the version and that prices make sense | 1 min |
| **Next step** (prod only) | Writes "approve the model in Catalog Explorer" into the run summary | – |

**Why doesn't prod wait for the deployment job?** The prod model needs a human in Databricks, and a GitHub machine shouldn't sit idle waiting for that.

### 4.3 The two gates in prod

1. **Code gate (GitHub):** the `prod` job shows **"Waiting for review"**. Click **Review deployments** → tick `prod` → **Approve and deploy**.
2. **Model gate (Databricks):** after prod trains, the new version waits. You approve it in Catalog Explorer (Part 5, step 9).

### 4.4 How to start each process

**A) The normal way: a pull request (starts `ci`)**
```bash
cd ~/learning/MLops_azure/Databricks
git switch -c demo/my-change
# change something small, e.g. the comment in resources/ml.yml
git commit -am "demo: my change"
git push -u origin demo/my-change
gh pr create --fill            # or: GitHub shows a yellow "Compare & pull request" button → click it
```
Then: repo → **Pull requests** → your PR → **Checks** tab shows `ci` → `checks` and `dev / deploy`.

**B) Ship to prod: merge the PR (starts `cd`)**
PR page → **Merge pull request** → **Confirm merge**. Then **Actions** → `cd` → the newest run → wait until
`prod / deploy` shows **Review deployments** → **Approve and deploy**.

**C) Run `cd` without a code change**
**Actions** → `cd` (left list) → **Run workflow** (right) → branch `main` → **Run workflow**.

**D) Rollback**
**Actions** → `rollback` → **Run workflow** → target `dev` (or `prod`) → version (e.g. `2`) → **Run workflow**.
⚠️ In dev, never use version 1: it's the broken model from before the serving fix.






## Part 5: The live presentation script (about 40 min)



### Step 2: Start a live change, so it runs while we talk (2 min)
**Click:** terminal, then commands **4.4 A**.
**Show:** the PR page with `ci` starting.
**Say:** "This change will test itself on dev while I show you the parts. We'll come back to it."

### Step 3: Layer 1, the platform in Terraform (4 min)
**Click:** `infra/platform/identities.tf` → `unity_catalog.tf` → `github.tf`. Then in Databricks:
**Settings → Service principals** (2 robots) → **Catalog → workspace → taxi_dev → Permissions**.
**Show:** `sp-taxi-mlops-dev` has ALL PRIVILEGES on `taxi_dev` and nothing on `taxi_prod`.
GitHub → **Settings → Environments → prod**: required reviewer, branch `main` only.
**Say:** "An admin creates the platform once, as code. Dev's robot can't even read prod's data.
GitHub gets each robot's credentials only inside the matching environment."

### Step 4: Layer 2, one bundle and two deployments (3 min)
**Click:** `databricks.yml`, scroll to `targets:`.
**Show:** `dev` has `schema: taxi_dev`, `max_rows: 3000`, `auto_approve: "true"`. `prod` has `taxi_prod`, `max_rows: 0` (everything), `auto_approve: "false"`.
**Say:** "Same code, different settings per environment. Prod trains on prod data: we deploy code, not models."

### Step 5: Data and tests, the Lakeflow pipeline (5 min)
**Click:** **Jobs & Pipelines** → `taxi-features-dev` → newest update.
**Show:** the graph `trips_raw → trips_clean → trips_train / trips_scoring → pickup_zip_features`.
Click `trips_clean` → **Data quality** (rows dropped by `valid_fare`, `valid_distance`, `has_zip`).
Then open `src/pipelines/features.py` and point at the `@dp.expect_or_drop` and `@dp.expect_or_fail` lines.
Then **Catalog** → `taxi_dev` → `pickup_zip_features` → primary key `pickup_zip`.
**Say:** "Data tests live inside the pipeline. Bad rows are dropped and counted. If the features are broken, the pipeline stops,
so nobody trains on bad data. The zip-code table with a primary key is our Feature Store table."

### Step 6: Training, Feature Store and MLflow tracking (5 min)
**Click:** `taxi-train-dev` → newest run (two tasks: `refresh_features` → `train`).
Then **Experiments** → `taxi-fare-experiment-dev` → newest run.
**Show:** parameters (rows), the input dataset `training_set`, tag `git_sha` (the exact commit), and the logged model with `holdout_rmse`.
Then **Catalog** → `taxi_dev` → `taxi_fare_model` → versions 1–3, and on a version page the metrics plus tag `git_sha`.
**Say:** "For any model version we know the code commit, the data, the metrics and who trained it: a robot, not a person.
Free Edition has no online feature store, so the small zip table is packed inside the model.
The API and batch scoring use exactly the same artifact."

### Step 7: Automatic promotion, the deployment job and `@champion` (5 min)

**Click:** model `taxi_dev.taxi_fare_model` → alias **`@champion` = v3** → link 14 (`taxi-deployment-dev`) → newest run.
**Show:** the run was **started automatically** by the new version (parameters `model_name`, `model_version` = 3).
Four green tasks: `evaluation` → `approval_check` → `deployment` → `batch_inference`.
On version 3, the tags `eval_rmse`, `eval_decision` and `approval_check = Approved`.
**Say:** "Nobody clicked Deploy. The new version had to beat the current champion on new data it has never seen.
In dev, approval is automatic. In prod, a person approves, and you'll see that in a minute."

### Step 8: The live API and monitoring (5 min)
**Click:** **Serving** → `taxi-fare-dev`: state Ready, served version 3, scale to zero on.
(If the PR from step 2 has already finished, dev serves **v4**. That's the CI result: say so and use 4 below.)
Click **Use** / **Query endpoint**, paste this, then **Send request**:
```json
{"dataframe_records": [
  {"trip_distance": 1.2, "pickup_hour": 8,  "pickup_dow": 2, "pickup_zip": 10001},
  {"trip_distance": 8.5, "pickup_hour": 18, "pickup_dow": 6, "pickup_zip": 10019},
  {"trip_distance": 3.0, "pickup_hour": 1,  "pickup_dow": 7, "pickup_zip": 99999}
]}
```
Expected answer is about `[8.2, 29.5, 11.3]` dollars. The unknown zip 99999 still gets a sensible price.
Terminal alternative:
`DATABRICKS_CONFIG_PROFILE=dev-sp python scripts/smoke_test_endpoint.py --endpoint taxi-fare-dev --expected-version 3`

Then in the **SQL Editor**:
```sql
SELECT model_version, measured_at, rows, ROUND(rmse,2) rmse, ROUND(r2,3) r2,
       ROUND(psi_trip_distance,3) psi_distance, ROUND(psi_pickup_hour,3) psi_hour
FROM workspace.taxi_dev.taxi_model_metrics ORDER BY measured_at DESC;
```
Then **Catalog** → `taxi_dev` → `taxi_predictions` → tab **Quality** (the Databricks data quality monitor).
**Say:** "Every new champion scores fresh trips. We store quality (RMSE, R²) and drift (PSI; above 0.2 means the data changed).
Drift can start retraining automatically, but the new model still has to pass evaluation and approval."






