#!/usr/bin/evn python
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
    inc_days.py

DESCRIPTION
    Calculates the increment in days for a particular
    date, when the increment is given in terms of years/months/days
'''

#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
from __future__ import division
import error
import time2days
import sys

def inc_days(y_start, m_start, d_start, y_inc, m_inc, d_inc, calendar):
    '''
    inc_days inputs:
        y_start: integer
        m_start: integer
        d_start: integer
        y_inc: integer
        m_inc: integer
        d_inc: integer
        calendar: string of value (360|365|gregorian) the type of calendar
      used.
    Returns the increment in number of days
    '''
    #has a valid calendar type been specified
    if calendar not in ['360', '365', 'gregorian']:
        sys.stderr.write('[FAIL] time2days: Invalid calendar type %s\n'
                         '  Calendar must have value\n 360\n 365\n '
                         'gregorian\n' % calendar)
        sys.exit(error.INVALID_FUNC_ARG_ERROR)

    #number of days since calendar zero
    days_to_start = time2days.time2days(y_start, m_start, d_start, calendar)

    #Add the month and year increments to the start values to get the end
    #month/year
    y_end = y_start + y_inc
    m_end = m_start + m_inc

    #Deal with monthly rollovers
    if m_end > 12:
        add_years = (m_end - 1)//12
        y_end += add_years
        m_end = ((m_end - 1) % 12) + 1

    #Calculate number of days from calendar zero to end date. Does not include
    #day increments
    days_to_end = time2days.time2days(y_end, m_end, d_start, calendar)

    #Account for day increments
    days_to_end += d_inc

    run_days = days_to_end - days_to_start
    return run_days
