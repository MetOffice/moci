#!/usr/bin/env bash
#
# NAME: run_tutorial.sh
#
# DESCRIPTION: Runs the OASIS3-MCT tutorial tests
#
# ENVIRONMENT VARIABLES (COMPULSORY):
#    NPROC_EXE1
#    NPROC_EXE2
#    TEST_MODEL1_EXE
#    TEST_MODEL2_EXE
#    PRISMPATH
#

tutorial_dir=$PRISMPATH/examples/tutorial
datadir=$tutorial_dir/data_oasis3

# Gather the input data
cp -f $datadir/*nc ./
cp -f $datadir/*.jnl ./
cp -f $CYLC_SUITE_RUN_DIR/file/namcouple_TP ./namcouple
cp -f $CYLC_SUITE_RUN_DIR/file/*.jnl ./

# Copy the executables
cp -f $tutorial_dir/$TEST_MODEL1_EXE ./
cp -f $tutorial_dir/$TEST_MODEL2_EXE ./

# Run the models using aprun
aprun -n $NPROC_EXE1 ./$TEST_MODEL1_EXE : -n $NPROC_EXE2 ./$TEST_MODEL2_EXE
