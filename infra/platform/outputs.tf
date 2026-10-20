output "service_principals" {
  value = local.sp_client_id
}

output "schemas" {
  value = { for k, s in databricks_schema.env : k => s.id }
}

output "workspace_folders" {
  value = { for k, d in databricks_directory.env : k => d.workspace_path }
}

# For local CLI profiles that act exactly like CI: terraform output -json sp_secrets
output "sp_secrets" {
  value     = local.sp_secret
  sensitive = true
}
