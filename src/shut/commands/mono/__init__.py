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

import click
import sys

from shut.model import MonorepoModel
from .. import shut, commons, project


@shut.group(help=__doc__)
@click.option('--checks/--no-checks', 'run_checks', default=True,
  help='Run checks before executing the subcommand (default: true)')
@click.pass_context
def mono(ctx, run_checks):
  """
  Manage the current mono repository.
  """

  if run_checks and ctx.invoked_subcommand not in ('new', 'checks'):
    monorepo = project.load(expect=MonorepoModel)
    checks.check_monorepo(monorepo, skip_positive_checks=True, print_stats=False, use_stderr=True)


@mono.command()
def get_version():
  monorepo = project.load(expect=MonorepoModel)
  if not monorepo.version:
    click.echo('version not defined', err=True)
    sys.exit(1)
  print(monorepo.version)


from . import bump
from . import checks
from . import install
from . import new
from . import publish
from . import status
from . import test
from . import update
