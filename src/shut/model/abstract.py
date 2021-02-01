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
import os
import warnings
from typing import List, Optional

from databind.core import datamodel, field

from .author import Author
from .changelog import ChangelogConfiguration
from .release import ReleaseConfiguration
from .version import Version
from shut.utils.fs import get_file_in_directory


@datamodel
class AbstractProjectModel(metaclass=abc.ABCMeta):
  # Derived fields that are not de-serialized per-se, but may be filled during the
  # deserialization process to track additional metadata.
  project: Optional['Project'] = field(derived=True, default=None)
  filename: Optional[str] = field(derived=True, default=None)
  unknown_keys: List[str] = field(derived=True, default_factory=list)

  name: str
  version: Optional[Version] = None
  author: Optional[Author] = None
  license: Optional[str] = None
  license_file: Optional[str] = None
  url: Optional[str] = None
  changelog: ChangelogConfiguration = field(default_factory=ChangelogConfiguration)
  release: ReleaseConfiguration = field(default_factory=ReleaseConfiguration)

  def get_name(self) -> str:
    warnings.warn(f'{type(self).__name__}.get_name() is deprecated, use .name instead', DeprecationWarning)
    return self.name

  def get_version(self) -> Optional[Version]:
    warnings.warn(f'{type(self).__name__}.get_version() is deprecated, use .version instead', DeprecationWarning)
    return self.version

  def get_tag(self, version: Version) -> str:
    return self.release.tag_format.format(name=self.get_name(), version=version)

  def get_directory(self) -> str:
    assert self.filename
    return os.path.dirname(self.filename)

  def get_author(self) -> Optional[Author]:
    return self.author

  def get_changelog_directory(self) -> str:
    assert self.filename
    return os.path.join(os.path.dirname(self.filename), self.changelog.directory)

  def get_license_file(self, inherit: bool = False) -> Optional[str]:
    """
    Returns the absolute path to the LICENSE file for this package.
    """

    if self.license_file:
      return self.license_file

    return get_file_in_directory(
      directory=os.path.dirname(self.filename),
      prefix='LICENSE.',
      preferred=['LICENSE', 'LICENSE.txt', 'LICENSE.rst', 'LICENSE.md'])


from . import Project  # pylint: disable=unused-import
