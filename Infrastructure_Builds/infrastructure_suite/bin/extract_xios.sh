#!/usr/bin/env bash
#
# NAME: extract_xios.sh
#
# DESCRIPTION: Extracts XIOS from a FCM repository
#
# ENVIRONMENT VARIABLES (COMPULSORY):
#    XIOSPATH
#    XIOS_REV
#    XIOS_URL
#    XIOS_VERSION
#

rm -rf $XIOSPATH
echo 'Attempting to checkout with the command'
echo "${XIOS_URL}/${XIOS_VERSION}@${XIOS_REV}"
fcm co $XIOS_URL/$XIOS_VERSION@$XIOS_REV

XIOS_VERSION_BASE="$(basename $XIOS_VERSION)"
mv $XIOS_VERSION_BASE $XIOSPATH

if [[ "$XIOS_REV" == "1873" ]]; then
   sed -i 's/#include <mpi.h>/#include <stdint.h>\n#include <mpi.h>/g' $XIOSPATH/src/mpi.hpp
fi

#End of script test
ls $XIOSPATH
[ $? -eq 0 ] || exit 1


