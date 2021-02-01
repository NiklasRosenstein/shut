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

import click
from nr.stream import groupby, Stream  # type: ignore
from termcolor import colored

from shut.builders import get_builders
from shut.model import PackageModel
from shut.model.target import TargetId
from shut.publishers import get_publishers
from . import pkg
from .build import run_builds
from .. import project


class PublishError(Exception):
  pass


def publish_package(
  package: PackageModel,
  target: TargetId,
  build_dir: str,
  skip_build: bool,
  test: bool,
  verbose: bool,
) -> None:

  if package.has_vendored_requirements():
    raise PublishError('package has vendored requirements and cannot be published')

  publishers = list(get_publishers(package))
  publishers = [p for p in publishers if target.match(p.id)]
  if not publishers:
    raise PublishError(f'no target matches "{target}"')

  # Prepare the builds that need to be built for the publishers.
  all_builders = list(get_builders(package))
  builders_for_publisher = {}
  for publisher in publishers:
    builders = []
    for target_id in publisher.get_build_dependencies():
      matched_builders = [b for b in all_builders if target_id.match(b.id)]
      if not matched_builders:
        raise PublishError(f'publisher "{publisher.id}" depends on build target "{target_id}" '
                           f'which could not be resolved.')
      builders.extend(b for b in matched_builders if b not in builders)
    builders_for_publisher[publisher.id] = builders

  # Build all builders that are needed.
  if not skip_build:
    built = set()
    for publisher in publishers:
      print()
      builders = builders_for_publisher[publisher.id]
      success = run_builds([b for b in builders if b not in built], build_dir, verbose)
      if not success:
        raise PublishError('build step failed')

  # Execute the publishers.
  for publisher in publishers:
    print()
    print(f'publishing {colored(publisher.id, "cyan")}')
    builders = builders_for_publisher[publisher.id]
    files = (Stream
      .concat(b.get_outputs() for b in builders)
      .map(lambda x: os.path.join(build_dir, x))
      .collect()
    )
    for filename in files:
      print(f'  :: {filename}')
    print()
    success = publisher.publish(files, test, verbose)
    if not success:
      raise PublishError('publish step failed')


@pkg.command()
@click.argument('target', type=lambda s: TargetId.parse(s, True), required=False)
@click.option('-t', '--test', is_flag=True, help='publish to the test repository instead')
@click.option('-l', '--list', 'list_', is_flag=True, help='list available publishers')
@click.option('-v', '--verbose', is_flag=True, help='show more output')
@click.option('-b', '--build-dir', default='build', help='build output directory')
@click.option('--skip-build', is_flag=True, help='do not build artifacts that are to be published')
def publish(target, test, list_, verbose, build_dir, skip_build):
  """
  Publish the package to PyPI or another target.
  """

  if list_ and target:
    sys.exit('error: conflicting options')

  package = project.load_or_exit(expect=PackageModel)

  if list_:
    publishers = list(get_publishers(package))
    for scope, publishers in groupby(publishers, lambda p: p.id.scope):
      print(f'{colored(scope, "green")}:')
      for publisher in publishers:
        print(f'  {publisher.id.name} – {publisher.get_description()}')
    return

  if not target:
    sys.exit('error: no target specified')

  if package.has_vendored_requirements():
    sys.exit(f'error: package has vendored requirements and cannot be published')

  if list_:
    for scope, publishers in groupby(publishers, lambda p: p.id.scope):
      print(f'{colored(scope, "green")}:')
      for publisher in publishers:
        print(f'  {publisher.id.name} – {publisher.get_description()}')
    return

  if not target:
    sys.exit('error: no target specified')

  try:
    publish_package(package, target, build_dir, skip_build, test, verbose)
  except PublishError as exc:
    sys.exit(f'error: {exc}')
