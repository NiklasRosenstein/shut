
import enum
import typing as t

from databind.core import datamodel

from shut.model import MonorepoModel, PackageModel




T_ConfigData = t.TypeVar('T_ConfigData', bound='ConfigData')


class ConfigNode:
  """
  A #ConfigNode is a container for #ConfigData subclasses.
  """

  def __init__(self, path: Path) -> None:
    self.path = path
    self.data: t.Dict[t.Type, ConfigData] = {}

  def add(self, data: ConfigData) -> None:
    if type(data) in self.data:
      raise RuntimeError(f'data element for type {type(data).__name__} already present')
    self.data[type(data)] = data

  def get(self, type_: t.Type[T_ConfigData]) -> t.Optional[T_ConfigData]:
    return self.data[type_]




if project := config.get(Project):
  pass
elif monorepo := config.get(Monorepo):
  pass





class Type(enum.Enum):
  PACKAGE = enum.auto()
  MONOREPO = enum.auto()


class Scope(t.NamedTuple):
  type: Type
  path: Path


class Project:
  """
  Represents a Slick project. A project is either a single package, or a multitude of projects
  combined under a mono repository.
  """

  def __init__(self, directory: Path) -> None:
    self.directory = directory
    self.packages: t.List[t.Tuple[Scope, PackageModel]] = []
    self.monorepo: t.Optional[t.Tuple[Scope, MonorepoModel]] = None
    self.errors: t.List[t.Tuple[Scope, BaseException]] = []
    self._load()

  def _load(self) -> None:
    """
    Internal. Loads the project configuration files. Any errors that are encountered while
    loading are stored in the #errors list.
    """





  def __bool__(self) -> bool:
    return bool(self.packages or self.monorepo)

  def is_package(self) -> bool:
    return len(self.packages) == 1 and not self.monorepo

  def is_monorepo(self) -> bool:
    return bool(self.monorepo) or len(self.packages) != 1

