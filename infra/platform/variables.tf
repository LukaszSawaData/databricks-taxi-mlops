variable "databricks_host" {
  type    = string
  default = "https://dbc-b7edd512-cbb9.cloud.databricks.com"
}

variable "databricks_profile" {
  type        = string
  default     = "free"
  description = "~/.databrickscfg profile (PAT or OAuth). Set to null to use DATABRICKS_TOKEN env instead."
}

variable "catalog" {
  type        = string
  default     = "workspace"
  description = "Free Edition default catalog. Environments are isolated by schema inside it."
}

variable "environments" {
  type = map(object({ schema = string }))
  default = {
    dev  = { schema = "taxi_dev" }
    prod = { schema = "taxi_prod" }
  }
}

variable "project" {
  type    = string
  default = "taxi-mlops"
}

variable "github_owner" {
  type = string
}

variable "github_repo" {
  type = string
}

variable "prod_required_reviewers" {
  type        = bool
  default     = true
  description = "Required reviewers on the `prod` environment (private repos need GitHub Pro/Team)."
}

variable "create_sp_secrets" {
  type        = bool
  default     = true
  description = "Create OAuth secrets for the SPs. Set false if your workspace rejects it and create them in the UI."
}

variable "manual_sp_secrets" {
  type        = map(string)
  default     = {}
  sensitive   = true
  description = "Used when create_sp_secrets = false: { dev = \"dose...\", prod = \"dose...\" }."
}
