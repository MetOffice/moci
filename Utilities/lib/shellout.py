import timer
import subprocess
import shlex
import os


def _exec_subprocess(cmd, verbose=True,current_working_directory=os.getcwd()):
    """
    Execute a given shell command

    :param cmd: The command to be executed given as a string
    :param verbose: A boolean value to determine if the stout
    stream is displayed during the runtime.
    :param current_working_directory: The directory in which the
    command should be executed.
    """
    process = subprocess.run(cmd,
                             stdin= subprocess.PIPE,
                             capture_output=True,
                             cwd=current_working_directory,
                             timeout=10
                             )
