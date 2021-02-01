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

import os
import sys
from typing import Any, Dict, List, Optional, TextIO, Tuple, Type, TypeVar, Union

import nr.fs  # type: ignore
import yaml
from databind.core import ConversionError, datamodel, field, Registry
from databind.json import from_json, to_json, registry as json_registry

registry = Registry(json_registry)
registry.set_option(datamodel, 'skip_defaults', True)
T = TypeVar('T')
ExcInfo = Tuple


def get_existing_file(directory: str, choices: List[str]) -> bool:
  for fn in choices:
    path = os.path.join(directory, fn)
    if os.path.isfile(path):
      return path
  return None


class Unexpected(Exception):

  def __init__(self, expected, got):
    self.expected = expected
    self.got = got

  def __str__(self):
    return f'expected: {self.expected}, got {self.got}'


class Project:
  """
  Loads package and mono repo configuration files and caches them to ensure that
  the same filename is never loaded into a different model object.
  """

  monorepo_filenames = ['monorepo.yml', 'monorepo.yaml']
  package_filenames = ['package.yml', 'package.yaml']

  Unexpected = Unexpected

  def __init__(self):
    self._cache: Dict[str, 'AbstractProjectModel'] = {}
    self.subject: 'AbstractProjectModel' = None
    self.monorepo: MonorepoModel = None
    self.packages: List[PackageModel] = []
    self.invalid_packages: List[Tuple[str, ExcInfo]] = []

  def load(
    self,
    directory: str = '.',
    expect: Optional[Type['AbstractProjectModel']] = None,
  ) -> 'AbstractProjectModel':
    """
    Loads all project information from *directory*. This searches in all parent directories
    for a package or monorepo configuration, then loads all resources that belong to the
    project.
    """

    directory = os.path.abspath(directory)
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

    if expect and not isinstance(self.subject, expect):
      raise Unexpected(expect, type(self.subject))

    return self.subject

  def reload(self) -> None:
    """
    Reloads the monorepo and packages.
    """

    if self.monorepo:
      self._reload(self.monorepo)

    for package in self.packages:
      self._reload(package)

  def _reload(self, obj: 'AbstractProjectModel') -> None:
    result = self._load_object(obj.filename, type(obj), force=True)
    vars(obj).update(vars(result))

  def load_or_exit(self, *args, **kwargs):
    try:
      return self.load(*args, **kwargs)
    except Unexpected as exc:
      if exc.expected == MonorepoModel:
        sys.exit('error: not in a mono repository context')
      elif exc.expected == PackageModel:
        sys.exit('error: not in a package context')
      else:
        raise

  def _load_object(self, filename: str, type_: Type[T], force: bool = False) -> T:
    filename = os.path.normpath(os.path.abspath(filename))
    if not force and filename in self._cache:
      obj = self._cache[filename]
      assert isinstance(obj, type_), 'type mismatch: have {} but expected {}'.format(
        type(obj).__name__, type_.__name__)
      return obj
    with open(filename) as fp:
      data = yaml.safe_load(fp)
    #node_collector = NodeCollector()
    obj = self._cache[filename] = from_json(type_, data, registry=registry)
    obj.filename = filename
    obj.project = self
    #obj.unknown_keys = list(Stream.concat(
    #    (x.locator.append(k) for k in x.unknowns)
    #    for x in node_collector.nodes))
    return obj

  def _load_monorepo(self, filename: str) -> 'MonorepoModel':
    self.monorepo = self._load_object(filename, MonorepoModel)

    # Load packages in that monorepo.
    directory = os.path.dirname(filename)
    for item_name in os.listdir(directory):
      package_fn = get_existing_file(os.path.join(directory, item_name), self.package_filenames)
      if package_fn:
        try:
          self._load_package(package_fn)
        except ConversionError as exc:
          self.invalid_packages.append((item_name, sys.exc_info()))

    return self.monorepo

  def _load_package(self, filename: str) -> 'PackageModel':
    package = self._load_object(filename, PackageModel)
    if package not in self.packages:
      self.packages.append(package)
    return package


def dump(obj: Any, file_: Union[str, TextIO]) -> None:
  if isinstance(file_, str):
    with nr.fs.atomic_file(file_, 'w') as fp:
      dump(obj, fp)
  else:
    data = to_json(obj, registry=registry)
    yaml.safe_dump(data, file_, sort_keys=False)


from .abstract import AbstractProjectModel
from .monorepo import MonorepoModel
from .package import PackageModel