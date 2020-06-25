#!/usr/bin/env bash
#
# NAME: extract_oasis.sh
#
# DESCRIPTION: Extracts OASIS3-MCT from a GIT repository and copies the code
#              to the HPC
#
# ENVIRONMENT VARIABLES (COMPULSORY):
#    HPC_HOST_OASIS
#    OASIS_BRANCH
#    OASIS_REPOSITORY
#

oasis_repository=${OASIS_REPOSITORY:-git@nitrox.cerfacs.fr:globc/OASIS3-MCT/oasis3-mct.git};

# Test before a checkout to save time
if [ -z "$OASIS_BRANCH" ]; then
    echo "We dont build from the oasis trunk, please chose a branch to use";
    echo "and assign to variable OASIS_BRANCH";
    exit 999
fi

if [ -z "$HPC_HOST_OASIS" ]; then
    hpc_build="False"
else
    hpc_build="True"
fi

user=$(whoami)

git clone $oasis_repository
# check that the repository has cloned correctly
if [ ! -d oasis3-mct ]; then
    1>&2 echo "Unable to successfully clone the oasis repository"
    exit 999;
fi
cd oasis3-mct
git checkout $OASIS_BRANCH
if [ $? -ne 0 ]; then
    1>&2 echo "Unable to succesfully checkout the oasis branch $OASIS_BRANCH";
    exit 999;
fi

cd ../
if [ "$hpc_build" = "True" ] && [ -z "$CYLC_SUITE_RUN_DIR" ]; then
    # we are not running within a suite context and need to copy all files up
    # manually
    # upload to the HPC
    ssh $user@$HPC_HOST "mkdir -p $OASIS_BUILD_DIR/";
    scp -r oasis3-mct $user@$HPC_HOST_OASIS:$OASIS_BUILD_DIR/;
    # cleanup
    rm -rf oasis3-mct
    # upload build scripts to hpc
    scp bin/oasis_build.sh $user@$HPC_HOST_OASIS:$OASIS_BUILD_DIR/
    # pass
    if [ "$BUILD_TEST" = "True" ]; then
	# upload our test executables to the HPC
	scp src/*.F90 $user@$HPC_HOST_OASIS:$OASIS_BUILD_DIR/oasis3-mct/examples/tutorial/
	# upload the run script
	scp bin/run_tutorial_mo_xc40.sh $user@$HPC_HOST_OASIS:$OASIS_BUILD_DIR/oasis3-mct/examples/tutorial/
	# upload the other files to make the test run
	for i_file in namcouple_TP script_ferret_FRECVOCN.jnl script_ferret_FSENDOCN_to_File.jnl
	do
	    scp file/$i_file $user@$HPC_HOST_OASIS:$OASIS_BUILD_DIR/oasis3-mct/examples/tutorial/data_oasis3
	done
    fi
else
    # we are running in a suite context and only need to upload the oasis
    # source code
    rsync -r oasis3-mct $user@$HPC_HOST_OASIS:$OASIS_BUILD_DIR/;
    if [ $? -ne 0 ]; then
	1>&2 echo "Unable to succesfully upload oasis source to $HPC_HOST_OASIS"
	exit 999;
    fi
    rm -rf oasis3-mct
fi

#End of script test, check that the code is avaliable
ssh $user@$HPC_HOST_OASIS ls $OASIS_BUILD_DIR/oasis3-mct
[ $? -eq 0 ] || exit 1
