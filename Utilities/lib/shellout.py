import timer
import subprocess
import shlex
import os
import sys


def _exec_subprocess(cmd, verbose=True, current_working_directory=os.getcwd()):
    """
    Execute a given shell command

    :param cmd: The command to be executed given as a string
    :param verbose: A boolean value to determine if the stdout
    stream is displayed during the runtime.
    :param current_working_directory: The directory in which the
    command should be executed.
    """
    try:

        output = subprocess.run(
            cmd,
            stdin=subprocess.PIPE,
            capture_output=True,
            cwd=current_working_directory,
            timeout=10,
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
    except OSError as exc:
        output = exc.strerror
        rcode = exc.errno

    return output, rcode
