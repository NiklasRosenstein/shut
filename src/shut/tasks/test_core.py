
from shut.tasks.core import Task, TaskGraph, TaskGroup
import pytest


def make_graph(num: int, connect_up_to: int = 0) -> TaskGraph:
  g = TaskGraph()
  prev = None
  for i in range(num):
    t = Task(str(i + 1))
    g.add_task(t)
    if prev and i < connect_up_to:
      t.depends_on(prev)
    prev = t
  return g


def test_task_ordering_01():
  g = make_graph(3, 3)
  assert g.ordered_tasks() == [g['1'], g['2'], g['3']]


def test_task_ordering_02():
  g = make_graph(4, 3)
  g['4'].depends_on([g['1'], g['2']])
  g['3'].depends_on(g['4'])
  assert g.ordered_tasks() == [g['1'], g['2'], g['4'], g['3']]


def test_task_grouping_01():
  graph = TaskGraph()
  g1 = TaskGroup('g1')
  t1 = Task('t1')
  graph.add_group(g1)
  g1.add_task(t1)

  assert t1.parent == g1
  assert g1.parent == None

  assert g1.id == 'g1'
  assert t1.id == 'g1:t1'
