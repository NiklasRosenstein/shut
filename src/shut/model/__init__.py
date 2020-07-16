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

from typing import List, Type, TypeVar

from nr.databind.core import ObjectMapper
from nr.databind.json import JsonModule
import yaml

import os

from .monorepo import MonorepoModel
from .package import PackageModel

T = TypeVar('T')


def get_existing_file(directory: str, choices: List[str]) -> bool:
  for fn in choices:
    path = os.path.join(directory, fn)
    if os.path.isfile(path):
      return path
  return None


class Project:
  """
  Loads package and mono repo configuration files and caches them to ensure that
  the same filename is never loaded into a different model object.
  """

  monorepo_filenames = ['monorepo.yml', 'monorepo.yaml']
  package_filenames = ['package.yml', 'package.yaml']

  def __init__(self, mapper: ObjectMapper = None):
    self._cache = {}
    self.mapper = mapper or ObjectMapper(JsonModule())
    self.subject: Union[MonorepoModel, PackageModel] = None
    self.monorepo: MonorepoModel = None
    self.packages: List[PackageModel] = []

  def load(self, directory: str) -> None:
    """
    Loads all project information from *directory*. This searches in all parent directories
    for a package or monorepo configuration, then loads all resources that belong to the
    project.
    """

    monorepo_fn = None
    package_fn = None

    # TODO(NiklasRosenstein): Iterate parent dirs until match is found.
    for dirname in [directory]:
      package_fn = get_existing_file(dirname, self.package_filenames)
      if package_fn:
        break
      monorepo_fn = get_existing_file(dirname, self.monorepo_filenames)
      if monorepo_fn:
        break

    if package_fn:
      monorepo_fn = get_existing_file(os.path.dirname(os.path.dirname(package_fn)),
                                      self.monorepo_filenames)

    if monorepo_fn:
      self.subject = self._load_monorepo(monorepo_fn)
    if package_fn:
      self.subject = self._load_package(package_fn)

  def _load_object(self, filename: str, type_: Type[T]) -> T:
    filename = os.path.normpath(os.path.abspath(filename))
    if filename in self._cache:
      obj = self._cache[filename]
      assert isinstance(obj, type_), 'type mismatch: have {} but expected {}'.format(
        type(obj).__name__, type_.__name__)
      return obj
    with open(filename) as fp:
      data = yaml.safe_load(fp)
    # TODO(NiklasRosenstein): Store unknown keys
    obj = self._cache[filename] = self.mapper.deserialize(data, type_, filename=filename)
    return obj

  def _load_monorepo(self, filename: str) -> MonorepoModel:
    self.monorepo = self._load_object(filename, MonorepoModel)

    # Load packages in that monorepo.
    directory = os.path.dirname(filename)
    for item_name in os.path.listdir(directory):
      package_fn = get_existing_file(os.path.join(directory, item_name), self.package_filenames)
      if package_fn:
        self._load_package(package_fn)

    return self.monorepo

  def _load_package(self, filename: str) -> PackageModel:
    package = self._load_object(filename, PackageModel)
    if package not in self.packages:
      self.packages.append(package)
    return package
