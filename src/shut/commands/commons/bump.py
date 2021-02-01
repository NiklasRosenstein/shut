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

import abc
import logging
import os
import sys
from collections import Counter
from typing import Iterable, Generic, Optional, T, Type

import click
import nr.fs  # type: ignore
from databind.core import datamodel
from nr.stream import Stream  # type: ignore
from nr.utils.git import Git  # type: ignore
from termcolor import colored

from shut.changelog.manager import ChangelogManager
from shut.commands import project
from shut.model import AbstractProjectModel, Project
from shut.model.version import bump_version, parse_version, Version
from shut.renderers import get_version_refs, VersionRef
from shut.utils.io.virtual import VirtualFiles
from shut.utils.text import substitute_ranges

logger = logging.getLogger(__name__)


@datamodel
class Args:
  version: Optional[Version]
  major: bool
  minor: bool
  patch: bool
  post: bool
  snapshot: bool
  tag: bool
  push: bool
  dry: bool
  warnings_as_errors: bool
  skip_checks: bool
  skip_update: bool
  force: bool
  allow_lower: bool = False


class VersionBumpData(Generic[T], metaclass=abc.ABCMeta):

  def __init__(self, args: Args, project: Project, obj: T) -> None:
    self.args = args
    self.project = project
    self.obj = obj

  def loaded(self) -> None:
    pass

  @abc.abstractmethod
  def get_snapshot_version(self) -> Version:
    pass

  def get_version_refs(self) -> Iterable[VersionRef]:
    yield from get_version_refs(self.obj)

  def bump_to_version(self, target_version: Version) -> Iterable[str]:
    """
    Called to bump to the specified *target_version*. The default implementation uses the
    version refs provided by #get_version_refs() to bump.
    """

    version_refs = list(self.get_version_refs())

    print()
    print(f'bumping {len(version_refs)} version reference(s)')
    for filename, refs in Stream.groupby(version_refs, lambda r: r.filename, collect=list):
      with open(filename) as fp:
        content = fp.read()

      if len(refs) == 1:
        ref = refs[0]
        print(f'  {colored(nr.fs.rel(ref.filename), "cyan")}: {ref.value} → {target_version}')
      else:
        print(f'  {colored(nr.fs.rel(ref.filename), "cyan")}:')
        for ref in refs:
          print(f'    {ref.value} → {target_version}')

      content = substitute_ranges(
        content,
        ((ref.start, ref.end, target_version) for ref in refs),
      )

      if not self.args.dry:
        with open(filename, 'w') as fp:
          fp.write(content)

    changed_files = set(x.filename for x in version_refs)

    # Release the staged changelog.
    managers = list(self.get_changelog_managers())
    managers = [m for m in managers if m.unreleased.exists()]
    if managers:
      print()
      print('release staged changelog' + ('s' if len(managers) > 1 else ''))
      for manager in managers:
        changed_files.add(manager.unreleased.filename)
        if self.args.dry:
          changelog = manager.version(target_version)
        else:
          changelog = manager.release(target_version)
        changed_files.add(changelog.filename)
        print(f'  {colored(os.path.relpath(manager.unreleased.filename), "cyan")} → {os.path.relpath(changelog.filename)}')

    return changed_files

  @abc.abstractmethod
  def update(self, new_version: Version) -> VirtualFiles:
    """
    Run the "update" function for the current monorepo or package. A list of the modified files
    must be returned.
    """

  def get_changelog_managers(self) -> Iterable[ChangelogManager]:
    yield ChangelogManager(self.obj.get_changelog_directory())


def make_bump_command(
  data_class: Type[VersionBumpData[AbstractProjectModel]],
  model_type: Type[AbstractProjectModel],
) -> click.Command:

  @click.argument('version', type=parse_version, required=False)
  @click.option('--major', is_flag=True, help='bump the major number')
  @click.option('--minor', is_flag=True, help='bump the minor number')
  @click.option('--patch', is_flag=True, help='bump the patch number')
  @click.option('--post', is_flag=True, help='bump the post-release number')
  @click.option('--snapshot', is_flag=True, help='update the version number by appending the Git commit distance and shasum (note: not compatible with publishing to PyPI)')
  @click.option('--tag', is_flag=True, help='create a commit and Git tag after bumping the version')
  @click.option('--push', is_flag=True, help='push the new commit and tag to the Git "origin" remote')
  @click.option('--dry', is_flag=True, help='do not write changes to disk')
  @click.option('-w', '--warnings-as-errors', is_flag=True, help='treat check warnings as errors')
  @click.option('--skip-checks', is_flag=True, help='skip running checks before bumping')
  @click.option('--skip-update', is_flag=True, help='skip update after bumping')
  @click.option('--force', '-f', is_flag=True, help='force target version (allowing you to "bump" '
    'the same or a lower version). the flag will also result in force adding a Git tag and force '
    'pushing to the remote repository if the respective options as set (--tag and --push).')
  def bump(**kwargs):
    """
    Bump the version number to prepare a new release.
    """

    args = Args(**kwargs)
    data = data_class(args, project, project.load_or_exit(expect=model_type))
    data.loaded()
    do_bump(args, data)

  return bump


def do_bump(args: Args, data: VersionBumpData[AbstractProjectModel]) -> None:
  # Validate arguments.
  if args.push and not args.tag:
    sys.exit('error: --push can only be used with --tag')

  bump_args = 'version major minor patch post snapshot'.split()
  provided_args = {k for k in bump_args if getattr(args, k)}
  if len(provided_args) > 1:
    sys.exit('error: conflicting options: {}'.format(provided_args))
  elif not provided_args:
    print()
    print('figuring bump mode from changelog')
    entries = []
    for manager in data.get_changelog_managers():
      if manager.unreleased.exists():
        entries += manager.unreleased.entries
    if not entries:
      sys.exit('error: no changelog entries found')
    counter = Counter(entry.type_.name for entry in entries)
    bump_mode = max(entry.type_.bump_mode for entry in entries)
    assert hasattr(args, bump_mode.name), bump_mode.name
    setattr(args, bump_mode.name, True)
    print('  {} → {}'.format(
      ', '.join(f'{c} {colored(k, "cyan")}' for k, c in counter.items()),
      colored(bump_mode.name, "blue", attrs=["bold"])))

  version_refs = list(get_version_refs(data.obj))
  if not version_refs:
    sys.exit('error: no version refs found')

  # Ensure the version is the same accross all refs.
  current_version = data.obj.get_version()
  is_inconsistent = any(parse_version(x.value) != current_version for x in version_refs)
  if is_inconsistent:
    if not args.force:
      sys.exit('error: inconsistent versions across files need to be fixed first.')
    logger.warning('inconsistent versions across files were found.')

  # Bump the current version number.
  if args.post:
    new_version = bump_version(current_version, 'post')
  elif args.patch:
    new_version = bump_version(current_version, 'patch')
  elif args.minor:
    new_version = bump_version(current_version, 'minor')
  elif args.major:
    new_version = bump_version(current_version, 'major')
  elif args.snapshot:
    new_version = data.get_snapshot_version()
    if new_version < current_version:
      # The snapshot version number can be considered lower, so we'll allow it.
      args.allow_lower = True
  else:
    new_version = parse_version(args.version)

  if not new_version.pep440_compliant:
    logger.warning(f'version "{new_version}" is not PEP440 compliant.')

  # The new version cannot be lower than the current one, unless forced.
  if new_version < current_version and not (args.force or args.allow_lower):
    sys.exit(f'version "{new_version}" is lower than current version "{current_version}"')
  if str(new_version) == str(current_version) and not args.force:
    # NOTE(NiklasRosenstein): Comparing as strings to include pre-release and build number.
    logger.warning(f'new version "{new_version}" is equal to current version')
    exit(0)

  # Bump version numbers in files.
  changed_files = list(data.bump_to_version(new_version))

  if not args.skip_update:
    print()
    print('updating files')
    changed_files += data.update(new_version).abspaths('.')

  if args.tag:
    print()
    git = Git()
    files = list(git.porcelain())

    # We require that no files are currently staged.
    if any(f.mode == 'A' for f in files):
      logger.error('cannot tag with non-empty staging area')
      exit(1)

    # TODO: If this step errors (e.g. for example because the unreleased changelog file
    #   was not yet tracked by Git, making Git complain that it doesn't know about the
    #   file and it doesn't exits anymore when we add it down below), it's a bit painful
    #   to recover from it because it's a manual process of reverting the version number
    #   bumps.

    tag_name = data.obj.get_tag(new_version)
    print(f'tagging {tag_name}')

    if not args.dry:
      git.add(changed_files)
      git.commit('({}) bump version to {}'.format(data.obj.get_name(), new_version), allow_empty=True)
      git.tag(tag_name, force=args.force)

    if not args.dry and args.push:
      git.push('origin', git.get_current_branch_name(), tag_name, force=args.force)
