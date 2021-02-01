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
import sys
from typing import List

import click
from nr.stream import groupby  # type: ignore
from termcolor import colored

from shut.builders import Builder, get_builders
from shut.model import PackageModel
from shut.model.target import TargetId
from . import pkg
from .. import project


def run_builds(builders: List[Builder], build_dir: str, verbose: bool) -> bool:
  os.makedirs(build_dir, exist_ok=True)
  for builder in builders:
    print(colored(f'building {colored(builder.id, "green")}'))
    for filename in builder.get_outputs():
      print(f'  :: {os.path.join(build_dir, filename)}')
    print()
    success = builder.build(build_dir, verbose)
    if not success:
      print(f'error: building "{builder.id}" failed', file=sys.stderr)
      return False
  return True


@pkg.command()
@click.argument('target', type=lambda s: TargetId.parse(s, True), required=False)
@click.option('-l', '--list', 'list_', is_flag=True, help='list available builders')
@click.option('-b', '--build-dir', default='build', help='build output directory')
@click.option('-v', '--verbose', is_flag=True, help='show more output')
def build(target, list_, build_dir, verbose):
  """
  Produce a build of the package.
  """

  if target and list_:
    sys.exit('error: conflicting options')

  package = project.load_or_exit(expect=PackageModel)
  builders = list(get_builders(package))

  if package.has_vendored_requirements():
    sys.exit(f'error: package has vendored requirements and cannot be built')

  if list_:
    print()
    for scope, builders in groupby(builders, lambda b: b.id.scope):
      print(f'{colored(scope, "green")}:')
      for builder in builders:
        print(f'  {builder.id.name} – {builder.get_description()}')
    print()
    return

  if not target:
    sys.exit('error: no target specified')

  builders = [b for b in builders if target.match(b.id)]
  if not builders:
    sys.exit(f'error: no target matches "{target}"')

  success = run_builds(builders, build_dir, verbose)
  if not success:
    sys.exit(1)
