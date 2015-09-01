#!/bin/sh
# Script to setup up environment variables for xiosBuild.py. 
# This is for debugging purposes, the build script should
# normally be part of a suite.

export TEST_SYSTEM=UKMO_CRAY_XC40
export NEMO=NEMO
export NEMO_REPO_URL=svn://fcm3/NEMO.xm_svn/branches/dev/shaddad/r5643_buildWithOasisNoKeys/NEMOGCM
export NEMO_REV=5648
export USE_OASIS=true
export OASIS_ROOT=/home/d02/shaddad/Projects/GC3Port/r1217_port_mct_xcf/oasis3-mct/crayxc40
export JP_CFG=50
export BUILD_PATH=$PWD/install
export NEMO_POST_BUILD_CLEANUP=false

module use /data/d02/shaddad/xiosTest_20150730_oasis/modules/modules
module load cray-hdf5-parallel/1.8.13
module load cray-netcdf-hdf5parallel/4.3.2
module load XIOS/1.0
