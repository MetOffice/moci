#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2019-2026 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    rates_lib.py

DESCRIPTION
    Library of functions required for the monitoring script
'''

import collections
import re
import sqlite3
import numpy

class ScriptError(Exception):
    '''
    A general exception for this script that can be caught easily
    '''

# Global containers
DAYS = collections.namedtuple('DAYS', ('submit', 'start', 'end'))
RATES = collections.namedtuple('RATES', ('day', 'effective', 'coupled',
                                         'coupled_queue', 'coupled_wait'))
INTEGRATEDRATES = collections.namedtuple('INTEGRATEDRATES', (
    'interval', 'n', 'effective', 'coupled', 'coupled_queue', 'coupled_wait'))


def days_from_db(suitedb, job="coupled"):
    '''
    Return a list of DAYS of successful coupled jobs from the cylc database
    These 'days' are universal times
    '''
    days = []
    # Check that the job name is valid
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", job):
        raise ScriptError('{} is an invalid job name'.format(job))

    with sqlite3.connect(suitedb) as dbase:
        cursor = dbase.cursor()
        cursor.execute('select '
                       'julianday(time_submit), julianday(time_run), '
                       'julianday(time_run_exit) '
                       'from '
                       'task_jobs '
                       'where '
                       'name == "{}" and submit_status == 0 '
                       'and run_status == 0 and '
                       'julianday(time_submit) IS NOT NULL and '
                       'julianday(time_run) IS NOT NULL and '
                       'julianday(time_run_exit) IS NOT NULL '
                       'order by julianday(time_submit)'.format(job))
        cycle_times = cursor.fetchall()
        for row in cycle_times:
            days.append(DAYS._make(row))
    if not days:
        raise ScriptError('Unable to retrieve cycle times from the cylc'
                          ' database')
    return days


def calculate_relative_times(times):
    '''
    Given an ordered tuple of DAYS, get all times in relation to the
    submit field of the first row
    '''
    t_0 = times[0].submit
    return tuple(DAYS(submit=times[i].submit - t_0,
                      start=times[i].start - t_0,
                      end=times[i].end - t_0)
                 for i in range(len(times)))


def calculate_rates(times, cycle_length, month_length, year_length):
    '''
    Calculate the rates of the model run, including queuing and coupling
    '''
    def rate(d_t):
        '''
        Return a rate in years per day corresponding to an interval of
        length dt days
        '''
        return (month_length * cycle_length) / (1.0 * year_length * d_t)

    if len(times) < 2:
        raise ScriptError('Need a completed cycle to compute a rate')
    rates = tuple(RATES(day=times[i].submit,
                        effective=rate(times[i + 1].submit - times[i].submit),
                        coupled=rate(times[i].end - times[i].start),
                        coupled_queue=rate(times[i].end - times[i].submit),
                        coupled_wait=rate(times[i + 1].submit -
                                          times[i].start))
                  for i in range(len(times) - 1))
    return rates


def integrate(resampled, interval):
    '''
    Integrate to get the total time
    '''
    return INTEGRATEDRATES(
        interval=interval,
        n=len(resampled),
        effective=sum(e.effective * interval for e in resampled),
        coupled=sum(e.coupled * interval for e in resampled),
        coupled_queue=sum(e.coupled_queue * interval for e in resampled),
        coupled_wait=sum(e.coupled_wait * interval for e in resampled))

def decay_mean(values, constant):
    '''
    Calculate a decaying mean of list of values. Takes in a decay constant
    as a second argument. Returns list of length of values
    '''
    constant = float(constant)

    decayed = values[0]
    results = []
    for val in values:
        decayed = (constant * val + (1 - constant) * decayed)
        results.append(decayed)
    return results

def decay_rates(rates, constant):
    '''
    Compute decaying rates, and return a tuple of modified rates objects
    '''
    initial_values = {'days': [r.day for r in rates],
                      'effective': [r.effective for r in rates],
                      'coupled': [r.coupled for r in rates],
                      'coupled_queue': [r.coupled_queue for r in rates],
                      'coupled_wait': [r.coupled_wait for r in rates]}
    results = {'days': initial_values['days'],
               'effective': None,
               'coupled': None,
               'coupled_queue': None,
               'coupled_wait': None}
    for key in initial_values:
        if key not in 'days':
            results[key] = decay_mean(initial_values[key], constant)

    # convert this back into a RATES object
    decayed_rates = tuple(RATES(
        day=results['days'][i],
        effective=results['effective'][i],
        coupled=results['coupled'][i],
        coupled_queue=results['coupled_queue'][i],
        coupled_wait=results['coupled_wait'][i])
                          for i in range(len(results['days'])))
    return decayed_rates


def interpolate(x_values, y_values, interval):
    '''
    Interpolate list of y_values at intervals of interval using linear
    inerpolation. These correspond to an xaxis of x_values
    Returns new list of y_values
    '''
    if len(x_values) != len(y_values):
        raise ScriptError('Need the same number of x- and y- values to'
                          ' interpolate')
    if len(x_values) < 2:
        raise ScriptError('Need two or more values to perform interpolation')

    x_min = x_values[0]
    x_max = x_values[-1]
    n_interp = int(((x_max - x_min) / float(interval))) + 1
    x_values_interp = numpy.linspace(x_min, x_max, n_interp)
    y_values_interp = numpy.interp(x_values_interp, x_values, y_values)

    return list(x_values_interp), list(y_values_interp)


def interpolate_rates(rates, interval):
    '''
    Resample rates at intervals of interval
    '''
    if len(rates) < 2:
        raise ScriptError('Need two or more completed cycles to perform'
                          ' interpolation')
    # get our initial values to perform the interpolations
    initial_values = {'days': [r.day for r in rates],
                      'effective': [r.effective for r in rates],
                      'coupled': [r.coupled for r in rates],
                      'coupled_queue': [r.coupled_queue for r in rates],
                      'coupled_wait': [r.coupled_wait for r in rates]}
    interp_values = {'days': None,
                     'effective': None,
                     'coupled': None,
                     'coupled_queue': None,
                     'coupled_wait': None}
    for key in initial_values:
        if key not in 'days':
            interp_k, interp_val = interpolate(initial_values['days'],
                                               initial_values[key], interval)
            interp_values['days'] = interp_k
            interp_values[key] = interp_val
    # convert this back into a RATES object
    interp_rates = tuple(RATES(
        day=interp_values['days'][i],
        effective=interp_values['effective'][i],
        coupled=interp_values['coupled'][i],
        coupled_queue=interp_values['coupled_queue'][i],
        coupled_wait=interp_values['coupled_wait'][i])
                         for i in range(len(interp_values['days'])))
    return interp_rates
