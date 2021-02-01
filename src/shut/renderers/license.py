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

import datetime
import os

from pkg_resources import resource_string

from .core import Renderer, register_renderer
from shut.model import AbstractProjectModel, PackageModel
from shut.utils.io.virtual import VirtualFiles


def get_license_template(license_name: str) -> str:
  return resource_string('shut', f'data/license_templates/{license_name}.txt').decode('utf-8')


def has_license_template(license_name: str) -> bool:
  try:
    return get_license_template(license_name)
  except FileNotFoundError:
    pass


class LicenseRenderer(Renderer[AbstractProjectModel]):

  def inherits_monorepo_license(self, package: PackageModel) -> bool:
    """
    Returns #True if the *package* inherits the license file of it's mono repository. This is
    only the case if there is a monorepo, and the package and the monorepo have the same license,
    and the license is one for which we deliver a template for.
    """

    if not package.license:
      if package.project.monorepo and package.project.monorepo.license:
        return True
      return False
    if not has_license_template(package.license):
      return False

    license_file = package.get_license_file()

    # If this is a package and it uses the same license as the monorepo, and the monorepo
    # license exists or is one we would generate, then we skip producing a license for this
    # package.
    if package.project.monorepo and \
        package.project.monorepo.license == package.license and \
        not license_file:
      return True

    return False

  def get_files(self, files: VirtualFiles, model: AbstractProjectModel) -> None:
    if not model.license or (isinstance(model, PackageModel)
        and self.inherits_monorepo_license(model)):
      return

    license_file = model.get_license_file()
    license_file = license_file or os.path.join(model.get_directory(), 'LICENSE.txt')
    files.add_static(
      license_file,
      get_license_template(model.license)
        .format(year=datetime.datetime.utcnow().year, author=model.get_author().name),
    )


register_renderer(AbstractProjectModel, LicenseRenderer)
