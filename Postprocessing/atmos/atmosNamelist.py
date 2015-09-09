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
    atmosNamelist.py

DESCRIPTION
    Default namelists for Atmosphere post processing control
'''

import os


class atmosNamelist:
    pp_run = False
    share_directory = os.environ['PWD']
    pumf_path = '/projects/um1/vn*.*/ibm/utilities/um-pumf'
    debug = False


class archiving:
    '''UM Atmosphere archiving namelist'''
    archive_switch = False
    arch_dump_freq = 'Monthly'
    arch_dump_offset = 0
    archive_dumps = False
    archive_pp = False
    arch_year_month = 1
    moose_data_set = ''


class delete_sc:
    '''UM Atmosphere file deletion namelist'''
    del_switch = False
    gcmdel = False
    gpdel = False


NAMELISTS = {
    'atmospp': atmosNamelist,
    'archiving': archiving,
    'delete_sc': delete_sc
}
