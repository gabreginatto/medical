view: international_exhibitors {
  # View for companies exhibiting at both CMEF and MEDICA
  sql_table_name: public.medical_exhibitors_merged_duplicates ;;
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
      url: "/dashboards/medical::international_exhibitor_detail?Exhibitor%20Name={{ value | url_encode }}"
    }
  }

  dimension: company_name_zh {
    type: string
    sql: ${TABLE}.company_name_zh ;;
    label: "Chinese Name"
  }

  dimension: location {
    type: string
    sql: ${TABLE}.location ;;
    description: "Combined location from both events"
  }

  dimension: booth_info {
    type: string
    sql: ${TABLE}.booth_info ;;
    description: "Booth locations at both CMEF and MEDICA"
    label: "Booth Information"
  }

  dimension: events {
    type: string
    sql: ${TABLE}.events ;;
    description: "Always 'BOTH (CMEF & MEDICA)' for this view"
  }

  dimension: primary_source {
    type: string
    sql: ${TABLE}.primary_source ;;
    description: "Which dataset has more complete information"
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
  }

  dimension: company_description {
    type: string
    sql: ${TABLE}.company_description ;;
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
    value_format_name: percent_2
  }

  dimension: website_validated {
    type: yesno
    sql: ${TABLE}.website_validated ;;
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

  # Measures
  measure: count {
    type: count
    drill_fields: [detail*]
    label: "International Exhibitors"
  }

  measure: count_with_email {
    type: count
    filters: [email: "-NULL"]
  }

  measure: count_with_website {
    type: count
    filters: [website: "-NULL"]
  }

  # Drill fields
  set: detail {
    fields: [
      id,
      name,
      company_name_zh,
      booth_info,
      country,
      product_category,
      email,
      phone,
      website
    ]
  }
}
