
import importlib
import typing as t

from shut.tasks.core import TaskGraph


def apply(graph: TaskGraph, plugin_module: str) -> None:
  """
  Applies the plugin from *plugin_module* to the *graph*. Skips if the plugin was already applied
  to the graph.
  """

  applied_plugins = t.cast(t.Set[str], graph.custom_data.setdefault('applied_plugins', set()))
  if plugin_module in applied_plugins:
    return

  module = importlib.import_module(plugin_module)
  module.register_plugin(graph)


class ConfigNode:
  """
  A config node represents a file on disk that contains configuration data and is composed of
  arbitrary data elements. Once the node is populated, it's data elements are
  """


class DataElement:
  """
  A data element on a #ConfigNode.
  """

  def extend_task_group(self, group: TaskGroup) -> None:
    """
    Called to create tasks in the specified *group*.
    """


class PrimaryDataElement(DataElement):
  """
  A primary data element can dictate some global behavior on a #ConfigNode.
  """

  def get_name(self) -> str:
    raise NotImplementedError
