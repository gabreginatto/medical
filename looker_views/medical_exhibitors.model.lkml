connection: "medical_cloud_sql"

# Include all view files
include: "*.view.lkml"

# Datagroup for caching
datagroup: medical_default_datagroup {
  sql_trigger: SELECT MAX(updated_at) FROM medical_exhibitors ;;
  max_cache_age: "1 hour"
}

persist_with: medical_default_datagroup

# Main Explore - All Exhibitors (Deduplicated)
explore: medical_exhibitors {
  label: "Medical Exhibitors (All)"
  description: "Unified view of CMEF and MEDICA exhibitors (deduplicated, 5,638 unique companies)"

  # Join product images (MEDICA only)
  join: medica_product_images {
    type: left_outer
    relationship: one_to_many
    sql_on: ${medical_exhibitors.id} = ${medica_product_images.exhibitor_id}
            AND ${medical_exhibitors.data_source} = 'MEDICA' ;;
  }

  # Join documents (MEDICA only)
  join: medica_documents {
    type: left_outer
    relationship: one_to_many
    sql_on: ${medical_exhibitors.id} = ${medica_documents.exhibitor_id}
            AND ${medical_exhibitors.data_source} = 'MEDICA' ;;
  }
}

# CMEF-specific Explore
explore: cmef_exhibitors {
  extends: [medical_exhibitors]
  label: "CMEF Exhibitors"
  description: "CMEF 2025 Chinese exhibitors (4,396 companies)"

  sql_always_where: ${medical_exhibitors.data_source} = 'CMEF' ;;
}

# MEDICA-specific Explore
explore: medica_exhibitors {
  extends: [medical_exhibitors]
  label: "MEDICA Exhibitors"
  description: "MEDICA 2025 exhibitors (1,242 unique companies)"

  sql_always_where: ${medical_exhibitors.data_source} = 'MEDICA' ;;
}

# International Companies Explore
explore: international_exhibitors {
  label: "International Exhibitors (Both Events)"
  description: "Companies exhibiting at both CMEF and MEDICA (79 companies)"

  # Join product images
  join: medica_product_images {
    type: left_outer
    relationship: one_to_many
    sql_on: ${international_exhibitors.id} = ${medica_product_images.exhibitor_id} ;;
  }

  # Join documents
  join: medica_documents {
    type: left_outer
    relationship: one_to_many
    sql_on: ${international_exhibitors.id} = ${medica_documents.exhibitor_id} ;;
  }
}

# China Companies Explore (from MEDICA)
explore: china_exhibitors {
  from: medical_exhibitors
  label: "China Exhibitors (MEDICA)"
  description: "Chinese companies at MEDICA 2025"

  sql_always_where: ${country} = 'China' AND ${data_source} = 'MEDICA' ;;

  join: medica_product_images {
    type: left_outer
    relationship: one_to_many
    sql_on: ${china_exhibitors.id} = ${medica_product_images.exhibitor_id} ;;
  }

  join: medica_documents {
    type: left_outer
    relationship: one_to_many
    sql_on: ${china_exhibitors.id} = ${medica_documents.exhibitor_id} ;;
  }
}

# Product Category Analysis
explore: product_categories {
  from: medical_exhibitors
  label: "Product Categories"
  description: "Analyze companies by AI-classified product categories"

  sql_always_where: ${product_category} IS NOT NULL ;;

  join: medica_product_images {
    type: left_outer
    relationship: one_to_many
    sql_on: ${product_categories.id} = ${medica_product_images.exhibitor_id}
            AND ${product_categories.data_source} = 'MEDICA' ;;
  }
}
