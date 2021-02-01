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
import logging
import shlex
import subprocess
import sys
from typing import Dict, List

import click
from nr.stream import concat  # type: ignore
from termcolor import colored

from shut.commands import project
from shut.model import dump, PackageModel
from shut.model.requirements import Requirement, VersionSelector, VendoredRequirement
from . import pkg

logger = logging.getLogger(__name__)


@pkg.group()
def requirements():
  """
  Update requirements in the package configuration.
  """


@requirements.command(no_args_is_help=True)
@click.argument('packages', nargs=-1)
@click.option('-v', '--vendor', 'vendored_packages', multiple=True,
  help='Specify a vendored installation source. This can point to a subdirectory of your project '
  'or a Git repository URL in a format that Pip understands (i.e. starting with git+). This is '
  'useful if a dependency is not available on any package index but only exists in a Git '
  'repository (in which case it can be tracked as a submodule and added with this option).')
@click.option('--test', is_flag=True, help='Add the requirement for testing.')
@click.option('--develop/--no-develop', default=True, help='Specifies whether vendored packages '
  'referencing a local directory should be installed in develop mode or not (default: true)')
def add(packages, test, vendored_packages, develop):
  """
  Install packages and save them to the package requirements.

  Note that this will remove any extranous whitespaces, empty lines and comments
  from the package configuration.
  """

  package = project.load_or_exit(expect=PackageModel)
  if not packages and not vendored_packages:
    sys.exit('error: no packages specified')

  reqs = [Requirement.parse(x) for x in packages]
  vendored_reqs = [VendoredRequirement.parse(x, fallback_to_path=True) for x in vendored_packages]
  target = package.test_requirements if test else package.requirements

  # Ensure that the same vendored requirement doesn't already exist.
  duplicate = next((x for x in vendored_reqs if x in target), None)
  if duplicate:
    logger.warning(f'vendored package {colored("%s", "cyan")} already exists', duplicate)

  # Install the requirements with Pip.
  python = shlex.split(os.getenv('PYTHON', 'python'))
  pip = python + ['-m', 'pip']
  command = pip + ['install'] + [r.to_setuptools() for r in reqs]
  command += concat(x.get_pip_args(package.get_directory(), develop) for x in vendored_reqs)
  command += package.install.get_pip_args()
  res = subprocess.call(command)
  if res != 0:
    sys.exit('error: pip install failed')

  scoped_reqs = [r for r in reqs if r.version != VersionSelector.ANY]
  unscoped_packages = [r.package for r in reqs if r.version == VersionSelector.ANY]

  if unscoped_packages:
    package_versions = get_pip_versions(pip, unscoped_packages)
    scoped_reqs += [Requirement.parse(f'{k} ^{v}') for k, v in package_versions.items()]

  # Update any existing requirements.
  seen = set()
  for req in target.reqs():
    matching_req = next((x for x in scoped_reqs if x.package == req.package), None)
    if matching_req:
      seen.add(req.package)
      req.version = matching_req.version

  # Append the remaining reqs.
  target += [r for r in scoped_reqs if r.package not in seen]
  target += [r for r in vendored_reqs if r not in target]

  dump(package, package.filename)


def get_pip_versions(pip: List[str], package_names: List[str]) -> Dict[str, str]:
  command = pip + ['show'] + package_names
  output = subprocess.check_output(command).decode()
  result = {}
  for chunk in output.split('---'):
    current = {}
    for line in chunk.splitlines():
      key, value = line.partition(':')[::2]
      if key:
        current[key] = value.strip()
    result[current['Name']] = current['Version']
  return result
