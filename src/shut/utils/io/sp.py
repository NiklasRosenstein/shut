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

import subprocess

from termcolor import colored


def subprocess_trimmed_call(*args, verbose: bool = False, **kwargs) -> int:
  """
  Executes a subprocess and only shows stderr in red and indented by 2 spaces if there
  was any error output. Returns the status code.

  If *verbose* is enabled, the stdout and stderr is not redirected.
  """

  proc = subprocess.Popen(
    *args,
    stdout=None if verbose else subprocess.PIPE,
    stderr=None if verbose else subprocess.PIPE,
    **kwargs)  # type: ignore

  stdout, stderr = proc.communicate()
  if stderr:
    for line in stderr.decode().splitlines():
      if not line:
        continue
      print(f'  {colored(line, "red")}')

  return proc.wait()
