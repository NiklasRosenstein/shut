
import os
import shlex
import subprocess as sp
import typing as t
from dataclasses import dataclass


@dataclass
class InstallOptions:

  # Quiet installation.
  quiet: bool = False

  # Whether to install the package in development mode. Defaults to `True`.
  develop: bool = True

  # Whether to upgrade dependencies during the installation.
  upgrade: bool = False

  # A set of extras to install for the package.
  extras: t.Optional[t.Set[str]] = None

  # The command sequence to invoke Pip. Defaults to `python -m pip`.
  pip: t.Optional[t.List[str]] = None

  # Additional arguments to append to the install command.
  pip_extra_args: t.Optional[t.List[str]] = None

  # Continue the installation if the current environment is determined to be a global environment,
  # as opposed to a virtual environment.
  allow_global: bool = False

  # Create a virtual environment in the current directory if the current environment is not a
  # virtual environment.
  create_environment: bool = False

  # Just print the command that would be run to install the package.
  dry: bool = False


def perform_install(options: InstallOptions, args: t.List[str]) -> None:

  # TODO(NiklasRosenstein): Check the current Python environment, potentially raise an
  #   exception or create a new Python virtual environment.

  if options.pip is None:
    pip_bin = shlex.split(os.getenv('PIP', 'python -m pip'))
  else:
    pip_bin = options.pip

  command = pip_bin + ['install'] + args + (options.pip_extra_args or [])
  if options.upgrade:
    command.append('--upgrade')
  if options.quiet:
    command.append('--quiet')

  if options.dry:
    print(' '.join(map(shlex.quote, command)))
  else:
    sp.call(command)
