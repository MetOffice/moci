#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016 Met Office. All rights reserved.

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


import error
import re
import os
import sys
import subprocess

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
        for i_key in self.env_vars.iterkeys():
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
            if variable_name in self.replace_vars.keys():
                output_file.write('%s=%s,\n' %
                                  (variable_name,
                                   self.replace_vars[variable_name]))
            else:
                output_file.write(line)
        input_file.close()
        output_file.close()
        os.remove(self.filename)
        os.rename(self.filename+'out', self.filename)


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
    if mode not in modes.keys():
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
    return process.returncode, output
