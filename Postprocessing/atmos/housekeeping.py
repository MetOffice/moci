#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2018 Met Office. All rights reserved.

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
    Atmosphere housekeeping methods
      File deletion utilities
      File processing utilities - conversion to pp format
                                  creation of means
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
                       re.compile(r'^{0}a\.({1})'.format(p, s)))),
    ('pp_mean_names', ([], lambda p, s:
                       re.compile(r'^{0}a\.({1})'.format(p, s)))),
    ('nc_names', ([], lambda p, s:
                  re.compile(r'^atmos_{0}a_.*_({1})'.format(p, s)))),
    ])
RTN = 0
REGEX = 1


def read_arch_logfile(logfile, prefix, inst, mean, ncfile):
    '''
    Read the archiving script log file, and identify the lines corresponding
    to dumps, instantaneous pp files, and mean pp files, and separate
    '''
    for line in open(logfile, 'r').readlines():
        print('[DEBUG] line:', line)
        fname, tag = line.split(' ', 1)
        tag = 'FAILED' not in tag
        for ftype in FILETYPE:
            if ftype == 'pp_inst_names':
                stream = inst
            elif ftype == 'pp_mean_names':
                stream = mean
            elif ftype == 'nc_names':
                stream = ncfile if ncfile else '*'
            else:
                stream = '*'
            if stream and FILETYPE[ftype][REGEX](prefix, stream).\
                    search(os.path.basename(fname)):
                FILETYPE[ftype][RTN].append((fname, tag))

    return tuple(FILETYPE[ftype][RTN] for ftype in FILETYPE)


@timer.run_timer
def delete_dumps(atmos, dump_names, archived):
    ''' Delete dumps files when no longer required'''
    patt = r'{0}a\.da[_\d]{{8,11}}$'.format(atmos.suite.prefix)
    dumps_available = utils.get_subset(atmos.share, patt)

    to_delete = []
    if archived:
        # Pre-determined list of files available following archiving operation
        arch_succeeded = sorted([dump for dump, tag in dump_names if tag])
        arch_failed = [dump for dump, tag in dump_names if not tag]

        if arch_succeeded:
            last_file = arch_succeeded[-1]
            for fname in dumps_available:
                if fname <= os.path.basename(last_file) and \
                        fname not in arch_failed:
                    to_delete.append(fname)
                if atmos.final_dumpname:
                    # Final dump should not be deleted as it is not superseded
                    try:
                        to_delete.remove(atmos.final_dumpname)
                    except ValueError:
                        pass

    else:  # Not archiving
        for fname in dumps_available:
            # Delete files upto and including current cycle time
            filetime = re.search(r'a.da(\d{8})', fname).group(1)
            if filetime <= atmos.suite.cyclepoint.startcycle['iso'][:8]:
                to_delete.append(fname)

    if to_delete:
        msg = 'Removing dump files:\n' + '\n '.join([f for f in to_delete])
        if utils.get_debugmode() and archived:
            # Append "ARCHIVED" suffix to archived files, rather than deleting
            utils.log_msg(msg, level='DEBUG')
            for fname in to_delete:
                if fname in arch_succeeded:
                    fname = os.path.join(atmos.share, fname)
                    os.rename(fname, fname + '_ARCHIVED')
                else:
                    utils.remove_files(fname, path=atmos.share)
        else:
            utils.log_msg(msg)
            utils.remove_files(to_delete, path=atmos.share)


@timer.run_timer
def delete_ppfiles(atmos, pp_inst_names, pp_mean_names, nc_names, archived):
    '''Delete pp files when finalised and archived as necessary'''
    to_delete = []
    if archived:
        # Pre-determined list of files available following archiving operation
        if atmos.naml.delete_sc.gpdel:
            to_delete += [pp for pp, tag in pp_inst_names if tag]
        if atmos.naml.delete_sc.gcmdel:
            to_delete += [pp for pp, tag in pp_mean_names if tag]
        if atmos.naml.delete_sc.ncdel:
            to_delete += [nc for nc, tag in nc_names if tag]

    else:  # Not archiving
        pattern = r'^{}a\.[pm][a-z1-9]'.format(atmos.suite.prefix)
        pattern += r'\d{4}(\d{4}|[a-z]{3})(_\d{2})?\.arch$'
        for ppfile in get_marked_files(atmos.work, pattern, '.arch'):
            pp_inst = atmos.naml.delete_sc.gpdel and \
                re.search(FILETYPE['pp_inst_names'][REGEX](atmos.suite.prefix,
                                                           atmos.streams),
                          ppfile)
            pp_mean = atmos.naml.delete_sc.gcmdel and \
                re.search(FILETYPE['pp_mean_names'][REGEX](atmos.suite.prefix,
                                                           atmos.means),
                          ppfile)
            if pp_inst or pp_mean:
                if atmos.ff_match(atmos.convpp_streams, filename=ppfile):
                    to_delete.append(ppfile + '.pp')
                # Mark the original fieldsfile for deletion regardless of
                # whether it should have been converted to pp.  If the file
                # contains no fields then it may not have been converted
                to_delete.append(ppfile)

    if to_delete:
        msg = 'Removing pp files:\n ' + '\n '.join([f for f in to_delete])
        if utils.get_debugmode() and archived:
            # Append "ARCHIVED" suffix to files, rather than deleting
            utils.log_msg(msg, level='DEBUG')
            for fname in to_delete:
                fname = os.path.join(atmos.share, fname)
                os.rename(fname, fname + '_ARCHIVED')
        else:
            utils.log_msg(msg)
            utils.remove_files(to_delete, path=atmos.share)

        # Remove .arch files from work directory(s)
        del_dot_arch = []
        for fname in to_delete:
            if fname.endswith('.nc'):
                # .arch files not available for data extracted to netCDF files
                pass
            else:
                lim = -3 if fname.endswith('.pp') else None
                del_dot_arch.append(os.path.basename(fname[:lim]) + ".arch")

        msg = 'Removing .arch files from work directory:\n ' + \
            '\n '.join([f for f in del_dot_arch])
        if utils.get_debugmode() and archived:
            # Append "ARCHIVED" suffix to files, rather than deleting
            utils.log_msg(msg, level='DEBUG')
            for fname in del_dot_arch:
                fname = os.path.join(atmos.work, fname)
                os.rename(fname, fname + '_ARCHIVED')
        else:
            utils.log_msg(msg)
            utils.remove_files(del_dot_arch, path=atmos.work,
                               ignore_non_exist=True)


@timer.run_timer
def get_marked_files(datadir, pattern, suffix):
    '''
    Returns a list of files marked as available for archiving.
    Completed fieldsfiles are marked by the presence of a '.arch' suffixed file
    in the work directory.
    '''
    marked_files = utils.get_subset(datadir, pattern.replace('$', suffix + '$'))
    if len(marked_files) == 0:
        utils.log_msg('No files marked ' + suffix, level='INFO')
    if suffix:
        marked_files = [fn.replace(suffix, '') for fn in marked_files]

    return marked_files

