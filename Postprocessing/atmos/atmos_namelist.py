#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2022 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    atmos_namelist.py

DESCRIPTION
    Default namelists for Atmosphere post processing control
'''

import os


class AtmosNamelist(object):
    '''Default Values for atmospostproc namelist'''

    pp_run = False
    share_directory = os.getcwd()
    debug = False
    try:
        um_utils = '/projects/um1/vn{}/xc40/utilities'.format(os.environ['VN'])
    except KeyError:
        um_utils = '/projects/um1/vn10.8/xc40/utilities'
    mule_utils = None
    convert_pp = True
    process_all_streams = True
    process_streams = None
    process_means = None
    convpp_all_streams = True
    archive_as_fieldsfiles = None
    streams_to_netcdf = None
    fields_to_netcdf = None
    netcdf_filetype = 'NETCDF4'
    netcdf_compression = None
    streams_to_cutout = None
    cutout_coords = None
    cutout_coords_type = 'coords'

    create_means = False
    create_monthly_mean = False
    create_seasonal_mean = False
    create_annual_mean = False
    create_decadal_mean = False
    meanbase_period = None
    meanbase_stream = 'pm'


class Archiving(object):
    '''UM Atmosphere archiving namelist'''

    archive_switch = False
    arch_dump_freq = 'Monthly'
    arch_dump_offset = 0
    arch_timestamps = []
    archive_dumps = False
    archive_pp = False
    archive_ncf = False
    arch_year_month = None


class Deletion(object):
    '''UM Atmosphere file deletion namelist'''

    del_switch = False
    gcmdel = False
    gpdel = False
    ncdel = False


NAMELISTS = {
    'atmospp': AtmosNamelist,
    'archiving': Archiving,
    'delete_sc': Deletion
}
