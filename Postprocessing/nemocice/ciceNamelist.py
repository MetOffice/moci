#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
(C) Crown copyright Met Office. All rights reserved.
For further details please refer to the file COPYRIGHT.txt
which you should have received as part of this distribution.
*****************************COPYRIGHT******************************
--------------------------------------------------------------------
 Code Owner: Please refer to the UM file CodeOwners.txt
 This file belongs in section: Rose scripts
--------------------------------------------------------------------
NAME
    ciceNamelist.py

DESCRIPTION
    Default namelists for CICE post processing control
'''


class ciceNamelist:
    pp_run = False
    restart_directory = '$DATAM'
    archive_restarts = False
    archive_timestamps = '06-01', '12-01'
    buffer_archive = 5
    means_directory = '$CYLC_TASK_WORK_DIR/../coupled'
    means_cmd = '/projects/ocean/hadgem3/nco/nco-3.9.5_clean/bin/ncra --64bit -O'
    create_means = False
    archive_means = False
    archive_set = '$CYLC_SUITE_NAME'
    debug = False

NAMELISTS = {'cicepostproc': ciceNamelist}
