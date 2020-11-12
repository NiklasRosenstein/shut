
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
