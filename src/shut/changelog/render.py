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
Provides functions to render a list of changelogs. Always only supports the newest
changelog version.
"""

from .manager import Changelog
from nr.stream import Stream  # type: ignore
from termcolor import colored
from typing import List, TextIO
import re
import shutil
import textwrap


def _group_entries_by_component(entries):
  key = lambda x: x.component
  return list(Stream.sortby(entries, key).groupby(key, collect=list))


def _terminal(fp: TextIO, changelogs: List[Changelog]) -> None:
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


def _markdown(fp: TextIO, changelogs: List[Changelog]) -> None:

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


renderers = {
  'terminal': _terminal,
  'markdown': _markdown,
}


def render(fp: TextIO, format: str, changelogs: List[Changelog]) -> None:
  changelogs = list(changelogs)
  unreleased = next((x for x in changelogs if not x.version), None)
  if unreleased:
    changelogs.remove(unreleased)
  changelogs.sort(key=lambda x: x.version, reverse=True)
  if unreleased:
    changelogs.insert(0, unreleased)

  renderers[format](fp, changelogs)
