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
from typing import Iterable

import nr.fs  # type: ignore
from nr.stream import Stream  # type: ignore
from termcolor import colored

from shut.changelog.manager import ChangelogManager
from shut.commands.commons.bump import make_bump_command, VersionBumpData, VersionRef
from shut.commands.pkg.bump import PackageBumpData
from shut.model import MonorepoModel
from shut.model.version import get_commit_distance_version, Version
from shut.utils.io.virtual import VirtualFiles
from shut.utils.text import substitute_ranges
from . import mono
from .update import update_monorepo

logger = logging.getLogger(__name__)


class MonorepoBumpdata(VersionBumpData[MonorepoModel]):

  def update(self, new_version: Version) -> VirtualFiles:
    # We have to re-load the monorepo and package definitions from the files since
    # they have been updated by #bump_to_version(). This is a workaround to updating
    # the version selectors of inter-dependencies in memory.
    self.project.reload()

    vfiles = update_monorepo(self.obj, dry=self.args.dry, indent=1)
    if self.obj.release.single_version:
      for package in self.project.packages:
        vfiles.update(
          PackageBumpData(self.args, self.project, package).update(new_version),
          os.path.relpath(package.get_directory(), self.obj.get_directory()))

    return vfiles

  def get_version_refs(self) -> Iterable[VersionRef]:
    yield from super().get_version_refs()
    if self.obj.release.single_version:
      for package in self.project.packages:
        yield from PackageBumpData(self.args, self.project, package).get_version_refs()

  def bump_to_version(self, target_version: Version) -> Iterable[str]:
    changed_files = list(super().bump_to_version(target_version))

    if not self.obj.release.single_version:
      return changed_files

    inter_deps = list(self.obj.get_inter_dependencies())
    if not inter_deps:
      return changed_files

    print()
    print(f'bumping {len(inter_deps)} mono repository inter-dependency(-ies)')
    for filename, refs in Stream.groupby(inter_deps, lambda d: d.filename, collect=list):
      print(f'  {colored(nr.fs.rel(filename), "cyan")}:')

      with open(filename) as fp:
        content = fp.read()

      for ref in refs:
        value = content[ref.version_start:ref.version_end]
        print(f'    {ref.package_name} {value} → ^{target_version}')

      content = substitute_ranges(
        content,
        ((ref.version_start, ref.version_end, f'^{target_version}') for ref in refs),
      )
      if not self.args.dry:
        with open(filename, 'w') as fp:
          fp.write(content)

      changed_files.append(filename)

    if self.args.tag and inter_deps and self.args.skip_update:
      logger.warning('bump requires an update in order to automatically tag')

    return changed_files

  def get_snapshot_version(self) -> Version:
    return get_commit_distance_version(
      self.obj.get_directory(),
      self.obj.version,
      self.obj.get_tag(self.obj.version)) or self.obj.version

  def get_changelog_managers(self) -> Iterable[ChangelogManager]:
    yield from super().get_changelog_managers()
    if self.obj.release.single_version:
      for package in self.project.packages:
        yield from PackageBumpData(self.args, self.project, package).get_changelog_managers()


mono.command()(make_bump_command(MonorepoBumpdata, MonorepoModel))
