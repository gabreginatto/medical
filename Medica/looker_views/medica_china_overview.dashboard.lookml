- dashboard: medica_china_overview
  title: "MEDICA 2025 - China Exhibitors Overview"
  layout: newspaper
  preferred_viewer: dashboards-next
  description: "Overview of Chinese medical equipment exhibitors at MEDICA 2025"

  elements:
  - title: "Total China Exhibitors"
    name: total_exhibitors
    model: medica
    explore: china_exhibitors
    type: single_value
    fields: [medica_exhibitors.count]
    limit: 500
    show_single_value_title: true
    show_comparison: false
    value_format: "#,##0"
    font_size: medium
    row: 0
    col: 0
    width: 6
    height: 3

  - title: "Exhibitors with Product Images"
    name: exhibitors_with_images
    model: medica
    explore: china_exhibitors
    type: single_value
    fields: [medica_exhibitors.count]
    filters:
      medica_product_images.count: ">0"
    limit: 500
    show_single_value_title: true
    show_comparison: false
    value_format: "#,##0"
    font_size: medium
    row: 0
    col: 6
    width: 6
    height: 3

  - title: "Total Product Images"
    name: total_images
    model: medica
    explore: china_exhibitors
    type: single_value
    fields: [medica_product_images.count]
    limit: 500
    show_single_value_title: true
    show_comparison: false
    value_format: "#,##0"
    font_size: medium
    row: 0
    col: 12
    width: 6
    height: 3

  - title: "Total Documents (PDFs)"
    name: total_documents
    model: medica
    explore: china_exhibitors
    type: single_value
    fields: [medica_documents.count]
    limit: 500
    show_single_value_title: true
    show_comparison: false
    value_format: "#,##0"
    font_size: medium
    row: 0
    col: 18
    width: 6
    height: 3

  - title: "Exhibitors by Location (Hall)"
    name: exhibitors_by_hall
    model: medica
    explore: china_exhibitors
    type: looker_column
    fields: [medica_exhibitors.location, medica_exhibitors.count]
    filters:
      medica_exhibitors.location: "-NULL"
    sorts: [medica_exhibitors.count desc]
    limit: 20
    x_axis_gridlines: false
    y_axis_gridlines: true
    show_view_names: false
    show_y_axis_labels: true
    show_y_axis_ticks: true
    y_axis_tick_density: default
    y_axis_tick_density_custom: 5
    show_x_axis_label: true
    show_x_axis_ticks: true
    x_axis_scale: auto
    y_axis_scale_mode: linear
    ordering: none
    show_null_labels: false
    show_totals_labels: false
    show_silhouette: false
    totals_color: "#808080"
    series_colors:
      medica_exhibitors.count: "#4285F4"
    row: 3
    col: 0
    width: 12
    height: 8

  - title: "Images per Exhibitor Distribution"
    name: images_distribution
    model: medica
    explore: china_exhibitors
    type: looker_column
    fields: [medica_product_images.count, medica_exhibitors.count]
    filters:
      medica_product_images.count: ">0"
    pivots: [medica_product_images.count]
    fill_fields: [medica_product_images.count]
    sorts: [medica_product_images.count]
    limit: 500
    x_axis_gridlines: false
    y_axis_gridlines: true
    show_view_names: false
    show_y_axis_labels: true
    show_y_axis_ticks: true
    y_axis_tick_density: default
    y_axis_tick_density_custom: 5
    show_x_axis_label: true
    show_x_axis_ticks: true
    x_axis_scale: auto
    y_axis_scale_mode: linear
    ordering: none
    show_null_labels: false
    show_totals_labels: false
    show_silhouette: false
    totals_color: "#808080"
    series_colors:
      medica_exhibitors.count: "#EA4335"
    row: 3
    col: 12
    width: 12
    height: 8

  - title: "Recent Exhibitors with Product Images"
    name: recent_exhibitors
    model: medica
    explore: china_exhibitors
    type: looker_grid
    fields: [
      medica_exhibitors.name,
      medica_exhibitors.location,
      medica_exhibitors.website,
      medica_product_images.count,
      medica_product_images.first_image
    ]
    filters:
      medica_product_images.count: ">0"
    sorts: [medica_exhibitors.name]
    limit: 50
    show_view_names: false
    show_row_numbers: true
    transpose: false
    truncate_text: true
    hide_totals: false
    hide_row_totals: false
    size_to_fit: true
    table_theme: white
    limit_displayed_rows: false
    enable_conditional_formatting: false
    header_text_alignment: left
    header_font_size: '12'
    rows_font_size: '12'
    conditional_formatting_include_totals: false
    conditional_formatting_include_nulls: false
    row: 11
    col: 0
    width: 24
    height: 10

  filters:
  - name: Exhibitor Name
    title: Exhibitor Name
    type: field_filter
    default_value: ''
    allow_multiple_values: true
    required: false
    ui_config:
      type: advanced
      display: popover
    model: medica
    explore: china_exhibitors
    listens_to_filters: []
    field: medica_exhibitors.name

  - name: Location (Hall)
    title: Location (Hall)
    type: field_filter
    default_value: ''
    allow_multiple_values: true
    required: false
    ui_config:
      type: tag_list
      display: popover
    model: medica
    explore: china_exhibitors
    listens_to_filters: []
    field: medica_exhibitors.location
