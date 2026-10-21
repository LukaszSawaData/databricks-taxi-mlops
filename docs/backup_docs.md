### 2.1 Architecture

1. **One Databricks workspace** (Free Edition) with two environments: `dev` and `prod`.
2. **Terraform** (`infra/platform/`), run once by an admin, creates:
   - 2 service principals: `sp-taxi-mlops-dev`, `sp-taxi-mlops-prod`
   - 2 schemas: `workspace.taxi_dev`, `workspace.taxi_prod`
   - permissions: each service principal can use only its own schema
   - GitHub environments `dev` and `prod` with the service principals' secrets