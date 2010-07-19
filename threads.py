import time
import threading

from datetime import datetime
from constants import NODE_LIST_UPDATE_INTERVAL, \
                      NODE_METRICS_UPDATE_INTERVAL

class NodeListThread(threading.Thread):
  def __init__(self, parent):
    super(NodeListThread, self).__init__()
    self.connection = parent.connection
    self.parent = parent
    
    self.running = True
    
  def run(self):
    
    i = 0
    while self.running:
      if not self.parent.nodes or \
        i == NODE_LIST_UPDATE_INTERVAL * 10:
        self.parent.updating_node_list = True
        self.parent.nodes = self.connection.nodes()
        self.parent.updating_node_list = False
        
        i = 0
      
      i += 1
      time.sleep(0.1)
    
class NodeMetricsThread(threading.Thread):
  def __init__(self, parent):
    super(NodeMetricsThread, self).__init__()
    self.connection = parent.connection
    self.parent = parent
    
    self.node_id = None
    self.update_now = False
    self.running = True
    
  def run(self):
    
    i = 0
    while self.running:
      if self.node_id and \
         (i == NODE_METRICS_UPDATE_INTERVAL * 10 or \
         self.update_now == True):
        
        self.parent.updating_node_metrics = True
        cpu_metrics = self.connection.live_data(self.node_id, 'cpu')['metrics']
        mem_metrics = self.connection.live_data(self.node_id, 'mem')['metrics']
        disk_metrics = self.connection.live_data(self.node_id, 'disk')['metrics']
        
        # Only update the metrics data if the currently updated node is still
        # selected
        if self.parent.nodes[self.parent.cursor_pos]['id'] == self.node_id:
          self.parent.node_metrics = {'cpu': cpu_metrics, 'mem': mem_metrics, \
                                      'disk': disk_metrics}
          self.parent.last_updated = datetime.now()
          self.parent.last_updated_node = self.node_id
        self.update_now = False
        self.parent.updating_node_metrics = False
        
        i = 0
      
      i += 1
      time.sleep(0.1)