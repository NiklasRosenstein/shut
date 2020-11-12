
import typing as t

T = t.TypeVar('T')


def expect(val: t.Optional[T], message: t.Optional[str] = None) -> T:
  """
  Expects that *val* is not None and returns it.
  """

  if val is None:
    raise RuntimeError(message or 'expected value to be not None')
  return val
