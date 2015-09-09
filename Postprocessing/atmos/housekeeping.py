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
    housekeeping.py

DESCRIPTION
    Atmosphere file deletion methods

'''

import re
import os

from collections import OrderedDict

import utils

# Constants
FILETYPE = OrderedDict([
        ('dump_names',    ([], lambda p:
                               re.compile(r'^{0}a\.da\d{{8}}'.format(p)))),
        ('pp_inst_names', ([], lambda p:
                               re.compile(r'^{0}a\.p[a-k\d]'.format(p)))),
        ('pp_mean_names', ([], lambda p:
                               re.compile(r'^{0}a\.p[lmpr-z12345]'.format(p)))),
        ])
RTN = 0
REGEX = 1


def read_arch_logfile(logfile, prefix):
    '''
    Read the archiving script log file, and identify the lines corresponding
    to dumps, instantaneous pp files, and mean pp files, and separate
    '''
    for line in open(logfile, 'r').readlines():
        fname, tag = line.split(' ', 1)
        tag = 'FAILED' not in tag
        for ft in FILETYPE:
            if FILETYPE[ft][REGEX](prefix).search(os.path.basename(fname)):
                FILETYPE[ft][RTN].append((fname, tag))

    return tuple(FILETYPE[ft][RTN] for ft in FILETYPE)


def delete_dumps(atmos, dump_names, archived):
    ''' Delete dumps files when no longer required'''
    to_delete = []
    if archived:
        # Pre-determined list of files available following archiving operation
        arch_succeeded = sorted([dump for dump, tag in dump_names if tag])
        arch_failed = [dump for dump, tag in dump_names if not tag]

        if 'delete.lock' in os.listdir(atmos.share):
            msg = 'delete.lock file exists.  Automatic file deletion disabled.'
            msg += '\n\t -> Please address archiving issues manually and ' \
                'delete lock file to allow automatic housekeeping to continue'
            utils.log_msg(msg, 3)
            return

        if arch_succeeded:
            last_file = arch_succeeded[-1]
            for fn in utils.get_subset(atmos.share, r'{0}a\.da\d{{8}}'.\
                                           format(atmos.suite.prefix)):
                if fn <= os.path.basename(last_file) and not \
                        fn.endswith('.done'):
                    to_delete.append(fn)
                if atmos.final_dumpname:
                    # Final dump should not be deleted as it is not superseded
                    try:
                        to_delete.remove(atmos.final_dumpname)
                    except ValueError:
                        pass

        if arch_failed:
            # failure mode, only delete up to the first safely archived dump
            # first touch our log file so any further runs of the
            # script will not try and delete any files
            open(os.path.join(atmos.share, 'delete.lock'), 'a').close()

    else:  # Not archiving
        for fn in utils.get_subset(atmos.share, r'{0}a\.da\d{{8}}'.\
                                       format(atmos.suite.prefix)):
            # Delete files upto and including current cycle time
            filetime = re.search('a.da(\d{8})', fn).group(1)
            if filetime <= ''.join(atmos.suite.cyclestring[:3]):
                to_delete.append(fn)

    if to_delete:
        msg = 'Removing dump files:\n' + '\n '.join([f for f in to_delete])
        utils.log_msg(msg)
        utils.remove_files(to_delete, atmos.share)


def delete_ppfiles(atmos, pp_inst_names, pp_mean_names, archived):
    '''Delete pp files when finalised and archived as necessary'''
    to_delete = []
    if archived:
        # Pre-determined list of files available following archiving operation
        if atmos.nl.delete_sc.gpdel:
            to_delete += [pp for pp, tag in pp_inst_names if tag]
        if atmos.nl.delete_sc.gcmdel:
            to_delete += [pp for pp, tag in pp_mean_names if tag]

    else:  # Not archiving
        for ppfile in atmos.get_marked_files():
            pp_inst = atmos.nl.delete_sc.gpdel and \
                re.search(FILETYPE['pp_inst_names'][REGEX](atmos.suite.prefix),
                          ppfile)
            pp_mean = atmos.nl.delete_sc.gcmdel and \
                re.search(FILETYPE['pp_mean_names'][REGEX](atmos.suite.prefix),
                          ppfile)
            if pp_inst or pp_mean:
                to_delete.append(ppfile)

    if to_delete:
        msg = 'Removing pp files:\n' + '\n '.join([f for f in to_delete])
        utils.log_msg(msg)
        utils.remove_files(to_delete, atmos.share)
