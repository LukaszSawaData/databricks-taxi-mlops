# Presenter guide: Databricks MLOps on Free Edition (NYC Taxi)

One document with everything you need: what was built, what already happened, where every object
lives, how the GitHub process works and how to start it, and a step-by-step script for presenting.

**Read once, top to bottom:** parts 1–4 teach you the system, part 5 is the live script, and parts 6–8 are backup material.

| | |
|---|---|
| Databricks workspace | https://dbc-b7edd512-cbb9.cloud.databricks.com |
| GitHub repo | https://github.com/LukaszSawaData/databricks-taxi-mlops |
| GitHub Actions | https://github.com/LukaszSawaData/databricks-taxi-mlops/actions |
| Local folder | `~/learning/MLops_azure/Databricks` |

---

## Part 1: The idea in plain language

We predict the **price of a NYC taxi trip** (`fare_amount`) from distance, pickup hour, weekday and pickup zip code.
The model is deliberately simple. **The point of the project is the factory around the model (MLOps)**, not the model itself.

The factory answers five questions every company has:

1. **Is the data good?** A pipeline tests the data before anyone trains on it.
2. **Can we trace every model?** Each model version records which code, which data and which metrics produced it.
3. **Who decides what goes to production?** Nobody edits production by hand. Code needs approval in GitHub, and a model needs approval in Databricks.
4. **Can apps use the model?** A REST endpoint answers price requests in real time.
5. **Is the model still good next week?** Monitoring measures quality and drift, and can start retraining.

### Words you will use (and what to say about them)

| Word | What it is | One sentence for the audience |
|---|---|---|
| **Workspace** | Our Databricks environment (Free Edition) | "One workspace, but dev and prod can't touch each other." |
| **Unity Catalog (UC)** | Databricks' catalog of tables and models, with permissions | "Every table and model has an owner and permissions, like files on a server." |
| **Schema** | A folder inside the catalog: `workspace.taxi_dev`, `workspace.taxi_prod` | "Dev's data and models live in `taxi_dev`, prod's in `taxi_prod`." |
| **Service principal (SP)** | A robot user: `sp-taxi-mlops-dev`, `sp-taxi-mlops-prod` | "Robots deploy and run everything, not people. The dev robot has no access to prod." |
| **Terraform** | Code that creates infrastructure | "The platform (robots, schemas, permissions, GitHub settings) is written as code." |
| **Bundle (DAB)** | *Declarative Automation Bundles* (formerly *Databricks Asset Bundles*): YAML describing jobs, pipelines and models | "One description and two deployments: dev and prod." |
| **Lakeflow pipeline** | A declarative data pipeline (tables defined in Python) | "It builds clean tables and features, and tests the data on the way." |
| **Expectation** | A data rule inside the pipeline, e.g. `fare BETWEEN 2.5 AND 200` | "These are our data tests: bad rows are dropped and counted." |
| **Feature Store table** | A table with a primary key, used to look features up | "Zip-code statistics are computed once and reused for training." |
| **Lakeflow Job** | A scheduled or triggered workflow of tasks | "Training is a job and runs the same way every time." |
| **MLflow** | Experiment tracking + model registry | "Every training run is recorded: parameters, metrics, data, code version." |
| **Model version** | A numbered copy of the model in UC (v1, v2, v3...) | "Each training creates a new version. Old ones stay for rollback." |
| **Alias `@champion`** | A label pointing at one version | "Production always uses whatever `@champion` points to." |
| **Deployment job** | MLflow 3 feature: a job that starts automatically when a new version appears | "A new model must pass evaluation and approval before it's deployed." |
| **Serving endpoint** | REST API hosting the model | "Any app can send a trip and get a price back." |
| **GitHub Actions** | Automation in GitHub (CI/CD) | "Every change is tested automatically, and prod needs a human click." |

---

## Part 2: What was built, and what already happened

### 2.1 Architecture (three layers)

```
 GitHub (code + automation)
   PR       ──► ci.yml  : tests, then deploy+run on DEV
   main     ──► cd.yml  : DEV again ──► [human approval] ──► PROD
   manual   ──► rollback.yml
        │  each environment logs in as its own robot (SP)
        ▼
 Databricks Free Edition (one workspace)
   Layer 1  Terraform  : robots, schemas, permissions, GitHub settings      (created once)
   Layer 2  Bundle     : pipeline + 3 jobs + experiment + model per env     (every deploy)
   Layer 3  Runtime    : data ► features ► model ► approval ► endpoint ► monitoring
```

### 2.2 The flow of one model (say this as a story)

```
samples.nyctaxi.trips          (built-in dataset, ~22k trips, Jan–Feb 2016)
   │  Lakeflow pipeline "taxi-features-<env>"
   ▼
trips_raw ─► trips_clean ─► trips_train   (before 2016-02-15: for training)
             (data tests)  └► trips_scoring (from 2016-02-15: "new" trips)
                trips_train ─► pickup_zip_features   (Feature Store table, key = pickup_zip)
   │  job "taxi-train-<env>"  (task refresh_features ► task train)
   ▼
new model version in workspace.taxi_<env>.taxi_fare_model   (MLflow 3, UC)
   │  automatically starts job "taxi-deployment-<env>"
   ▼
evaluation ─► approval_check ─► deployment ─► batch_inference
 new vs         dev: automatic    @champion     score trips_scoring,
 @champion      prod: a human     + endpoint    monitoring tables
```

### 2.3 Dev vs prod: what is separated

| | dev | prod |
|---|---|---|
| Robot (deploys and runs) | `sp-taxi-mlops-dev` | `sp-taxi-mlops-prod` |
| Data + models | `workspace.taxi_dev` | `workspace.taxi_prod` |
| Training data | 3,000 sampled trips | all trips (~22k) |
| New model approval | automatic | a human in Databricks |
| Code approval | none | a human in GitHub |
| Endpoint | `taxi-fare-dev` | `taxi-fare-prod` |
| Files, experiment, dashboards | `/Workspace/Users/2b1aec99-…/` (dev robot's home) | `/Workspace/Users/b7a42199-…/` (prod robot's home) |

**Why robots' home folders?** In `/Workspace/Shared` every user gets edit rights that can't be removed.

**"Deploy code, not models":** prod is **not** a copy of dev's model. The same code is deployed to prod, and prod trains its own model on prod data.

### 2.4 What already happened (timeline)

| When | What | Result |
|---|---|---|
| 20 Oct, evening | Repo created, first push | `cd` run **failed**: GitHub secrets didn't exist yet. Expected. |
| 21 Oct | `terraform apply` in `infra/platform` | 2 robots + secrets, 2 schemas + permissions, GitHub `dev`/`prod` environments + secrets |
| 21 Oct | Repo made **public** | Needed on GitHub Free for environment secrets and approvals |
| 21 Oct | First dev runs from the laptop | Found and fixed 6 bugs (see Part 7). Dev v1 is a **broken** model from before a fix: never roll back to v1 |
| 21 Oct | Dev v2 deployed | Endpoint `taxi-fare-dev` READY, smoke test passed, monitoring tables written |
| 21 Oct, 04:53 UTC | Push to `main` → `cd` run [39546495717](https://github.com/LukaszSawaData/databricks-taxi-mlops/actions/runs/39546495717) | **dev job:** deploy → train (v3) → deployment job → smoke test ✅ |
| | | **prod job:** waited for approval → **you approved** → deploy → train on prod data ✅ |
| now | Prod model **v1** (RMSE 2.79, R² 0.92) | Prod deployment job **stopped at `approval_check`** on purpose. **Waiting for your approval (do it live, step 9 of Part 5).** |

### 2.5 Current state (what the audience will see)

| Object | dev | prod |
|---|---|---|
| Model versions | v1 (broken, ignore), v2, v3 | v1 |
| `@champion` | **v3** | none yet (waiting for approval) |
| Endpoint | `taxi-fare-dev` READY, serving v3 | not created yet (created when you approve) |
| Monitoring | `taxi_model_metrics`, `taxi_predictions` + data quality monitor | after approval |

---

## Part 3: Map of every object (where to click)

Short form: **W** = https://dbc-b7edd512-cbb9.cloud.databricks.com. In the left sidebar of Databricks you use
**Catalog**, **Jobs & Pipelines**, **Experiments**, **Serving** and **SQL Editor**.

### 3.1 Databricks objects

| # | Object | Click path | Direct link |
|---|---|---|---|
| 1 | Robots (SPs) | Avatar (top right) → **Settings** → Identity and access → **Service principals** | – |
| 2 | Schemas + permissions | **Catalog** → `workspace` → `taxi_dev` → tab **Permissions** | – |
| 3 | Source dataset | **Catalog** → `samples` → `nyctaxi` → `trips` → **Sample data** | – |
| 4 | Pipeline (dev) | **Jobs & Pipelines** → `taxi-features-dev` | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/pipelines/c8dc1740-b712-452e-a4c9-359124914a71?w=7474659274314955) |
| 5 | Pipeline (prod) | **Jobs & Pipelines** → `taxi-features-prod` | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/pipelines/ae08b94c-e4db-4d5a-840b-bae49efcd0f6?w=7474659274314955) |
| 6 | Data tests (expectations) | Pipeline → last update → click `trips_clean` in the graph → **Data quality** | – |
| 7 | Feature Store table | **Catalog** → `workspace` → `taxi_dev` → `pickup_zip_features` (see **primary key** `pickup_zip`) | – |
| 8 | Train job (dev) | **Jobs & Pipelines** → `taxi-train-dev` → **Runs** | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/jobs/219390601285598?w=7474659274314955) |
| 9 | Train job (prod) | `taxi-train-prod` | [open](https://dbc-b7edd512-cbb9.cloud.databricks.com/jobs/935896757180582?w=7474659274314955) |
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

### 3.2 GitHub objects

| # | Object | Click path |
|---|---|---|
| 20 | Environments (`dev`, `prod`) + approval rule | Repo → **Settings** → **Environments** → `prod` (required reviewer, only branch `main`) |
| 21 | Secrets per environment | Settings → Environments → `dev` → **Environment secrets**: `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET` |
| 22 | Workspace URL variable | Settings → **Secrets and variables** → **Actions** → tab **Variables** → `DATABRICKS_HOST` |
| 23 | Workflows | Repo → **Actions** → left list: `ci`, `cd`, `rollback` |
| 24 | The run that did everything | [cd run 39546495717](https://github.com/LukaszSawaData/databricks-taxi-mlops/actions/runs/39546495717) |
| 25 | Deployments history | Repo main page → right sidebar **Deployments** → `dev`, `prod` |

### 3.3 Code files worth opening (one line each)

| File | What to point at |
|---|---|
| `infra/platform/identities.tf` | Robots + their secrets |
| `infra/platform/unity_catalog.tf` | Schemas + "dev robot only on dev schema" |
| `infra/platform/github.tf` | GitHub environments, secrets, prod approval rule |
| `databricks.yml` | Targets `dev` / `prod`: different schema, data size, approval |
| `resources/jobs.yml` | The three jobs and their tasks |
| `src/pipelines/features.py` | `@dp.expect_or_drop` / `@dp.expect_or_fail` = data tests; the feature table |
| `src/jobs/train.py` | `FeatureLookup`, `mlflow.pyfunc.log_model`, link to the deployment job |
| `src/jobs/evaluate.py` | New model vs `@champion` |
| `src/jobs/approval.py` | "Not approved → stop" |
| `src/jobs/deploy.py` + `src/taxi_mlops/serving.py` | Move `@champion`, update endpoint |
| `src/jobs/batch_inference.py` | Predictions, metrics, drift, data quality monitor |
| `.github/workflows/*.yml` | CI/CD (Part 4) |

---

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

**E) From the laptop, without GitHub (same robot identity as CI)**
```bash
databricks bundle deploy    -t dev --profile dev-sp
databricks bundle run train -t dev --profile dev-sp
```
Profiles `dev-sp` / `prod-sp` are in `~/.databrickscfg`. Never deploy with your own profile `free`: you would
become the model owner, and the robot couldn't move `@champion` anymore.

---

## Part 5: The live presentation script (about 40 min)

Format per step: **Click** (what you do) → **Show** (what they see) → **Say** (the sentence to say).

### Before the audience arrives (15 min)

- [ ] Open these tabs in order: 1) GitHub repo, 2) GitHub Actions, 3) Databricks **Catalog**, 4) **Jobs & Pipelines**,
      5) **Experiments**, 6) **Serving**, 7) **SQL Editor** with the queries from step 8 pasted in, 8) a terminal in the repo folder.
- [ ] **Serving** → `taxi-fare-dev` is **Ready**. If it scaled to zero, send one test query (step 8) to wake it up.
- [ ] Prod deployment run is **waiting** at `approval_check` (link 15 in Part 3). Keep it for step 9.
- [ ] Don't start new training runs on the presentation day: Free Edition has daily limits and can queue runs for 45 minutes.

### Step 1: The problem (2 min)
**Click:** GitHub repo → `README.md` → architecture diagram.
**Say:** "A model on a laptop isn't a product. Today I'll show the factory around a model: tested data,
traceable training, automatic but controlled deployment, a live API and monitoring. All of it as code,
in one Databricks Free Edition workspace with dev and prod fully separated."

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

### Step 9: Production with two human gates (the highlight, 6 min)
**Click:** GitHub → **Actions** → `cd` → [run 39546495717](https://github.com/LukaszSawaData/databricks-taxi-mlops/actions/runs/39546495717).
**Show:** `dev / deploy` ✅, then `prod / deploy` with the approval you gave (**gate 1, code**). Open `prod / deploy`
and walk through the steps: validate, deploy, **Train on prod data**.
Now **gate 2, live**: link 15 → `taxi-deployment-prod` → the run for version 1 → `approval_check` is red:
*"v1 is not approved"*. Then open model `taxi_prod.taxi_fare_model` → **version 1**:
**Show:** metrics: RMSE 2.79, R² 0.92 (better than dev, because it trained on all prod data).
**Click:** **Approve** in the deployment-job section of the version page.
*Fallback if there's no button:* version page → **Tags** → add `approval_check` = `Approved`, then go back to the run → **Repair run**.
**Show:** the run continues: `approval_check` ✅ → `deployment` (creates `taxi-fare-prod`) → `batch_inference`.
**Say:** "Two different people can own two different gates: an engineer approves code, a model owner approves the model.
Creating the prod endpoint takes about 15 minutes, so we'll check it at the end."

### Step 10: Back to the PR from step 2 (3 min)
**Click:** GitHub → **Pull requests** → your PR → **Checks**.
**Show:** `checks` (lint, 12 unit tests, terraform) → `dev / deploy` (deploy, train, deployment job, smoke test).
Open the job in Databricks: **Run as** = `sp-taxi-mlops-dev`, not your name.
**Say:** "Every change proves itself on dev before anyone can merge it. Merging starts the prod process we just saw."
(If it's still running, say so. Free Edition queues jobs, and that's normal.)

### Step 11: Rollback in one click (2 min)
**Click:** **Actions** → `rollback` → **Run workflow** → target `dev`, version `2` → **Run workflow**.
**Show:** after about a minute, `@champion` = v2, the endpoint serves v2, the smoke test is green.
**Say:** "If something goes wrong, we move a label back. No retraining, about one minute."

### Step 12: Wrap-up (1 min)
**Say:** "Terraform builds the platform. The bundle builds the workload. The pipeline tests the data.
MLflow tracks every model. The deployment job promotes only better models, with a human gate in prod.
Serving makes it an API, monitoring watches it, and GitHub automates all of it."
Optionally show **Serving** → `taxi-fare-prod`, now Ready.

---

## Part 6: Questions the audience will ask

| Question | Answer |
|---|---|
| Why not two workspaces? | That's the best practice. Free Edition allows only one, so we separate with robots, schemas and folders. With two workspaces only `host` in `databricks.yml` changes. |
| Why Terraform **and** bundles? | Terraform creates things that rarely change (robots, permissions). Bundles change with every commit (jobs, code). |
| Why isn't the endpoint in the bundle? | The served version changes when a model is approved, not when code is deployed. If the bundle owned it, every deploy would reset the version. |
| Where is the Feature Store at serving time? | Real-time lookup needs an online store (Lakebase), which Free Edition doesn't have. The zip table is small, so it's packed inside the model. |
| What if the new model is worse? | `evaluation` fails, `@champion` doesn't move, and the endpoint keeps the old version. |
| What if the data is bad? | An `expect_or_fail` rule stops the pipeline, so training never starts. |
| Who can deploy to prod? | Only the prod robot, and only from `main`, after GitHub approval. The model then needs a second approval. |
| Can the prod robot see dev data? | No. Each robot has rights only on its own schema. |

---

## Part 7: Troubleshooting (all errors we really hit, and what they mean)

| Message you see | What it means | Fix |
|---|---|---|
| `GET https://api.github.com/users/%3Cyour-github-login%3E: 404` | `terraform.tfvars` still has the placeholder | Set `github_owner = "LukaszSawaData"` (done) |
| `no value assigned to required variable service_principal_id` | Old bundle config | Fixed: the robot IDs are now in `databricks.yml` per target |
| `UNRESOLVED_COLUMN ... tpep_pickup_datetime` in `trips_clean` | An expectation used a column name from before the rename | Fixed: it now uses `pickup_ts` |
| `EndpointCoreConfigInput.__init__() missing ... 'name'` | SDK requires the endpoint name in the config | Fixed in `serving.py` |
| `UPDATE_FAILED` + serving log `No module named 'pyspark'` | The model pickle contained Spark metadata from `toPandas()` | Fixed in `FarePredictor` (plain DataFrame) + a unit test. Dev v1 is still broken: don't serve it |
| `deployment job finished with FAILED` in prod at `approval_check` | **Not an error.** The prod model waits for a human | Approve it (step 9) |
| Deployment job run with empty `model_name` | Someone pressed **Run now** by hand | Don't. It starts itself after training |
| `An active update already exists for pipeline` | The pipeline is already running (only one at a time on Free Edition) | Wait for it to finish |
| `Your current $PATH prefers running CLI v0.18.0` | An old CLI is in `~/.local/bin` | `rm ~/.local/bin/databricks` |
| GitHub run stuck "Waiting for review" | Gate 1 is waiting for you | **Review deployments → Approve and deploy** |
| A run is slow (30–45 min) | Free Edition queues serverless compute | Normal. Run everything ahead of time |

**Where to look when something fails:**
1. GitHub run → the red step → expand the log.
2. Databricks → **Jobs & Pipelines** → the job → the run → the red task → **Output** (the error is at the bottom).
3. Pipeline failures: pipeline → update → **Event log** (red rows).
4. Endpoint failures: **Serving** → endpoint → **Logs** (*Service logs* / *Build logs*).

---

## Part 8: After the presentation

**Keep it** (costs nothing while idle, because endpoints scale to zero) or **remove everything**:
```bash
cd ~/learning/MLops_azure/Databricks
databricks bundle destroy -t dev  --profile dev-sp  --auto-approve
databricks bundle destroy -t prod --profile prod-sp --auto-approve
databricks serving-endpoints delete taxi-fare-dev  --profile free
databricks serving-endpoints delete taxi-fare-prod --profile free
cd infra/platform && GITHUB_TOKEN=$(gh auth token) terraform destroy
```
Then revoke your personal token: Databricks → avatar → **Settings → Developer → Access tokens**.
The robot secrets expire after 180 days. Run `terraform apply` again to rotate them; it also updates GitHub.

---

## Sources
- [From Laptop Prototype to Scheduled Job (Oct 2026)](https://hovinh.github.io/blog/2026-10-10-databricks-ml-setup/): Free Edition, `samples.nyctaxi.trips`, a schema per environment, serverless jobs
- [kkarki7120/databricks-mlops-platform](https://github.com/kkarki7120/databricks-mlops-platform): `@champion` aliases, bundle targets deployed by GitHub Actions
- [Asset Bundles renamed to Declarative Automation Bundles (community)](https://community.databricks.com/t5/mvp-articles/databricks-asset-bundles-is-now-declarative-automation-bundles/td-p/151594)
- [Aliases in bundle config not applied (community)](https://community.databricks.com/t5/data-engineering/dab-registered-model-aliases-not-being-applied-to-unity-catalog/m-p/140509/highlight/true): why `@champion` is set by the deployment job
- Vendor pages, used only to check facts: [MLflow 3 deployment jobs](https://docs.databricks.com/aws/en/mlflow/deployment-job), [Free Edition limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
