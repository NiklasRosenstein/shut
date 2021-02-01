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
import subprocess
from typing import Any, Dict, Optional

import jinja2
import nr.fs  # type: ignore
from termcolor import colored

from shut.model.author import Author
from shut.utils.external.license import get_license_metadata, wrap_license_text
from shut.utils.io.virtual import VirtualFiles

GITIGNORE_TEMPLATE = '''
.venv*/
dist/
build/
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


def get_license_file_text(license: str, template_vars: Dict[str, Any]) -> str:
  license_text = 'Copyright (c) {year} {author.name}\n\n'.format(**template_vars)
  license_text += wrap_license_text(get_license_metadata(license)['license_text'])
  return license_text


def render_template(fp, template_string, template_vars):
  for data in jinja2.Template(template_string).stream(**template_vars):
    fp.write(data)
  fp.write('\n')


def write_files(
  files: VirtualFiles,
  target_directory: str,
  force: bool = False,
  dry: bool = False,
  indent: int = 0,
):
  def _rel(fn: str) -> str:
    path = os.path.relpath(fn)
    if nr.fs.issub(path):
      return path
    return fn
  str_indent = '  ' * indent
  files.write_all(
    target_directory,
    on_write=lambda fn: print(str_indent + colored('write ' + _rel(fn), 'cyan')),
    on_skip=lambda fn: print(str_indent + colored('skip ' + _rel(fn), 'yellow')),
    overwrite=force,
    dry=dry,
  )
