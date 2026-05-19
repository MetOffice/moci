#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------
# NAME
#     build_pp
#
# DESCRIPTION
#     Move PostProc application code to executable location within a rose suite
#
# -----------------------------------------------------------------------------

# Fail if environment variables are unset
set -eu

# Required environment
PP_SOURCE_DIR=${PP_SOURCE_DIR:=$CYLC_WORKFLOW_SHARE_DIR/source/moci_postproc}
PP_TARGET_DIR=${PP_TARGET_DIR:=$CYLC_WORKFLOW_SHARE_DIR/bin}

MOCILIB=${MOCILIB:=true}
MOCILIB_PATH=${MOCILIB_PATH:=$PP_SOURCE_DIR/mocilib}

PP_COMPONENTS=${PP_COMPONENTS:="atmos nemocice unicicles archive_verify"}
PP_TESTS=${PP_TESTS:=false}

echo [INFO] Building PostProc application from $PP_SOURCE_DIR
echo [INFO]  -- Build location: $PP_TARGET_DIR

if [[ ! -d $PP_SOURCE_DIR ]] ; then
    echo [ERROR] $PP_SOURCE_DIR does not exist >&2
    exit 1
fi
if [[ ! -d $PP_TARGET_DIR ]] ; then
    echo [INFO] Creating build directory ...
    mkdir -p $PP_TARGET_DIR
fi

# Link mocilib
if [[ "$MOCILIB" != true ]] ; then
    echo [INFO] MOCIlib library not requested
elif [[ -d "$MOCILIB_PATH" ]] ; then
    echo [INFO] Linking to MOCILIB at $MOCILIB_PATH ...
    ln -sf $MOCILIB_PATH $PP_TARGET_DIR/mocilib
else
    echo [ERROR] Failed to find the required \"mocilib\" library >&2
    exit 1
fi

# Copy NEMO tools
if [[ -d "$PP_SOURCE_DIR/../nemotools" ]] ; then
    cp $PP_SOURCE_DIR/../nemotools/* $PP_TARGET_DIR
else
    echo [INFO] NEMO iceberg rebuilding tools not available
fi

# Copy main_pp executable
mainscr=$PP_SOURCE_DIR/Postprocessing/main_pp.py
if [[ -f "$mainscr" ]] ; then
    cp $mainscr $PP_TARGET_DIR
else
    echo [ERROR] Source for PostProc executable $mainscr does not exist >&2
    exit 1
fi

# Copy component directory contents
src_dirs="common platforms $PP_COMPONENTS"
if [[ "$PP_TESTS" = true ]] ; then
    src_dirs="$src_dirs unittests"
fi
for directory in $src_dirs; do
    if [[ -d $PP_SOURCE_DIR/Postprocessing/$directory ]] ; then
	cp $PP_SOURCE_DIR/Postprocessing/$directory/* $PP_TARGET_DIR
    else
	echo [ERROR] Source for PostProc component $directory does not exist >&2
	exit 1
    fi
done
