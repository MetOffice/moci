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
    nemoNamelist.py

DESCRIPTION
    Default namelists for NEMO post processing control
'''


class nemoNamelist:
    pp_run = False
    restart_directory = '$DATAM'
    exec_rebuild = '/projects/ocean/hadgem3/scripts/GC2.0/rebuild_nemo.exe'
    rebuild_timestamps = '05-30', '11-30', '06-01', '12-01'
    buffer_rebuild_rst = 5
    buffer_rebuild_mean = 1
    archive_restarts = False
    archive_timestamps = '05-30', '11-30', '06-01', '12-01'
    buffer_archive = 0
    means_cmd = '/projects/ocean/hadgem3/scripts/GC2.0/mean_nemo.exe'
    means_directory = '$CYLC_TASK_WORK_DIR/../coupled'
    create_means = False
    archive_means = False
    archive_set = '$CYLC_SUITE_NAME'
    debug = False

NAMELISTS = {'nemopostproc': nemoNamelist}
