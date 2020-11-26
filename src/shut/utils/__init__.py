
import collections
import typing as t

T = t.TypeVar('T')
K = t.TypeVar('K')
V = t.TypeVar('V')


def expect(val: t.Optional[T], message: t.Optional[str] = None) -> T:
  """
  Expects that *val* is not None and returns it.
  """

  if val is None:
    raise RuntimeError(message or 'expected value to be not None')
  return val


def checked_cast(val: t.Any, expected_type: t.Type[T]) -> T:
  """
  Cast *val* to the specified type(s) and check it.
  """

  if hasattr(expected_type, '__origin__'):
    # NOTE(NiklasRosenstein): We do not check specialized types recursively.
    expected_type = expected_type.__origin__

  if not isinstance(val, expected_type):
    raise TypeError(f'expected on of {type(expected_type).__name__}, got {type(val).__name__}')

  return val


class ReadOnlyMapping(collections.abc.Mapping, t.Generic[K, V]):

  def __init__(self, data: t.Mapping[K, V]) -> None:
    self._data = data

  def __getitem__(self, key: K) -> V:
    return self._data[key]

  def __len__(self) -> int:
    return len(self._data)

  def __iter__(self) -> t.Iterable[K]:
    return iter(self._data)
