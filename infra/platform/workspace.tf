# Workspace folder per environment: bundle files, experiment and monitoring dashboards.
# Only the env SP (plus admins) can manage it -> dev artifacts stay in dev, prod in prod.
resource "databricks_directory" "env" {
  for_each = var.environments
  path     = "/Shared/${var.project}/${each.key}"
}

resource "databricks_permissions" "env_dir" {
  for_each       = var.environments
  directory_path = databricks_directory.env[each.key].path

  access_control {
    service_principal_name = local.sp_client_id[each.key]
    permission_level       = "CAN_MANAGE"
  }
  access_control {
    group_name       = "users"
    permission_level = "CAN_READ"
  }
}
