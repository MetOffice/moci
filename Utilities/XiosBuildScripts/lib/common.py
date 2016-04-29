#!/usr/bin/env python2.7
"""
*****************************COPYRIGHT******************************
 (C) Crown copyright Met Office. All rights reserved.
 For further details please refer to the file COPYRIGHT.txt
 which you should have received as part of this distribution.
*****************************COPYRIGHT******************************

 CODE OWNER
   Stephen Haddad

 NAME
   common.py


A set of small classes and functions and that are used throughout the
build and test scripts
"""

import os
import textwrap

SYSTEM_NAME_MONSOON = 'Monsoon'

def formatted_write(output, text):
    """
    Takes a single unbroken string of arbitrary length and attempts to
    intelligently split the string into multiple lines of no more than 80
    characters in each line, appropriate for console output. The string is
    then written to the output object.

    Usage
    formatted_write(output, text)

    Parameters
    output - An object with a write member function defined which the wrapped
             string is written to.
    text - The string to be wrapped. It should contain no new line characters.
    """
    output.write('\n'.join(textwrap.wrap(text)))


class XbsBase(object):

    """
    Base class for all the XIOS/Oasis3-mct
    """

    def __init__(self, settings_dict):
        try:
            self.working_dir = settings_dict['WORKING_DIR']
        except KeyError:
            self.working_dir = os.getcwd()

        try:
            self.verbose = settings_dict['VERBOSE'] == 'true'
        except KeyError:
            self.verbose = False
        self.system_name = settings_dict['SYSTEM_NAME']


class MissingVariableError(Exception):

    """
    Exception raised when an required environment variable is missing.
    """
    pass


class SourceCodeExtractionError(Exception):

    """
    Exception raised when there is an error with retrieving source code
    """
    pass


class BuildError(Exception):

    """
    Exception raised when there is a build failure.
    """
    pass


class TestError(Exception):

    """
    Exception raised when there is an error running a test.
    """
    pass


class ModuleCreationError(Exception):

    """
    Exception raised when there is an error while creating a module file.
    """
    pass


class ConfigError(Exception):

    """
    Exception raised when there is an error detected in the input
    configuration.
    """
    pass


class MissingTestFileError(Exception):

    """
    Missing file required for test to function.
    """
    pass
