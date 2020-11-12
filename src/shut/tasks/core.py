
import enum
import collections
import typing as t
import types
import weakref

import networkx as nx

from shut.utils import expect, ReadOnlyMapping


class Skip(Exception):
  pass


class ExcInfo(t.NamedTuple):
  type: t.Type[BaseException]
  val: BaseException
  tb: types.TracebackType


class _NamedObject:

  VisitorFunc = t.Callable[['_NamedObject'], None]

  def __init__(self, name: str) -> None:
    self._name = name
    self._graph: t.Optional[weakref.ReferenceType['TaskGraph']] = None
    self._parent: t.Optional[weakref.ReferenceType['TaskGroup']] = None

  @property
  def id(self) -> str:
    parent = self.parent
    if parent:
      return parent.id + ':' + self._name
    return self._name

  @property
  def name(self) -> str:
    return self._name

  @property
  def graph(self) -> t.Optional['TaskGraph']:
    if self._graph is None:
      return None
    return self._graph()

  @property
  def parent(self) -> t.Optional['TaskGroup']:
    if self._parent is None:
      return None
    return self._parent()

  def visit(self, func: VisitorFunc) -> None:
    raise NotImplementedError

  def _ensure_same_graph(self, other: '_NamedObject') -> None:
    if self.graph != other.graph:
      raise RuntimeError(f'expected {other!r} in the same graph (or both in none) as {self!r}')


class TaskStatus(enum.Enum):
  PENDING = enum.auto()
  RUNNING = enum.auto()
  SKIPPED = enum.auto()
  SUCCESS = enum.auto()
  ERROR = enum.auto()


class Task(_NamedObject):
  """
  Represents a task that can have dependencies on other task and perform an action when it is
  executed.
  """

  Status = TaskStatus

  def __init__(self, name: str) -> None:
    super().__init__(name)
    self._status = TaskStatus.PENDING
    self._error: t.Optional[ExcInfo] = None

  def __repr__(self) -> str:
    return f'{type(self).__name__}(id={self.id!r})'

  @property
  def status(self) -> TaskStatus:
    return self._status

  @property
  def dependencies(self) -> t.List['Task']:
    """
    Returns a list of the dependencies for this task.
    """

    return expect(self.graph)._get_dependencies(self)

  @property
  def dependants(self) -> t.List['Task']:
    """
    Returns a list of the tasks that depend on this task.
    """

    return expect(self.graph)._get_dependants(self)

  def skip(self) -> t.NoReturn:
    """
    Call from inside #_execute_internal() to mark the execution as skipped. Raises a #Skip error.
    """

    raise Skip

  def execute(self) -> None:
    """
    Execute the task. Cannot be called multiple times. This calls #_execute_internal() and catches
    any exception to store it in the #error property and set the status to #TaskStatus.ERROR. If
    no exception occurs, the #status will be set to #TaskStatus.SUCCESS.
    """

    if self._status != TaskStatus.PENDING:
      raise RuntimeError(f'task "{self.id}" was already executed (status: {self.status.name})')

    self._status = TaskStatus.RUNNING
    self.graph.trigger_event('task.begin', self)
    try:
      self._execute_internal()
      self._status = TaskStatus.SUCCESS
    except Skip:
      self._status = TaskStatus.SKIPPED
    except BaseException:
      self._status = TaskStatus.ERROR
      self._error = ExcInfo(*sys.exc_info())
    finally:
      self.graph.trigger_event('task.end', self)

  def _execute_internal(self) -> None:
    raise NotImplementedError

  def depends_on(self, tasks: t.Union['Task', t.Iterable['Task']]) -> None:
    if isinstance(tasks, Task):
      tasks = [tasks]
    for task in tasks:
      self.graph._add_edge(task, self)

  # _NamedObject overrides

  def visit(self, func: _NamedObject.VisitorFunc) -> None:
    func(self)


class TaskGroup(_NamedObject):
  """
  Represents a group of tasks. Groups can contain other groups.
  """

  def __init__(self, name: str) -> str:
    super().__init__(name)
    self._groups: t.Dict[str, 'TaskGroup'] = {}
    self._tasks: t.Dict[str, 'Task'] = {}

  def __contains__(self, key: str) -> bool:
    return key in self._groups or key in self._tasks

  def __getitem__(self, key: str) -> t.Union['TaskGroup', 'Task']:
    try:
      return self._groups[key]
    except KeyError:
      return self._tasks[key]

  @property
  def groups(self) -> t.Mapping[str, 'TaskGroup']:
    return ReadOnlyMapping(self._groups)

  @property
  def tasks(self) -> t.Mapping[str, 'Task']:
    return ReadOnlyMapping(self._tasks)

  def add_group(self, group: 'TaskGroup') -> None:
    """
    Adds a sub group to this group. The group must be registered to the graph before a sub group
    can be added to it.
    """

    if not self.graph:
      raise RuntimeError(f'{self!r} must be in graph before task can be added')

    if group.graph is not None:
      raise RuntimeError(f'{group!r} is already added to a graph')

    if group.name in self:
      raise ValueError(f'{group!r} cannot be added to {self!r}, name already used')

    self._groups[group.name] = group
    group._parent = weakref.ref(self)
    self.graph.add_group(group)

  def add_task(self, task: 'Task') -> None:
    """
    Adds a task to the group. The task will be registered to the graph as well. The group must
    be registered to a graph before a task can be added to it.
    """

    if not self.graph:
      raise RuntimeError(f'{self!r} must be in graph before task can be added')

    if task.graph is not None:
      raise RuntimeError(f'{task!r} is already added to a graph')

    if task.name in self:
      raise ValueError(f'{task!r} cannot be added to {self!r}, name already used')

    self._tasks[task.name] = task
    task._parent = weakref.ref(self)
    self.graph.add_task(task)

  # _NamedObject overrides

  def visit(self, func: _NamedObject.VisitorFunc) -> None:
    func(self)
    for task in self._tasks.values():
      task.visit(func)
    for group in self._groups.values():
      group.visit(func)


class TaskGraph(TaskGroup):
  """
  Represents a directed graph of tasks.
  """

  EventListenerFunc = t.Callable[[str, t.Any], None]

  def __init__(self, event_listener: t.Optional[EventListenerFunc] = None):
    self._tasks: t.Dict[str, Task] = {}
    self._groups: t.Dict[str, TaskGroup] = {}
    self._graph = nx.DiGraph()
    self._event_listener = event_listener
    self.custom_data: t.Dict[str, Any] = {}

  def __contains__(self, task: t.Union[str, Task]) -> bool:
    if isinstance(task, Task):
      return task.id in self._tasks and task == self._tasks[task.id]
    elif isinstance(task, str):
      return task.id in self._tasks
    else:
      return False

  def __getitem__(self, name: str) -> t.Union[Task, TaskGroup]:
    try:
      return self._groups[name]
    except KeyError:
      return self._tasks[name]

  def _add_edge(self, a: Task, b: Task) -> None:
    assert isinstance(a, Task)
    assert isinstance(b, Task)
    assert a.id in self._tasks
    assert b.id in self._tasks
    self._graph.add_edge(a.id, b.id)

  def add_group(self, group: TaskGroup) -> None:
    assert isinstance(group, TaskGroup)
    assert not group.graph
    self._groups[group.id] = group
    group._graph = weakref.ref(self)

  def create_group(self, name: str, parent: t.Optional[TaskGroup] = None) -> TaskGroup:
    group = TaskGroup(name)
    if parent:
      assert parent.graph is self
      parent.add_group(group)
    else:
      self.add_group(group)
    return group

  def add_task(self, task: Task) -> None:
    assert isinstance(task, Task)
    assert not task.graph
    if task.id in self._tasks:
      raise RuntimeError(f'task id {task.id!r} already used')
    task._graph = weakref.ref(self)
    self._tasks[task.id] = task
    self._graph.add_node(task.id)

  @property
  def groups(self) -> t.Mapping[str, TaskGroup]:
    return ReadOnlyMapping(self._groups)

  @property
  def tasks(self) -> t.Mapping[str, Task]:
    return ReadOnlyMapping(self._tasks)

  def select(self, value: t.Union[str, t.List[str]]) -> t.List[Task]:
    """
    Selects a set of tasks by their ID or parent group ID.
    """

    if isinstance(value, str):
      value = [value]

    tasks = set()
    for name in value:
      item = self[name]
      if isinstance(item, TaskGroup):
        tasks.update(item.tasks.values())
        tasks.update([g.id for g in item.groups.values()])
      else:
        tasks.add(item)

    return tasks

  def ordered_tasks(self, select: t.Union[str, t.List[str], None] = None) -> t.List[Task]:
    """
    Returns a list of tasks in the order they need to be executed. If *select* is specified,
    the returned list only includes the tasks that need to be executed for the selected tasks.
    You can also select groups of tasks.
    """

    if select is not None:
      # Create a copy of the graph that contains only the selected tasks and their in nodes.
      stack = collections.deque(t.id for t in self.select(select))
      nodes: t.Set[str] = set()
      while stack:
        task_id = stack.popleft()
        nodes.add(task_id)
        stack.extend(e[0] for e in self._graph.in_edges(task_id))
      graph = self._graph.subgraph(nodes)

    else:
      graph = self._graph

    return [self._tasks[t_id] for t_id in nx.algorithms.topological_sort(graph)]

  def trigger_event(self, event_name: str, data: t.Any) -> None:
    if self._event_listener:
      self._event_listener(event_name, data)
