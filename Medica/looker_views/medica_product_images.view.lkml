view: medica_product_images {
  sql_table_name: public.medica_product_images ;;
  drill_fields: [id]

  dimension: id {
    primary_key: yes
    type: number
    sql: ${TABLE}.id ;;
  }

  dimension: exhibitor_id {
    type: number
    hidden: yes
    sql: ${TABLE}.exhibitor_id ;;
  }

  dimension: image_filename {
    type: string
    sql: ${TABLE}.image_filename ;;
  }

  dimension: gcs_url {
    type: string
    sql: ${TABLE}.gcs_url ;;
    hidden: yes
  }

  dimension: gcs_bucket {
    type: string
    sql: ${TABLE}.gcs_bucket ;;
    hidden: yes
  }

  dimension: gcs_path {
    type: string
    sql: ${TABLE}.gcs_path ;;
    hidden: yes
  }

  dimension: image_order {
    type: number
    sql: ${TABLE}.image_order ;;
  }

  dimension: file_size_bytes {
    type: number
    sql: ${TABLE}.file_size_bytes ;;
    hidden: yes
  }

  dimension: file_size_kb {
    type: number
    sql: ${TABLE}.file_size_bytes / 1024.0 ;;
    value_format_name: decimal_1
  }

  dimension: file_size_mb {
    type: number
    sql: ${TABLE}.file_size_bytes / 1024.0 / 1024.0 ;;
    value_format_name: decimal_2
  }

  dimension_group: uploaded {
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
    sql: ${TABLE}.uploaded_at ;;
  }

  # HTML dimension to display image inline
  dimension: product_image {
    type: string
    sql: ${gcs_url} ;;
    html: <img src="{{ value }}" style="max-width: 200px; max-height: 200px; border: 1px solid #ddd; border-radius: 4px; padding: 5px;"> ;;
  }

  # Thumbnail version
  dimension: product_image_thumbnail {
    type: string
    sql: ${gcs_url} ;;
    html: <img src="{{ value }}" style="max-width: 100px; max-height: 100px; border: 1px solid #ddd; border-radius: 4px; padding: 2px;"> ;;
  }

  # Clickable image that opens in new tab
  dimension: product_image_link {
    type: string
    sql: ${gcs_url} ;;
    html: <a href="{{ value }}" target="_blank"><img src="{{ value }}" style="max-width: 150px; max-height: 150px; border: 1px solid #ddd; border-radius: 4px; padding: 3px;"></a> ;;
  }

  # Image gallery - shows all images for an exhibitor
  dimension: image_gallery {
    type: string
    sql: ${gcs_url} ;;
    html:
      <div style="display: inline-block; margin: 5px;">
        <a href="{{ value }}" target="_blank">
          <img src="{{ value }}" style="max-width: 120px; max-height: 120px; border: 2px solid #4285f4; border-radius: 8px; padding: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        </a>
        <div style="font-size: 10px; text-align: center; margin-top: 2px; color: #666;">
          {{ medica_product_images.image_order._value }}
        </div>
      </div>
    ;;
  }

  # Measures
  measure: count {
    type: count
    drill_fields: [detail*]
  }

  measure: total_file_size_mb {
    type: sum
    sql: ${file_size_mb} ;;
    value_format_name: decimal_2
    label: "Total Size (MB)"
  }

  measure: avg_file_size_kb {
    type: average
    sql: ${file_size_kb} ;;
    value_format_name: decimal_1
    label: "Average Size (KB)"
  }

  measure: first_image {
    type: string
    sql: MIN(CASE WHEN ${image_order} = 1 THEN ${gcs_url} END) ;;
    html: <img src="{{ value }}" style="max-width: 200px; max-height: 200px; border: 1px solid #ddd; border-radius: 4px; padding: 5px;"> ;;
  }

  # Drill fields
  set: detail {
    fields: [
      id,
      exhibitor_id,
      image_filename,
      image_order,
      file_size_mb,
      uploaded_date
    ]
  }
}
