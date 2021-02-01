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
from fnmatch import fnmatch

from databind.core import datamodel


@datamodel(frozen=True)
class TargetId:
  """
  Represents the ID of a target that can be selected on the command line. We use the
  "target" concept for builds and publishers. A target ID may contain wildcard characters
  in which case it can be used to match multiple targets with #fnmatch().
  """

  scope: str
  name: str

  def __str__(self):
    return f'{self.scope}:{self.name}'

  @classmethod
  def parse(cls, s: str, allow_scope_only: bool = False) -> 'TargetId':
    parts = s.split(':')
    if allow_scope_only and len(parts) == 1:
      parts = [parts[0], '*']
    return cls(*parts)

  def match(self, other_id: 'TargetId', allow_match_name: bool = False) -> bool:
    if fnmatch(other_id.scope, self.scope) and fnmatch(other_id.name, self.name):
      return True
    if allow_match_name and self.name == '*':
      return self.scope == other_id.name
    return False


class Target(metaclass=abc.ABCMeta):

  @abc.abstractproperty
  def id(self) -> TargetId:
    pass
