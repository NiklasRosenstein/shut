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

from shore.util.license import get_license_metadata, wrap_license_text

from shut.model import dump
from shut.model.author import Author
from shut.model.package import PackageModel, PackageData
from shut.model.requirements import Requirement, VersionSelector
from shut.model.version import Version
from shut.utils.io.virtual import VirtualFiles

from . import pkg
from termcolor import colored
from typing import Optional
import click
import datetime
import jinja2
import os
import subprocess

INIT_TEMPLATE = '''
__author__ = '{{author or "Me <me@me.org>"}}'
__version__ = '{{version or "0.0.1"}}'
'''

NAMESPACE_INIT_TEMPLATE = '''
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
'''

GITIGNORE_TEMPLATE = '''
/.venv*/
/dist
/build
*.py[cod]
*.egg-info
*.egg
'''.lstrip()

README_TEMPLATE = '''
# {{project_name}}

---

<p align="center">Copyright &copy; {{year}} {{author.name}}</p>
'''.lstrip()


def load_author_from_git() -> Optional[str]:
  """
  Returns a string formatted as "name <mail>" from the Git `user.name` and `user.email`
  configuration values. Returns `None` if Git is not configured.
  """

  try:
    name = subprocess.getoutput('git config user.name')
    email = subprocess.getoutput('git config user.email')
  except FileNotFoundError:
    return None
  if not name and not email:
    return None
  return Author(name, email)


@pkg.command(no_args_is_help=True)
@click.argument('target_directory', required=False)
@click.option('--project-name', '--name', metavar='name', required=True, help='The name of the project as it would appear on PyPI.')
@click.option('--module-name', metavar='fqn', help='The name of the main Python module (this may be a dotted module name). Defaults to the package name (hyphens replaced with underscores).')
@click.option('--author', metavar='"name <mail>"', type=Author.parse, help='The name of the author to write into the package configuration file. Defaults to the name and email from the Git config.')
@click.option('--version', metavar='x.y.z', help='The version number to start counting from. Defaults to "0.0.0" (stands for "unreleased").')
@click.option('--license', metavar='name', help='The name of the license to use for the project. A LICENSE.txt file will be created.')
@click.option('--description', metavar='text', help='A short summary of the project.')
@click.option('--universal', is_flag=True, help='Mark the package as universal (Python 2 and 3 compatible).')
@click.option('--suffix', type=click.Choice(['yaml', 'yml']), help='The suffix for YAML files. Defaults to "yml".', default='yml')
@click.option('--dry', is_flag=True, help='Do not write files to disk.')
@click.option('-f', '--force', is_flag=True, help='Overwrite files if they already exist.')
def new(
  target_directory,
  project_name,
  module_name,
  author,
  version,
  license,
  description,
  universal,
  suffix,
  dry,
  force,
):
  """
  Create files for a new Python package. If the *target_directory* is specified, the files will
  be written to that directory. Otherwise the value of the --project-name argument will be used
  as the target directory.

  The following project layout will be created:

    \b
    project_name/
      .gitignore
      LICENSE.txt
      package.yml
      README.md
      src/
        module_name/
          __init__.py

  If the "module_name" represents a namespace package (that is, if it contains any dots),
  package namespace files will be automatically created. [1]

  ---

  Footnotes:

  \b
  [1]: Package namespace files are "__init__.py" files that contain a single line, allowing
    the Python import machinery to discover other packages in the same namespace. Shut assumes
    pkgutil-style namespace packages. For more information on such files, check out out the
    Python Packaging Guide (https://packaging.python.org/guides/packaging-namespace-packages/).
  """

  if not target_directory:
    target_directory = project_name
  if not module_name:
    module_name = project_name.replace('-', '_')
  if not author:
    author = load_author_from_git() or Author('Unknown', '<unknown@example.org>')
  if not version:
    version = version or Version('0.0.0')

  package_manifest = PackageModel(
    data=PackageData(
      name=project_name,
      modulename=None if module_name == project_name.replace('-', '_') else module_name,
      version=version,
      author=author,
      license=license,
      description=description or 'Package description here.',
      requirements=[
        Requirement('python', VersionSelector('^2.7|^3.5' if universal else '^3.5')),
      ],
    ),
  )

  template_vars = {
    'project_name': project_name,
    'version': version,
    'author': author,
    'year': datetime.date.today().year,
  }

  def _render_template(fp, template_string):
    for data in jinja2.Template(template_string).stream(**template_vars):
      fp.write(data)
    fp.write('\n')

  files = VirtualFiles()

  files.add_static('.gitignore', GITIGNORE_TEMPLATE)
  files.add_dynamic('README.md', _render_template, README_TEMPLATE)
  files.add_dynamic('package.' + suffix, lambda fp: dump(package_manifest, fp))

  files.add_dynamic(
    'src/{}/__init__.py'.format(module_name.replace('.', '/')),
    _render_template,
    INIT_TEMPLATE,
  )

  parts = []
  for item in module_name.split('.')[:-1]:
    parts.append(item)
    files.add_static(
      os.path.join('src', *parts, '__init__.py'),
      NAMESPACE_INIT_TEMPLATE,
    )

  if license:
    license_text = 'Copyright (c) {year} {author.name}\n\n'.format(**template_vars)
    license_text += wrap_license_text(get_license_metadata(license)['license_text'])
    files.add_static('LICENSE.txt', license_text)

  files.write_all(
    target_directory,
    on_write=lambda fn: print(colored('Write ' + fn, 'cyan')),
    on_skip=lambda fn: print(colored('Skip ' + fn, 'yellow')),
    overwrite=force,
    dry=dry,
  )