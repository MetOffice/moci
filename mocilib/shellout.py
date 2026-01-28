# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------

import subprocess
import os
import sys
import shlex


def _exec_subprocess(cmd, verbose=False, timeout=None ,current_working_directory=os.getcwd()):
    """
    Execute a given shell command

    :param cmd: The command to be executed given as a string
    :param verbose: A boolean value to determine if the stdout
    stream is displayed during the runtime.
    :param current_working_directory: The directory in which the
    command should be executed.
    """

    cmd = shlex.split(cmd)

    try:

        output = subprocess.run(
            cmd,
            capture_output=True,
            cwd=current_working_directory,
            timeout=timeout,
            check=True
        )
        rcode = output.returncode

        if verbose and output:
            sys.stdout.write(f"[DEBUG]{output.stdout}\n")
        if output.stderr and output.returncode != 0:
            sys.stderr.write(f"[ERROR] {output.stderr}\n")
        if sys.version_info[0] >= 3:
            output.stdout = output.stdout.decode()

    except subprocess.CalledProcessError as exc:
        output = exc.output
        rcode = exc.returncode

    return output, rcode
