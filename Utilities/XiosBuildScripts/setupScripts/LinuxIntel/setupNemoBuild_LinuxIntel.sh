#!/bin/sh
# Script to setup up environment variables for nemoBuild.py. 
# This is for debugging purposes, the build script should
# normally be part of a suite.

export TEST_SYSTEM=UKMO_LINUX_INTEL
export NEMO=NEMO
export NEMO_REPO_URL=svn://fcm3/NEMO.xm_svn/trunk/NEMOGCM
export NEMO_REV=5432
export USE_OASIS=false
export JP_CFG=50
export BUILD_PATH=$PWD/install
export NEMO_POST_BUILD_CLEANUP=false

source /data/cr1/mhambley/modules/setup
module load environment/dynamo/compiler/intelfortran/15.0.0

module use /data/cr1/shaddad/xiosTest_20150714/modules/modules
module load XIOS/1.0
