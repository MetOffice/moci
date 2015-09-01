#!/bin/bash
# Script to setup up environment variables for xiosBuild.py. 
# This is for debugging purposes, the build script should
# normally be part of a suite.

. /data/cr1/mhambley/modules/setup
module load environment/dynamo/compiler/intelfortran/15.0.0

export TEST_SYSTEM=UKMO_LINUX_INTEL
export XIOS_DO_CLEAN_BUILD=true
export XIOS_POST_BUILD_CLEANUP=false
export XIOS_REPO_URL=svn://fcm1/xios.xm_svn/XIOS/branchs/xios-1.0
export XIOS_REV=HEAD
export XIOS=XIOS
export USE_OASIS=false
export OASIS_ROOT=
export BUILD_PATH=$(pwd)/install
export MTOOLS=$NETCDF_DIR
export XIOS_NUM_CORES=4
export XLF_MODULE=
export XLCPP_MODULE=
export DEPLOY_AS_MODULE=true
export MODULE_INSTALL_PATH=$(pwd)/modules
export MODULE_VERSION=1.0

