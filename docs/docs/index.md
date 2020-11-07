# Welcome to the Shut documentation

Shut is an opinionated release management tool for pure Python packages.

__Supported Workflows__

* [Bootstrap a new Python project](workflows/new-project)
* [Auto-generate setup.py and supporting files](workflows/generate-files)
* [Correctness checks](workflows/correctness-checks)
* [Release management](workflows/release-management)
* [Changelog management](workflows/changelog.md)

Among it's features is the automatic generation of setuptools files, sanity checks, version number
bumping and release publishing as well as changelog management.

## Installation

Shut can be installed from PyPI:

    $ pip install shut

## Typical Usage

Initialize a new Python package:

    $ shut pkg new --name my.package .
    write .gitignore
    write package.yml
    write README.md
    write src/my/__init__.py
    write src/my/package/__init__.py

Generate setuptools files:

    $ shut pkg update
    write setup.py
    write MANIFEST.in

Create a changelog entry and commit:

    $ shut changelog --add feature --for cli -cm 'Added some useful options.'

Release a new version:

    $ shut pkg bump --minor --tag --push --dry

    ✔️ classifiers
    ✔️ consistent-author
    ✔️ consistent-version
    ✔️ license
    ✔️ readme
    ✔️ unknown-config
    ✔️ url

    ran 7 checks for package my.package in 0.001s

    bumping 3 version reference(s)
    package.yaml: 0.0.0 → 0.1.0
    setup.py: 0.0.0 → 0.1.0
    src/my/package/__init__.py: 0.0.0 → 0.1.0

    updating files
    write setup.py
    write MANIFEST.in

    tagging 0.2.0

Publish the release to PyPI:

    $ shut pkg publish warehouse:pypi

        building setuptools:sdist
        :: build/my.package-0.1.0.tar.gz

        building setuptools:wheel
        :: build/my.package-0.1.0-py3-none-any.whl

        publishing warehouse:pypi
        :: build/my.package-0.1.0.tar.gz
        :: build/my.package-0.1.0-py3-none-any.whl

Shut also makes it easy to publish from within CI jobs. For more information on this,
check out the [Publishing Guide][0].

  [0]: publishing-guide.md
