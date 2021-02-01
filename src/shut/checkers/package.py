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
from typing import Iterable

from shut.model.package import PackageError, PackageModel
from shut.renderers import get_files
from shut.utils.external.classifiers import get_classifiers
from .base import CheckResult, CheckStatus, Checker, SkipCheck, check, register_checker


class PackageChecker(Checker[PackageModel]):

  @check('readme')
  def _check_readme(self, package: PackageModel) -> Iterable[CheckResult]:
    if not package.get_readme_file():
      yield CheckResult(CheckStatus.WARNING, 'No README file found.')

  @check('license')
  def _check_license(self, package: PackageModel) -> Iterable[CheckResult]:
    if not package.get_license_file(True):
      if not package.license:
        yield CheckResult(CheckStatus.WARNING, 'not specified')
      else:
        yield CheckResult(CheckStatus.WARNING, 'No LICENSE file')

    monorepo = package.project.monorepo
    if package.license and monorepo and monorepo.license \
        and monorepo.license != package.license:
      yield CheckResult(CheckStatus.ERROR,
        'License is not consistent with parent mono repository (package: {}, monorepo: {}).'
          .format(package.license, monorepo.license))

  @check('classifiers')
  def _check_classifiers(self, package: PackageModel) -> Iterable[CheckResult]:
    classifiers = get_classifiers()
    unknown_classifiers = [x for x in package.classifiers if x not in classifiers]
    if unknown_classifiers:
      yield CheckResult(
        CheckStatus.WARNING,
        'Unknown classifiers: ' + ', '.join(unknown_classifiers))

  @check('package-url')
  def _check_author(self, package: PackageModel) -> Iterable[CheckResult]:
    if not package.get_url():
      yield CheckResult(CheckStatus.WARNING, 'missing')

  @check('package-author')
  def _check_consistent_author(self, package: PackageModel) -> Iterable[CheckResult]:
    if not package.get_author():
      yield CheckResult(CheckStatus.ERROR, 'missing')
    metadata = package.get_python_package_metadata()
    try:
      author = metadata.author
    except PackageError as exc:
      yield CheckResult(CheckStatus.ERROR, str(exc))
      return
    if package.get_author() and author != str(package.get_author()):
      yield CheckResult(
        CheckStatus.ERROR,
        'Inconsistent package author (package.yaml: {!r} != {}: {!r})'.format(
          str(package.get_author()), metadata.filename, author))

  @check('package-version')
  def _check_consistent_version(self, package: PackageModel) -> Iterable[CheckResult]:
    metadata = package.get_python_package_metadata()
    try:
      version = metadata.version
    except PackageError as exc:
      yield CheckResult(CheckStatus.ERROR, str(exc))
      return
    if package.version and version != str(package.version):
      yield CheckResult(
        CheckStatus.ERROR,
        '{!r} ({}) != {!r} ({})'.format(
          str(package.version),
          os.path.basename(package.filename),
          version,
          os.path.relpath(metadata.filename)))

  @check('typed')
  def _check_typed(self, package: PackageModel) -> Iterable[CheckResult]:
    metadata = package.get_python_package_metadata()
    try:
      py_typed_file = os.path.join(metadata.package_directory, 'py.typed')
    except PackageError as exc:
      yield CheckResult(CheckStatus.ERROR, str(exc))
    except ValueError as exc:
      if package.typed:
        yield CheckResult(
          CheckStatus.WARNING,
          '$.package.typed only works with packages, but this is a module')
    else:
      if os.path.isfile(py_typed_file) and not package.typed:
        yield CheckResult(
          CheckStatus.WARNING,
          'file "py.typed" exists but $.typed is not set')
    yield SkipCheck()

  @check('namespace files')
  def _check_naemspace_files(self, package: PackageModel) -> Iterable[CheckResult]:
    namespaces = package.get_modulename().split('.')[:-1]
    namespaces = [os.sep.join(namespaces[:i+1]) for i in range(len(namespaces))]

    for namespace in namespaces:
      namespace_file = os.path.join(package.get_directory(), package.source_directory, namespace, '__init__.py')
      if not os.path.exists(namespace_file):
        yield CheckResult(CheckStatus.WARNING,
          f'namespace file "{namespace + os.sep}__init__.py" does not exist')

  @check('up to date')
  def _check_up_to_date(self, package: PackageModel) -> Iterable[CheckResult]:
    """
    Checks if the package is up to date.
    """

    files = get_files(package)
    modified_files = files.get_modified_files(package.get_directory())
    if modified_files:
      yield CheckResult(
        CheckStatus.ERROR,
        f'managed files are not up to date ({",".join(modified_files)})')


register_checker(PackageModel, PackageChecker)
