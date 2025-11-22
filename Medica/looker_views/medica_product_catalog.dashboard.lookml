- dashboard: medica_product_catalog
  title: "MEDICA 2025 - Product Catalog (China)"
  layout: newspaper
  preferred_viewer: dashboards-next
  description: "Browse Chinese exhibitor product catalogs with images"

  elements:
  - title: "Product Image Gallery"
    name: product_gallery
    model: medica
    explore: china_exhibitors
    type: looker_grid
    fields: [
      medica_exhibitors.name,
      medica_exhibitors.location,
      medica_exhibitors.company_description,
      medica_product_images.image_gallery,
      medica_product_images.count
    ]
    filters:
      medica_product_images.count: ">0"
    sorts: [medica_product_images.count desc]
    limit: 100
    show_view_names: false
    show_row_numbers: false
    transpose: false
    truncate_text: false
    hide_totals: false
    hide_row_totals: false
    size_to_fit: true
    table_theme: white
    limit_displayed_rows: false
    enable_conditional_formatting: false
    header_text_alignment: left
    header_font_size: '14'
    rows_font_size: '12'
    conditional_formatting_include_totals: false
    conditional_formatting_include_nulls: false
    truncate_column_names: false
    series_column_widths:
      medica_exhibitors.name: 200
      medica_exhibitors.location: 120
      medica_exhibitors.company_description: 300
      medica_product_images.image_gallery: 500
      medica_product_images.count: 80
    row: 0
    col: 0
    width: 24
    height: 16

  - title: "Exhibitors with Most Products"
    name: top_exhibitors_by_images
    model: medica
    explore: china_exhibitors
    type: looker_bar
    fields: [
      medica_exhibitors.name,
      medica_product_images.count,
      medica_product_images.first_image
    ]
    filters:
      medica_product_images.count: ">0"
    sorts: [medica_product_images.count desc]
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
      medica_product_images.count: "#34A853"
    row: 16
    col: 0
    width: 12
    height: 8

  - title: "Storage Statistics"
    name: storage_stats
    model: medica
    explore: china_exhibitors
    type: looker_column
    fields: [
      medica_product_images.count,
      medica_product_images.total_file_size_mb,
      medica_documents.count,
      medica_documents.total_file_size_mb
    ]
    limit: 500
    x_axis_gridlines: false
    y_axis_gridlines: true
    show_view_names: false
    show_y_axis_labels: true
    show_y_axis_ticks: true
    y_axis_tick_density: default
    y_axis_tick_density_custom: 5
    show_x_axis_label: false
    show_x_axis_ticks: false
    x_axis_scale: auto
    y_axis_scale_mode: linear
    ordering: none
    show_null_labels: false
    show_totals_labels: true
    show_silhouette: false
    totals_color: "#808080"
    series_types:
      medica_product_images.total_file_size_mb: line
      medica_documents.total_file_size_mb: line
    series_colors:
      medica_product_images.count: "#4285F4"
      medica_documents.count: "#FBBC04"
      medica_product_images.total_file_size_mb: "#EA4335"
      medica_documents.total_file_size_mb: "#34A853"
    y_axes: [{label: Count, orientation: left, series: [{axisId: medica_product_images.count,
            id: medica_product_images.count, name: Product Images Count}, {axisId: medica_documents.count,
            id: medica_documents.count, name: Documents Count}], showLabels: true,
        showValues: true, unpinAxis: false, tickDensity: default, tickDensityCustom: 5,
        type: linear}, {label: Size (MB), orientation: right, series: [{axisId: medica_product_images.total_file_size_mb,
            id: medica_product_images.total_file_size_mb, name: Total Size (MB)},
          {axisId: medica_documents.total_file_size_mb, id: medica_documents.total_file_size_mb,
            name: Total Documents Size (MB)}], showLabels: true, showValues: true,
        unpinAxis: false, tickDensity: default, tickDensityCustom: 5, type: linear}]
    row: 16
    col: 12
    width: 12
    height: 8

  filters:
  - name: Exhibitor Name
    title: Search Exhibitor
    type: field_filter
    default_value: ''
    allow_multiple_values: true
    required: false
    ui_config:
      type: advanced
      display: popover
      options: []
    model: medica
    explore: china_exhibitors
    listens_to_filters: []
    field: medica_exhibitors.name

  - name: Min Images
    title: Minimum Number of Images
    type: field_filter
    default_value: '1'
    allow_multiple_values: false
    required: false
    ui_config:
      type: slider
      display: inline
      options:
        min: 0
        max: 20
    model: medica
    explore: china_exhibitors
    listens_to_filters: []
    field: medica_product_images.count
