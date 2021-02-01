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
import typing as t
from typing import cast, List, Optional, Set

import click
import networkx as nx

from shut.model.package import PackageModel
from shut.model.monorepo import InterdependencyRef
from shut.model.requirements import RequirementsList, VendoredRequirement
from . import pkg
from .. import project


def collect_requirement_args(
  package: bool,
  develop: bool,
  inter_deps: bool,
  extra: Optional[Set[str]],
) -> List[str]:
  reqs = RequirementsList()

  # Pip does not understand "test" as an extra and does not have an option to
  # install test requirements.
  if extra and 'test' in extra:
    reqs += package.test_requirements

  reqs.append(VendoredRequirement(VendoredRequirement.Type.Path, package.get_directory()))
  reqs += package.requirements.vendored_reqs()

  if project.monorepo and inter_deps:
    # TODO(NiklasRosenstein): get_inter_dependencies_for() does not currently differentiate
    #   between normal, test and extra requirements.

    # In the case of transitive inter-dependencies, we need to make sure to install them
    # in the right order. For example in the command-line `pip install -e a -e b -e c`, where
    # package `a` depends on package `b`, Pip is not able to tell that `b` is supplied on the
    # command-line as well and will instead try to resolve it from PyPI.
    project_packages: t.Dict[str, PackageModel] = {p.name: p for p in project.packages}
    direct_inter_dependencies: t.Dict[str, InterdependencyRef]  = {ref.package_name: ref
      for ref in project.monorepo.get_inter_dependencies_for(package)}
    graph: nx.DiGraph = project.monorepo.get_inter_dependencies_graph().subgraph(
      direct_inter_dependencies)

    insert_index = 0
    for dep_name in nx.algorithms.topological_sort(graph):
      dep = project_packages[dep_name]
      ref = direct_inter_dependencies[dep_name]
      if not ref.version_selector.matches(dep.version):
        print('note: skipping inter-dependency on package "{}" because the version selector '
              '{} does not match the present version {}'
              .format(dep.name, ref.version_selector, dep.version), file=sys.stderr)
      else:
        reqs.insert(insert_index, VendoredRequirement(VendoredRequirement.Type.Path, dep.get_directory()))
        insert_index += 1

  return reqs.get_pip_args(package.get_directory(), develop)


def run_install(
  pip: Optional[str],
  args: List[str],
  upgrade: bool,
  quiet: bool,
  dry: bool,
) -> None:

  pip_bin = shlex.split(os.getenv('PIP', pip or 'python -m pip'))
  command = pip_bin + ['install'] + args
  if upgrade:
    command.append('--upgrade')
  if quiet:
    command.append('--quiet')

  if dry:
    print(' '.join(map(shlex.quote, command)))
  else:
    sys.exit(sp.call(command))


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
@click.option('-v', '--verbose', is_flag=True, help='Verbose install')
@click.option('--pip', help='Override the command to run Pip. Defaults to "python -m pip" or the PIP variable.')
@click.option('--pip-args', help='Additional arguments to pass to Pip.')
@click.option('--dry', is_flag=True, help='Print the Pip command to stdout instead of running it.')
@click.option('--pipx', is_flag=True, help='Install using Pipx.')
def install(develop, inter_deps, extra, upgrade, quiet, verbose, pip, pip_args, dry, pipx):
  """
  Install the package using `python -m pip`. If the package is part of a mono repository,
  inter-dependencies will be installed from the mono repsitory rather than from PyPI.

  The command used to invoke Pip can be overwritten using the `PIP` environment variable.
  """

  if not pip and pipx:
    pip = 'pipx'

  package = cast(PackageModel, project.load_or_exit(expect=PackageModel))
  args = collect_requirement_args(package, develop, inter_deps, extra)
  if pipx:
    args += ['--pip-args', ' '.join(map(shlex.quote, package.install.get_pip_args()))]
  else:
    args += package.install.get_pip_args()
  if verbose:
    pip_args.append('--verbose')
  if pip_args:
    args += shlex.split(pip_args)
  run_install(pip, args, upgrade, quiet, dry)
