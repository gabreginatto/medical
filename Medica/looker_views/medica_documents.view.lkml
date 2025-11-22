view: medica_documents {
  sql_table_name: public.medica_documents ;;
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

  dimension: document_filename {
    type: string
    sql: ${TABLE}.document_filename ;;
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

  # Document type based on extension
  dimension: document_type {
    type: string
    sql: UPPER(SPLIT_PART(${document_filename}, '.', -1)) ;;
  }

  # Clickable download link
  dimension: download_link {
    type: string
    sql: ${gcs_url} ;;
    html: <a href="{{ value }}" target="_blank" download><i class="fa fa-download"></i> {{ medica_documents.document_filename._value }}</a> ;;
  }

  # Document icon with link
  dimension: document_with_icon {
    type: string
    sql: ${gcs_url} ;;
    html:
      <a href="{{ value }}" target="_blank" style="text-decoration: none;">
        <div style="display: inline-block; padding: 8px 12px; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; margin: 2px;">
          <i class="fa fa-file-pdf-o" style="color: #d32f2f; margin-right: 5px;"></i>
          <span style="color: #333;">{{ medica_documents.document_filename._value }}</span>
          <span style="color: #999; font-size: 11px; margin-left: 5px;">({{ medica_documents.file_size_mb._rendered }})</span>
        </div>
      </a>
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

  measure: avg_file_size_mb {
    type: average
    sql: ${file_size_mb} ;;
    value_format_name: decimal_2
    label: "Average Size (MB)"
  }

  # Drill fields
  set: detail {
    fields: [
      id,
      exhibitor_id,
      document_filename,
      document_type,
      file_size_mb,
      uploaded_date
    ]
  }
}
