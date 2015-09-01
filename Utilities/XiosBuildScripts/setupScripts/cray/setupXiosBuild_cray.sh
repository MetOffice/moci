#!/bin/bash
# Script to setup up environment variables for xiosBuild.py. 
# This is for debugging purposes, the build script should
# normally be part of a suite.

module load cray-hdf5-parallel/1.8.13
module load cray-netcdf-hdf5parallel/4.3.2

export TEST_SYSTEM=UKMO_CRAY_XC40
export XIOS_DO_CLEAN_BUILD=true
export XIOS_POST_BUILD_CLEANUP=false
export XIOS_REPO_URL=svn://fcm1/xios.xm_svn/XIOS/branchs/xios-1.0
export XIOS_REV=HEAD
export XIOS=XIOS
export USE_OASIS=false
export OASIS_ROOT=/home/d02/shaddad/Projects/GC3Port/r1217_port_mct_xcf/oasis3-mct/crayxc40
export BUILD_PATH=$(pwd)/install
export MTOOLS=$NETCDF_DIR
export XIOS_NUM_CORES=8
export XLF_MODULE=
export XLCPP_MODULE=
export DEPLOY_AS_MODULE=true
export MODULE_INSTALL_PATH=$(pwd)/modules
export MODULE_VERSION=1.0

