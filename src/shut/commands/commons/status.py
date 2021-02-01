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

from nr.utils.git import Git  # type: ignore
from termcolor import colored

from shut.model import AbstractProjectModel, MonorepoModel, Project


def get_commits_since_last_tag(subject: AbstractProjectModel):
  tag = subject.get_tag(subject.get_version())
  ref = Git().rev_parse(tag)
  if not ref:
    return tag, None
  else:
    return tag, len(Git().rev_list(tag + '..HEAD', subject.get_directory()))


def print_status(project: Project) -> None:
  """
  The latest version is taken from the current version number in the package
  configuration file. Git is then queried for the tag and the commit distance
  to the current revision.
  """

  assert project.subject, "No subject"

  if isinstance(project.subject, MonorepoModel):
    monorepo_dir = project.subject.get_directory()
    if not project.packages:
      sys.exit('error: monorepo has no packages')
    items = sorted(project.packages, key=lambda x: x.name)
    names = [os.path.normpath(os.path.relpath(x.get_directory(), monorepo_dir)) for x in items]
  else:
    items = [project.subject]
    names = [project.subject.get_name()]

  width = max(map(len, names)) if names else 0

  for item, name in zip(items, names):
    tag, num_commits = get_commits_since_last_tag(item)
    if num_commits is None:
      item_info = colored('tag "{}" not found'.format(tag), 'red')
    elif num_commits == 0:
      item_info = colored('no commits', 'green') + ' since "{}"'.format(tag)
    else:
      item_info = colored('{} commit(s)'.format(num_commits), 'yellow') + ' since "{}"'.format(tag)
    print('{}: {}'.format(name.rjust(width), item_info))
