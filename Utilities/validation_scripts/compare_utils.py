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
import sys

import numpy
import iris

import validate_common

iris.FUTURE.netcdf_promote = True

ERROR_TOLERANCE = 1e-10
CF_TIME_UNIT = 'seconds since 1900-01-01 00:00:00'
CF_CALENDAR = 'noleap'



def compare_cube_list_files(file_path1,
                            file_path2,
                            stop_on_error=False,
                            ignore_halos=False,
                            halo_size=0,
                            ignore_variables=None,
                            save_memory=False):
    """
    Compare the cube list at directory1/fileName1 with the cube list at
    directory2/fileName1.

    Inputs:
    file_path1 - path to first file of pair to compare
    file_path2 - path to first file of pair to compare
    stop_on_error - If true, an exception will be raised when an error is found
    ignore_halos - If true, a halo for each field will be ignored when
                   comparing values
    halo_size - If ignore_halos is True, this specifies the size of the halo
                to ignore
    ignore_variables - a list of strings representing netcdf variables to be
                       ignored for comparison purposes
    save_memory -  if true, then the data in the netcdf file will be loaded
                   one variable at a time, so peak memory usage will
                   be approximately the size of one variable, rather than
                   all variables
    """

    #load files to get list of variables
    try:
        cube_list1 = iris.load(file_path1)
    except:
        raise validate_common.FileLoadError(file_path1)

    try:
        cube_list2 = iris.load(file_path2)
    except:
        raise validate_common.FileLoadError(file_path2)

    if len(cube_list1) != len(cube_list2):
        raise validate_common.CubeCountMismatchError()

    print 'comparing cubes with tolerance {0:g}'.format(ERROR_TOLERANCE)
    if ignore_variables:
        ignore_msg = 'the following variables are being ignored: \n'
        ignore_list = ['{0:d}:{1}\n'.format(cix1, c1.name())
                       for cix1, c1 in enumerate(cube_list1)
                       if c1.name() in ignore_variables]
        print ignore_msg + '\n'.join(ignore_list)

        variable_list = [(cix1, c1.name()) for cix1, c1 in enumerate(cube_list1)
                         if c1.name() not in ignore_variables]
    else:
        variable_list = [(cix1, c1.name())
                         for cix1, c1 in enumerate(cube_list1)]
    error_list = []

    for cix1, var_name in variable_list:
        msg1 = 'comparing cube {currentCube} of {totalCubes}'
        msg1 += ' - variable {var_name}'
        msg1 = msg1.format(currentCube=cix1+1,
                           totalCubes=len(cube_list1),
                           filename=file_path1,
                           var_name=var_name)
        print msg1
        try:
            # load cubes here, to ensure that only the data for the current
            # variable is loaded into memory, reducing memory required
            if save_memory:
                cube1 = iris.load_cube(file_path1, var_name)
                cube2 = iris.load_cube(file_path2, var_name)
                compare_cubes(cube1,
                              cube2,
                              ignore_halos,
                              halo_size)
            # in some cases, loading each cube by name can cause errors
            # so we also have the option to just load all the data
            else:
                compare_cubes(cube_list1[cix1],
                              cube_list2[cix1],
                              ignore_halos,
                              halo_size)
        except validate_common.DataSizeMismatchError as error1:
            error1.file_name1 = file_path1
            error1.file_name2 = file_path2
            msg1 = 'size mismatch for variable {var_name}'
            msg1 = msg1.format(var_name=var_name)
            print msg1
            if stop_on_error:
                print error1
                raise error1
            error_list += [error1]
        except validate_common.DataMismatchError as error1:
            error1.file_name1 = file_path1
            error1.file_name2 = file_path2
            msg1 = \
                'mismatch for variable {var_name}\n'.format(var_name=var_name)
            msg1 += 'max diff = {0:g}'.format(error1.max_error)
            print msg1
            if stop_on_error:
                print error1
                raise error1
            error_list += [error1]
    return error_list



def compare_cubes(cube1, cube2, ignore_halos, halo_size):
    """
    Compare 2 iris cubes. Halos can be ignored in the comparison.

    Inputs:
    cube1 - First cubes to compare
    cube2 - Second cubes to compare
    ignore_halos - If true, ignore the first and last halo_size rows and
                    columns.
    halo_size - Determines the number of rows/columns ignored if ignore_halos
                is set to true

    Errors raised:
    DataSizeMismatchError - Raised if the data in the 2 cubes is of different
                            sizes
    DataMismatchError - Raised if the data in the cubes differs
    """
    if cube1.shape != cube2.shape:
        error1 = validate_common.DataSizeMismatchError()
        error1.cube_name = cube1.name()
        raise error1
    max_error = 0.0
    # In some cases we want to ignore halos
    if ignore_halos:
        if len(cube1.shape) == 1:
            num_mismatches = \
                numpy.count_nonzero(abs(cube1.data-cube2.data)
                                    > ERROR_TOLERANCE)
            max_error = numpy.max(abs(cube1.data-cube2.data))
        elif len(cube1.shape) == 2:
            num_mismatches = \
                numpy.count_nonzero(abs(cube1.data[halo_size:-halo_size,
                                                   halo_size:-halo_size] -
                                        cube2.data[halo_size:-halo_size,
                                                   halo_size:-halo_size])
                                    > ERROR_TOLERANCE)
            max_error = numpy.max(abs(cube1.data[halo_size:-halo_size,
                                                 halo_size:-halo_size] -
                                      cube2.data[halo_size:-halo_size,
                                                 halo_size:-halo_size]))
        elif len(cube1.shape) == 3:
            num_mismatches = \
                numpy.count_nonzero(abs(cube1.data[:,
                                                   halo_size:-halo_size,
                                                   halo_size:-halo_size] -
                                        cube2.data[:,
                                                   halo_size:-halo_size,
                                                   halo_size:-halo_size])
                                    > ERROR_TOLERANCE)
            max_error = numpy.max(abs(cube1.data[:,
                                                 halo_size:-halo_size,
                                                 halo_size:-halo_size] -
                                      cube2.data[:,
                                                 halo_size:-halo_size,
                                                 halo_size:-halo_size]))
        elif len(cube1.shape) == 4:
            num_mismatches = \
                numpy.count_nonzero(abs(cube1.data[:,
                                                   :,
                                                   halo_size:-halo_size,
                                                   halo_size:-halo_size] -
                                        cube2.data[:,
                                                   :,
                                                   halo_size:-halo_size,
                                                   halo_size:-halo_size])
                                    > ERROR_TOLERANCE)
            max_error = numpy.max(abs(cube1.data[:,
                                                 :,
                                                 halo_size:-halo_size,
                                                 halo_size:-halo_size] -
                                      cube2.data[:,
                                                 :,
                                                 halo_size:-halo_size,
                                                 halo_size:-halo_size]))
    else:
        num_mismatches = \
            numpy.count_nonzero(abs(cube1.data-cube2.data) > ERROR_TOLERANCE)
        max_error = numpy.max(abs(cube1.data-cube2.data))

    if num_mismatches > 0:
        error2 = validate_common.DataMismatchError()
        error2.cube_name = cube1.name()
        error2.max_error = float(max_error)
        raise error2

def print_cube_errors(name, error_list):
    """
    Print out a list of errors resulting from comparing 2 cubes

    Inputs:
    name -  The name of the model that generated the cubes
    error_list - a list of python error objects containing a cube_name variable
    """
    if len(error_list) > 0:
        msg1 = '{0} files contain mismatches in the following cubes: \n'
        msg1 = msg1.format(name)

        for error1 in error_list:
            msg1 += '{0} max diff {1:g}\n'.format(error1.cube_name,
                                                  error1.max_error)

        sys.stderr.write(msg1)
        print msg1
    else:
        sys.stderr.write('No mismatches in {0} files.\n'.format(name))
