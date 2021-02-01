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

import logging
import sys
from typing import List, Optional

from databind.json import from_json, to_json
from nr.utils.git import Git  # type: ignore
from termcolor import colored
import click
import yaml

from .. import shut, commons, project
from shut.changelog import v3
from shut.changelog.manager import ChangelogManager
from shut.changelog.render import render as render_changelogs
from shut.model import registry
from shut.model.version import parse_version
from shut.model.package import PackageModel
from shut.utils.cli import editor_open, edit_text


_git = Git()
logger = logging.getLogger(__name__)


@shut.command()
@click.argument('version', type=parse_version, required=False)
@click.option('--reformat', is_flag=True, help='reformat the changelog')
@click.option('--add', metavar='type', help='create a new changelog entry')
@click.option('--for', metavar='component', help='components for the new changelog entry (default: general)', default='general')
@click.option('--fixes', metavar='issue,…', help='issues that this changelog entry fixes')
@click.option('-m', '--message', metavar='text', help='changelog entry description')
@click.option('-e', '--edit', is_flag=True, help='edit the changelog entry or file')
@click.option('--markdown', is_flag=True, help='render the changelog as markdown')
@click.option('-a', '--all', is_flag=True, help='show the changelog for all versions')
@click.option('-s', '--stage', is_flag=True, help='stage the created/updated changelog file with git')
@click.option('-c', '--commit', is_flag=True, help='commit the created/updated changelog file with git, together with other currently staged files')
def changelog(**args):
  """
  Show changelogs or create new entries.
  """

  if (args['version'] or args['reformat']) and args['add']:
    logger.error('unsupported combination of arguments')
    sys.exit(1)

  project.load()
  monorepo = project.monorepo
  package = project.subject if project.subject != monorepo else None

  def _split(s: Optional[str]) -> List[str]:
    return list(filter(bool, map(str.strip, (s or '').split(','))))

  manager = ChangelogManager(
    package.get_changelog_directory() if package
    else monorepo.get_changelog_directory() if monorepo
    else '.changelog')

  if args['add']:

    if not args['for']:
      args['for'] = 'general'

    try:
      type_ = v3.Changelog.Entry.Type[args['add']]
    except KeyError:
      logger.error('invalid changelog type: %r', args['add'])
      sys.exit(1)

    fixes = ['#' + f if f.isdigit() else f for f in _split(args['fixes'])]
    entry = v3.Changelog.Entry(
      type_,
      args['for'],
      args['message'] or '',
      fixes)

    # Allow the user to edit the entry if no description is provided or the
    # -e,--edit option was set.
    if not entry.description or args['edit']:
      serialized = yaml.safe_dump(to_json(entry, v3.Changelog.Entry, registry=registry), sort_keys=False)
      entry = from_json(v3.Changelog.Entry, yaml.safe_load(edit_text(serialized)), registry=registry)

    # Validate the entry contents (need a description and at least one type and component).
    if not entry.description or not entry.component:
      logger.error('changelog entries need a component and description')
      sys.exit(1)

    created = not manager.unreleased.exists()
    manager.unreleased.add_entry(entry)
    manager.unreleased.save(create_directory=True)
    message = ('Created' if created else 'Updated') + ' "{}"'.format(manager.unreleased.filename)
    print(colored(message, 'cyan'))

    if args['stage'] or args['commit']:
      _git.add([manager.unreleased.filename])
    if args['commit']:
      commit_message = entry.description
      if package and monorepo:
        commit_message = '{}({}): '.format(entry.type_.name, package.name) + commit_message
      else:
        commit_message = '{}: '.format(entry.type_.name) + commit_message
      if fixes:
        commit_message += '\n\nfixes ' + ', '.join(fixes)
      _git.commit(commit_message)

    sys.exit(0)

  if args['edit']:
    if not manager.unreleased.exists():
      logger.error('no staged changelog')
      sys.exit(1)
    sys.exit(editor_open(manager.unreleased.filename))

  changelogs = []
  if args['version'] or not args['all']:
    if args['all']:
      sys.exit('error: incompatible arguments: <version> and -a,--all')
    changelog = manager.version(args['version']) if args['version'] else manager.unreleased
    # Load the changelog for the specified version or the current staged entries.
    if not changelog.exists():
      print('No changelog for {}.'.format(colored(str(args['version'] or 'unreleased'), 'yellow')))
      sys.exit(0)
    changelogs.append(changelog)
  else:
    changelogs = list(manager.all())

  if args['reformat']:
    for changelog in changelogs:
      changelog.save()
    sys.exit(0)

  if args['markdown']:
    changelog_format = 'markdown'
  else:
    changelog_format = 'terminal'

  render_changelogs(sys.stdout, changelog_format, changelogs)
