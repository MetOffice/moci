# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------

import subprocess
import os
import sys
import shlex


def exec_subprocess(cmd, verbose=False, timeout=None ,current_working_directory=os.getcwd()):
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
        output_message = output.stdout.decode()

        if verbose and output:
            sys.stdout.write(f"[DEBUG]{output.stdout}\n")
        if output.stderr and output.returncode != 0:
            sys.stderr.write(f"[ERROR] {output.stderr}\n")

    except subprocess.CalledProcessError as exc:
        output_message = exc.stdout.decode() if exc.stdout else ""
        rcode = exc.returncode

    except subprocess.TimeoutExpired as exc:
        output_message = exc.stdout.decode() if exc.stdout else ""
        rcode = exc.returncode

    return rcode,output_message
