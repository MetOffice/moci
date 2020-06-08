#!/usr/bin/env bash
#
# NAME: oasis_build.sh
#
# DESCRIPTION: Create a make config file, and build OASIS3-MCT, along with the
#              toy tests if required.
#
# ENVIRONMENT VARIABLES (COMPULSORY):
#    BUILD_MCT
#    BUILD_TEST
#    OASIS_BUILD_DIR
#    PLATFORM-CONFIG
#    PRISMPATH
#


PRISMHOME=$PRISMPATH
oasis_src_dir=$PRISMPATH
build_mct=$BUILD_MCT
build_test=$BUILD_TEST
make_config_fn=$PLATFORM_CONFIG

# remove (if we need to) and write new make config file
rm $PRISMHOME/util/make_dir/$make_config_fn
cat <<'EOF' >$PRISMHOME/util/make_dir/$make_config_fn
###############################################################################
#
# CHAN : MPI1/MPI2
CHAN            = MPI1
#
# Paths for libraries, object files and binaries
#
# COUPLE	: path for oasis3-mct main directory
COUPLE          = $(PRISMHOME)
#
# ARCHDIR       : directory created when compiling
EOF
cat <<EOF >>$PRISMHOME/util/make_dir/$make_config_fn
ARCHDIR         = \$(COUPLE)/$OASIS_BUILD_DIR
EOF
cat <<'EOF' >>$PRISMHOME/util/make_dir/$make_config_fn
#
# MPI library
MPIDIR      = 
MPIBIN      = 
MPI_INCLUDE = 
MPILIB      = 
#
# NETCDF library
NETCDF_INCLUDE  =
NETCDF_LIBRARY  =
#

# Compiling and other commands
MAKE        = make
F90         = ftn
F           = $(F90)
f90         = $(F90)
f           = $(F90)
CC          = gcc
LD          = ftn
AR          = ar
ARFLAGS     = -ruv
#
# compiler options and cpp keys
# 
#CPPDEF    = -Duse_netCDF -Duse_comm_$(CHAN) -D__VERBOSE -DTREAT_OVERLAY

CPPDEF    = -Duse_libMPI -Duse_netCDF -Duse_comm_$(CHAN) -DDEBUG 
CCPPDEF   = -Duse_libMPI -Duse_netCDF -Duse_comm_$(CHAN) -DDEBUG 

#
# -g is necessary in F90FLAGS and LDFLAGS for pgf90 versions lower than 6.1
# 

F90FLAGS_1  = -e m -sreal64 -O2 $(PSMILE_INCDIR) $(CPPDEF)
f90FLAGS_1  = $(F90FLAGS_1)
FFLAGS_1    = $(F90FLAGS_1)
fFLAGS_1    = $(F90FLAGS_1)
CCFLAGS_1   = $(PSMILE_INCDIR) $(CPPDEF) 
LDFLAGS   =  -h byteswapio 
#
###################
#
# Additional definitions that should not be changed
#
FLIBS		= $(NETCDF_LIBRARY)
# BINDIR        : directory for executables
BINDIR          = $(ARCHDIR)/bin
# LIBBUILD      : contains a directory for each library
LIBBUILD        = $(ARCHDIR)/build/lib
# INCPSMILE     : includes all *o and *mod for each library
INCPSMILE       = -I$(LIBBUILD)/psmile.$(CHAN) -I$(LIBBUILD)/scrip  -I$(LIBBUILD)/mct 

F90FLAGS  = $(F90FLAGS_1) $(INCPSMILE) $(CPPDEF) 
f90FLAGS  = $(f90FLAGS_1) $(INCPSMILE) $(CPPDEF) 
FFLAGS    = $(FFLAGS_1) $(INCPSMILE) $(CPPDEF) 
fFLAGS    = $(fFLAGS_1) $(INCPSMILE) $(CPPDEF) 
CCFLAGS   = $(CCFLAGS_1) $(INCPSMILE) $(CPPDEF) 	
#
#
#############################################################################
EOF


# remove and overwrite the existing make.inc file with our new one
rm $PRISMHOME/util/make_dir/make.inc
cat <<EOF >$PRISMHOME/util/make_dir/make.inc
PRISMHOME = $PRISMHOME
include $PRISMHOME/util/make_dir/$make_config_fn
EOF

# do the build
if [ "$build_mct" = "True" ]; then
    cd $oasis_src_dir/util/make_dir
    make -f TopMakefileOasis3 realclean
    make -f TopMakefileOasis3
    if [ $? -ne 0 ]; then
	1>&2 echo "Unable to succesfully build oasis3-mct. Please see compiler output for more informaton"
	exit 999;
    fi
fi

if [ "$build_test" = "True" ]; then
    # if we are running in a suite, we need to move some files
    if [[ ! -z $CYLC_SUITE_RUN_DIR ]]; then
	cp $CYLC_SUITE_RUN_DIR/src/model*_ukmo_cray_xc40.F90 $oasis_src_dir/examples/tutorial
    fi
    cd $oasis_src_dir/examples/tutorial
    rm *.o
    rm *.mod
    rm model1.F90 model2.F90
    mv model1_ukmo_cray_xc40.F90 model1.F90
    mv model2_ukmo_cray_xc40.F90 model2.F90
    make model1
    make model2
fi
