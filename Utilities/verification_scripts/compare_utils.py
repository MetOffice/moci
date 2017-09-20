#!/usr/bin/env python2.7
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""
Created on 20 August 2015

@author: Stephen Haddad

Utility functions for use in test scripts.
"""
import itertools

import numpy

import iris

import test_common
import cf_units

iris.FUTURE.netcdf_promote = True

ERROR_TOLERANCE = 1e-10
CF_TIME_UNIT = 'seconds since 1900-01-01 00:00:00'
CF_CALENDAR = 'noleap'

NEMO_TIME_COORD_NAME = 'time'

def compare_cube_list_files(file_path1,
                            file_path2,
                            stop_on_error=False,
                            ignore_halos=False,
                            halo_size=0,
                            ignore_variables=None,
                            save_memory=False,
                            io_manager=None):
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

    if not io_manager:
        io_manager = test_common.TestIO()
    #load files to get list of variables
    try:
        cube_list1 = iris.load(file_path1)
    except:
        raise test_common.FileLoadError(file_path1)

    try:
        cube_list2 = iris.load(file_path2)
    except:
        raise test_common.FileLoadError(file_path2)

    if len(cube_list1) != len(cube_list2):
        raise test_common.CubeCountMismatchError()

    io_manager.write_out(
        'comparing cubes with tolerance {0:g}'.format(ERROR_TOLERANCE))
    if ignore_variables:
        ignore_msg = 'the following variables are being ignored: \n'
        ignore_list = ['{0:d}:{1}\n'.format(cix1, c1.name())
                       for cix1, c1 in enumerate(cube_list1)
                       if c1.name() in ignore_variables]
        io_manager.write_out(ignore_msg + '\n'.join(ignore_list))

        variable_list = [(cix1, c1.name(), c1.var_name)
                         for cix1, c1 in enumerate(cube_list1)
                         if c1.name() not in ignore_variables]
    else:
        variable_list = [(cix1, c1.name(), c1.var_name)
                         for cix1, c1 in enumerate(cube_list1)]
    error_list = []

    for cix1, name1, var_name in variable_list:
        msg1 = 'comparing cube {currentCube} of {totalCubes}'
        msg1 += ' - variable {name} ({vname})'
        msg1 = msg1.format(currentCube=cix1+1,
                           totalCubes=len(cube_list1),
                           filename=file_path1,
                           name=name1,
                           vname=var_name)
        io_manager.write_out(msg1)
        try:
            # load cubes here, to ensure that only the data for the current
            # variable is loaded into memory, reducing memory required
            if save_memory:
                cube_func1 = lambda cube_in: cube_in.var_name == var_name
                constraint1 = iris.Constraint(cube_func=cube_func1)
                cube1 = iris.load_cube(file_path1, constraint1)
                cube2 = iris.load_cube(file_path2, constraint1)
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
        except test_common.DataSizeMismatchError as error1:
            error1.file_name1 = file_path1
            error1.file_name2 = file_path2
            msg1 = 'size mismatch for variable {var_name}'
            msg1 = msg1.format(var_name=var_name)
            io_manager.write_out(msg1)
            if stop_on_error:
                io_manager.write_out(error1)
                raise error1
            error_list += [error1]
        except test_common.DataMismatchError as error1:
            error1.file_name1 = file_path1
            error1.file_name2 = file_path2
            msg1 = \
                'mismatch for variable {var_name}\n'.format(var_name=var_name)
            msg1 += 'max diff = {0:g}'.format(error1.max_error)
            io_manager.write_out(msg1)
            if stop_on_error:
                io_manager.write_out(error1)
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
        error1 = test_common.DataSizeMismatchError()
        error1.cube_name = cube1.name()
        raise error1
    max_error = 0.0
    # In some cases we want to ignore halos
    if ignore_halos:
        if len(cube1.shape) == 1:
            num_mismatches = \
                numpy.sum(numpy.abs(cube1.data-cube2.data)
                          > ERROR_TOLERANCE)
            max_error = numpy.max(numpy.abs(cube1.data-cube2.data))
        elif len(cube1.shape) == 2:
            num_mismatches = \
                numpy.sum(numpy.abs(cube1.data[halo_size:-halo_size,
                                               halo_size:-halo_size] -
                                    cube2.data[halo_size:-halo_size,
                                               halo_size:-halo_size])
                          > ERROR_TOLERANCE)



            max_error = numpy.max(numpy.abs(cube1.data[halo_size:-halo_size,
                                                       halo_size:-halo_size] -
                                            cube2.data[halo_size:-halo_size,
                                                       halo_size:-halo_size]))
        elif len(cube1.shape) == 3:
            num_mismatches = \
                numpy.sum(numpy.abs(cube1.data[:,
                                               halo_size:-halo_size,
                                               halo_size:-halo_size] -
                                    cube2.data[:,
                                               halo_size:-halo_size,
                                               halo_size:-halo_size])
                          > ERROR_TOLERANCE)
            max_error = numpy.max(numpy.abs(cube1.data[:,
                                                       halo_size:-halo_size,
                                                       halo_size:-halo_size] -
                                            cube2.data[:,
                                                       halo_size:-halo_size,
                                                       halo_size:-halo_size]))
        elif len(cube1.shape) == 4:
            num_mismatches = \
                numpy.sum(numpy.abs(cube1.data[:,
                                               :,
                                               halo_size:-halo_size,
                                               halo_size:-halo_size] -
                                    cube2.data[:,
                                               :,
                                               halo_size:-halo_size,
                                               halo_size:-halo_size])
                          > ERROR_TOLERANCE)
            max_error = numpy.max(numpy.abs(cube1.data[:,
                                                       :,
                                                       halo_size:-halo_size,
                                                       halo_size:-halo_size] -
                                            cube2.data[:,
                                                       :,
                                                       halo_size:-halo_size,
                                                       halo_size:-halo_size]))
    else:
        num_mismatches = \
            numpy.sum(numpy.abs(cube1.data-cube2.data) > ERROR_TOLERANCE)
        max_error = numpy.max(numpy.abs(cube1.data-cube2.data))

    if num_mismatches > 0:
        error2 = test_common.DataMismatchError()
        error2.cube_name = cube1.name()
        error2.max_error = float(max_error)
        raise error2

def print_cube_errors(name, error_list, io_manager):
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

        io_manager.write_both(msg1)
    else:
        io_manager.write_out('No mismatches in {0} files.\n'.format(name))


def find_matching_timesteps(cube1, cube2):
    """
    Compare the time coordinates in 2 cubes, and return a list of tuples
    representing the time values present in both cubes. The tuples have three
    elements: the time value, the index of the time in the first cube and
    the index of the time in second cube.

    Inputs:
    cube1 - The first cube to compare. Must contain a time coordinate.
    cube2 - The second cube to compare. Must contain a time coordinate.

    Returns:
    ts_tuples - A list of tuples representing the matching times. The tuples
                contain 3 elements: the time value, and the indices of that
                time in each cube.
    """
    timesteps1 = cube1.coords(NEMO_TIME_COORD_NAME)[0].points
    timesteps2 = cube2.coords(NEMO_TIME_COORD_NAME)[0].points

    ts_list = [ts for ts in timesteps1 if ts in timesteps2]
    ix1_list = [ix1 for ix1, ts in enumerate(timesteps1) if ts in timesteps2]
    ix2_list = [ix2 for ix2, ts in enumerate(timesteps2) if ts in timesteps1]
    ts_tuples = \
        [(ts, ix1, ix2)
         for ts, ix1, ix2 in itertools.izip(ts_list, ix1_list, ix2_list)]

    return ts_tuples

def compare_cubes_at_timesteps(diag_path1,
                               cube_list1,
                               diag_path2,
                               cube_list2,
                               timestep_tuples,
                               save_memory,
                               stop_on_error,
                               io_manager):
    """
    Compare all cubes in 2 cube lists for matching values of the time
    coordinate.

    Inputs:
    diag_path1 - Path to first netcdf file
    cube_list1 - cube list loaded from diag_path1
    diag_path2 - Path to second netcdf file
    cube_list2 - cube list loaded from diag_path2
    timestep_tuples - a list of tuples reperesenting the timesteps present in
                      both cube lists and thus where the cubes should be
                      compared. Each tuple has 3 elements: the time value, the
                      index of that time in the cubes of the first list and
                      the index of the time in the cubes of the second list.
    save_memory - If true, only 1 cube at one time value will be load into
                  memory
    stop_on_error - If true, the function will raise an exception on finding
                    a mismatch between the data in the cubes.
    io_manager - Wrapper class for output. This allows output to be easily
                 redirected, for example to the rose_ana reporting mechanism.

    Return values:
    error_list -If any mismatches are found, a list of the mismatches is
                returned. The list consist of Exception objects which contain
                the details of the mismatch.

    Errors raised:
    CubeCountMismatchError - Raised if the re are a different number of cubes
                             in the 2 files.
    DataSizeMismatchError - Raised if the data fields in 2 cubes being compared
                            are of different sizes
    DataMismatchError - This error is only raised if the stop_on_error flag is
                        true. If stop_on_error is true, this error will be
                        raised the first time a mismatch between cube data is
                        encountered.
    """
    if len(cube_list1) != len(cube_list2):
        raise test_common.CubeCountMismatchError()
    num_cubes = len(cube_list1)
    error_list = []
    ignore_halos = True
    halo_size = 1

    for cix1, (cube1, cube2) \
        in enumerate(itertools.izip(cube_list1, cube_list2)):
        name1 = cube1.name()
        var_name = cube1.var_name



        msg1 = 'comparing cube {0} of {1}\n   name: {2}\n   var_name: {3}'
        msg1 = msg1.format(cix1+1,
                           num_cubes,
                           name1,
                           var_name)
        io_manager.write_out(msg1)


        ts_comp_func = lambda ts_in: ts_in == timestamp
        for timestamp, ix1, ix2 in timestep_tuples:

            ts_cf = cf_units.num2date(timestamp, CF_TIME_UNIT, CF_CALENDAR)
            io_manager.write_out('comparing matching timesteps '
                                 'at {0}'.format(ts_cf))

            # load cubes here, to ensure that only the data for the current
            # variable is loaded into memory, reducing memory required
            try:
                if save_memory:


                    cube_func1 = \
                        lambda cube_in: cube_in.var_name == var_name
                    coord_dict1 = {NEMO_TIME_COORD_NAME: ts_comp_func}

                    current_constraint = \
                        iris.Constraint(cube_func=cube_func1,
                                        coord_values=coord_dict1)
                    cube1 = iris.load_cube(diag_path1, current_constraint)
                    cube2 = iris.load_cube(diag_path2, current_constraint)

                    compare_cubes(cube1,
                                  cube2,
                                  ignore_halos,
                                  halo_size)
                # in some cases, loading each cube by name can cause errors
                # so we also have the option to just load all the data
                else:
                    compare_cubes(cube_list1[cix1][ix1],
                                  cube_list2[cix1][ix2],
                                  ignore_halos,
                                  halo_size)
            except test_common.DataSizeMismatchError as error1:
                error1.file_name1 = diag_path1
                error1.file_name2 = diag_path2
                msg1 = 'size mismatch for variable {var_name}'
                msg1 = msg1.format(var_name=var_name)
                io_manager.write_out(msg1)
                if stop_on_error:
                    io_manager.write_out(error1)
                    raise error1
                error_list += [error1]
            except test_common.DataMismatchError as error1:
                error1.file_name1 = diag_path1
                error1.file_name2 = diag_path2
                msg1 = 'mismatch for variable {var_name}\n max diff = {diff:g}'
                msg1 = msg1.format(var_name=var_name,
                                   diff=error1.max_error)
                io_manager.write_out(msg1)
                if stop_on_error:
                    io_manager.write_out(error1)
                    raise error1
                error_list += [error1]
    return error_list



def compare_netcdf_diagnostic_files(diag_path1,
                                    diag_path2,
                                    stop_on_error,
                                    io_manager):
    """

    Inputs:
    diag_path1 -
    diag_path2 -
    stop_on_error -
    io_manager -

    Return values:
    error_list -

    Errors raised:
    CubeCountMismatchError - Raised if the re are a different number of cubes
                             in the 2 files.
    DataSizeMismatchError - Raised if the data fields in 2 cubes being compared
                            are of different sizes
    DataMismatchError - This error is only raised if the stop_on_error flag is
                        true. If stop_on_error is true, this error will be
                        raised the first time a mismatch between cube data is
                        encountered.
    """

    try:
        cube_list1 = iris.load(diag_path1)
    except:
        raise test_common.FileLoadError(diag_path1)

    try:
        cube_list2 = iris.load(diag_path2)
    except:
        raise test_common.FileLoadError(diag_path2)

    if len(cube_list1) != len(cube_list2):
        raise test_common.CubeCountMismatchError()

    # look at first cube to find matching timesteps (assuming all cubes have
    # data for the same timestamps
    timestep_tuples = find_matching_timesteps(cube_list1[0], cube_list2[0])

    save_memory = True
    try:
        error_list = compare_cubes_at_timesteps(diag_path1,
                                                cube_list1,
                                                diag_path2,
                                                cube_list2,
                                                timestep_tuples,
                                                save_memory,
                                                stop_on_error,
                                                io_manager)
    except test_common.DataSizeMismatchError as error1:
        error1.file_name1 = diag_path1
        error1.file_name2 = diag_path2
        io_manager.write_out(error1)
        raise error1
    except test_common.DataMismatchError as error1:
        error1.file_name1 = diag_path1
        error1.file_name2 = diag_path2
        io_manager.write_out(error1)
        raise error1

    return error_list
