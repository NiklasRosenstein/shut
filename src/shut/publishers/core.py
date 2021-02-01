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

import abc
from typing import Generic, Iterable, List, T, Type

from nr.stream import concat  # type: ignore

from shut.model import AbstractProjectModel
from shut.model.target import Target, TargetId
from shut.utils.type_registry import TypeRegistry

__all__ = [
  'Publisher',
  'PublisherProvider',
  'register_publisher_provider',
  'get_publishers',
]


class Publisher(Target, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def get_description(self) -> str:
    pass

  @abc.abstractmethod
  def get_build_dependencies(self) -> Iterable[TargetId]:
    """
    Return the IDs of build targets that this publisher depends on.
    """

  @abc.abstractmethod
  def publish(self, files: List[str], test: bool, verbose: bool) -> bool:
    """
    Run the publishing logic. The builders resolved from #get_build_dependencies() are
    passed to this function. They will already be built when this method is called.
    """


class PublisherProvider(Generic[T], metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def get_publishers(self, obj: T) -> Iterable[Publisher]:
    """
    Return the publishers provided by this plugin.
    """


registry = TypeRegistry[PublisherProvider[AbstractProjectModel]]()


def register_publisher_provider(type_: Type[T], provider_class: Type[PublisherProvider[T]]) -> None:
  registry.put(type_, provider_class)


def get_publishers(obj: T) -> Iterable[Publisher]:
  return concat(provider().get_publishers(obj) for provider in registry.for_type(type(obj)))
