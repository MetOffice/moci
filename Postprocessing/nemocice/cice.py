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
        return {
            mt.RR: lambda y, m, s, f: '^{}i\.restart{}\.\d{{4}}-[-\d]*$'.
            format(self.prefix, f),
            mt.MM: lambda y, m, s, f: '^{}i\.10d\.{}-{}-\d{{2}}\.nc$'.
            format(self.prefix, y, m),
            mt.SS: lambda y, m, s, f: '^{}i\.1m\.({}-{}|{}-{}|{}-{})\.nc$'.
            format(self.prefix,
                   y if type(s[3]) != int else (int(y) - s[3]),
                   s[0], y, s[1], y, s[2]),
            mt.AA: lambda y, m, s, f: '^{}i\.1s\.{}-\d{{2}}\.nc$'.
            format(self.prefix, y),
        }

    @property
    def end_stencil(self):
        return {
            mt.RR: None,
            mt.MM: lambda s, f: '^{}i\.10d\.\d{{4}}-\d{{2}}-30\.nc$'.
            format(self.prefix),
            mt.SS: lambda s, f: '^{}i\.1m\.\d{{4}}-{}\.nc$'.
            format(self.prefix, s[2]),
            mt.AA: lambda s, f: '^{}i\.1s\.\d{{4}}-11\.nc$'.
            format(self.prefix),
        }

    @property
    def mean_stencil(self):
        return {
            mt.RR: None,  # Required for rebuilding restart files
            mt.MM: lambda y, m, s, f: '{}i.1m.{}-{}.nc'.
            format(self.prefix, y, m),
            mt.SS: lambda y, m, s, f: '{}i.1s.{}-{}.nc'.
            format(self.prefix, y, s[2]),
            mt.AA: lambda y, m, s, f: '{}i.1y.{}-11.nc'.
            format(self.prefix, y),
        }

    @property
    def rsttypes(self):
        return ('', '\.age')

    @staticmethod
    def get_date(fname):
        for string in fname.split('.'):
            if re.match('^[\d-]*$', string):
                return string[:4], string[5:7], string[8:10]
        utils.log_msg('Unable to get date for file:\n\t' + fname, 3)


INSTANCE = ('nemocicepp.nl', CicePostProc)


if __name__ == '__main__':
    pass
