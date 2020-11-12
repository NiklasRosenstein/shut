
from shut.tasks.core import Task, TaskGraph, TaskGroup


class TestCheckTask(Task):

  def _execute_internal(self) -> None:
    print('test check task!')


def register_plugin(graph: TaskGraph):
  checks_group = graph.create_group('checks')
  checks_group.add_task(TestCheckTask('test'))
