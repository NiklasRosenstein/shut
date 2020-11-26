
from shut.tasks.core import TaskGraph
from shut.plugins import apply


def on_event(name, data):
  print('@', name, data)


g = TaskGraph(on_event)
apply(g, 'shut.plugins.checks')
g.create_group('foo')

for task in g.ordered_tasks('checks'):
  task.execute()
