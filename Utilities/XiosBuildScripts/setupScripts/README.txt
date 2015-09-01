Setup scripts to run build & test scripts from command line:
============================================================

The build and test scripts in the directory above this one are designed 
primarily to run as part of rose suite. Users may also want to be able to 
run them individually for various reasons.

To do this, the relevant environment variables that would be provided by the 
Rose suite environment need to be set up first. These she be run using the
'source' command e.g.
. setupScripts/cray/setupXiosBuild.sh

After setting up the environment variables in this way the relevant script can 
be run. For example to build XIOS on the Cray platform, the following 2 commands
should be run:

. $SCRIPT_ROOT/setupScripts/cray/setupXiosBuild.py
$SCRIPT_ROOT/buildXios.py

Each of the executable scripts has a corresponding setup script for each 
supported platform.
