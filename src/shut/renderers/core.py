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
from typing import Iterable, Generic, Type, TypeVar

from databind.core import datamodel

from shut.utils.io.virtual import VirtualFiles
from shut.utils.type_registry import TypeRegistry

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)

__all__ = [
  'VersionRef',
  'Renderer',
  'register_renderer',
  'get_files',
  'get_version_refs',
]


@datamodel
class VersionRef:
  filename: str
  start: int
  end: int
  value: str


class Renderer(Generic[T_co], metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def get_files(self, files: VirtualFiles, obj: T) -> None:
    pass

  def get_version_refs(self, obj: T) -> Iterable[VersionRef]:
    return; yield


registry = TypeRegistry[Renderer[T_co]]()


def register_renderer(t: Type[T_co], renderer: Type[Renderer[T_co]]) -> None:
  """
  Register the *renderer* implementation to run when creating files for *t*.
  """

  registry.put(t, renderer)


def get_files(obj: T) -> VirtualFiles:
  """
  Gets all the files from the renderers registered to the type of *obj*.
  """

  files = VirtualFiles()
  for renderer in registry.for_type(type(obj)):
    renderer().get_files(files, obj)

  return files


def get_version_refs(obj: T) -> Iterable[VersionRef]:
  """
  Gets all version refs returned by registered for type *T_co*.
  """

  for renderer in registry.for_type(type(obj)):
    yield from renderer().get_version_refs(obj)
