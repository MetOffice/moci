#!/usr/bin/env bash
#
# NAME: extract_oasis.sh
#
# DESCRIPTION: Extracts OASIS3-MCT from a GIT repository and copies the code
#              to the HPC
#
# ENVIRONMENT VARIABLES (COMPULSORY):
#    EXTRACT_OASIS
#    HPC_HOST
#    OASIS_BRANCH
#    OASIS_REPOSITORY
#
# ENVIRONMENT VARIABLES (OPTIONAL):
#    OASIS_WC_DIR
#    HPC_HOST_USERNAME

oasis_repository=${OASIS_REPOSITORY:-git@nitrox.cerfacs.fr:globc/OASIS3-MCT/oasis3-mct.git};
user=${HPC_HOST_USERNAME:-$(whoami)}

if [ "$EXTRACT_OASIS" = "True" ]; then
    oasis_extract_dir=oasis3-mct
    # Test before a checkout to save time
    if [ -z "$OASIS_BRANCH" ]; then
	echo "We dont build from the oasis trunk, please chose a branch to use";
	echo "and assign to variable OASIS_BRANCH";
	exit 999
    fi

    if [ -z "$HPC_HOST" ]; then
	hpc_build="False"
    else
	hpc_build="True"
    fi

    git clone $oasis_repository
    # check that the repository has cloned correctly
    if [ ! -d $oasis_extract_dir ]; then
	1>&2 echo "Unable to successfully clone the oasis repository"
	exit 999;
    fi
    cd $oasis_extract_dir
    git checkout $OASIS_BRANCH
    if [ $? -ne 0 ]; then
	1>&2 echo "Unable to succesfully checkout the oasis branch $OASIS_BRANCH";
	exit 999;
    fi
else
    oasis_extract_dir=${OASIS_WC_DIR:-oasis3-mct}
fi

cd ../
if [ "$hpc_build" = "True" ] && [ -z "$CYLC_SUITE_RUN_DIR" ]; then
    # we are not running within a suite context and need to copy all files up
    # manually
    # upload to the HPC
    ssh $user@$HPC_HOST "mkdir -p $OASIS_BUILD_DIR/";
    scp -r $oasis_extract_dir $user@$HPC_HOST:$OASIS_BUILD_DIR/;
    # cleanup, only if we have extracted the code from GIT
    if [ "$EXTRACT_OASIS" = "True" ]; then
	rm -rf $oasis_extract_dir
    fi
    # upload build scripts to hpc
    scp bin/oasis_build.sh $user@$HPC_HOST:$OASIS_BUILD_DIR/
    # pass
    if [ "$BUILD_TEST" = "True" ]; then
	# upload our test executables to the HPC
	scp src/*.F90 $user@$HPC_HOST:$OASIS_BUILD_DIR/oasis3-mct/examples/tutorial/
	# upload the run script
	scp bin/run_tutorial_mo_xc40.sh $user@$HPC_HOST:$OASIS_BUILD_DIR/oasis3-mct/examples/tutorial/
	# upload the other files to make the test run
	for i_file in namcouple_TP script_ferret_FRECVOCN.jnl script_ferret_FSENDOCN_to_File.jnl
	do
	    scp file/$i_file $user@$HPC_HOST:$OASIS_BUILD_DIR/oasis3-mct/examples/tutorial/data_oasis3
	done
    fi
else
    # we are running in a suite context and only need to upload the oasis
    # source code
    scp -r $oasis_extract_dir $user@$HPC_HOST:$OASIS_BUILD_DIR/;
    if [ $? -ne 0 ]; then
	1>&2 echo "Unable to succesfully upload oasis source to $HPC_HOST"
	exit 999;
    fi
    # cleanup, only if we have extracted the code from GIT
    if [ "$EXTRACT_OASIS" = "True" ]; then
	rm -rf $oasis_extract_dir
    fi
fi

#End of script test, check that the code is avaliable
ssh $user@$HPC_HOST ls $OASIS_BUILD_DIR/oasis3-mct
[ $? -eq 0 ] || exit 1
