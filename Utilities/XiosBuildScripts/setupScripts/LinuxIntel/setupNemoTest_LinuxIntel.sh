#!/bin/sh
export TEST_SYSTEM=UKMO_LINUX_INTEL
export NEMO=NEMO

#export XIOS=XIOS
#export XIOS_PATH=/data/d02/shaddad/xiosTest_20150612/XIOS

export BUILD_PATH=$PWD/install
export nemoTasksJpi=2
export nemoTasksJpj=2
export xiosTasks=1
export JP_CFG=50
export NEMO_EXP_REL_PATH=
export TasksPerNode=6
export XiosTasksPerNode=1

source /data/cr1/mhambley/modules/setup
module load environment/dynamo/compiler/intelfortran/15.0.0

module use /data/cr1/shaddad/xiosTest_20150714/modules/modules
module load XIOS/1.0
