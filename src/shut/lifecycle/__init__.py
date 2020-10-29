
import abc
import subprocess as sp
import typing as t

import networkx as nx

from shut.model.requirements import RequirementsList, VendoredRequirement
from shut.model.package import PackageModel
from shut.model.monorepo import MonorepoModel
from shut.test import Runtime, TestRun, TestStatus, Virtualenv
from .install import InstallOptions, perform_install


class BaseLifecycle(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def install(self, options: InstallOptions) -> None:
    """
    Install the entity into the current environment. Unless #InstallOptions.allow_global is set
    to `True`, the current environment is expected to be a Python virtual environment. If that is
    not the case, either an #EnvironmentError is raised or a new virtual environment will be
    created automatically (if #InstallOptions.create_environment is `True`).
    """


class MonorepoLifecycle(BaseLifecycle):

  def __init__(self, config: MonorepoModel) -> None:
    self.config = config

  # BaseLifecycle

  def install(self, options: InstallOptions) -> None:

    # Order the packages in topological order.
    graph = monorepo.get_inter_dependencies_graph()
    package_map = {p.name: p for p in project.packages}
    packages = [package_map[p] for p in nx.algorithms.dag.topological_sort(graph)]

    # Generate the install arguments for each of the packages.
    args = [PackageLifecycle(p).get_install_args(options) for p in packages]

    perform_install(options, args)


class PackageLifecycle(BaseLifecycle):

  def __init__(self, config: PackageModel) -> None:
    self.config = config

  def get_install_args(self, options: InstallOptions) -> t.List[str]:
    """
    Returns a list arguments that would be passed to the Pip install command for this package.
    Does not include any global options.
    """

    reqs = RequirementsList()

    # Pip does not understand "test" as an extra and does not have an option to
    # install test requirements.
    if options.extras and 'test' in options.extras:
      reqs += self.config.test_requirements

    reqs.append(VendoredRequirement(VendoredRequirement.Type.Path, self.config.get_directory()))
    reqs += self.config.requirements.vendored_reqs()

    if self.config.project.monorepo and inter_deps:
      # TODO(NiklasRosenstein): get_inter_dependencies_for() does not currently differentiate
      #   between normal, test and extra requirements.
      project_packages = {p.name: p for p in self.config.project.packages}
      for ref in self.config.project.monorepo.get_inter_dependencies_for(self.config):
        dep = project_packages[ref.package_name]
        if not ref.version_selector.matches(dep.version):
          print('note: skipping inter-dependency on package "{}" because the version selector '
                '{} does not match the present version {}'
                .format(dep.name, ref.version_selector, dep.version), file=sys.stderr)
        else:
          reqs.insert(0, VendoredRequirement(VendoredRequirement.Type.Path, dep.get_directory()))

    # TODO(NiklasRosenstein): Handle extras

    return reqs.get_pip_args(self.config.get_directory(), options.develop)

  def test(self, isolate: bool, keep_test_env: bool = False, capture: bool = True) -> TestRun:
    if not self.config.test_driver:
      raise RuntimeError('package has no test driver configured')
    if isolate:
      venv = Virtualenv(os.path.join(self.config.get_directory(), '.venv-test'))
      if venv.exists():
        print('Re-using existing virtual environment at .venv-test ...')
      else:
        print('Creating temporary virtual environment at .venv-test ...')
        venv.create(Runtime.from_env())
      runtime = venv.get_runtime()
      print(f'Installing package "{self.config.name}" and test requirements ...')
      try:
        orig_cwd = os.getcwd()
        os.chdir(self.config.get_directory())
        shut(['pkg', '--no-checks', 'install', '--pip', venv.bin('pip'), '--extra', 'test', '-q'], standalone_mode=False)
      except SystemExit as exc:
        os.chdir(orig_cwd)
        if exc.code != 0:
          raise
    else:
      venv = None
      runtime = Runtime.from_env()

    test_reqs = [req.to_setuptools() for req in self.config.test_driver.get_test_requirements()]
    if test_reqs:
      sp.check_call(runtime.pip + ['install', '-q'] + test_reqs)

    try:
      return self.config.test_driver.test_package(self.config, runtime, capture)
    finally:
      if venv and not keep_test_env:
        venv.rm()

  # BaseLifecycle

  def install(self, options: InstallOptions) -> None:
    args = self.get_install_args(options)
    perform_install(options, args)
