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

"""
This package implements the Shut CLI.
"""

from shut import __version__
from shut.model import Project
from nr.proxy import proxy

import click
import logging
import os
import warnings
import sys

context = proxy(lambda: click.get_current_context().obj)
project = proxy(lambda: click.get_current_context().obj['project'])


@click.group()
@click.option('-C', '--cwd', metavar='path', help='Run as if shut was started inside the specified directory.')
@click.option('-v', '--verbose', count=True, help='Increase the log verbosity.')
@click.option('-q', '--quiet', is_flag=True, help='Quiet mode, wins over --verbose.')
@click.option('-W', '--disable-warnings', is_flag=True, help='Disable Python warnings.')
@click.version_option(__version__)
def shut(cwd, verbose, quiet, disable_warnings):
  """
  Shut is a tool to manage the lifecycle of pure Python packages. It automates tasks such
  as bootstrapping a project, bumping version numbers, managing changelogs and publishing
  packages to PyPI all the while performing sanity checks.

  Shut makes strong assumptions on the project structure and assumes that the source-control
  system of choice is Git.
  """

  if cwd:
    os.chdir(cwd)

  ctx = click.get_current_context()
  ctx.ensure_object(dict)
  context['quiet'] = quiet
  context['project'] = Project()

  if quiet:
    level = logging.CRITICAL
  elif verbose >= 2:
    level = logging.DEBUG
  elif verbose >= 1:
    level = logging.INFO
  else:
    level = logging.WARNING

  logging.basicConfig(
    format='[%(levelname)s|%(asctime)s|%(name)s]: %(message)s',
    level=level,
  )

  if not sys.warnoptions and not disable_warnings:
    warnings.simplefilter("default") # Change the filter in this process


from . import changelog
from . import classifiers
from . import conda_forge
from . import license
from . import mono
from . import pkg
from .commons import install
from .commons import test
