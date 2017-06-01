#!/usr/bin/env python2.7
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""
Created on 3 March 2017

@author: Stephen Haddad

Common validation-related error classes derived from Exception.
"""

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
