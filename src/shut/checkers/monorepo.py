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

from shut.model import MonorepoModel
from .base import CheckStatus, CheckResult, Checker, SkipCheck, check, register_checker


class MonorepoChecker(Checker[MonorepoModel]):

  @check('invalid-package')
  def _check_no_invalid_packages(self, monorepo):
    for package_name, exc_info in monorepo.project.invalid_packages:
      yield CheckResult(CheckStatus.ERROR, f'{package_name}: {exc_info[1]}')

  @check('inconsistent-single-version')
  def _check_consistent_mono_version(self, monorepo):
    if monorepo.release.single_version and monorepo.project.packages:
      for package in monorepo.project.packages:
        if package.version is not None and package.version != monorepo.version:
          yield CheckResult(CheckStatus.ERROR, f'{package.name} v{package.version}, expected v{monorepo.version}')
    yield SkipCheck()


register_checker(MonorepoModel, MonorepoChecker)
