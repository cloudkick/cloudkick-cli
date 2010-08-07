import sys
import time
import curses
import threading
import signal

from datetime import datetime
from optparse import OptionParser
from threads import NodeListThread, NodeMetricsThread
from constants import SCREEN_MIN_X, SCREEN_MIN_Y, SCREEN_NODE_TABLE_START, \
                      SCREEN_NODE_LIST_START, SCREEN_REDRAW_INTERVAL, \
                      NODE_TABLE_COLUMNS, NODE_TABLE_ROWS, NODE_METRICS, \
                      CHART_METRICS

try:
  from cloudkick.base import Connection
except ImportError:
  print 'You need to have cloudkick-py library installed to use this application. ' \
        'You can get it at http://github.com/cloudkick/cloudkick-py'
  sys.exit(1)


__title__ = 'Cloudkick CLI'
__version__ = '0.1-dev'

class Screen(object):
  
  def __init__(self, connection):
    self.connection = connection
    self.screen = self._get_screen()
    
    self.min_y = 0
    self.min_x = 0
    
    self.cursor_pos = -1
    self.previously_selected_node = None
    self.selected_node = None
    self.min_cursor_pos = 0
    self.max_cursor_pos = 0
    
    self.node_list_thread = None
    self.node_metrics_thread = None

    self.updating_node_list = False
    self.updating_node_metrics = False
    self.last_updated_node = None
    self.last_updated = None
    
    self.nodes = []
    self.node_metrics = {}
    
    self.table_lines = []

  def run(self):
    self._run_worker_threads()
    self._main_loop()
  
  def _main_loop(self):
    while True:
      self._redraw() 
      event = self.screen.getch()
      
      if 0 < event < 256:
        self._handle_key_event(chr(event))
      elif event in [curses.KEY_UP, curses.KEY_DOWN, curses.KEY_PPAGE,
                curses.KEY_NPAGE]:
        self._handle_movement_key(event)
      else:
        self._handle_event(event)

      time.sleep(SCREEN_REDRAW_INTERVAL)
  
  def _run_worker_threads(self):
    # Start the node list and metrics update threads
    self.node_list_thread = NodeListThread(self)
    self.node_list_thread.daemon = True
    self.node_list_thread.start()
    
    self.node_metrics_thread = NodeMetricsThread(self)
    self.node_metrics_thread.daemon = True
    self.node_metrics_thread.start()
    
  def _update_node_metrics(self, update_now = False):
    try:
      self.selected_node = self.nodes[self.cursor_pos]
    except IndexError:
      self.selected_node = None
    
    if self.selected_node and self.selected_node.has_key('id'):
      self.node_metrics_thread.node_id = self.selected_node['id']
      self.node_metrics_thread.update_now = update_now
        
  def _get_screen(self):
    screen = curses.initscr()
    
    curses.noecho()
    
    try:
      # Try to hide the cursor
      curses.curs_set(0)
    except Exception:
      pass
    
    if curses.has_colors():
      curses.start_color()
      curses.use_default_colors()
      
      # Initialize the colors
      curses.init_pair(1, curses.COLOR_WHITE, -1)
      curses.init_pair(2, curses.COLOR_GREEN, -1)
      curses.init_pair(3, curses.COLOR_BLUE, -1)
      curses.init_pair(4, curses.COLOR_RED, -1)
    
    screen.keypad(1)
    screen.nodelay(1)
    
    curses.def_prog_mode()
    
    return screen
  
  def _draw_node_data(self):
    # Draws the node data on the upper part of the screen
    
    metrics = {}
    for metric in CHART_METRICS:
      metrics[metric] = {}
          
    if self.nodes and \
      self.node_metrics.has_key('cpu') and \
      self.node_metrics.has_key('mem') and \
      self.node_metrics.has_key('disk'):
      node = self.nodes[self.cursor_pos]
      node_metrics = self.node_metrics

      name = node['name']
      ip_address = node['ipaddress']

      if self.updating_node_metrics and \
        self.last_updated_node != node['id']:
        
        for metric in CHART_METRICS:
          metrics[metric]['chart'] = 'loading...'
      else:
        for metric in CHART_METRICS:
          chart_metric = [check_data for check_data in node_metrics[metric] if check_data['name'] == NODE_METRICS[metric]['chart_metric']]
          if not chart_metric:
            metrics[metric]['chart'] = 'error loading chart metric'
          else:
            metrics[metric]['chart'], metrics[metric]['meta'], metrics[metric]['percent'] =  self._get_vertical_chart(metric, node_metrics[metric])
      
      tags = ', ' . join(node['tags'])
    else:
      name = '/'
      ip_address = '/'      
      tags = '/'
    
    self.addstr(self.min_y + 3, self.min_x + 2,
                'Node: %s' % (name))
    self.addstr(self.min_y + 4, self.min_x + 2,
                'IP address: %s' % (ip_address))
    
    for index, metric in enumerate(CHART_METRICS):
      metric_data = metrics[metric]
      percent = metric_data.get('percent', '')
      chart = metric_data.get('chart', '')
      meta = metric_data.get('meta', '')
      self.addstr(self.min_y + 6 + index, self.min_x + 2,
                  '%s:' % (metric.capitalize()))
      self._draw_chart(self.min_y + 6 + index, self.min_x + 10, 
                       percent, chart, meta)

    self.addstr(self.min_y + 10, self.min_x + 2,
                'Tags: %s' % (tags))
    
  def _get_vertical_chart(self, check, metrics):
    # Return chart data for the provided metric
    chart_metric = NODE_METRICS[check]['chart_metric']
    display_metrics = NODE_METRICS[check]['metrics']
    wanted_metrics = display_metrics + [chart_metric]
    
    node_metrics = {}
    for metric in metrics:
      if metric['name'] in wanted_metrics:
        node_metrics[metric['name']] = metric['value']
      
    percent = NODE_METRICS[check]['normalization_function'](node_metrics, NODE_METRICS[check]['chart_metric'])
    
    lines = ''
    max_chart_width = self.max_x - 55
    percent_normalized = (max_chart_width / 100.0) * percent
    for index in range(0, max_chart_width):
      if index <= percent_normalized:
        lines += '|'
      else:
        lines += ' '
        
    display_values = tuple([str(node_metrics[m]) for m in display_metrics])
    display_values = NODE_METRICS[check]['format_function'](*display_values)
    chart = '%s' % (lines)
    chart_meta = '%s%% used (%s)' % (percent, (NODE_METRICS[check]['chart_text'] % display_values))
    
    return chart, chart_meta, percent
  
  def _draw_chart(self, y_offset, x_offset, percent, chart, chart_meta = ''):
    chart_length = len(chart) or 1
    if percent == None:
      color = curses.color_pair(1)
    elif percent < 50:
      color = curses.color_pair(2)
    elif percent >= 50 and percent <= 75:
      color = curses.color_pair(3)
    else:
      color = curses.color_pair(4)
    
    self.addstr(y_offset, x_offset,
                '[', curses.A_BOLD)
    self.addstr(y_offset, x_offset + 1,
                chart, color)
    self.addstr(y_offset, x_offset + chart_length + 1,
                ']', curses.A_BOLD)
    
    self.addstr(y_offset, x_offset + chart_length + 3,
                chart_meta)
    
  def _draw_node_list(self):
    # Draws the node list in the bottom part of the screen
    self.table_lines = []
    for index, node in enumerate(self.nodes):

      coord_y = (self.min_y + SCREEN_NODE_LIST_START) + (index + 2)
      if coord_y < self.max_y - 1:
        
        columns = []
        for column in NODE_TABLE_ROWS:
          
          value, width, align = node[column['field_name']], column['width'], column['align']
          column_string = self._get_table_column_string(value, width, align)
          columns.append(column_string)
    
        columns = '' . join(columns)
        self.table_lines.append(columns)
        self.addstr(coord_y, self.min_x, columns)

  def _draw_header(self):
    time = datetime.strftime(datetime.now(), '%m/%d/%Y %I:%M %p')
    
    self.addstr(self.min_y, 'center',
                __title__,
                 curses.A_BOLD)
    self.addstr(self.min_y, self.min_x,
                __version__,
                curses.A_BOLD)
    self.addstr(self.min_y, 'right',
                time,
                curses.A_BOLD)
    self.screen.hline(self.min_y + 1, self.min_x, '_', self.max_x)

  def _draw_footer(self):
    if self.last_updated:
      last_updated = datetime.strftime(self.last_updated, '%I:%M:%S %p')
    
    else:
      last_updated = '/'
      
    if self.updating_node_list:
      status = 'updating node list...'
    elif self.updating_node_metrics:
      status = 'updating node metrics...'
    else:
      status = ''

    self.addstr(self.max_y, self.min_x,
                'Updated: %s' % (last_updated),
                 curses.A_BOLD)
    self.addstr(self.max_y, 'center',
                status,
                curses.A_BOLD)
    self.addstr(self.max_y, 'right',
                'Nodes: %d' %
                (len(self.nodes)),
                curses.A_BOLD)
    
  def _draw_body(self):
    self._draw_table_header()
    self._draw_node_data()
    self._draw_node_list()
    
  def _draw_table_header(self):
    columns = []
    for column in NODE_TABLE_COLUMNS:
      name, width, align = column['name'].upper(), column['width'], column['align']
      
      column_string = self._get_table_column_string(name, width, align)
      columns.append(column_string)
    
    columns = '' . join(columns)
    self.addstr(self.min_y + SCREEN_NODE_TABLE_START, self.min_x, columns, curses.A_REVERSE)
    
  def _get_table_column_string(self, text, width, align):
    width = int(self.max_x * (width / 100.0))
      
    if align == 'center':
      column_string = text.center(width)
    elif align == 'left':
      column_string = text.ljust(width)
    else:
      column_string = text.rjust(width)
      
    return column_string
        
  def _redraw(self):
    self._update_max_size()
    self._check_min_screen_size()
    
    self.screen.clear()
    self._draw_header()
    self._draw_body()
    self._draw_selection()
    self._draw_footer()
    self._draw_node_data()
    
    self.screen.refresh()
    curses.doupdate()
    
  def _draw_selection(self):
    # Highlights the selection
    for index, line in enumerate(self.table_lines):
      if index == self.cursor_pos:
        attr = curses.A_REVERSE
      else:
        attr = 0
      
      coord_y = (self.min_y + SCREEN_NODE_LIST_START) + (index + 2)
      if coord_y < self.max_y - 1:
        self.addstr(coord_y, self.min_x, line, attr)
    
  def _update_max_size(self):
    max_y, max_x = self.screen.getmaxyx()
    
    self._max_y = max_y - 2
    self._max_x = max_x
    
  def _check_min_screen_size(self):
    if self.max_x < SCREEN_MIN_X or \
      self.max_y < SCREEN_MIN_Y:
      raise RuntimeError('Minimum screen size must be %sx%s lines' %
                         (SCREEN_MIN_X, SCREEN_MIN_Y))
    
  def _reset(self):
    # Resets the screen
    self.screen.keypad(0)
    curses.echo()
    curses.nocbreak()
    curses.endwin()
    
  def _clean(self):
    self.screen.erase()

  # Event handlers
  def _handle_key_event(self, key):
    if key in 'u':
      self._update_node_metrics(update_now = True)
    elif key in 'qQ':
      exit_handler()
        
  def _handle_movement_key(self, key):
    # Highlight the corresponding node in the list
    self.max_cursor_pos = len(self.table_lines) - 1
    if key == curses.KEY_UP:
      if self.cursor_pos > self.min_cursor_pos:
        self.cursor_pos -= 1

    elif key == curses.KEY_DOWN:
      if self.cursor_pos < self.max_cursor_pos:
        self.cursor_pos += 1
        
    elif key == curses.KEY_PPAGE:
      self.cursor_pos = 0
      
    elif key == curses.KEY_NPAGE:
      self.cursor_pos = self.max_cursor_pos
    
    self._update_node_metrics(update_now = True)
        
  def _handle_event(self, event):
    if event == curses.KEY_RESIZE:
      # Redraw the screen on resize
      self._redraw()
        
  # Helper methods
  def addstr(self, y, x, str, attr = 0):
    if x == 'center':
      x = self._get_center_offset(self.max_x, len(str))
    elif x == 'right':
      x = self._get_right_offset(self.max_x, len(str))
      
    if y == 'center':
      y = self._get_center_offset(self.max_y, len(str))
    elif y == 'right':
      y = self._get_right_offset(self.max_y, len(str))

    self.screen.addstr(y, x, str, attr)
    
  # Properties
  @property
  def max_y(self):
    return self._max_y
  
  @property
  def max_x(self):
    return self._max_x

  def _get_center_offset(self, max_offset, string_length):
    return ((max_offset / 2) - string_length / 2)
  
  def _get_right_offset(self, max_offset, string_length):
    return (max_offset - string_length)
  
class ScreenLine(object):
  def __init__(self, text = ''):
    self.text = text

def exit_handler(*args):
  # Wait for and stop all the running threads
  for thread in threading.enumerate():
    if thread != threading.current_thread():
      thread.running = False
      thread.join()
          
  screen._reset()
  sys.exit(0)
  
def validate_credentials(connection):
  try:
    connection.nodes()
  except Exception:
    return False
  
  return True

# Register exit signals
signal.signal(signal.SIGTERM, exit_handler)
signal.signal(signal.SIGINT, exit_handler)

if __name__ == '__main__':
  parser = OptionParser()
  parser.add_option('--oauth-key', dest='oauth_key',
                    help='OAuth consumer key')
  parser.add_option('--oauth-secret', dest='oauth_secret',
                    help = 'OAuth consumer secret')
  parser.add_option('--config-path', dest='config_path',
                    help = 'Path to the config file which contains OAuth credentials')
  
  (options, args) = parser.parse_args()
  
  if not (options.oauth_key or not options.oauth_secret) and \
     not options.config_path:
    print 'You need to provide the OAuth consumer and secret key or the path to the config file with the credentials'
    sys.exit(1)
  
  if options.config_path:
    connection = Connection(config_path = options.config_path)
  else:
    connection = Connection(oauth_key = options.oauth_key, \
                            oauth_secret = options.oauth_secret)
    
  if not validate_credentials(connection):
    print 'Invalid OAuth consumer and / or secret key provided'
    sys.exit(1)

  screen = Screen(connection)
  
  try:
    screen.run()
  except RuntimeError, e:
    screen._reset()
    print e
    sys.exit(1)
  except Exception, e:
    screen._reset()
    print e
    sys.exit(1)

