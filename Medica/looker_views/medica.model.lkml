connection: "medical_cloud_sql"

# Include all view files
include: "*.view.lkml"

# Datagroup for caching
datagroup: medica_default_datagroup {
  sql_trigger: SELECT MAX(updated_at) FROM medica_exhibitors ;;
  max_cache_age: "1 hour"
}

persist_with: medica_default_datagroup

# Main Explore
explore: medica_exhibitors {
  label: "MEDICA Exhibitors"
  description: "Explore MEDICA 2025 exhibitor data with product images and documents"

  # Join product images
  join: medica_product_images {
    type: left_outer
    relationship: one_to_many
    sql_on: ${medica_exhibitors.id} = ${medica_product_images.exhibitor_id} ;;
  }

  # Join documents
  join: medica_documents {
    type: left_outer
    relationship: one_to_many
    sql_on: ${medica_exhibitors.id} = ${medica_documents.exhibitor_id} ;;
  }
}

# Filtered Explore for China exhibitors only
explore: china_exhibitors {
  extends: [medica_exhibitors]
  label: "China Exhibitors"
  description: "MEDICA 2025 Chinese exhibitors with product catalogs"

  sql_always_where: ${medica_exhibitors.region} = 'China' ;;
}

# Filtered Explore for Global exhibitors only
explore: global_exhibitors {
  extends: [medica_exhibitors]
  label: "Global Exhibitors"
  description: "MEDICA 2025 global (non-China) exhibitors"

  sql_always_where: ${medica_exhibitors.region} = 'Global' ;;
}
