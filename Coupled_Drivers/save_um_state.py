#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2017 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    save_um_state.py

DESCRIPTION
    Module to save the state of the UM at the start of the model run. The
    partial sum files from the climate meaning are backed up, to ensure
    that if the model fails climate meaning data can be restored.
'''

#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
from __future__ import division
import os
import shutil
import re
import sys
import common

def save_state(common_envar, iscrun):
    '''
    Manage backup copies of the partial sum files, this allows for the UM
    to retrieve a previous state for the climate meaning, to reduce instances
    of the 'ACUMPS1: Partial sum file inconsistent' error.
    '''

    cyclepoint = common_envar['CYLC_TASK_CYCLE_POINT']
    datam_files = os.listdir(common_envar['DATAM'])

    # If this is an NRUN we want to remove any exisiting partial sum files
    # to avoid restoring files from any previous cycles should they exist.
    if iscrun in ('', 'false'):
        sys.stdout.write('preparing to delete partial sums\n')
        all_partial_sum_regex = r'.*%sa_s\d{1}(?:a|b)$' % common_envar['RUNID']
        previous_psums = [f for f in datam_files if \
                              re.match(all_partial_sum_regex, f)]
        for psum_to_delete in previous_psums:
            common.remove_file(os.path.join(common_envar['DATAM'],
                                            psum_to_delete))

    # Find the non backed up partial sum files
    partial_sum_regex = r'^%sa_s\d{1}(?:a|b)$' % common_envar['RUNID']
    partial_sum_files = [f for f in datam_files if \
                             re.match(partial_sum_regex, f)]
    # as each mean period has an a and b file
    num_mean_period = len(partial_sum_files) // 2
    if len(partial_sum_files) != 0:
        # If there are no partial sum files we either have an NRUN, or no
        # climate meaning is engaged, so we don't need to do the following
        # process
        # Check for backed up partial sum files from this cycle
        current_bup_regex = r'%s_%sa_s\d{1}(?:a|b)' % (cyclepoint,
                                                       common_envar['RUNID'])
        general_bup_regex = r'\S+_%sa_s\d{1}(?:a|b)' % common_envar['RUNID']
        current_bup = [f for f in datam_files if \
                           re.match(current_bup_regex, f)]
        general_bup = [f for f in datam_files if \
                           re.match(general_bup_regex, f)]
        if len(current_bup):
            # The run has previously failed, copy the backup partial
            # sums to allow the model to pick them up
            for psum_f in current_bup:
                dst = psum_f.replace('%s_' % cyclepoint, '')
                shutil.copy(os.path.join(common_envar['DATAM'], psum_f),
                            os.path.join(common_envar['DATAM'], dst))
        else:
            # No previous partial sums for this cycle, back them up
            for psum_f in partial_sum_files:
                dst = '%s_%s' % (cyclepoint, psum_f)
                shutil.copy(os.path.join(common_envar['DATAM'], psum_f),
                            os.path.join(common_envar['DATAM'], dst))
        # Delete old partial sum files, keeping the previous two cycles
        # and the current cycle. Two per meaning period, times 3 cycles.
        # Until the partial sum files for all the meaning periods are produced
        # this will keep a few more cycles back.
        general_bup.sort()
        num_partial_sum_to_keep = num_mean_period * 2 * 3
        for psum_to_delete in general_bup[:-num_partial_sum_to_keep]:
            common.remove_file(os.path.join(common_envar['DATAM'],
                                            psum_to_delete))
