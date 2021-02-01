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

import logging
import re
import subprocess
import sys

import click
import nr.fs  # type: ignore
import requests
from nr.utils.git import Git  # type: ignore
from termcolor import colored

from shut.model import PackageModel
from shut.model.version import parse_version
from . import project, shut

logger = logging.getLogger(__name__)


def _call(*args, **kwargs):
  proc = subprocess.Popen(*args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
  stdout, _ = proc.communicate()
  if proc.returncode != 0:
    print(colored(stdout.decode(), 'red'))
    sys.exit(proc.returncode)


@shut.group()
def conda_forge():
  """
  Utility to update conda-forge recipes.
  """


@conda_forge.command()
@click.argument('package_name', required=False)
@click.argument('version', type=parse_version, required=False)
@click.option('-f', '--force', is_flag=True, help='force push to the Git repository')
def update_feedstock(package_name, version, force):
  """
  Update a conda-forge feedstock from a PyPI release. You can explicitly specify a *package_name*
  and *version*, or rely on the metadata from the package configuration file in your cwd.

  This command will clone the feedstack from the conda-forge organization on GitHub, then
  update thr version and sha256 reference and push a new branch to the repository.
  """

  if package_name or version:
    if not (package_name and version):
      sys.exit('error: need package_name AND version, OR neither')
    version = str(version)
  else:
    package = project.load_or_exit(expect=PackageModel)
    package_name, version = package.name, str(package.version)
    del package

  repo_name = 'conda-forge/{}-feedstock'.format(package_name)
  clone_url = 'git@github.com:' + repo_name
  branch_name = 'v' + version

  s_repo_name = colored(repo_name, 'cyan')
  s_package_name = colored(package_name, 'yellow')
  s_clone_url = colored(clone_url, 'cyan')
  s_branch_name = colored(branch_name, 'yellow')

  print(f'Fetching PyPI record for {s_package_name} ...')
  url = f'https://pypi.org/pypi/{package_name}/json'
  pypi_data = requests.get(url).json()
  if version not in pypi_data['releases']:
    sys.exit(f'error: no release on PyPI for {s_package_name} v{version}.')

  sdist = next((x for x in pypi_data['releases'][version] if x['packagetype'] == 'sdist'), None)
  if not sdist:
    logger.error('No sdist on PyPI for %s v%s.', s_package_name, version)
    sys.exit(1)
  sha256 = sdist['digests']['sha256']

  print(f'Updating {s_repo_name} from PyPI package {s_package_name} v{version}.')

  with nr.fs.tempdir() as tmpdir:

    print(f'Cloning {s_clone_url} ...')
    git = Git().clone(tmpdir.name, clone_url)
    git.create_branch(branch_name)

    recipe_path = nr.fs.join(tmpdir.name, 'recipe', 'meta.yaml')
    with open(recipe_path) as fp:
      recipe = fp.read()

    recipe = re.sub(r'(version = ")([^"]+)"', r'\g<1>' + version + '"', recipe)
    recipe = re.sub(r'(sha256:\s*")([^"]+)"', r'\g<1>' + sha256 + '"', recipe)

    with open(recipe_path, 'w') as fp:
      fp.write(recipe)

    print()
    subprocess.check_call(['git', '--no-pager', 'diff'], cwd=tmpdir.name)
    print()

    git.add(['.'])
    git.commit(f'Updating recipe for {package_name} v{version}.')

    print(f'pushing branch {s_branch_name} to {s_clone_url} ...')
    git.push('origin', branch_name, force=force)
