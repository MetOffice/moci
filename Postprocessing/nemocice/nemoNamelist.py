#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    nemoNamelist.py

DESCRIPTION
    Default namelists for NEMO post processing control
'''
import os


class NemoNamelist:
    '''Default values for the nemopostproc namelist'''
    pp_run = False
    restart_directory = os.environ['DATAM']
    exec_rebuild = '/projects/ocean/hadgem3/scripts/GC2.0/rebuild_nemo.exe'
    exec_rebuild_icebergs = os.environ['CYLC_SUITE_SHARE_DIR'] + \
        '/fcm_make_pp/build/bin/icb_combrest.py'
    rebuild_timestamps = '05-30', '11-30', '06-01', '12-01'
    buffer_rebuild_rst = 5
    buffer_rebuild_mean = 1
    archive_restarts = False
    archive_timestamps = '05-30', '11-30', '06-01', '12-01'
    buffer_archive = 0
    means_cmd = '/projects/ocean/hadgem3/scripts/GC2.0/mean_nemo.exe'
    means_directory = os.environ['CYLC_TASK_WORK_DIR'] + '/../coupled'
    create_means = False
    archive_means = False
    archive_set = os.environ['CYLC_SUITE_NAME']
    debug = False

NAMELISTS = {'nemopostproc': NemoNamelist}
