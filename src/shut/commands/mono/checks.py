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

from shut.checkers import get_checks
from shut.commands import project
from shut.commands.commons.checks import print_checks_all, get_checks_status
from shut.commands.mono import mono
from shut.model import MonorepoModel

import click
import logging
import sys
import time

logger = logging.getLogger(__name__)


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
