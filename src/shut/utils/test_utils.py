
import typing as t
import pytest
from shut.utils import checked_cast


def test_checked_cast():
  checked_cast(0, int)
  checked_cast(0.0, float)
  checked_cast(0, (int, float))

  with pytest.raises(TypeError):
    checked_cast(0, (float, str))

  with pytest.raises(TypeError):
    checked_cast(0, float)

  checked_cast([], t.List[int])
  checked_cast(['foo'], t.List)
  checked_cast(['foo'], t.List[int]) == ['foo']
