# Functions which formats the metric value for
# the chart. The returned value is between 0 and 100.
def normalize_cpu(metrics, chart_metric):
  return 100 - int(metrics[chart_metric])

def normalize_mem(metrics, chart_metric):
  return int(metrics[chart_metric])

def normalize_disk(metrics, chart_metric):
  return int(metrics[chart_metric])

# Functions which format the display values
# which are shown after the horizontal bar char
def format_cpu_metrics(*args):
  cpu_user = float(args[0])
  cpu_sys = float(args[1])
  cpu_idle = float(args[2])
  
  return (cpu_user, cpu_sys, cpu_idle)

def format_mem_metrics(*args):
  mem_used = float(args[0]) / 1024 / 1024
  mem_free = float(args[1]) / 1024 / 1024
  
  return (mem_used, mem_free)

def format_disk_metrics(*args):
  block_size = float(args[0])
  blocks_free = float(args[1])
  blocks_total = float(args[2])
  
  free_gb = (blocks_free * block_size) / 1024 / 1024 / 1024
  total_gb = (blocks_total * block_size) / 1024 / 1024 / 1024
  
  return (free_gb, total_gb)