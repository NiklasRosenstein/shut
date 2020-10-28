
import click
import networkx as nx

from shut.commands.mono import mono, project
from shut.commands.pkg.install import split_extras
from shut.lifecycle import MonorepoLifecycle, InstallOptions
from shut.model.monorepo import MonorepoModel


@mono.command()
@click.option('--develop/--no-develop', default=True,
  help='Install in develop mode (default: true)')
@click.option('--extra', type=split_extras, help='Specify one or more extras to install.')
@click.option('-U', '--upgrade', is_flag=True, help='Upgrade all packages (forwarded to pip install).')
@click.option('-q', '--quiet', is_flag=True, help='Quiet install')
@click.option('--pip', help='Override the command to run Pip. Defaults to "python -m pip" or the PIP variable.')
@click.option('--pip-args', help='Additional arguments to pass to Pip.')
@click.option('--dry', is_flag=True, help='Print the Pip command to stdout instead of running it.')
def install(develop, extra, upgrade, quiet, pip, pip_args, dry):
  """
  Install all packages in the monorepo using`python -m pip`.

  The command used to invoke Pip can be overwritten using the `PIP` environment variable.
  """

  monorepo = project.load_or_exit(expect=MonorepoModel)
  options = InstallOptions(
    quiet=quiet,
    develop=develop,
    upgrade=upgrade,
    extras=extra,
    pip=shlex.split(pip) if pip else None,
    pip_extra_args=shlex.split(pip_args) if pip_args else None,
    allow_global=False,
    create_environment=False,
    dry=dry)
  MonorepoLifecycle(monorepo).install(options)
