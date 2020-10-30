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

import builtins
import sys
import time
import typing as t
from functools import partial

import click
import termcolor
from nr.stream import Stream
from termcolor import colored

from shut.checkers import Check, CheckStatus, get_checks
from shut.commands import project
from shut.commands import mono
from shut.commands import pkg
from shut.model import MonorepoModel, PackageModel, Project


def print_checks(
  checks: t.List[Check],
  emojis: bool = True,
  colors: bool = True,
  prefix: str = '',
  skip_positive_checks: bool = False,
  use_stderr: bool = False,
) -> None:
  """
  Prints the list of *checks* to the terminal.
  """

  emoji_chars = {
    CheckStatus.PASSED: '✔️ ',
    CheckStatus.WARNING: '⚠️ ',
    CheckStatus.ERROR: '❌'}

  color_names = {
    CheckStatus.PASSED: 'green',
    CheckStatus.WARNING: 'yellow',
    CheckStatus.ERROR: 'red'}

  if colors:
    colored = termcolor.colored
  else:
    def colored(s, *a, **kw):
      return str(s)

  out = sys.stderr if use_stderr else sys.stdout
  print = partial(builtins.print, file=out)

  num_printed = 0
  for check in checks:
    if skip_positive_checks and check.result.status == CheckStatus.PASSED:
      continue
    if num_printed == 0:
      print()
    num_printed += 1
    color = color_names[check.result.status]
    if emojis:
      print(prefix, emoji_chars[check.result.status], end='', sep='')
    print(prefix, colored(check.name, color, attrs=['bold']), sep='', end='')
    if check.result.status != CheckStatus.PASSED:
      print(':', check.result.message)
    else:
      print()

  if num_printed > 0:
    print()


def print_checks_all(
  name: str,
  checks: t.List[Check],
  seconds: float,
  skip_positive_checks: bool = False,
  print_stats: bool = True,
  use_stderr: bool = False,
):
  package_name = termcolor.colored(name, 'yellow')
  print_checks(checks, prefix='  ', skip_positive_checks=skip_positive_checks, use_stderr=use_stderr)
  if print_stats:
    print('ran', len(checks), 'checks for package', package_name, 'in {:.3f}s'.format(seconds))


def get_checks_status(checks: t.List[Check], warnings_as_errors: bool = False) -> int:
  max_level = max(x.result.status for x in checks)
  if max_level == CheckStatus.PASSED:
    status = 0
  elif max_level == CheckStatus.WARNING:
    status = 1 if warnings_as_errors else 0
  elif max_level ==  CheckStatus.ERROR:
    status = 1
  else:
    assert False, max_level
  return status


def check_monorepo(
  monorepo: MonorepoModel,
  warnings_as_errors: bool = False,
  skip_positive_checks: bool = False,
  print_stats: bool = True,
  use_stderr: bool = False,
) -> int:
  start_time = time.perf_counter()
  checks = sorted(get_checks(monorepo), key=lambda c: c.name)
  seconds = time.perf_counter() - start_time
  print_checks_all(monorepo.name, checks, seconds,
    skip_positive_checks=skip_positive_checks, print_stats=print_stats,
    use_stderr=use_stderr)
  return get_checks_status(checks, warnings_as_errors)


def get_package_checks(package: PackageModel) -> t.List[Check]:
  checks = list(get_checks(package))
  if package.project.monorepo:
    # Inherit mono-repo checks if the check targets the package specifically.
    for check in get_checks(package.project.monorepo):
      if check.result.subject == package:
        checks.append(check)
  return sorted(checks, key=lambda c: c.name)


def check_package(
  package: PackageModel,
  warnings_as_errors: bool = False,
  skip_positive_checks: bool = False,
  print_stats: bool = True,
  use_stderr: bool = False,
) -> int:
  start_time = time.perf_counter()
  checks = get_package_checks(package)
  seconds = time.perf_counter() - start_time
  print_checks_all(package.name, checks, seconds,
    skip_positive_checks=skip_positive_checks, print_stats=print_stats,
    use_stderr=use_stderr)
  return get_checks_status(checks, warnings_as_errors)


@mono.command()
@click.option('-w', '--warnings-as-errors', is_flag=True)
def checks(warnings_as_errors):
  """
  Sanity-check the package configuration and package files. Which checks are performed
  depends on the features that are enabled in the package configuration. Usually that
  will at least include the "setuptools" feature which will perform basic sanity checks
  on the package configuration and entrypoint definition.
  """

  monorepo = project.load_or_exit(expect=MonorepoModel)
  sys.exit(check_monorepo(monorepo, warnings_as_errors))


@pkg.command()
@click.option('-w', '--warnings-as-errors', is_flag=True)
def checks(warnings_as_errors):
  """
  Sanity-check the package configuration and package files. Which checks are performed
  depends on the features that are enabled in the package configuration. Usually that
  will at least include the "setuptools" feature which will perform basic sanity checks
  on the package configuration and entrypoint definition.
  """

  package = project.load(expect=PackageModel)
  sys.exit(check_package(package, warnings_as_errors))
