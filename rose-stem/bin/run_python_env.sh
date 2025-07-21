#!/usr/bin/env sh
###############################################################################
# Script: run_python_env.sh
#
# Purpose: Wrapper script to launch the appropriate app with a pre-defined
#          environment.
#          This is currently necessary to run with Python 3, since Rose
#          is not yet compatible with Python 3, so the environment cannot
#          be set in the rose app (pre-)script(s).
#
# Arguments: The name of the executable or script to be run, followed by any
#            relevant arguments.
###############################################################################

eval "$PYTHON_ENVIRONMENT" 

echo >&2 [INFO] Running $1 application with Python version:
python --version >&2
echo >&2
$@
