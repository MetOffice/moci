#!/usr/bin/env python2.7
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""
Created on 20 August 2015

@author: Stephen Haddad

Utility functions for use in validating output of test scripts.
"""
import os
import iris

ERROR_TOLERANCE = 1e-10

class MissingArgumentException(Exception):
    """
    Error triggered when an input argument has not been defined.
    """
    pass

class FileLoadException(Exception):
    """
    Exception triggered when file fails to load.
    """
    def __init__(self, filePath):
        Exception.__init__(self)
        self.message = 'failed to load file {0}'
        self.message = self.message.format(filePath)

    def __str__(self):
        return self.message

class CubeCountMismatchException(Exception):
    """
    Error triggered when inputs have a different number of cubes.
    """
    def __init__(self):
        Exception.__init__(self)
        self.message = 'mismatch in number of cubes'

    def __str__(self):
        return self.message

class DataMismatchException(Exception):
    """
    Error triggered when inputs have different values for data fields.
    """
    def __init__(self, cubeNum, fileName):
        Exception.__init__(self)
        self.message = 'mismatch in cube {cubeNum} in output file {fileName}'
        self.message = self.message.format(cubeNum=cubeNum,
                                           fileName=fileName)

    def __str__(self):
        return self.Message


def compare_cube_list_files(directory1, directory2, file_name1):
    """
    Compare the cube list at directory1/fileName1 with the cube list at
    directory2/fileName1.
    """
    file_path1 = os.path.join(directory1, file_name1)
    file_path2 = os.path.join(directory2, file_name1)

    try:
        cube_list1 = iris.load(file_path1)
    except:
        raise FileLoadException(file_path1)

    try:
        cube_list2 = iris.load(file_path2)
    except:
        raise FileLoadException(file_path2)

    if len(cube_list1) != len(cube_list2):
        raise CubeCountMismatchException()

    for ix1, (cube1, cube2) in enumerate(zip(cube_list1, cube_list2)):
        msg1 = 'comparing cube {currentCube} of {totalCubes}'
        msg1 = msg1.format(currentCube=ix1+1,
                           totalCubes=len(cube_list1),
                           filename=file_path1)
        print msg1
        cube_diff = (cube1.data-cube2.data).flatten().sum()
        if abs(cube_diff) > ERROR_TOLERANCE:
            raise DataMismatchException(ix1, file_name1)
            