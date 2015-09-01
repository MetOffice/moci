#!/bin/sh
export TEST_SYSTEM=UKMO_CRAY_XC40
export NEMO=NEMO

#export XIOS=XIOS
#export XIOS_PATH=/data/d02/shaddad/xiosTest_20150612/XIOS

export BUILD_PATH=$PWD/install
export nemoTasksJpi=8
export nemoTasksJpj=16
export xiosTasks=16
export JP_CFG=50
export NEMO_EXP_REL_PATH=
export TasksPerNode=32
export XiosTasksPerNode=8


module load python/v2.7.9

module use /data/d02/shaddad/xiosTest_20150730_oasis/modules/modules
module load cray-hdf5-parallel/1.8.13
module load cray-netcdf-hdf5parallel/4.3.2
module load XIOS/1.0
