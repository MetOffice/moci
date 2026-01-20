#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2022-2025 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    common.py

DESCRIPTION
    Common functions and classes required by multiple model drivers
'''



import datetime
import glob
import shutil
import re
import os
import sys
import subprocess
import threading
import math
import error
import inc_days


class ModNamelist(object):
    '''
    Modify a fortran namelist. This will not add any new variables, only
    modify existing ones
    '''

    def __init__(self, filename):
        '''
        Initialise the container, with the name of file to be updated
        '''
        self.filename = filename
        self.replace_vars = {}

    def var_val(self, variable, value):
        '''
        Create a container of variable name, value pairs to be updated. Note
        that if a variable doesn't exist in the namelist file, then it
        will be ignored
        '''
        if isinstance(value, str):
            if value.lower() not in ('.true.', '.false.'):
                value = '\'%s\'' % value

        self.replace_vars[variable] = value

    def replace(self):
        '''
        Do the update
        '''
        output_file = open_text_file(self.filename+'out', 'w')
        input_file = open_text_file(self.filename, 'r')
        for line in input_file.readlines():
            variable_name = re.findall(r'\s*(\S*)\s*=\s*', line)
            if variable_name:
                variable_name = variable_name[0]
            if variable_name in list(self.replace_vars.keys()):
                output_file.write('%s=%s,\n' %
                                  (variable_name,
                                   self.replace_vars[variable_name]))
            else:
                output_file.write(line)
        input_file.close()
        output_file.close()
        os.remove(self.filename)
        os.rename(self.filename+'out', self.filename)

def find_previous_workdir(cyclepoint, workdir, taskname, task_param_run=None):
    '''
    Find the work directory for the previous cycle. Takes as argument
    the current cyclepoint, the path to the current work directory, and
    the current taskname, a value specifying multiple tasks within
    same cycle (e.g. coupled_run1, coupled_run2) as used in coupled NWP
    and returns an absolute path.
    '''

    if task_param_run:
        stem = workdir.rstrip(task_param_run)
        nchars = len(task_param_run)
        prev_param_run = '{:0{}d}'.format(int(task_param_run) - 1, nchars)
        previous_workdir = stem + prev_param_run
        if not os.path.isdir(previous_workdir):
            sys.stderr.write('[FAIL] Can not find previous work directory for'
                             ' task %s\n' % taskname)
            sys.exit(error.MISSING_DRIVER_FILE_ERROR)

        return previous_workdir

    else:
        cyclesdir = os.sep.join(workdir.split(os.sep)[:-2])
        #find the work directory for the previous cycle
        work_cycles = os.listdir(cyclesdir)
        work_cycles.sort()
        try:
            work_cycles.remove(cyclepoint)
        except ValueError:
            pass
        # find the last restart directory for the task we are interested in
        # initialise previous_task_cycle to None
        previous_task_cycle = None
        for work_cycle in work_cycles[::-1]:
            if taskname in os.listdir(os.path.join(cyclesdir, work_cycle)):
                previous_task_cycle = work_cycle
                break

        if not previous_task_cycle:
            sys.stderr.write('[FAIL] Can not find previous work directory for'
                             ' task %s\n' % taskname)
            sys.exit(error.MISSING_DRIVER_FILE_ERROR)

        return os.path.join(cyclesdir, previous_task_cycle, taskname)


def get_filepaths(directory):
    '''
    Equivilant to ls -d
    Provides an absolute path to every file in directory including
    subdirectorys
    '''
    file_paths = []
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)
    return file_paths


def open_text_file(name, mode):
    '''
    Provide a common function to open a file and provide a suitiable error
    should this not be possible
    '''
    modes = {'r':'reading',
             'w':'writing',
             'a':'appending',
             'r+':'updating (reading)',
             'w+':'updating (writing)',
             'a+':'updating (appending)'}
    if mode not in list(modes.keys()):
        options = ''
        for k in modes:
            options += '  %s: %s\n' % (k, modes[k])
        sys.stderr.write('[FAIL] Attempting to open file %s, do not recognise'
                         ' mode %s. Please use one of the following modes:\n%s'
                         % (name, mode, options))
        sys.exit(error.IOERROR)
    try:
        handle = open(name, mode)
    except IOError:
        sys.stderr.write('[FAIL] Unable to open file %s using mode %s (%s)\n'
                         % (name, mode, modes[mode]))
        sys.exit(error.IOERROR)
    return handle

def is_non_zero_file(path):
    '''
    Check to see if a file 'path' exists and has non zero length. Returns
    True if that is the case. If the file a) doesn't exist, or b) has zero
    length, returns False
    '''
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return True
    else:
        return False

def remove_file(filename):
    '''
    Check to see if a file or a link exists and if it does, remove it.
    Return True if a file/link was removed, False otherwise.
    '''
    if os.path.isfile(filename) or os.path.islink(filename):
        os.remove(filename)
        return True
    else:
        return False

def setup_runtime(common_env):
    '''
    Set up model run length in seconds based on the model suite
    env vars (rather than in the manner of the old UM control scripts
    by interrogating NEMO namelists!)
    '''
    if not common_env['CALENDAR']:
        sys.stderr.write('[WARN] setup_runtime: Environment variable' \
                         ' CALENDAR not set. Assuming 360 day calendar.\n')
        calendar = '360'
    else:
        calendar = common_env['CALENDAR']
        if calendar == '360day':
            calendar = '360'
        elif calendar == '365day':
            calendar = '365'
        elif calendar == 'gregorian':
            pass
        else:
            sys.stderr.write('[FAIL] setup_runtime: Calendar type %s not' \
                                 ' recognised\n' % calendar)
            sys.exit(error.INVALID_EVAR_ERROR)


    # Turn our times into lists of integers
    run_start = [int(i) for i in common_env['TASKSTART'].split(',')]
    run_length = [int(i) for i in common_env['TASKLENGTH'].split(',')]

    run_days = inc_days.inc_days(run_start[0], run_start[1], run_start[2],
                                 run_length[0], run_length[1], run_length[2],
                                 calendar)

    # Work out the total run length in seconds
    runlen_sec = (run_days * 86400)     \
                 + (run_length[3]*3600) \
                 + (run_length[4]*60)   \
                 + run_length[5]

    return runlen_sec


def _calculate_ppn_values(nproc, nodes):
    '''
    Calculates number of processes per node and numa node for launch
    command options
    '''
    nproc = int(nproc)
    nodes = float(nodes)
    numa_nodes = 2

    ppnu = int(math.ceil(nproc/nodes/numa_nodes))
    ppn = (ppnu * numa_nodes) if nproc > 1 else nproc

    return ppnu, ppn


def set_aprun_options(nproc, nodes, ompthr, hyperthreads, ss):
    '''
    Setup the aprun options for the launcher command
    '''
    ppnu, ppn = _calculate_ppn_values(nproc, nodes)
    rose_launcher_preopts = \
        '-n %s -N %s -S %s -d %s -j %s env OMP_NUM_THREADS=%s env HYPERTHREADS=%s' \
            % (nproc, ppn, ppnu, ompthr, hyperthreads, ompthr, hyperthreads)

    if ss:
        rose_launcher_preopts = "-ss " + rose_launcher_preopts

    return rose_launcher_preopts


def _sort_hist_dirs_by_date(dir_list):
    '''
    Sort a list of history directories by date
    '''
    # Pattern that defines the name of the history directories,
    # which contain a date of the form YYYYmmddHHMM.
    pattern = r'\.(\d{12})'

    try:
        dir_list.sort(key=lambda dname: datetime.datetime.strptime(
            re.search(pattern, dname).group(1), '%Y%m%d%H%M'))
    except AttributeError:
        msg = '[FAIL] Cannot order directories: %s' % " ".join(dir_list)
        sys.stderr.write(msg)
        sys.exit(error.IOERROR)

    return dir_list


def remove_latest_hist_dir(old_hist_dir):
    '''
    If a model task has failed, then removed the last created history
    directory, before a new one is created, associated with the
    re-attempt.
    '''
    # Replace the regex pattern that defines the history directory
    # name (that contains a date of the format YYYYmmddHHMM) with a
    # generic pattern so that we can perform the directory glob.
    history_pattern = re.sub(
        r'\.\d{12}', '.????????????', old_hist_dir)

    # Find and sort the history directories, and delete
    # the latest one, corresponding to the last entry in
    # the list.
    history_dirs = glob.glob(history_pattern)
    history_dirs = _sort_hist_dirs_by_date(history_dirs)

    msg = '[INFO] Found history directories: %s \n' % ' '.join(
        history_dirs)
    sys.stdout.write(msg)

    latest_hist_dir = history_dirs[-1]
    msg = ("[WARN] Re-attempting failed model step. \n"
           "[WARN] Clearing out latest history \n"
           "[WARN] directory %s. \n" % latest_hist_dir)
    sys.stdout.write(msg)

    shutil.rmtree(latest_hist_dir)
