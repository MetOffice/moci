#!/usr/bin/env bash
#
# NAME: xios_build.sh
#
# DESCRIPTION: Creates .arch files and builds XIOS
#
# ENVIRONMENT VARIABLES (COMPULSORY):
#    XIOSPATH
#

cd $XIOSPATH/arch

cat << EOF > arch-XC40_UKMO.env
export HDF5_INC_DIR=""
export HDF5_LIB_DIR=""

export NETCDF_INC_DIR=""
export NETCDF_LIB_DIR=""

export BOOST_INC_DIR=""
export BOOST_LIB_DIR=""

export BLITZ_INC_DIR=""
export BLITZ_LIB_DIR=""
EOF

cat << EOF > arch-XC40_UKMO.fcm
################################################################################
###################                Projet XIOS               ###################
################################################################################

# Cray XC build instructions for XIOS/xios-1.0
# These files have been tested on 
# Archer (XC30), ECMWF (XC30), and the Met Office (XC40) using the Cray PrgEnv.
# One must also: 
#    module load cray-netcdf-hdf5parallel/4.3.2
# There is a bug in the CC compiler prior to cce/8.3.7 using -O3 or -O2
# The workarounds are not ideal:
# Use -Gfast and put up with VERY large executables
# Use -O1 and possibly suffer a significant performance loss.
#
# Mike Rezny Met Office 23/03/2015

%CCOMPILER      CC
%FCOMPILER      ftn
%LINKER         CC

%BASE_CFLAGS    -em -DMPICH_SKIP_MPICXX -h msglevel_4 -h zero -h gnu

## Only use -O3 if you can load module cce/8.3.7 or later
#%PROD_CFLAGS    -O3 -DBOOST_DISABLE_ASSERTS

## Otherwise take your pick of these, refer to information above.
%PROD_CFLAGS    -O1 -DBOOST_DISABLE_ASSERTS
## %PROD_CFLAGS    -Gfast -DBOOST_DISABLE_ASSERTS
%DEV_CFLAGS     -O2
%DEBUG_CFLAGS   -g

%BASE_FFLAGS    -em -m 4 -e0 -eZ
%PROD_FFLAGS    -O2
%DEV_FFLAGS     -G2
%DEBUG_FFLAGS   -g

%BASE_INC       -D__NONE__
%BASE_LD        -D__NONE__

%CPP            cpp
%FPP            cpp -P -CC
%MAKE           gmake
EOF

cat << EOF > arch-XC40_UKMO.path
NETCDF_INCDIR=""
NETCDF_LIBDIR=""
NETCDF_LIB=""

MPI_INCDIR=""
MPI_LIBDIR=""
MPI_LIB=""

HDF5_INCDIR=""
HDF5_LIBDIR=""
HDF5_LIB=""

BOOST_INCDIR="-I$BOOST_INCDIR"
BOOST_LIBDIR="-L$BOOST_LIBDIR"
BOOST_LIB=""

BLITZ_INCDIR="-I$BLITZ_INCDIR"
BLITZ_LIBDIR="-L$BLITZ_LIBDIR"
BLITZ_LIB=""

OASIS_INCDIR="-I$OASIS_ROOT/build/lib/psmile.MPI1"
OASIS_LIBDIR="-L$OASIS_LIB"
OASIS_LIB="-lpsmile.MPI1 -lscrip -lmct -lmpeu"
EOF

cd $CYLC_SUITE_RUN_DIR/share
tar -cvf xios_tmp.tar xios
mv xios_tmp.tar $RAMTMP
cd $RAMTMP
tar -xvf xios_tmp.tar
rm xios_tmp.tar

cd $RAMTMP/xios
echo 'Building xios in'
echo $PWD

./make_xios --job 8 --arch XC40_UKMO --use_oasis oasis3_mct

find .
mv ./bin $XIOSPATH/
mv ./lib $XIOSPATH/
mv ./inc $XIOSPATH/

cd $RAMTMP
rm -rf $RAMTMP/xios
