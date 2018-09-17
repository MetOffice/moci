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
    time2days.py

DESCRIPTION
    Converts the date to seconds since calendar zero
'''

#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
from __future__ import division
import error
import sys

def time2days(year, month, day, calendar):
    '''
    time2days inputs:
        year: integer
        month: integer
        day: integer
        calendar: string of value (360|365|gregorian) the type of calendar
      used.
    Returns the number of days since calendar zero
    '''

    #has a valid calendar type been specified
    if calendar not in ['360', '365', 'gregorian']:
        sys.stderr.write('[FAIL] time2days: Invalid calendar type %s\n'
                         '  Calendar must have value\n 360\n 365\n '
                         'gregorian\n' % calendar)
        sys.exit(error.INVALID_FUNC_ARG_ERROR)

    #Define constants c: centuries, y: years
    days_per_4c = 146097
    days_per_c = 36524
    days_per_4y = 1461
    days_per_y = 365

    if calendar == '360':
        days_since_calz = 360*year + 30*(month-1) + day - 1

    elif calendar == '365':
        days_month = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
        days_since_calz = 365*year + days_month[month-1] + day - 1

    elif calendar == 'gregorian':
        # Check for leap year
        if year % 400 == 0:
            leap_year = True
        elif year % 100 == 0:
            leap_year = False
        elif year % 4 == 0:
            leap_year = True
        else:
            leap_year = False

        # set the correct calendar
        if leap_year:
            days_month = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
        else:
            days_month = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]

        # Add on the days for the current month
        days_since_calz = days_month[month-1] + day - 1

        # Subtract a year as we only want to count whole years
        years_since_calz = year - 1

        # Add days from preceding years, note we make use of integer division
        # Number for 4 centuries first
        days_since_calz += days_per_4c*(years_since_calz//400)
        years_since_calz -= 400*(years_since_calz//400)

        # Count number of centuries
        days_since_calz += days_per_c*(years_since_calz//100)
        years_since_calz -= 100*(years_since_calz//100)

        # Count number of four year periods
        days_since_calz += days_per_4y*(years_since_calz//4)
        years_since_calz -= 4*(years_since_calz//4)

        # Count the remaining years
        days_since_calz += years_since_calz*days_per_y

    return days_since_calz
