# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
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

from nr.databind.core import Collection, Field, FieldName, ObjectMapper, Struct
from nr.stream import Stream
from shore.util.version import Version
from termcolor import colored
from typing import Iterable, List, Optional, TextIO
import datetime
import enum
import os
import re
import shutil
import textwrap
import yaml


## changelog v1

class ChangelogV1Entry(Struct):
  types = Field([str])
  issues = Field([(str, int)], default=list)
  components = Field([str])
  description = Field(str)

  def to_v3(self) -> 'ChangelogV3Entry':
    try:
      type_ = ChangelogV3Type[self.types[0].strip().lower()]
    except KeyError:
      type_ = ChangelogV3Type.change
    return ChangelogV3Entry(
      type_,
      self.components[0],
      self.description,
      list(map(str, self.issues)))


class ChangelogV1(Collection, list):
  item_type = ChangelogV1Entry

  def to_v3(self) -> 'ChangelogV3':
    return ChangelogV3(None, [x.to_v3() for x in self])


## changelog v2

class ChangelogV2Type(enum.Enum):
  fix = 0
  improvement = 1
  change = 3
  refactor = 4
  feature = 5
  docs = 6
  tests = 7


class ChangelogV2Entry(Struct):
  type_ = Field(ChangelogV2Type, FieldName('type'))
  component = Field(str)
  description = Field(str)
  fixes = Field([str])


class ChangelogV2(Collection, list):
  item_type = ChangelogV2Entry

  def to_v3(self) -> 'ChangelogV3':
    return ChangelogV3(None, list(self))


## changelog v3

ChangelogV3Type = ChangelogV2Type
ChangelogV3Entry = ChangelogV2Entry


class ChangelogV3(Struct):
  release_date = Field(datetime.date, default=None)
  changes = Field([ChangelogV3Entry])

  Type = ChangelogV3Type
  Entry = ChangelogV3Entry


## public API

class Changelog:
  """
  Represents a changelog on disk.
  """

  #: A mapping for the changelog renderers that are available. The default
  #: renderer implementations are "terminal" and "markdown".
  RENDERERS = {}

  def __init__(self, filename: str, version: Optional[Version], mapper: ObjectMapper) -> None:
    self.filename = filename
    self.version = version
    self.mapper = mapper
    self.data = ChangelogV3(changes=[])

  @property
  def entries(self):
    return self.data.changes

  def exists(self) -> bool:
    " Returns #True if the changelog file exists. "

    return os.path.isfile(self.filename)

  def load(self) -> None:
    " Loads the data from the file of this changelog. "

    with open(self.filename) as fp:
      raw_data = yaml.safe_load(fp)

    datatype = (ChangelogV1, ChangelogV2, ChangelogV3)
    data = self.mapper.deserialize(raw_data, datatype, filename=self.filename)
    if isinstance(data, (ChangelogV1, ChangelogV2)):
      data = data.to_v3()

    self.data = data

  def save(self, create_directory: bool = False) -> None:
    " Saves the changelog. It will always save the changelog in the newest supported format. "

    if create_directory:
      os.makedirs(os.path.dirname(self.filename), exist_ok=True)
    data = self.mapper.serialize(self.data, ChangelogV3)
    with open(self.filename, 'w') as fp:
      yaml.safe_dump(data, fp, sort_keys=False)

  def set_release_date(self, date: datetime.date) -> None:
    self.data.release_date = date

  def add_entry(self, entry: ChangelogV2Entry) -> None:
    self.data.changes.append(entry)


class ChangelogManager:

  TYPES = frozenset(['fix', 'improvement', 'docs', 'change', 'refactor', 'feature', 'enhancement'])

  def __init__(self, directory: str, mapper: ObjectMapper) -> None:
    self.directory = directory
    self.mapper = mapper
    self._cache = {}

  def _get(self, name: str, version: Optional[str]) -> Changelog:
    key = (name, str(version))
    if key in self._cache:
      return self._cache[key]
    changelog = Changelog(os.path.join(self.directory, name), version, self.mapper)
    if os.path.isfile(changelog.filename):
      changelog.load()
    self._cache[key] = changelog
    return changelog

  @property
  def unreleased(self) -> Changelog:
    return self._get('_unreleased.yml', None)

  def version(self, version: Version) -> Changelog:
    return self._get(str(version) + '.yml', version)

  def release(self, version: Version) -> Changelog:
    """
    Renames the unreleased changelog to the file name for the specified *version*.
    """

    unreleased = self.unreleased
    unreleased.release_date = datetime.date.today()
    unreleased.save()

    os.rename(unreleased.filename, self.version(version).filename)
    self._cache.clear()

    return self.version(version)

  def all(self) -> Iterable[Changelog]:
    """
    Yields all changelogs.
    """

    for name in os.listdir(self.directory):
      if not name.endswith('.yml'):
        continue
      if name == '_unreleased.yml':
        yield self.unreleased
      else:
        version = Version(name[:-4])
        yield self.version(version)


## changelog renderers


def _group_entries_by_component(entries):
  key = lambda x: x.component
  return list(Stream.sortby(entries, key).groupby(key, collect=list))


def render_changelogs_for_terminal(fp: TextIO, changelogs: List[Changelog]) -> None:
  """
  Renders a #Changelog for the terminal to *fp*.
  """

  def _md_term_stylize(text: str) -> str:
    def _code(m):
      return colored(m.group(1), 'cyan')
    def _issue_ref(m):
      return colored(m.group(0), 'yellow', attrs=['bold'])
    text = re.sub(r'`([^`]+)`', _code, text)
    text = re.sub(r'#\d+', _issue_ref, text)
    return text

  def _fmt_issue(i):
    if str(i).isdigit():
      return '#' + str(i)
    return i

  def _fmt_issues(entry):
    if not entry.fixes:
      return None
    return '(' + ', '.join(colored(_fmt_issue(i), 'yellow', attrs=['underline']) for i in entry.fixes) + ')'

  def _fmt_types(entry):
    return colored(entry.type_.name, attrs=['bold'])

  if hasattr(shutil, 'get_terminal_size'):
    width = shutil.get_terminal_size((80, 23))[0]
  else:
    width = 80

  # Explode entries by component.
  for changelog in changelogs:
    fp.write(colored(changelog.version or 'Unreleased', 'blue', attrs=['bold', 'underline']))
    fp.write(' ({})\n'.format(changelog.data.release_date or 'no release date'))
    for component, entries in _group_entries_by_component(changelog.entries):
      maxw = max(map(lambda x: len(x.type_.name), entries))
      fp.write('  ' + colored(component or 'No Component', 'red', attrs=['bold', 'underline']) + '\n')
      for entry in entries:
        lines = textwrap.wrap(entry.description, width - (maxw + 6))
        suffix_fmt = ' '.join(filter(bool, (_fmt_issues(entry),)))
        lines[-1] += ' ' + suffix_fmt
        delta = maxw - len(entry.type_.name)
        fp.write('    {} {}\n'.format(colored((_fmt_types(entry) + ':') + ' ' * delta, attrs=['bold']), _md_term_stylize(lines[0])))
        for line in lines[1:]:
          fp.write('    {}{}\n'.format(' ' * (maxw+2), _md_term_stylize(line)))
    fp.write('\n')


def render_changelogs_as_markdown(fp: TextIO, changelogs: List[Changelog]) -> None:

  def _fmt_issue(i):
    if str(i).isdigit():
      return '#' + str(i)
    return i

  def _fmt_issues(entry):
    if not entry.fixes:
      return None
    return '(' + ', '.join(_fmt_issue(i) for i in entry.fixes) + ')'

  for changelog in changelogs:
    fp.write('## {}'.format(changelog.version or 'Unreleased'))
    fp.write(' ({})\n\n'.format(changelog.data.release_date or 'no release date'))
    for component, entries in _group_entries_by_component(changelog.entries):
      fp.write('* __{}__\n'.format(component))
      for entry in entries:
        description ='**' + entry.type_.name + '**: ' + entry.description
        if entry.fixes:
          description += ' ' + _fmt_issues(entry)
        lines = textwrap.wrap(description, 80)
        fp.write('    * {}\n'.format(lines[0]))
        for line in lines[1:]:
          fp.write('      {}\n'.format(line))
    fp.write('\n')


def render_changelogs(fp: TextIO, format: str, changelogs: List[Changelog]) -> None:
  changelogs = list(changelogs)
  unreleased = next((x for x in changelogs if not x.version), None)
  if unreleased:
    changelogs.remove(unreleased)
  changelogs.sort(key=lambda x: x.version, reverse=True)
  if unreleased:
    changelogs.insert(0, unreleased)
  Changelog.RENDERERS[format](fp, changelogs)


Changelog.RENDERERS.update({
  'terminal': render_changelogs_for_terminal,
  'markdown': render_changelogs_as_markdown,
})
