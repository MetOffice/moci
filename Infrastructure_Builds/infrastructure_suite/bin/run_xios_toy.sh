#!/usr/bin/env bash
#
# NAME: run_xios_toy.sh
#
# DESCRIPTION: Runs the XIOS toy test
#
# ENVIRONMENT VARIABLES (COMPULSORY):
#    XIOS_ONLY

source_file=xios_toy.F90
executable_file=xios_toy.exe

cp -f $CYLC_SUITE_RUN_DIR/src/$source_file ./

if [ -f $executable_file ]; then
    echo "File $executable_file exists - removing before compilation"
    rm $executable_file
fi

echo "Building $executable_file"
if [ "$XIOS_ONLY" = "True" ]; then
    build_flags="-I$XIOS_INC -L$XIOS_LIB -lxios -lfmpich"
else
    build_flags="-I$OASIS_INC -L$OASIS_LIB -lpsmile.MPI1 -lscrip -lmct -lmpeu -I$XIOS_INC -L$XIOS_LIB -I$OASIS_INC -L$OASIS_LIB -lxios -lpsmile.MPI1 -lscrip -lmct -lmpeu -lfmpich"
fi

ftn -o $executable_file $build_flags $source_file
#check the build has run ok
[ $? -eq 0 ] || exit 1

echo "Running...."
mpiexec -n 1 ./$executable_file

#check mpiexec has run ok
[ $? -eq 0 ] || exit 1

#check the output file is produced
ls output.nc
[ $? -eq 0 ] || exit 1
