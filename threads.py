import threading

from datetime import datetime

class NodeListThread(threading.Thread):
  def __init__(self, parent):
    super(NodeListThread, self).__init__()
    self.connection = parent.connection
    self.parent = parent
    
  def run(self):
    self.parent.nodes = self.connection.nodes()
    
class NodeMetricsThread(threading.Thread):
  def __init__(self, parent, node_id):
    super(NodeMetricsThread, self).__init__()
    self.connection = parent.connection
    self.parent = parent
    self.node_id = node_id
    
  def run(self):
    cpu_metrics = self.connection.live_data(self.node_id, 'cpu')['metrics']
    mem_metrics = self.connection.live_data(self.node_id, 'mem')['metrics']
    disk_metrics = self.connection.live_data(self.node_id, 'disk')['metrics']
    
    # Only update the metrics data if the currently updated node is still
    # selected
    if self.parent.nodes[self.parent.cursor_pos]['id'] == self.node_id:
      self.parent.node_metrics = {'cpu': cpu_metrics, 'mem': mem_metrics, \
                                    'disk': disk_metrics}
      self.parent.last_updated = datetime.now()
    self.parent.updating_metrics = False