#!/usr/bin/env python2.7
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""
Created on 3 March 2017

@author: Stephen Haddad

Common test-related error classes derived from Exception.
"""
import sys

HELP_STOP_ON_ERROR = '''If present, the script will stop on encounter an error.
Otherwise, the script will perform all comparisons and output the result at
the end'''

HELP_LIST_ERRORS = '''If true, a detailed list of the errors will be output to
stdout. IMPORTANT NOTE: If the stop-on-error flag is used, the script will stop
performing comparisons when an error is encountered, so the list-errors flag
will be ignored as the script will immediately abort and the list of errors
will not be output.'''

HELP_INSTANT_ONLY = '''If this flag is present, any fields in a restart dump
that are not instantaneous values e.g. a monthly mean field, will be ignored
when comparing 2 dump files.'''

HELP_SOLVER_OFFSET = '''If the 2 jobs have different timestep numbers for
the same point in model time, as offset must be provided to allow comparison.
This typically happens when comparing NRUN and CRUN outputs. If for example
P19780902T1200Z is timestep 720 in job 1 and timestep 360 in job 2, then an
offset of 360 should be specified.'''

HELP_IGNORE_VARIABLES = \
'''A list of variables to be ignored when comparing NEMO
and CICE restart files.'''

HELP_DIAGNOSTIC_FILE = '''If present, then the command line arguments should be
treated as diagnostic files.'''

class TestIO(object):
    """
    Wrapper class for output functionality. The main reason for wrapping this
    basic functionality is so that comparison functions don't need to know
    how they're called (command line or rose_ana) and thus how they need to
    write logging information. The wrapper class provides a consistent
    interface, and different IO methods are handled by passing different
    objects to the comparison functions.
    """
    def write_out(self, msg):
        """
        Write message to stdout.
        """
        sys.stdout.write(msg + '\n')

    def write_error(self, msg):
        """
        Write message to stderr.
        """
        sys.stderr.write(msg + '\n')

    def write_both(self, msg):
        """
        Write message to both stdout and stderr.
        """
        self.write_out(msg)
        self.write_error(msg)


class MissingArgumentError(Exception):
    """
    Error triggered when an input argument has not been defined.
    """
    pass

class FileLoadError(Exception):
    """
    Exception triggered when file fails to load.
    """
    def __init__(self, filePath):
        Exception.__init__(self)
        self.message = 'failed to load file {0}'
        self.message = self.message.format(filePath)

    def __str__(self):
        return self.message

class CubeCountMismatchError(Exception):
    """
    Error triggered when inputs have a different number of cubes.
    """
    def __init__(self):
        Exception.__init__(self)
        self.message = 'mismatch in number of cubes'

    def __str__(self):
        return self.message

class DataSizeMismatchError(Exception):
    """
    Error triggered when inputs have different values for data fields.
    """
    def __init__(self):
        Exception.__init__(self)
        self.file_name1 = 'unknown'
        self.file_name2 = 'unknown'
        self.cube_name = 'unknown'

    def __str__(self):
        self.message = 'size mismatch in  cube {cube_name} in output files '\
                       '{file_name1} and {file_name2}'
        self.message = self.message.format(** self.__dict__)
        return self.message

class DataMismatchError(Exception):
    """
    Error triggered when inputs have different values for data fields.
    """
    def __init__(self):
        Exception.__init__(self)
        self.file_name1 = 'unknown'
        self.file_name2 = 'unknown'
        self.cube_name = 'unknown'
        self.max_error = 0.0

    def __str__(self):
        self.message = 'mismatch in cube {cube_name} in output files '\
                       '{file_name1} and {file_name2}'
        self.message = self.message.format(**self.__dict__)
        return self.message

class HashMismatchException(Exception):
    """
    Error triggered when files have different SHA-1 hashes
    """
    def __init__(self, fileName):
        Exception.__init__(self)
        self.message = 'files have different SHA1 hash '\
                       'values for file {fileName}'
        self.message = self.message.format(fileName=fileName)

    def __str__(self):
        return self.message
