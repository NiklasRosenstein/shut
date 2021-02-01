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
The V3 of changelogs.
"""

import enum
from typing import List
from databind.core import datamodel, field
from . import _ChangelogBase, v1


class BumpMode(enum.IntEnum):
  patch = 0
  minor = 1
  major = 2


class Type(enum.Enum):
  fix = ('fix', BumpMode.patch)
  improvement = ('improvement', BumpMode.patch)
  change = ('change', BumpMode.minor)
  breaking_change = ('breaking_change', BumpMode.major)
  refactor = ('refactor', BumpMode.patch)
  feature = ('feature', BumpMode.minor)
  docs = ('docs', BumpMode.patch)
  tests = ('test', BumpMode.patch)

  @property
  def bump_mode(self) -> BumpMode:
    return self.value[1]


@datamodel
class Entry:
  type_: Type = field(altname='type')
  component: str
  description: str
  fixes: List[str]

  Type = Type

  @classmethod
  def from_v1(cls, v1_entry: v1.Entry) -> 'Entry':
    try:
      type_ = Type[v1_entry.types[0].strip().lower()]
    except KeyError:
      type_ = Type.change
    return cls(
      type_=type_,
      component=v1_entry.components[0],
      description=v1_entry.description,
      fixes=list(map(str, v1_entry.issues)),
    )


class Changelog(_ChangelogBase[v1.Changelog], List[Entry]):
  Supersedes = v1.Changelog  # _ChangelogBase

  @classmethod
  def adapt(cls, v1_changelog: v1.Changelog) -> 'Changelog':
    return cls(map(Entry.from_v1, v1_changelog))
