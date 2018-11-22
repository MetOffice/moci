#!/usr/bin/env python
'''
NAME
    my_archive_script.py

DESCRIPTION
    Dummy archiving script for verification purposes.
    Creates a "Moose listing" in the file $CYLC_SUITE_SHARE_DIR/CYLCLOG

REQUIRED ENVIRONMENT
    Standard Cylc environment: CYLC_SUITE_SHARE_DIR
    TEST_ENV    - Required to test the postproc is correctly passing environment
                  via the &archive_script namelist.

OPTIONAL ENVIRONMENT
    ARCHIVE_SET - Name of the Moose archive dataset.  Default=dummy
'''

import sys
import os
import re

if len(sys.argv) > 2:
    FULL_FILENAME = sys.argv[-2]
    SOURCEDIR = sys.argv[-1]
else:
    print('\n[FAIL] archive_script.py - ' +
          'Require filename and source directory as arguments')
    exit(10)

CYLCLOG = os.path.join(os.environ.get('CYLC_SUITE_SHARE_DIR', os.getcwd()),
                       'cylclog')
ARCHIVE_SET = os.environ.get('ARCHIVE_SET', 'dummy')

if sys.argv[1:-2]:
    print('\n[INFO] my_archive_script.py: Script arguments: ' +
          ', '.join(sys.argv[1:]))
else:
    print('\n[ERROR] No arguments found - expected "DummyArg"')
    exit(20)

ADUMP = re.compile(r'.*a\.da\d{8}(_\d{2})?')
ADIAG = re.compile(r'.*a\.([pm])([a-z0-9])\d{4}[a-z_\d]*(\.pp)?')
ANCF = re.compile(r'atmos_.*_[pm]([a-z0-9]).*\.nc')
NCDATA = re.compile(r'[a-zA-Z0-9_-]*([io])[_.][\d_-]*([hdmsyx])?'
                    '(restart)?(trajectory)?')

COLLECTION = None
FILENAME = os.path.basename(FULL_FILENAME)

if ADUMP.match(FILENAME):
    # Atmos dump file
    COLLECTION = 'ada.file'
elif ADIAG.match(FILENAME):
    # Atmos fields and pp files
    CHAR1, CHAR2, PP = ADIAG.match(FILENAME).groups()
    COLLECTION = 'a{}{}.{}'.format(CHAR1, CHAR2, 'pp' if PP else 'file')
elif ANCF.match(FILENAME):
    # Atmos netCDF files
    COLLECTION = 'an{}.nc.file'.format(ANCF.match(FILENAME).group(1))
elif NCDATA.match(FILENAME):
    # NEMOCICE
    REALM, PERIOD, RESTART, TRAJ = NCDATA.match(FILENAME).groups()
    if RESTART:
        COLLECTION = REALM + 'da.file'
    else:
        DATATYPE = 'i' if TRAJ else PERIOD
        COLLECTION = '{}n{}.nc.file'.format(REALM, DATATYPE)
else:
    # Unknown Data
    print('\n[FAIL] Unable to determine collection for the data')
    exit(30)

PERMISSION = 'a' if os.path.isfile(CYLCLOG) else 'w'
with open(CYLCLOG, PERMISSION) as archive:
    archive.write(os.path.join(ARCHIVE_SET, str(COLLECTION), FILENAME) + '\n')

