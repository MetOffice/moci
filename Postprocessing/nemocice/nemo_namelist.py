#!/usr/bin/env python
# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------
'''
NAME
    nemo_namelist.py

DESCRIPTION
    Default namelists for NEMO post processing control
'''
import os
import template_namelist


class TopLevel(template_namelist.TopLevel):
    ''' Default values for nemo_pp namelist '''
    process_all_fieldsfiles = True


class Processing(template_namelist.Processing):
    ''' Default values for nemo_processing namelist '''
    means_fieldsfiles = None

    exec_rebuild = '/projects/ocean/hadgem3/scripts/GC2.0/rebuild_nemo.exe'
    exec_rebuild_icebergs = os.environ['CYLC_WORKFLOW_SHARE_DIR'] + \
        '/bin/icb_combrest.py'
    exec_rebuild_iceberg_trajectory = os.environ['CYLC_WORKFLOW_SHARE_DIR'] + \
        '/bin/icb_pp.py'
    msk_rebuild = False
    rebuild_restart_timestamps = '05-30', '11-30', '06-01', '12-01'
    rebuild_omp_numthreads = 1
    rebuild_compress = False
    xchunk = None
    ychunk = None
    zchunk = None
    tchunk = None
    rebuild_restart_buffer = None
    rebuild_mean_buffer = None
    rebu_cache = None

    means_cmd = '/projects/ocean/hadgem3/scripts/GC2.0/mean_nemo.exe'
    ncatted_cmd = '/projects/ocean/hadgem3/nco/nco-4.4.7/bin/ncatted'

    chunking_arguments = 'time_counter/1,y/205,x/289'
    chunking_exclude_fields = ''

    time_vars = 'time_counter', 'time_centered'

    extract_region = False
    region_fieldsfiles = None
    region_dimensions = 'x', '1055,1198', 'y', '850,1040'
    region_chunking_args = 'time_counter/1,y/191,x/144'


class Archiving(template_namelist.Archiving):
    ''' Default values for nemo_archiving namelist '''

    archive_iceberg_trajectory = False


NAMELISTS = {'nemo_pp': TopLevel,
             'nemo_processing': Processing,
             'nemo_archiving': Archiving}
