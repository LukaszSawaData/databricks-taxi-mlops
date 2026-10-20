terraform {
  required_version = ">= 1.9"
  required_providers {
    databricks = { source = "databricks/databricks", version = "~> 1.138" }
    github     = { source = "integrations/github", version = "~> 6.13" }
  }
  # Local state on purpose: run once by the workspace admin. It contains SP secrets -> never commit it.
}

# Auth as you (workspace admin): profile `free` from `databricks configure --profile free` (PAT)
# or `databricks auth login --profile free` (OAuth). The PAT is only for this local bootstrap.
provider "databricks" {
  host    = var.databricks_host
  profile = var.databricks_profile
}

# Auth: GITHUB_TOKEN env var (fine-grained PAT: Administration, Environments, Secrets, Variables = RW).
provider "github" {
  owner = var.github_owner
}
