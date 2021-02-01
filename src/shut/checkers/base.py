# -*- coding: utf8 -*-
# Copyright (c) 2020 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
API for describing sanity checks around a package or monorepo configuration.
"""

from typing import Callable, Iterable, Generic, NamedTuple, Optional, Type, TypeVar
import enum
import types

from shut.model import AbstractProjectModel
from shut.utils.type_registry import TypeRegistry

__all__ = [
  'CheckStatus',
  'CheckResult',
  'Check',
  'register_checker',
  'get_checks',
]

T = TypeVar('T')


class CheckStatus(enum.IntEnum):
  PASSED = enum.auto()  #: The check has passed.
  WARNING = enum.auto()  #: The check is merely giving a warning.
  ERROR = enum.auto()  #: The check has an error, something is in a bad or invalid state.


class CheckResult(NamedTuple):
  """
  Yield this from a #@check() decorated method on a #Checker subclass to return a result
  for the check. Multiple results can be returned from a check.
  """

  status: CheckStatus
  message: str
  subject: Optional[AbstractProjectModel] = None


class SkipCheck(NamedTuple):
  """
  Yield this from a #@check() decorated method on a #Checker subclass to indicate that the
  check should be skipped. This is different from not yielding anything as the check will be
  considered successful in that case.
  """


class Check(NamedTuple):
  name: str
  result: CheckResult


def check(name: str) -> Callable[[Callable], Callable]:
  """
  Decorator for methods on a #Checker instance.
  """

  def decorator(func: Callable) -> Callable:
    func.__check_name__ = name  # type: ignore
    return func

  return decorator


class Checker(Generic[T]):

  def get_checks(self, subject: T) -> Iterable[Check]:
    """
    Yield #Check objects for the *subject*. By default, all methods decorated with
    #check() are called.
    """

    for key in dir(self):
      value = getattr(self, key)
      check_value = value
      if isinstance(value, types.MethodType):
        check_value = value.__func__
      if isinstance(check_value, types.FunctionType) and hasattr(check_value, '__check_name__'):
        index = None
        for index, result in enumerate(value(subject)):
          if not isinstance(result, SkipCheck):
            yield Check(value.__check_name__, result)
        if index is None:
          yield Check(value.__check_name__, CheckResult(CheckStatus.PASSED, None))


registry = TypeRegistry[Checker]()


def register_checker(t: Type[T], checker: Type[Checker[T]]) -> None:
  """
  Register a *checker* class to run checks for type *t*.
  """

  registry.put(t, checker)


def get_checks(obj: T) -> Iterable[Check]:
  """
  Returns all checks from the checkers registered for the type of *obj*.
  """

  for checker in registry.for_type(type(obj)):
    yield from checker().get_checks(obj)
