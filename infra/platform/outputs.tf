output "service_principals" {
  value = local.sp_client_id
}

output "schemas" {
  value = { for k, s in databricks_schema.env : k => s.id }
}

# Bundle files, experiment and dashboards live in each SP's home: /Workspace/Users/<app id>/
output "workspace_folders" {
  value = { for k, id in local.sp_client_id : k => "/Workspace/Users/${id}" }
}

# For local CLI profiles that act exactly like CI: terraform output -json sp_secrets
output "sp_secrets" {
  value     = local.sp_secret
  sensitive = true
}
