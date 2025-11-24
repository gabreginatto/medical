view: medical_exhibitors {
  # Use the deduplicated view by default
  sql_table_name: public.medical_exhibitors_unique ;;
  drill_fields: [id]

  dimension: id {
    primary_key: yes
    type: number
    sql: ${TABLE}.id ;;
  }

  dimension: name {
    type: string
    sql: ${TABLE}.name ;;
    link: {
      label: "View Exhibitor Details"
      url: "/dashboards/medical::exhibitor_detail?Exhibitor%20Name={{ value | url_encode }}"
    }
  }

  dimension: company_name_zh {
    type: string
    sql: ${TABLE}.company_name_zh ;;
    label: "Chinese Name"
    description: "Company name in Chinese (CMEF data only)"
  }

  dimension: location {
    type: string
    sql: ${TABLE}.location ;;
    description: "Hall and booth location"
  }

  dimension: booth_number {
    type: string
    sql: ${TABLE}.booth_number ;;
    description: "Booth number(s) at exhibition"
  }

  dimension: company_description {
    type: string
    sql: ${TABLE}.company_description ;;
  }

  dimension: email {
    type: string
    sql: ${TABLE}.email ;;
  }

  dimension: phone {
    type: string
    sql: ${TABLE}.phone ;;
  }

  dimension: website {
    type: string
    sql: ${TABLE}.website ;;
    link: {
      label: "Visit Website"
      url: "{{ value }}"
      icon_url: "https://www.google.com/s2/favicons?domain={{ value }}"
    }
  }

  dimension: address {
    type: string
    sql: ${TABLE}.address ;;
  }

  dimension: country {
    type: string
    sql: ${TABLE}.country ;;
    map_layer_name: countries
  }

  dimension: region {
    type: string
    sql: ${TABLE}.region ;;
    description: "Geographic region"
  }

  dimension: event {
    type: string
    sql: ${TABLE}.event ;;
    description: "CMEF 2025 or MEDICA 2025"
  }

  dimension: data_source {
    type: string
    sql: ${TABLE}.data_source ;;
    description: "CMEF or MEDICA"
  }

  # AI Classification fields
  dimension: product_category {
    type: string
    sql: ${TABLE}.product_category ;;
    description: "AI-classified product category"
  }

  dimension: product_keywords {
    type: string
    sql: ARRAY_TO_STRING(${TABLE}.product_keywords, ', ') ;;
    description: "AI-extracted product keywords"
  }

  dimension: category_confidence {
    type: number
    sql: ${TABLE}.category_confidence ;;
    description: "AI classification confidence score (0-1)"
    value_format_name: percent_2
  }

  # Website validation
  dimension: website_validated {
    type: yesno
    sql: ${TABLE}.website_validated ;;
  }

  dimension: website_status_code {
    type: number
    sql: ${TABLE}.website_status_code ;;
  }

  dimension: website_status {
    type: string
    sql: CASE
           WHEN ${website_status_code} = 200 THEN 'Active'
           WHEN ${website_status_code} >= 400 THEN 'Broken'
           WHEN ${website_status_code} IS NULL THEN 'Not Checked'
           ELSE 'Unknown'
         END ;;
  }

  # Time dimensions
  dimension_group: scraped {
    type: time
    timeframes: [raw, time, date, week, month, quarter, year]
    sql: ${TABLE}.scraped_at ;;
  }

  dimension_group: created {
    type: time
    timeframes: [raw, time, date, week, month, quarter, year]
    sql: ${TABLE}.created_at ;;
  }

  dimension_group: updated {
    type: time
    timeframes: [raw, time, date, week, month, quarter, year]
    sql: ${TABLE}.updated_at ;;
  }

  # Derived dimensions
  dimension: has_chinese_name {
    type: yesno
    sql: ${company_name_zh} IS NOT NULL ;;
  }

  dimension: has_contact_info {
    type: yesno
    sql: ${email} IS NOT NULL OR ${phone} IS NOT NULL ;;
  }

  dimension: has_website {
    type: yesno
    sql: ${website} IS NOT NULL ;;
  }

  dimension: has_description {
    type: yesno
    sql: ${company_description} IS NOT NULL ;;
  }

  dimension: completeness_score {
    type: number
    sql: (CASE WHEN ${company_name_zh} IS NOT NULL THEN 1 ELSE 0 END +
          CASE WHEN ${email} IS NOT NULL THEN 1 ELSE 0 END +
          CASE WHEN ${phone} IS NOT NULL THEN 1 ELSE 0 END +
          CASE WHEN ${website} IS NOT NULL THEN 1 ELSE 0 END +
          CASE WHEN ${address} IS NOT NULL THEN 1 ELSE 0 END +
          CASE WHEN ${company_description} IS NOT NULL THEN 1 ELSE 0 END +
          CASE WHEN ${booth_number} IS NOT NULL THEN 1 ELSE 0 END) ;;
    description: "Data completeness score (0-7)"
  }

  # Certification dimensions
  dimension: has_fda {
    type: yesno
    sql: ${company_description} ~* '\bFDA\b' ;;
    description: "Company mentions FDA approval/clearance"
  }

  dimension: has_ce_mark {
    type: yesno
    sql: ${company_description} ~* '\bCE\b' ;;
    description: "Company mentions CE Mark"
  }

  dimension: has_iso {
    type: yesno
    sql: ${company_description} ~* '\bISO\s*\d{4,5}' ;;
    description: "Company mentions ISO certification (e.g., ISO 13485)"
  }

  dimension: has_cfda {
    type: yesno
    sql: ${company_description} ~* '\bCFDA\b' ;;
    description: "Company mentions CFDA (China FDA) approval"
  }

  dimension: has_nmpa {
    type: yesno
    sql: ${company_description} ~* '\bNMPA\b' ;;
    description: "Company mentions NMPA (China regulatory) approval"
  }

  dimension: has_gmp {
    type: yesno
    sql: ${company_description} ~* '\bGMP\b' ;;
    description: "Company mentions GMP certification"
  }

  dimension: has_tuv {
    type: yesno
    sql: ${company_description} ~* '\bT[UÜ]V\b' ;;
    description: "Company mentions TUV certification"
  }

  dimension: has_any_certification {
    type: yesno
    sql: ${company_description} ~* '\b(FDA|CE|ISO|CFDA|NMPA|GMP|TUV|MDR|certif|approv)\b' ;;
    description: "Company mentions any certification or approval"
  }

  dimension: certification_count {
    type: number
    sql: (CASE WHEN ${company_description} ~* '\bFDA\b' THEN 1 ELSE 0 END +
          CASE WHEN ${company_description} ~* '\bCE\b' THEN 1 ELSE 0 END +
          CASE WHEN ${company_description} ~* '\bISO\s*\d{4,5}' THEN 1 ELSE 0 END +
          CASE WHEN ${company_description} ~* '\bCFDA\b' THEN 1 ELSE 0 END +
          CASE WHEN ${company_description} ~* '\bNMPA\b' THEN 1 ELSE 0 END +
          CASE WHEN ${company_description} ~* '\bGMP\b' THEN 1 ELSE 0 END +
          CASE WHEN ${company_description} ~* '\bT[UÜ]V\b' THEN 1 ELSE 0 END) ;;
    description: "Number of major certifications mentioned (0-7)"
  }

  dimension: certification_tier {
    type: tier
    tiers: [0, 1, 2, 3, 4]
    sql: ${certification_count} ;;
    style: integer
    description: "Certification tier based on count"
  }

  # Measures
  measure: count {
    type: count
    drill_fields: [detail*]
  }

  measure: count_cmef {
    type: count
    filters: [data_source: "CMEF"]
    label: "CMEF Exhibitors"
  }

  measure: count_medica {
    type: count
    filters: [data_source: "MEDICA"]
    label: "MEDICA Exhibitors"
  }

  measure: count_with_email {
    type: count
    filters: [email: "-NULL"]
    label: "Exhibitors with Email"
  }

  measure: count_with_website {
    type: count
    filters: [website: "-NULL"]
    label: "Exhibitors with Website"
  }

  measure: count_with_description {
    type: count
    filters: [company_description: "-NULL"]
    label: "Exhibitors with Description"
  }

  measure: count_classified {
    type: count
    filters: [product_category: "-NULL"]
    label: "Classified Exhibitors"
  }

  measure: avg_completeness_score {
    type: average
    sql: ${completeness_score} ;;
    value_format_name: decimal_2
    label: "Average Completeness Score"
  }

  measure: avg_confidence {
    type: average
    sql: ${category_confidence} ;;
    value_format_name: percent_2
    label: "Average Classification Confidence"
  }

  # Drill fields
  set: detail {
    fields: [
      id,
      name,
      company_name_zh,
      location,
      booth_number,
      country,
      region,
      data_source,
      product_category,
      email,
      phone,
      website,
      medica_product_images.count,
      medica_documents.count
    ]
  }
}
