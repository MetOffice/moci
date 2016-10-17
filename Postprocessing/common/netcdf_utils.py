#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    netcdf_utils.py

DESCRIPTION
    Module containing methods to fix times and tims bounds in a mean
    netcdf file created from multiple input files
'''
from netCDF4 import Dataset, num2date, date2num
import numpy

import utils


def get_dataset(fname, action='r'):
    '''Return dataset from netcdf Dataset.variables'''
    try:
        ncid = Dataset(fname, action)
    except RuntimeError as err:
        utils.log_msg('netcdf_utils.py: File: {} \n\t{}'.format(fname, err),
                      level='FAIL')
    return ncid


def get_vardata(dataset, varname, attribute=None):
    '''Return requested value or attribute from netcdf Dataset.variables'''
    msg = ''
    if attribute:
        try:
            rtnval = getattr(dataset.variables[varname], attribute)
        except AttributeError:
            msg = 'netcdf_utils: - get_vardata: Variable "{}" is missing ' \
                '"{}" attribute'.format(varname, attribute)
    else:
        try:
            rtnval = dataset.variables[varname]
        except KeyError:
            msg = 'netcdf_utils - get_vardata: Variable "{}" not found ' \
                'in dataset'.format(varname)

    if msg:
        utils.log_msg(msg, level='FAIL')
    return rtnval


def time_bounds_var_to_date(fname, time_var):
    '''
    Read in time bounds variable from fname
    Convert to netcdf.datetime objects using units and calendar from time_var
    '''
    with get_dataset(fname) as ncid:
        units = get_vardata(ncid, time_var, attribute='units')
        calendar = get_vardata(ncid, time_var, attribute='calendar').lower()
        bounds_var = get_vardata(ncid, time_var, attribute='bounds')
        bounds = get_vardata(ncid, bounds_var)[:]
        date = [num2date(bound, units, calendar) for bound in bounds]
    return date


def first_and_last_dates(dates, target_units, calendar):
    '''
    Return the earliest and latest dates as floats using
    target_units and calendar.
    Input dates should be a list of netcdf.datetime objects
    '''
    datevals = [date2num(date, target_units, calendar) for date in dates]
    datevals = numpy.array(datevals)
    first_and_last = numpy.array([datevals.min(), datevals.max()])
    return first_and_last


def correct_bounds(meanset, time_var, units, calendar):
    '''Return correct time bounds for meanfile'''
    dates_in = [time_bounds_var_to_date(fname, time_var) for fname in meanset]
    return first_and_last_dates(dates_in, units, calendar)


def time_var_to_date(fname, time_var):
    '''Return netcdf.datetime object from time_var in fname'''
    with get_dataset(fname) as ncid:
        time = get_vardata(ncid, time_var)
        time_units = get_vardata(ncid, time_var, attribute='units')
        time_cal = get_vardata(ncid, time_var, attribute='calendar').lower()
        date = num2date(time[:], time_units, time_cal)
    return date


def correct_time(meanset, time_var, target_unit, calendar):
    '''Return correct float value of time for mean file'''
    dates_in = [time_var_to_date(fname, time_var) for fname in meanset]
    # Convert date to float values
    floats = [date2num(date, target_unit, calendar) for date in dates_in]
    return numpy.array(floats).mean()


def fix_times(meanset, meanfile, time_var, do_time=False, do_bounds=False):
    '''
    Fix time variable in meanfile to the mean of the input times taking
    account of calendar
    Fix time bounds variable in meanfile to the earliest and latest
    dates in the same variable in meanset
    Variables: meanset = A set of files that have been averaged together
               meanfile = Mean file created by averaging the files above
               time_var = name of the time variable to be used to obtain the
                          units and calendar attributes
               time_bounds_var = name of time bounds variable to be corrected
    '''
    ncid = get_dataset(meanfile, action='r+')
    units = get_vardata(ncid, time_var, attribute='units')
    calendar = get_vardata(ncid, time_var, attribute='calendar').lower()

    rmsg = ''
    if do_time:
        mean_time_var = get_vardata(ncid, time_var)
        mean_time_var[:] = correct_time(meanset, time_var, units, calendar)
        rmsg = rmsg + 'Corrected {} in file: {}\n'.format(time_var, meanfile)

    if do_bounds:
        bounds_var = get_vardata(ncid, time_var, attribute='bounds')
        mean_bounds_shape = get_vardata(ncid, bounds_var, attribute='shape')
        mean_bounds_var = get_vardata(ncid, bounds_var)
        new_bounds = correct_bounds(meanset, time_var, units, calendar)
        mean_bounds_var[:] = numpy.reshape(new_bounds, mean_bounds_shape)
        rmsg = rmsg + 'Corrected {} in file: {}\n'.format(bounds_var, meanfile)

    ncid.close()
    return rmsg
