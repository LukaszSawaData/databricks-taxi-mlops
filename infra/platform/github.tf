data "github_user" "owner" {
  username = var.github_owner
}

resource "github_repository_environment" "env" {
  for_each    = var.environments
  repository  = var.github_repo
  environment = each.key

  dynamic "reviewers" {
    for_each = each.key == "prod" && var.prod_required_reviewers ? [1] : []
    content {
      users = [data.github_user.owner.id]
    }
  }
  prevent_self_review = false

  # prod deploys only from main.
  dynamic "deployment_branch_policy" {
    for_each = each.key == "prod" ? [1] : []
    content {
      protected_branches     = false
      custom_branch_policies = true
    }
  }
}

resource "github_repository_environment_deployment_policy" "prod_main" {
  repository     = var.github_repo
  environment    = github_repository_environment.env["prod"].environment
  branch_pattern = "main"
}

resource "github_actions_variable" "host" {
  repository    = var.github_repo
  variable_name = "DATABRICKS_HOST"
  value         = var.databricks_host
}

resource "github_actions_environment_secret" "client_id" {
  for_each    = var.environments
  repository  = var.github_repo
  environment = github_repository_environment.env[each.key].environment
  secret_name = "DATABRICKS_CLIENT_ID"
  value       = local.sp_client_id[each.key]
}

resource "github_actions_environment_secret" "client_secret" {
  for_each    = var.environments
  repository  = var.github_repo
  environment = github_repository_environment.env[each.key].environment
  secret_name = "DATABRICKS_CLIENT_SECRET"
  value       = local.sp_secret[each.key]
}
