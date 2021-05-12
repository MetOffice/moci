#!/usr/bin/env bash

###############################################################################
# Script: test_tab.sh
#
# Purpose: Script to look at python code in a directory (recursively) and
#          identify if tab characters are present.
# Arguments: Path to the directory of python files
###############################################################################

echo "List of files containing tab characters (with line numbers) below:"
grep -nP '\t' $(find $1 | grep -P '.py$')
if [ $? -eq 0 ]; then
    echo "There are tab characters found in the drivers python code." >& 2;
    echo "Check standard output for more details" >& 2;
    exit 1;
else
    echo "None of the files contain tabs!"
    exit 0;
fi
