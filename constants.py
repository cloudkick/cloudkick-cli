from formatting import normalize_cpu, normalize_mem, normalize_disk, \
                       format_cpu_metrics, format_mem_metrics, format_disk_metrics
                       
# Minimum screen size
SCREEN_MIN_X = 80
SCREEN_MIN_Y = 24

SCREEN_NODE_TABLE_START = 13
SCREEN_NODE_LIST_START = 13

SCREEN_REDRAW_INTERVAL = 0.1
NODE_LIST_UPDATE_INTERVAL = 30
NODE_METRICS_UPDATE_INTERVAL = 5

CHART_METRICS = ('cpu', 'mem', 'disk')

# Node list table rows and columns
NODE_TABLE_COLUMNS = (
  {'name': 'name', 'width': 36, 'align': 'center'},
  {'name': 'server ip', 'width': 26, 'align': 'center'},
  {'name': 'provider', 'width': 24, 'align': 'center'},
  {'name': 'status', 'width': 14, 'align': 'center'},
)

NODE_TABLE_ROWS = (
  {'field_name': 'name', 'width': 35, 'align': 'center'},
  {'field_name': 'ipaddress', 'width': 25, 'align': 'center'},
  {'field_name': 'provider_name', 'width': 25, 'align': 'center'},
  {'field_name': 'status', 'width': 15, 'align': 'center'},
)

NODE_METRICS = {
  'cpu': {'chart_metric': 'cpu_idle', 'chart_text': '%2.f%% user, %.2f%% sys, %2.f%% idle', 'metrics': ['cpu_user', 'cpu_sys', 'cpu_idle'],
  'normalization_function': normalize_cpu, 'format_function': format_cpu_metrics},
  'mem': {'chart_metric': 'mem_percent_used', 'chart_text': '%.2fMB used, %.2fMB free', 'metrics': ['mem_used', \
  'mem_free'], 'normalization_function': normalize_mem, 'format_function': format_mem_metrics},
  'disk': {'chart_metric': 'capacity', 'chart_text': '%.2fGB free, %.2fGB total', 'metrics': ['bsize', 'bfree', 'blocks'],
  'normalization_function': normalize_disk, 'format_function': format_disk_metrics},
}