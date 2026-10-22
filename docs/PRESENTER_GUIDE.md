| Databricks workspace | https://dbc-b7edd512-cbb9.cloud.databricks.com |
| GitHub repo | https://github.com/LukaszSawaData/databricks-taxi-mlops |
| GitHub Actions | https://github.com/LukaszSawaData/databricks-taxi-mlops/actions |
| Local folder | `~/learning/MLops_azure/Databricks` |



1. Pokazemy databricks usluge: 
   - katalogi
            workspace.taxi_dev, workspace.taxi_prod
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
   - MLflow tracks every model



3. przechodzimy do githuba: 

      - omawiamy cicd 
      - omawiamy cd
      - Krok po kroku co sie odbywa
      - Two different people can own two different gates: an engineer approves code, a model owner approves the model.
Creating the prod endpoint takes about 15 minutes, so we'll check it at the end."


4. Joby : 
      TRAIN: 
               1. Refresh_features 

            ETL + Feature Store
            https://dbc-b7edd512-cbb9.cloud.databricks.com/jobs/219390601285598/runs/819898332620342?w=7474659274314955&o=7474659274314955

            https://dbc-b7edd512-cbb9.cloud.databricks.com/explore/data/workspace/taxi_dev/pickup_zip_features?w=7474659274314955&o=7474659274314955&activeTab=sample

            Pokazac to ze jest Expectations w jobach features


            train: 
               https://dbc-b7edd512-cbb9.cloud.databricks.com/ml/experiments/3879132776008438/runs/5183f528c12d4ed0b2b5cb2ee38947c3?o=7474659274314955
               https://dbc-b7edd512-cbb9.cloud.databricks.com/ml/experiments/3879132776008438/runs/8ea31042cf9e4c108c8f2a7c26d05d54?o=7474659274314955
               
               By experimetns: 

               W Databricks experiments to podstawowe jednostki organizacyjne w MLflow służące do śledzenia i zarządzania przebiegami (ang. runs) uczenia maszynowego oraz modeli. Pozwalają logować parametry, metryki, kod oraz pliki wynikowe (artefakty), ułatwiając porównywanie różnych wersji model
               • Śledzenie (Tracking): Zapisuje hiperparametry, wyniki metryk (np. accuracy, loss) oraz wersje kodu dla każdego treningu.
               • Porównywanie: Umożliwia zestawianie wielu przebiegów obok siebie w interfejsie graficznym w celu wyboru najlepszego modelu.
      DEPLOYMENT: 


               Start when Every training run saves the model again with a new number: v1, v2, v3… The old versions are kept too. A "new version" is simply the model that was just trained.
            - `evaluation`: compares the new version with `@champion` on `trips_scoring`; it stops if the new version is worse
            - `approval_check`: automatic in dev, needs a human in prod
            - `deployment`: points `@champion` at the new version and updates the endpoint `taxi-fare-<env>`
            - `batch_inference`: scores `trips_scoring` and writes the monitoring tables - GDZIE ZNALEZC TE TEBELE !!!Batch inference job

               @champion -> v4
               updating endpoint taxi-fare-dev -> workspace.taxi_dev.taxi_fare_model v4
               The deployment job promotes only better models, with a human gate in prod


               mODEL REGISTRY
               Twój zarejestrowany model nie żyje już w odizolowanym rejestrze, lecz jest pełnoprawnym obiektem w bazie danych identyfikowanym ścieżką:
               catalog.schema.model_name
                     pokaza prod jako werstwa 1 oraz dev jako registry z testam numer 4.

5. Featery: 
   - gdzie sa utrzymywane
   ROLLBACK: 

            ### Step 11: Rollback in one click (2 min)
            **Click:** **Actions** → `rollback` → **Run workflow** → target `dev`, version `2` → **Run workflow**.
            **Show:** after about a minute, `@champion` = v2, the endpoint serves v2, the smoke test is green.
            **Say:** "If something goes wrong, we move a label back. No retraining, about one minute."


15. uruchomic moze cicd 
      

17. serving
Serving makes it an API
Optionally show **Serving** → `taxi-fare-prod`, now Ready.
Endpoint
https://dbc-b7edd512-cbb9.cloud.databricks.com/ml/endpoints/taxi-fare-dev/events?o=7474659274314955
https://dbc-b7edd512-cbb9.cloud.databricks.com/ml/endpoints/taxi-fare-prod/overview?o=7474659274314955


query endpoint: 

{"dataframe_records": [
  {"trip_distance": 1.2, "pickup_hour": 8,  "pickup_dow": 2, "pickup_zip": 10001},
  {"trip_distance": 8.5, "pickup_hour": 18, "pickup_dow": 6, "pickup_zip": 10019},
  {"trip_distance": 3.0, "pickup_hour": 1,  "pickup_dow": 7, "pickup_zip": 99999}
]}




18. 
MODELS: 

1. dev: https://dbc-b7edd512-cbb9.cloud.databricks.com/explore/data/models/workspace/taxi_dev/taxi_fare_model?o=7474659274314955&activeTab=overview&sortingColumn=name&sortingOrder=asc
2. prd: 
https://dbc-b7edd512-cbb9.cloud.databricks.com/explore/data/models/workspace/taxi_prod/taxi_fare_model?o=7474659274314955







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







@champion - co to jest . na devie z auotmatu na prodzie trzeba approva ??


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



