#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016-2017 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    verify_namelist.py

DESCRIPTION
    Default namelists for periodic archive verification app
'''


class PeriodicVerify(object):
    ''' Default namelist for model independent aspects of verification '''
    def __init__(self):
        pass

    startdate = None
    enddate = None
    prefix = None
    dataset = None
    check_additional_files_archived = False
    testing = False


class AtmosVerify(object):
    ''' Default namelist for atmosphere archive verification '''
    def __init__(self):
        pass

    verify_model = False
    archive_timestamps = 'Seasonal'
    delay_rst_archive = '0d'
    meanfields = None
    mean_reference_date = '10001201'
    meanstreams = ['1m', '1s', '1y', '1x']
    streams_90d = None
    streams_30d = None
    streams_10d = None
    streams_2d = None
    streams_1d = None
    ff_streams = None
    spawn_netcdf_streams = None
    timelimitedstreams = False
    tlim_streams = None
    tlim_starts = None
    tlim_ends = None


class NemoVerify(object):
    ''' Default namelist for atmosphere archive verification '''
    def __init__(self):
        pass

    verify_model = False
    archive_timestamps = 'Biannual'
    buffer_restart = 1
    buffer_mean = 0
    base_mean = '10d'
    nemo_icebergs_rst = False
    nemo_ptracer_rst = False
    meanfields = ['grid-U', 'grid-T', 'grid-W', 'grid-V']
    mean_reference_date = '10001201'
    meanstreams = ['1m', '1s', '1y']
    streams_1d_1m = None
    streams_6h_1m = None
    iberg_traj = False
    iberg_traj_tstamp = 'Timestep'
    iberg_traj_freq = '10d'
    iberg_traj_ts_per_day = 72


class CiceVerify(object):
    ''' Default namelist for atmosphere archive verification '''
    def __init__(self):
        pass

    verify_model = False
    archive_timestamps = 'Biannual'
    restart_suffix = '.nc'
    buffer_restart = 1
    buffer_mean = None
    base_mean = '10d'
    cice_age_rst = False
    meanfields = None
    mean_reference_date = '10001201'
    meanstreams = ['1m', '1s', '1y']
    streams_1d_1m = False


NAMELISTS = {'commonverify': PeriodicVerify,
             'atmosverify': AtmosVerify,
             'nemoverify': NemoVerify,
             'ciceverify': CiceVerify}
