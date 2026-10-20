# One service principal per environment. CI deploys AS this SP and every job runs AS this SP,
# so dev can never write to prod objects and vice versa.
resource "databricks_service_principal" "env" {
  for_each         = var.environments
  display_name     = "sp-${var.project}-${each.key}"
  workspace_access = true
}

# OAuth M2M secret -> GitHub environment secret. Free Edition has no account console, so no
# GitHub OIDC federation policy; a client secret is the available option.
resource "databricks_service_principal_secret" "env" {
  for_each             = var.create_sp_secrets ? var.environments : {}
  service_principal_id = databricks_service_principal.env[each.key].id
  api                  = "workspace" # Free Edition: no account-level APIs
  lifetime             = "15552000s" # 180 days; re-apply to rotate
}

locals {
  sp_client_id = { for k, sp in databricks_service_principal.env : k => sp.application_id }
  sp_secret = {
    for k in keys(var.environments) : k => (
      var.create_sp_secrets ? databricks_service_principal_secret.env[k].secret : var.manual_sp_secrets[k]
    )
  }
}
