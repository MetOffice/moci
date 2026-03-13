#!/usr/bin/env bash

if [ $# -ne 2 ]; then
    echo 'This script takes two arguments, the deployment host, and the deployment path for the modules'
    exit 999;
fi

specified_host=$1
deployment_location=$2

# Ensure that the branch has been checked in
git_status=$(git status)
if [[ $git_status == *"nothing to commit, working tree clean"* ]]; then
    echo "Suite checked in, running in deployment mode"
else
    echo "The suite working copy must be checked in to run in deployment mode"
    exit 999
fi

# Get our remote repository location, and check that it exists on github
remote_url=($(git remote -v))
remote_url=${remote_url[1]}
if [[ $remote_url == "git@github.com"* ]]; then
    echo "The suite has a remote url $remote_url"
else
    echo 'This suite must be connected to an upstream repository in github'
    exit 999
fi

fullhash=$(git log -n 1 --pretty=format:"%H")
# Check to see if the commit exists upstream
git ls-remote $remote_url | grep $fullhash
if [[ $? == 0 ]]; then
    echo 'The remote repository contains this hash'
else
    echo 'The remote repository does not contain the current hash. Please push changes'
    exit 999
fi


# Get our parameters
#Suite revision is branch name and hash
branch_name=$(git rev-parse --abbrev-ref HEAD)
trunc_hash=$(git log -n 1 --pretty=format:"%h")
suite_revision="$branch_name""_""$trunc_hash"

cd infrastructure_suite

# Test the versioning fits our specifications (YYYY-mm-compiler)
xios_only=$(grep '^XIOS_ONLY=' rose-suite.conf | cut -d '=' -f 2-)

if [ $xios_only == 'true' ]; then
    xiosprgenv_version=$(grep '^XIOS_PRG_ENV_VERSION=' rose-suite.conf | cut -d '=' -f 2-)
    gc_version='unused'
    oasis_version='unused'
else
    xiosprgenv_version='unused'
    gc_version=$(grep '^GC_PRG_ENV_VERSION=' rose-suite.conf | cut -d '=' -f 2-)
    oasis_version=$(grep '^OASIS_MOD_VERSION=' rose-suite.conf | cut -d '=' -f 2-)
fi
xios_version=$(grep '^XIOS_MOD_VERSION=' rose-suite.conf | cut -d '=' -f 2-)

#check this isn't the default value
version_default=\'YYYY-mm-compiler\'
if [ $gc_version == $version_default ] || [ $xios_version == $version_default ] || [ $oasis_version == $version_default ] || [ $xiosprgenv_version == $version_default ]; then
    1>&2 echo "At least one module version is set to the default value, please verify"
    exit 999
fi

# Check we deploy only when extracting code from the Cerfacs GIT repository
# if we run in a mode where we build Oasis.
xios_only=$(grep '^XIOS_ONLY=' rose-suite.conf | cut -d '=' -f 2-)
if [ $xios_only != "true" ]; then
    cerfacs_repo_url=\'https://gitlab.com/cerfacs/oasis3-mct.git\'
    l_extract_oasis=$(grep '^EXTRACT_OASIS=' rose-suite.conf | cut -d '=' -f 2-)
    oasis_repo_conf=$(grep -E '^\!{0,2}OASIS_REPOSITORY=' rose-suite.conf | cut -d '=' -f 2-)
    if [ $l_extract_oasis != "true" ] || [ $cerfacs_repo_url != $oasis_repo_conf ]; then
	1>&2 echo "Must extract oasis from Cerfacs repository to run in deployment mode"
	exit 999
    fi
fi

current_directory=$(basename "$PWD")
run_name="${current_directory}_deploy_${specified_host}"
echo "Running launch suite as $run_name. Deploying modules to $specified_host"


echo $remote_url
echo $suite_revision

cylc vip -S "DEPLOYMENT_HOST='$specified_host'" -S "MODULE_BASE='$deployment_location'" -S "SUITE_URL='$remote_url'" -S "SUITE_REVISION='$suite_revision'" --workflow-name="$run_name" --no-run-name
