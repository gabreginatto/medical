view: medica_exhibitors {
  sql_table_name: public.medica_exhibitors ;;
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
      url: "/dashboards/medica::medica_exhibitor_detail?Exhibitor%20Name={{ value | url_encode }}"
    }
  }

  dimension: location {
    type: string
    sql: ${TABLE}.location ;;
    description: "Hall and booth location at MEDICA 2025"
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

  dimension: raw_text {
    type: string
    sql: ${TABLE}.raw_text ;;
    hidden: yes
  }

  dimension: country {
    type: string
    sql: ${TABLE}.country ;;
    map_layer_name: countries
  }

  dimension: region {
    type: string
    sql: ${TABLE}.region ;;
    description: "China or Global"
  }

  dimension: event {
    type: string
    sql: ${TABLE}.event ;;
  }

  dimension_group: scraped {
    type: time
    timeframes: [
      raw,
      time,
      date,
      week,
      month,
      quarter,
      year
    ]
    sql: ${TABLE}.scraped_at ;;
  }

  dimension_group: created {
    type: time
    timeframes: [
      raw,
      time,
      date,
      week,
      month,
      quarter,
      year
    ]
    sql: ${TABLE}.created_at ;;
  }

  dimension_group: updated {
    type: time
    timeframes: [
      raw,
      time,
      date,
      week,
      month,
      quarter,
      year
    ]
    sql: ${TABLE}.updated_at ;;
  }

  # Measures
  measure: count {
    type: count
    drill_fields: [detail*]
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

  # Drill fields
  set: detail {
    fields: [
      id,
      name,
      location,
      country,
      region,
      email,
      phone,
      website,
      medica_product_images.count,
      medica_documents.count
    ]
  }
}
