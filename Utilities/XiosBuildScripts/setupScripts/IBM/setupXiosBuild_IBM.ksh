#!/bin/ksh
# Script to setup up environment variables for xiosBuild.py. 
# This is for debugging purposes, the build script should
# normally be part of a suite.


export TEST_SYSTEM=UKMO_IBM_PW7
export XIOS_DO_CLEAN_BUILD=true
export XIOS_POST_BUILD_CLEANUP=false
export XIOS_USE_PREBUILT_LIB=false
export XIOS_PREBUILT_DIR='/data/cr/crum/shaddad/xiosTest01/XIOS'
export XIOS_REPO_URL=svn://fcm1/xios.xm_svn/XIOS/branchs/xios-1.0
export XIOS_REV=HEAD
export XIOS=XIOS
export USE_OASIS=true
export OASIS_ROOT='/home/nwp/nm/frrj/Applications/r1164_vn2.0m1_AIX_COMPLIANT/oasis3-mct/ibm_power7'
export BUILD_PATH=$(pwd)/install
export MTOOLS=/data/nwp/nm/frrj/xios_bench/mtools_parallel_underscores/usr
export XIOS_NUM_CORES=8
export XLCPP_MODULE=xlcpp/v12.1.0.0
export XLF_MODULE=xlf/v14.1.0.1


