#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016-2018 Met Office. All rights reserved.

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

#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
import re
import os
import sys
import subprocess
import threading
import error
import inc_days

class LoadEnvar(object):
    '''
    Container to hold loaded environemnt variables so they can be easily
    accessed and modified as needed
    '''

    def __init__(self):
        '''
        Initialise a container dictionary for the variables
        '''
        self.env_vars = {}

    def load_envar(self, name, default_value=None):
        '''
        Load an environment variable, if it doesn't exist and no default is
        specified return an error code. If a default is specified set to
        default and alert the user that this has occured
        '''
        try:
            self.env_vars[name] = os.environ[name]
            return 0
        except KeyError:
            if default_value != None:
                sys.stdout.write('[INFO] environment variable %s doesn\'t '
                                 'exist, setting to default value %s\n' %
                                 (name, default_value))
                self.env_vars[name] = default_value
                return 0
            else:
                return 1

    def contains(self, varname):
        '''
        Does the container contain the variable varname
        '''
        does_contain = varname in self.env_vars
        return does_contain

    def is_set(self, varname):
        '''
        Is the variable varname set in the environment
        '''
        try:
            _ = os.environ[varname]
            return True
        except KeyError:
            return False

    def add(self, varname, value):
        '''
        Add a variable to the container
        '''
        self.env_vars[varname] = value

    def remove(self, varname):
        '''
        Remove a variable from the container
        '''
        del self.env_vars[varname]

    def export(self):
        '''
        Export environment variable to the calling process
        '''
        for i_key in self.env_vars.keys():
            os.environ[i_key] = self.env_vars[i_key]

    def __getitem__(self, var_name):
        '''
        Return an environment variable value using the syntax
        LoadEnvar['variable_name']. Will exit with an error if the variable
        is not contained in the class instance.
        '''
        try:
            return self.env_vars[var_name]
        except KeyError:
            sys.stderr.write('[FAIL] Attempt to access environment variable'
                             ' %s. This has not been loaded\n' %
                             var_name)
            sys.exit(error.MISSING_EVAR_ERROR)

    def __setitem__(self, var_name, value):
        '''
        Allow an enivronment variable to be added to the container by
        using the syntax LoadEnvar['variable_name'] = x.
        '''
        self.add(var_name, value)


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
        that if a variable doesn't exisit in the namelist file, then it
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


def find_previous_workdir(cyclepoint, workdir, taskname):
    '''
    Find the work directory for the previous cycle. Takes as argument
    the current cyclepoint, the path to the current work directory, and
    the current taskname, and returns an absolute path.
    '''
    cyclesdir = os.sep.join(workdir.split(os.sep)[:-2])
    #find the work directory for the previous cycle
    work_cycles = os.listdir(cyclesdir)
    work_cycles.sort()

    # find the last restart directory for the task we are interested in
    # initialise previous_task_cycle to None
    previous_task_cycle = None
    for work_cycle in work_cycles[::-1]:
        # If this is an ensemble run we need to ensure that we're not looking
        # at a future cycle, or the current cycle.
        if (work_cycle < cyclepoint) and \
                (taskname in os.listdir(os.path.join(cyclesdir, work_cycle))):
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
        for k in modes.keys():
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

def setup_runtime():
    '''
    Set up model run length in seconds based on the model suite
    env vars (rather than in the manner of the old UM control scripts
    by interrogating NEMO namelists!)
    '''
    runtime_envar = LoadEnvar()

    if runtime_envar.load_envar('TASKSTART') != 0:
        sys.stderr.write('[FAIL] setup_runtime: Environment variable' \
                             ' TASKSTART not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    if runtime_envar.load_envar('TASKLENGTH') != 0:
        sys.stderr.write('[FAIL] setup_runtime: Environment variable' \
                             ' TASKLENGTH not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)


    if runtime_envar.load_envar('CALENDAR') != 0:
        sys.stderr.write('[WARN] setup_runtime: Environment variable' \
                             ' CALENDAR not set. Assuming 360 day calendar.\n')
        calendar = '360'
    else:
        calendar = runtime_envar['CALENDAR']
        if calendar == '360day':
            calendar = '360'
        elif calendar == '365day':
            calendar = '365'
        else:
            sys.stderr.write('[FAIL] setup_runtime: Calendar type %s not' \
                                 ' recognised\n' % calendar)
            sys.exit(error.INVALID_EVAR_ERROR)


    # Turn our times into lists of integers
    run_start = [int(i) for i in runtime_envar['TASKSTART'].split(',')]
    run_length = [int(i) for i in runtime_envar['TASKLENGTH'].split(',')]

    run_days = inc_days.inc_days(run_start[0], run_start[1], run_start[2],
                                 run_length[0], run_length[1], run_length[2],
                                 calendar)

    # Work out the total run length in seconds
    runlen_sec = (run_days * 86400)     \
                 + (run_length[3]*3600) \
                 + (run_length[4]*60)   \
                 + run_length[5]

    return runlen_sec

def exec_subproc_timeout(cmd, timeout_sec=10):
    '''
    Execute a given shell command with a timeout. Takes a list containing
    the commands to be run, and an integer timeout_sec for how long to
    wait for the command to run. Returns the return code from the process
    and the standard out from the command or 'None' if the command times out.
    '''
    process = subprocess.Popen(cmd, shell=False,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    timer = threading.Timer(timeout_sec, process.kill)
    try:
        timer.start()
        stdout, err = process.communicate()
        if err:
            sys.stderr.write('[SUBPROCESS ERROR] %s\n' % error)
        rcode = process.returncode
    finally:
        timer.cancel()
    if sys.version_info[0] >= 3:
        output = stdout.decode()
    else:
        output = stdout
    return rcode, output


def exec_subproc(cmd, verbose=True):
    '''
    Execute given shell command. Takes a list containing the commands to be
    run, and a logical verbose which if set to true will write the output of
    the command to stdout.
    '''
    process = subprocess.Popen(cmd, shell=False,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    output, err = process.communicate()
    if verbose and output:
        sys.stdout.write('[SUBPROCESS OUTPUT] %s\n' % output)
    if err:
        sys.stderr.write('[SUBPROCESS ERROR] %s\n' % error)
    if sys.version_info[0] >= 3:
        output = output.decode()
    return process.returncode, output


def __exec_subproc_true_shell(cmd, verbose=True):
    '''
    Execute given shell command, with shell=True. Only use this function if
    exec_subproc does not work correctly. Takes a list containing the commands
    to be run, and a logical verbose which if set to true will write the
    output of the command to stdout.
    '''
    process = subprocess.Popen(cmd, shell=True,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    output, err = process.communicate()
    if verbose and output:
        sys.stdout.write('[SUBPROCESS OUTPUT] %s\n' % output)
    if err:
        sys.stderr.write('[SUBPROCESS ERROR] %s\n' % error)
    if sys.version_info[0] >= 3:
        output = output.decode()
    return process.returncode, output
