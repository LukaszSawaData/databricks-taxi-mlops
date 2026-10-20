# Isolation boundary per environment = schema (pipelines tables, feature table, model, predictions,
# monitoring tables). Owned by you; the env SP gets full rights only on its own schema.
resource "databricks_schema" "env" {
  for_each      = var.environments
  catalog_name  = var.catalog
  name          = each.value.schema
  comment       = "${var.project} ${each.key} - managed by Terraform"
  force_destroy = true
}

# databricks_grant (singular) is additive: it does not wipe grants others already have.
resource "databricks_grant" "catalog_use" {
  for_each   = var.environments
  catalog    = var.catalog
  principal  = local.sp_client_id[each.key]
  privileges = ["USE_CATALOG"]
}

resource "databricks_grant" "schema_owner_rights" {
  for_each   = var.environments
  schema     = databricks_schema.env[each.key].id
  principal  = local.sp_client_id[each.key]
  privileges = ["ALL_PRIVILEGES", "MANAGE"] # MANAGE: needed for the data quality monitor
}
