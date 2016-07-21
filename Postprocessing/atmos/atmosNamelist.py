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
    atmosNamelist.py

DESCRIPTION
    Default namelists for Atmosphere post processing control
'''

import os


class AtmosNamelist:
    '''Default Values for atmospostproc namelist'''

    def __init__(self):
        pass

    pp_run = False
    share_directory = os.getcwd()
    debug = False
    try:
        um_utils = '/projects/um1/vn{}/xc40/utilities'.format(os.environ['VN'])
    except KeyError:
        um_utils = '/projects/um1/vn10.3/xc40/utilities'


class Archiving:
    '''UM Atmosphere archiving namelist'''

    def __init__(self):
        pass

    archive_switch = False
    arch_dump_freq = 'Monthly'
    arch_dump_offset = 0
    archive_dumps = False
    archive_pp = False
    arch_year_month = 1
    convert_pp = True
    process_all_streams = True
    process_streams = None
    process_means = None
    convert_all_streams = True
    archive_as_fieldsfiles = None


class Deletion:
    '''UM Atmosphere file deletion namelist'''

    def __init__(self):
        pass

    del_switch = False
    gcmdel = False
    gpdel = False


NAMELISTS = {
    'atmospp': AtmosNamelist,
    'archiving': Archiving,
    'delete_sc': Deletion
}
