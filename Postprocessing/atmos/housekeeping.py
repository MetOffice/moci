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
    housekeeping.py

DESCRIPTION
    Atmosphere housekeeping methods:
      File deletion utilities
      File processing utilities - conversion to pp format
'''

import re
import os

from collections import OrderedDict

import timer
import utils

# Constants
FILETYPE = OrderedDict([
    ('dump_names', ([], lambda p, s:
                    re.compile(r'^{0}a\.da\d{{8}}'.format(p)))),
    ('pp_inst_names', ([], lambda p, s:
                       re.compile(r'^{0}a\.p[{1}]'.format(p, s)))),
    ('pp_mean_names', ([], lambda p, s:
                       re.compile(r'^{0}a\.[pm][{1}]'.format(p, s)))),
    ])
RTN = 0
REGEX = 1


def read_arch_logfile(logfile, prefix, inst, mean):
    '''
    Read the archiving script log file, and identify the lines corresponding
    to dumps, instantaneous pp files, and mean pp files, and separate
    '''
    for line in open(logfile, 'r').readlines():
        fname, tag = line.split(' ', 1)
        tag = 'FAILED' not in tag
        for ftype in FILETYPE:
            stream = inst if ftype == 'pp_inst_names' else mean
            if FILETYPE[ftype][REGEX](prefix, stream).\
                    search(os.path.basename(fname)):
                FILETYPE[ftype][RTN].append((fname, tag))

    return tuple(FILETYPE[ftype][RTN] for ftype in FILETYPE)


@timer.run_timer
def delete_dumps(atmos, dump_names, archived):
    ''' Delete dumps files when no longer required'''
    to_delete = []
    if archived:
        # Pre-determined list of files available following archiving operation
        arch_succeeded = sorted([dump for dump, tag in dump_names if tag])

        if arch_succeeded:
            last_file = arch_succeeded[-1]
            for fname in utils.get_subset(atmos.share, r'{0}a\.da\d{{8}}'.
                                          format(atmos.suite.prefix)):
                if fname <= os.path.basename(last_file) and \
                        not fname.endswith('.done'):
                    to_delete.append(fname)
                if atmos.final_dumpname:
                    # Final dump should not be deleted as it is not superseded
                    try:
                        to_delete.remove(atmos.final_dumpname)
                    except ValueError:
                        pass

    else:  # Not archiving
        for fname in utils.get_subset(atmos.share, r'{0}a\.da\d{{8}}'.
                                      format(atmos.suite.prefix)):
            # Delete files upto and including current cycle time
            filetime = re.search(r'a.da(\d{8})', fname).group(1)
            if filetime <= ''.join(atmos.suite.cyclestring[:3]):
                to_delete.append(fname)

    if to_delete:
        msg = 'Removing dump files:\n' + '\n '.join([f for f in to_delete])
        utils.log_msg(msg)
        utils.remove_files(to_delete, atmos.share)

        
@timer.run_timer
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
                re.search(FILETYPE['pp_inst_names'][REGEX](atmos.suite.prefix,
                                                           atmos.streams),
                          ppfile)
            pp_mean = atmos.nl.delete_sc.gcmdel and \
                re.search(FILETYPE['pp_mean_names'][REGEX](atmos.suite.prefix,
                                                           atmos.means),
                          ppfile)
            if pp_inst or pp_mean:
                to_delete.append(ppfile)

    if to_delete:
        msg = 'Removing pp files:\n ' + '\n '.join([f for f in to_delete])
        utils.log_msg(msg)
        utils.remove_files(to_delete, atmos.share)

        # Remove .arch files from work directory(s)
        del_dot_arch = [os.path.basename(fname).rstrip('.pp') + ".arch" for
                        fname in to_delete]
        msg = 'Removing .arch files from work directory:\n ' + \
            '\n '.join([f for f in del_dot_arch])
        utils.log_msg(msg)
        utils.remove_files(del_dot_arch, atmos.work, ignoreNonExist=True)


@timer.run_timer
def convert_to_pp(fieldsfile, sharedir, umutils):
    '''
    Create the command to call UM utility ff2pp for file
    conversion to pp format
    '''
    ppfname = fieldsfile + '.pp'
    cmd = ' '.join([os.path.join(umutils, 'um-ff2pp'),
                    fieldsfile, ppfname])
    ret_code, output = utils.exec_subproc(cmd, cwd=sharedir)

    if ret_code == 0:
        msg = 'convert_to_pp: Converted to pp format: ' + ppfname
        utils.remove_files(fieldsfile, path=sharedir)
        level = 1
    else:
        msg = 'convert_to_pp: Conversion to pp format failed: {}\n {}\n'.\
            format(fieldsfile, output)
        level = 5

    utils.log_msg(msg, level)
    return ppfname
