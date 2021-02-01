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
import os
import sys
from typing import Iterable, List
from urllib.parse import urlparse

from shut.model import PackageModel
from shut.model.publish import WarehouseCredentials, WarehouseConfiguration
from shut.model.target import TargetId
from shut.utils.io.sp import subprocess_trimmed_call
from .core import Publisher, PublisherProvider, register_publisher_provider

logger = logging.getLogger(__name__)


def _resolve_envvars(s):
  if s and s.startswith('$'):
    value = os.getenv(s[1:])
    if not value:
      raise RuntimeError('environment variable {} is not set.'.format(s))
    return value
  return s


class WarehousePublisher(Publisher):
  """
  A publisher target that uploads files to a Warehouse (Python Package Index) using the
  "twine" command.
  """

  def __init__(self, id_: TargetId, config: WarehouseConfiguration, name: str) -> None:
    self._id = id_
    self.config = config
    self.name = name

  @classmethod
  def from_pypi_credentials(cls, id_: TargetId, creds: WarehouseCredentials) -> 'WarehousePublisher':
    config = WarehouseConfiguration(
      repository='pypi',
      test_repository='testpypi',
    ).with_creds(creds)
    return cls(id_, config, 'PyPI')

  # Publisher Overrides

  def get_description(self) -> str:
    return f'Publish the package to {self.name}.'

  def get_build_dependencies(self) -> Iterable[TargetId]:
    yield TargetId.parse('setuptools:*')

  def publish(self, files: List[str], test: bool, verbose: bool):
    command = [sys.executable, '-m', 'twine', 'upload', '--non-interactive']

    config = self.config
    repo = config.test_repository if test else config.repository
    repo_url = config.test_repository_url if test else config.repository_url
    username = config.test_username if test else config.username
    password = config.test_password if test else config.password

    username = _resolve_envvars(username)
    password = _resolve_envvars(password)

    if not repo and not repo_url:
      prefix = 'test_' if test else ''
      raise RuntimeError('missing {0}repository or {0}repository_url for PypiPublisher'.format(prefix))

    if repo:
      command += ('--repository', repo)
    if repo_url:
      command += ('--repository-url', repo_url)
    #if config.sign:
    #  command.append('--sign')
    #if config.sign_with:
    #  command += ('--sign-with', config.sign_with)
    #if config.identity:
    #  command += ('--identity', config.identity)
    if username is not None:
      command += ('--username', username)
    if password is not None:
      command += ('--password', password)
    #if config.skip_existing:
    #  command.append('--skip-existing')
    #if config.cert:
    #  command += ('--cert', config.cert)
    #if config.client_cert:
    #  command += ('--client-cert', config.client_cert)
    command += files
    command += ['--verbose']

    logger.debug('invoking twine: %s', command)
    res = subprocess_trimmed_call(command)
    return res == 0

  # Target Overrides

  @property
  def id(self) -> TargetId:
    return self._id


class WarehouseProvider(PublisherProvider[PackageModel]):

  # PublisherProvider Overrides

  def get_publishers(self, package: PackageModel) -> Iterable[Publisher]:
    publish = package.get_publish_config()
    if publish.pypi.enabled:
      yield WarehousePublisher.from_pypi_credentials(
        TargetId('warehouse', 'pypi'),
        publish.pypi.credentials)

    for name, config in publish.warehouses.items():
      display_name = name
      if config.repository_url:
        display_name = urlparse(config.repository_url).netloc
      elif config.repository:
        display_name = config.repository
      yield WarehousePublisher(TargetId('warehouse', name), config, display_name)


register_publisher_provider(PackageModel, WarehouseProvider)
