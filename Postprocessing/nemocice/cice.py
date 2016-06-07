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
    cice.py

DESCRIPTION
    Class definition for CicePostProc - holds CICE model properties
    and methods
'''
import re

import modeltemplate as mt
import utils


class CicePostProc(mt.ModelTemplate):
    '''
    Methods and properties specific to the CICE post processing application.
    '''
    @property
    def set_stencil(self):
        '''
        Returns a dictionary of regular expressions to match files belonging
        to each period (keyword) set

        The same 4 arguments (year, month, season and field) are required to
        access any indivdual regular expression regardless of the need to use
        them.  This is a consequence of the @property nature of the method
        '''
        return {
            mt.RR: lambda y, m, s, f:
                   r'^{P}i\.restart{F}\.\d{{4}}-[-\d]*(\.nc)?$'.
                   format(P=self.prefix, F=f),
            mt.MM: lambda y, m, s, f: r'^{P}i\.{B}\.{Y}-{M}-\d{{2}}\.nc$'.
                   format(P=self.prefix, B=self.month_base, Y=y, M=m),
            mt.SS: lambda y, m, s, f:
                   r'^{P}i\.1m\.({Y1}-{M1}|{Y2}-{M2}|{Y2}-{M3})\.nc$'.
                   format(P=self.prefix,
                          Y1=int(y) - s[3] if isinstance(s[3], int) else y,
                          Y2=y,
                          M1=s[0],
                          M2=s[1],
                          M3=s[2]),
            mt.AA: lambda y, m, s, f: r'^{P}i\.1s\.{Y}-\d{{2}}\.nc$'.
                   format(P=self.prefix, Y=y),
        }

    @property
    def end_stencil(self):
        '''
        Returns a dictionary of regular expressions to match files belonging
        to each period (keyword) end

        The same 2 arguments (season and field) are required to access any
        indivdual regular expression regardless of the need to use them.
        This is a consequence of the @property nature of the method
        '''
        return {
            mt.RR: None,
            mt.MM: lambda s, f:
                   r'^{P}i\.{B}\.\d{{4}}-\d{{2}}-(28|29|30|31)\.nc$'.
                   format(P=self.prefix, B=self.month_base),
            mt.SS: lambda s, f: r'^{P}i\.1m\.\d{{4}}-{M}\.nc$'.
                   format(P=self.prefix, M=s[2]),
            mt.AA: lambda s, f: r'^{P}i\.1s\.\d{{4}}-11\.nc$'.
                   format(P=self.prefix),
        }

    @property
    def mean_stencil(self):
        '''
        Returns a dictionary of regular expressions to match files belonging
        to each period (keyword) mean

        The same 4 arguments (year, month, season and field) are required to
        access any indivdual regular expression regardless of the need to use
        them.  This is a consequence of the @property nature of the method
        '''
        return {
            mt.XX: lambda y, m, s, f:
                   r'^{P}i\.{B}\.\d{{4}}-\d{{2}}(-\d{{2}})?(-\d{{2}})?\.nc$'.
                   format(P=self.prefix, B=y if y else r'\d+[hdmsy]'),
            mt.MM: lambda y, m, s, f: r'{P}i.1m.{Y}-{M}.nc'.
                   format(P=self.prefix, Y=y, M=m),
            mt.SS: lambda y, m, s, f: r'{P}i.1s.{Y}-{M}.nc'.
                   format(P=self.prefix, Y=y, M=s[2]),
            mt.AA: lambda y, m, s, f: r'{P}i.1y.{Y}-11.nc'.
                   format(P=self.prefix, Y=y),
        }

    @property
    def rsttypes(self):
        return ('', r'.age')

    @staticmethod
    def get_date(fname):
        for string in fname.split('.'):
            if re.match(r'^[\d-]*$', string):
                return string[:4], string[5:7], string[8:10]
        utils.log_msg('Unable to get date for file:\n\t' + fname, 3)


INSTANCE = ('nemocicepp.nl', CicePostProc)


if __name__ == '__main__':
    pass
