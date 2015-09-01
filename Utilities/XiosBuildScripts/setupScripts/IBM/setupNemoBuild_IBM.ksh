#!/bin/ksh
# Script to setup up environment variables for xiosBuild.py. 
# This is for debugging purposes, the build script should
# normally be part of a suite.

export TEST_SYSTEM=UKMO_IBM_PW7
export NEMO=NEMO
export NEMO_REPO_URL=svn://fcm3/NEMO.xm_svn/trunk/NEMOGCM
export NEMO_REV=3841
export XIOS=XIOS
export XIOS_PATH=/data/cr/crum/shaddad/xiosTest_20150511/XIOS
export MTOOLS=/data/nwp/nm/frrj/xios_bench/mtools_parallel_underscores/usr
export USE_OASIS=true
export OASIS_ROOT=/home/nwp/nm/frrj/Applications/r1164_vn2.0m1_AIX_COMPLIANT/oasis3-mct/ibm_power7
export JP_CFG=50
export XLCPP_MODULE=xlcpp/v12.1.0.0
export XLF_MODULE=xlf/v14.1.0.1
export BUILD_PATH=$PWD/install
export NEMO_POST_BUILD_CLEANUP=true