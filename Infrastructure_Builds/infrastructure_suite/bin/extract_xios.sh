#!/usr/bin/env bash
#
# NAME: extract_xios.sh
#
# DESCRIPTION: Extracts XIOS from a FCM repository
#
# ENVIRONMENT VARIABLES (COMPULSORY):
#    XIOS_REV
#    XIOS_URL
#    XIOS_VERSION
#

rm -rf $XIOSPATH
fcm co $XIOS_URL/$XIOS_VERSION@$XIOS_REV
mv $XIOS_VERSION $XIOSPATH


