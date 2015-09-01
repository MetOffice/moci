#!/bin/sh

export TEST_SYSTEM=UKMO_LINUX_INTEL

. /data/cr1/mhambley/modules/setup
module load environment/dynamo/compiler/intelfortran/15.0.0

module use $(pwd)/modules/modules 
module load XIOS/1.0

