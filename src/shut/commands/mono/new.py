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

import datetime

import click

from shut.commands.commons.new import (
  GITIGNORE_TEMPLATE,
  README_TEMPLATE,
  load_author_from_git,
  get_license_file_text,
  render_template,
  write_files,
)
from shut.model import dump
from shut.model.author import Author
from shut.model.monorepo import MonorepoModel
from shut.model.release import MonorepoReleaseConfiguration
from shut.model.version import Version
from shut.utils.io.virtual import VirtualFiles
from . import mono


@mono.command(no_args_is_help=True)
@click.argument('target_directory', required=False)
@click.option('--project-name', '--name', metavar='name', required=True, help='The name of the project.')
@click.option('--author', metavar='"name <mail>"', type=Author.parse, help='The name of the author to write into the configuration file. Defaults to the name and email from the Git config.')
@click.option('--version', metavar='x.y.z', help='The version number to start counting from. Defaults to "0.0.0" (stands for "unreleased").')
@click.option('--license', metavar='name', help='The name of the license to use for the project. A LICENSE.txt file will be created.')
@click.option('--url', metavar='url', help='The URL to the project (e.g. the Git repository website).')
@click.option('--single-version', is_flag=True, help='Enable mono repository single-versioning.')
@click.option('--suffix', type=click.Choice(['yaml', 'yml']), help='The suffix for YAML files. Defaults to "yml".', default='yml')
@click.option('--dry', is_flag=True, help='Do not write files to disk.')
@click.option('-f', '--force', is_flag=True, help='Overwrite files if they already exist.')
def new(
  target_directory,
  project_name,
  author,
  version,
  license,
  url,
  single_version,
  suffix,
  dry,
  force,
):
  """
  Create files for a new Python monorepository. If the *target_directory* is specified, the files
  will be written to that directory. Otherwise the value of the --project-name argument will be
  used as the target directory.

  The following project layout will be created:

    \b
    project_name/
      .gitignore
      LICENSE.txt
      monorepo.yml
      README.md
  """

  if not target_directory:
    target_directory = project_name
  if not author:
    author = load_author_from_git() or Author('Unknown', '<unknown@example.org>')
  if not version:
    version = version or (Version('0.0.0') if single_version else None)

  package_manifest = MonorepoModel(
    name=project_name,
    version=version,
    author=author,
    license=license,
    url=url,
    release=MonorepoReleaseConfiguration(
      single_version=single_version,
    ),
  )

  template_vars = {
    'project_name': project_name,
    'version': version,
    'author': author,
    'year': datetime.date.today().year,
  }

  files = VirtualFiles()
  files.add_static('.gitignore', GITIGNORE_TEMPLATE)
  files.add_dynamic('README.md', render_template, README_TEMPLATE, template_vars)
  files.add_dynamic('monorepo.' + suffix, lambda fp: dump(package_manifest, fp))
  if license:
    files.add_dynamic('LICENSE.txt', get_license_file_text, license, template_vars)
  write_files(files, target_directory, force, dry)
