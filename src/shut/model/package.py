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

import ast
import os
import re
from typing import Dict, List, Optional, Union

from databind.core import datamodel, field
from nr.stream import chain, concat  # type: ignore

from shut.utils.ast import load_module_members
from shut.utils.fs import get_file_in_directory
from .author import Author
from .abstract import AbstractProjectModel
from .linter import LinterConfiguration
from .publish import PublishConfiguration
from .requirements import Requirement, RequirementsList
from .test import TestDriver
from .version import Version


class PackageError(Exception):
  pass


@datamodel
class InstallConfiguration:
  @datamodel
  class InstallHooks:
    before_install: List[str] = field(altname='before-install', default_factory=list)
    after_install: List[str] = field(altname='after-install', default_factory=list)
    before_develop: List[str] = field(altname='before-develop', default_factory=list)
    after_develop: List[str] = field(altname='after-develop', default_factory=list)

    def any(self):
      return any((self.before_install, self.after_install, self.before_develop, self.after_develop))

  hooks: InstallHooks = field(default_factory=InstallHooks)

  #: A value for the `--index-url` option to pass to Pip when using `shut pkg install`.
  index_url: Optional[str] = field(altname='index-url', default=None)

  #: A list of URLs to pass to Pip via the `--extra-index-url` option when using
  #: `shut pkg install`.
  extra_index_urls: List[str] = field(altname='extra-index-urls', default_factory=list)

  def get_pip_args(self) -> List[str]:
    result = []
    if self.index_url:
      result += ['--index-url', self.index_url]
    for url in self.extra_index_urls:
      result += ['--extra-index-url', url]
    return result


@datamodel
class Include:
  include: str


@datamodel
class Exclude:
  exclude: str


@datamodel
class PackageModel(AbstractProjectModel):
  modulename: Optional[str] = None
  description: Optional[str] = None
  readme: Optional[str] = None
  wheel: Optional[bool] = True
  universal: Optional[bool] = None
  typed: Optional[bool] = False
  requirements: RequirementsList = field(default_factory=RequirementsList)
  test_requirements: RequirementsList = field(altname='test-requirements', default_factory=RequirementsList)
  extra_requirements: Dict[str, RequirementsList] = field(altname='extra-requirements', default_factory=dict)
  source_directory: str = field(altname='source-directory', default='src')
  exclude: List[str] = field(default_factory=lambda: ['test', 'tests', 'docs'])
  entrypoints: Dict[str, List[str]] = field(default_factory=dict)
  classifiers: List[str] = field(default_factory=list)
  keywords: List[str] = field(default_factory=list)
  package_data: List[Union[Include, Exclude]] = field(altname='package-data', default_factory=list)

  install: InstallConfiguration = field(default_factory=InstallConfiguration)
  linter: LinterConfiguration = field(default_factory=LinterConfiguration)
  publish: PublishConfiguration = field(default_factory=PublishConfiguration)
  test_driver: TestDriver = field(altname='test-driver', default=None)

  def get_modulename(self) -> str:
    if self.modulename:
      return self.modulename

    # Check for PEP-561 stub packages.
    # See also https://mypy.readthedocs.io/en/latest/installed_packages.html#making-pep-561-compatible-packages
    if self.name.endswith('-stubs'):
      return self.name[:-6].replace('-', '_') + '-stubs'

    return self.name.replace('-', '_')

  def get_python_requirement(self) -> Optional[Requirement]:
    return next(filter(lambda x: isinstance(x, Requirement) and x.package == 'python', self.requirements), None)

  def has_vendored_requirements(self) -> bool:
    """
    Returns #True if the package has any vendored requirements.
    """

    return any(chain(
      self.requirements.vendored_reqs(),
      self.test_requirements.vendored_reqs(),
      concat(l.vendored_reqs() for l in self.extra_requirements.values())
    ))

  def is_universal(self) -> bool:
    """
    Checks if the package is a universal Python package (i.e. it is Python 2 and 3 compatible)
    by testing the `$.requirements.python` version selector. If none is specified, the package
    is also considered universal.
    """

    if self.universal is not None:
      return self.universal

    python_requirement = self.get_python_requirement()
    if not python_requirement:
      return True

    # TODO (@NiklasRosenstein): This method of detecting if the version selector
    #   selects a Python 2 and 3 version is very suboptimal.
    has_2 = re.search(r'\b2\b|\b2\.\b', str(python_requirement))
    has_3 = re.search(r'\b3\b|\b3\.\b', str(python_requirement))
    return bool(has_2 and has_3)

  def get_python_package_metadata(self) -> 'PythonPackageMetadata':
    """
    Returns a #PythonPackageMetadata object for this #PackageModel. This object can be
    used to inspect the author and version information that is defined in the package
    source code.
    """

    return PythonPackageMetadata(
      os.path.join(os.path.dirname(self.filename), self.source_directory),
      self.get_modulename())

  def get_readme_file(self) -> Optional[str]:
    """
    Returns the absolute path to the README for this package.
    """

    directory = os.path.dirname(self.filename)

    if self.readme:
      return os.path.abspath(os.path.join(directory, self.readme))

    return get_file_in_directory(
      directory=directory,
      prefix='README.',
      preferred=['README.md', 'README.rst', 'README.txt', 'README'])

  def get_py_typed_file(self) -> Optional[str]:
    if not self.typed:
      return None

    directory = self.get_python_package_metadata().package_directory
    return os.path.join(directory, 'py.typed')

  def get_publish_config(self) -> PublishConfiguration:
    if self.project and self.project.monorepo and self.project.monorepo.publish:
      return self.project.monorepo.publish
    return self.publish

  def get_license(self) -> Optional[str]:
    if self.license:
      return self.license
    if self.project.monorepo:
      return self.project.monorepo.license
    return None

  def get_author(self) -> Optional[Author]:
    if self.author:
      return self.author
    if self.project.monorepo:
      return self.project.monorepo.author
    return None

  def get_url(self) -> Optional[str]:
    if self.url:
      return self.url
    if self.project.monorepo:
      return self.project.monorepo.url
    return None

  # AbstractProjectModel

  def get_name(self) -> str:
    return self.name

  def get_version(self) -> Optional[Version]:
    if self.version:
      return self.version
    if self.project.monorepo and self.project.monorepo.release.single_version:
      return self.project.monorepo.get_version()
    return None

  def get_tag(self, version: Version) -> str:
    tag_format = self.release.tag_format
    if self.project and self.project.monorepo and '{name}' not in tag_format:
      tag_format = '{name}@' + tag_format
    return tag_format.format(name=self.name, version=version)

  def get_license_file(self, inherit: bool = False) -> Optional[str]:
    if not self.license_file and inherit and self.project.monorepo and \
        (not self.license or self.license == self.project.monorepo.license):
      filename = self.project.monorepo.get_license_file()
      if filename:
        return os.path.join(self.project.monorepo.get_directory(), filename)
    return super().get_license_file(False)


class PythonPackageMetadata:
  """
  Represents the metadata of a Python package on disk.
  """

  def __init__(self, source_directory: str, modulename: str) -> None:
    self.source_directory = source_directory
    self.modulename = modulename
    self._filename = None
    self._author = None
    self._version = None

  @property
  def filename(self) -> str:
    """
    Returns the file that contains the package metadata in the Python source code. This is
    usually the module filename, the package `__init__.py` or `__version__.py`.
    """

    if self._filename:
      return self._filename

    parts = self.modulename.split('.')
    prefix = os.sep.join(parts[:-1])
    choices = [
      parts[-1] + '.py',
      os.path.join(parts[-1], '__version__.py'),
      os.path.join(parts[-1], '__init__.py'),
    ]
    for filename in choices:
      filename = os.path.join(self.source_directory, prefix, filename)
      if os.path.isfile(filename):
        self._filename = filename
        return filename

    raise PackageError('Entry file for package "{}" could not be determined'
                       .format(self.modulename))

  @property
  def package_directory(self) -> str:
    """
    Returns the Python package directory. Raises a #ValueError if this metadata represents
    just a single Python module.
    """

    if self.is_single_module:
      raise ValueError('this package is in module-only form')

    return os.path.dirname(self.filename) or '.'

  @property
  def is_single_module(self) -> bool:
    basename = os.path.basename(self.filename)
    return basename not in ('__init__.py', '__version__.py')

  @property
  def author(self) -> str:
    if not self._author:
      self._load_metadata()
    return self._author

  @property
  def version(self) -> str:
    if not self._version:
      self._load_metadata()
    return self._version

  def _load_metadata(self) -> None:
    members = load_module_members(self.filename)

    author = None
    version = None

    if '__version__' in members:
      try:
        version = ast.literal_eval(members['__version__'])
      except ValueError:
        version = '<Non-literal expression>'

    if '__author__' in members:
      try:
        author = ast.literal_eval(members['__author__'])
      except ValueError:
        author = '<Non-literal expression>'

    self._author = author
    self._version = version
