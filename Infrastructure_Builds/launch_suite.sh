#!/usr/bin/env bash

if [ $# -ne 2 ]; then
    echo 'This script takes two arguments, the deployment host, and the deployment path for the modules'
    exit 999;
fi

specified_host=$1
deployment_location=$2

cd infrastructure_suite

fcm_status=$(fcm stat)
if [ -z "$fcm_status" ]; then
    suite_url=$(fcm info | grep URL | grep -v Relative);
    suite_revision=$(fcm info | grep Revision);
else
    echo "The suite working copy must be checked in to run in deployment mode"
    exit 999;
fi

echo $suite_url
echo $suite_revision

rose suite-run --define-suite="DEPLOYMENT_HOST='$specified_host'" --define-suite="MODULE_BASE='$deployment_location'" --define-suite="SUITE_URL='$suite_url'" --define-suite="SUITE_REVISION='$suite_revision'" --new
