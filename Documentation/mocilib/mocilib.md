# MOCIlib

MOCIlib is intended as a library to hold an assorted range on utility functions that can be used throughout new development and maintainance of MOCI along with their associated unit tests to ensure robust and unified approach to MOCI's functionality.

## shellout

The shelllout module contains the relevant functions to execute and handle shell commands in a safe manner.

exec_subprocess is a function to execute a shell subprocess and takes the several parameters as follows:

```python
def exec_subprocess(cmd, verbose=False, timeout=None, current_working_directory=os.getcwd())
```

cmd - the command to be executed by exec_subprocess given as a string.

verbose - a boolean (True or False) to determine if the standard output (stdout) stream is output during the execution of the shell command.

timeout - an integer number determining the number of seconds a shell command can run for before a TimeoutExpired error is raised.

current_working_directory - The working directory which the shell command will be executed in given as a string.
