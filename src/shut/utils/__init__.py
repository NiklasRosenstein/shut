
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


class ReadOnlyMapping(collections.Mapping, t.Generic[K, V]):

  def __init__(self, data: t.Mapping[K, V]) -> None:
    self._data = data

  def __getitem__(self, key: K) -> V:
    return self._data[key]

  def __len__(self) -> int:
    return len(self._data)

  def __iter__(self) -> t.Iterable[K]:
    return iter(self._data)
