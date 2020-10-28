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
import shlex
import subprocess as sp
import sys
from typing import List, Optional, Set, Tuple

import click
from nr.stream import concat
from termcolor import colored

from shut.commands import project
from shut.commands.pkg import pkg
from shut.lifecycle import PackageLifecycle, InstallOptions
from shut.model.package import PackageModel
from shut.model.requirements import Requirement, RequirementsList, VendoredRequirement


def split_extras(extras: str) -> Set[str]:
  result = set(map(str.strip, extras.split(',')))
  result.discard('')
  return result


@pkg.command()
@click.option('--develop/--no-develop', default=True,
  help='Install in develop mode (default: true)')
@click.option('--inter-deps/--no-inter-deps', default=True,
  help='Install package inter dependencies from inside the same monorepo (default: true)')
@click.option('--extra', type=split_extras, help='Specify one or more extras to install.')
@click.option('-U', '--upgrade', is_flag=True, help='Upgrade all packages (forwarded to pip install).')
@click.option('-q', '--quiet', is_flag=True, help='Quiet install')
@click.option('--pip', help='Override the command to run Pip. Defaults to "python -m pip" or the PIP variable.')
@click.option('--pip-args', help='Additional arguments to pass to Pip.')
@click.option('--dry', is_flag=True, help='Print the Pip command to stdout instead of running it.')
@click.option('--pipx', is_flag=True, help='Install using Pipx.')
def install(develop, inter_deps, extra, upgrade, quiet, pip, pip_args, dry, pipx):
  """
  Install the package using `python -m pip`. If the package is part of a mono repository,
  inter-dependencies will be installed from the mono repsitory rather than from PyPI.

  The command used to invoke Pip can be overwritten using the `PIP` environment variable.
  """

  if not pip and pipx:
    pip = 'pipx'

  package = project.load_or_exit(expect=PackageModel)
  options = InstallOptions(
    quiet=quiet,
    develop=develop,
    upgrade=upgrade,
    extras=extra,
    pip=shlex.split(pip) if pip else None,
    pip_extra_args=shlex.split(pip_args) if pip_args else None,
    allow_global=False,
    create_environment=False,
    dry=dry)
  PackageLifecycle(package).install(options)
