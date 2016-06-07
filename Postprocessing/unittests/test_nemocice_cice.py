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
'''
import unittest
import mock
import os
import sys
import re

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'common'))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'cicecice'))

import runtime_environment
runtime_environment.setup_env()
import testing_functions as func

import cice


class StencilTests(unittest.TestCase):
    '''Unit tests relating to the CICE output filename stencils'''
    def setUp(self):
        self.files = [
            'RUNIDi.restart.1981-12-01-00000',
            'RUNIDi.restart.1981-12-01-00000.nc',
            'RUNIDi.6h.1985-11-11-13.nc',
            'RUNIDi.5d.1985-11-06.nc',
            'RUNIDi.10d.1985-11-11.nc',
            'RUNIDi.1m.1985-11.nc',
            'RUNIDi.1s.1985-11.nc',
            'RUNIDi.1y.1984-11.nc',
            'RUNIDi.1y.1985-11.nc'
            ]
        self.cice = cice.CicePostProc()
        self.cice.suite = mock.Mock()
        self.cice.suite.prefix = 'RUNID'
        self.date = ('1985', '09')
        self.ssn = ('09', '10', '11', 0)
        self.setstencil = self.cice.set_stencil
        self.endstencil = self.cice.end_stencil
        self.meanstencil = self.cice.mean_stencil

    def tearDown(self):
        try:
            os.remove('nemocicepp.nl')
        except OSError:
            pass

    def test_set_stencil_restarts(self):
        '''Test the regular expressions of the set_stencil method - restarts'''
        func.logtest('Assert restart pattern matching of set_stencil:')
        patt = re.compile(self.setstencil['Restarts']('', None, None, ''))
        cice_rst = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(cice_rst,
                         [fname for fname in self.files if 'restart' in fname])

    def test_set_stencil_monthly(self):
        '''Test the regex of the set_stencil method - monthly'''
        func.logtest('Assert monthly pattern matching of set_stencil:')
        args = (self.date[0], self.date[1], None, '')
        patt = re.compile(self.setstencil['Monthly'](*args))
        month_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(month_set,
                         [fname for fname in self.files if '10d_' in fname])

    def test_set_stencil_seasonal(self):
        '''Test the regex of the set_stencil method - seasonal'''
        func.logtest('Assert seasonal pattern matching of set_stencil:')
        args = (self.date[0], None, self.ssn, '')
        patt = re.compile(self.setstencil['Seasonal'](*args))
        season_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(season_set,
                         [fname for fname in self.files if '.1m.' in fname])

    def test_set_stencil_annual(self):
        '''Test the regex of the set_stencil method - annual'''
        func.logtest('Assert annual pattern matching of set_stencil:')
        args = (self.date[0], None, None, '')
        patt = re.compile(self.setstencil['Annual'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '.1s.' in fname])

    def test_end_stencil_restarts(self):
        '''Test the regular expressions of the set_stencil method - restarts'''
        func.logtest('Assert restart pattern matching of end_stencil:')
        self.assertEqual(self.endstencil['Restarts'], None)

    def test_end_stencil_monthly(self):
        '''Test the regex of the end_stencil method - monthly'''
        func.logtest('Assert monthly pattern matching of end_stencil:')
        args = (None, '')
        patt = re.compile(self.endstencil['Monthly'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if
                          '10d_' in fname and '30.nc' in fname])

    def test_end_stencil_seasonal(self):
        '''Test the regex of the end_stencil method - seasonal'''
        func.logtest('Assert seasonal pattern matching of end_stencil:')
        args = (self.ssn, '')
        patt = re.compile(self.endstencil['Seasonal'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '.1m.' in fname])

    def test_end_stencil_annual(self):
        '''Test the regex of the end_stencil method - annual'''
        func.logtest('Assert annual pattern matching of end_stencil:')
        args = (None, '')
        patt = re.compile(self.endstencil['Annual'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '.1s.' in fname])

    def test_mean_stencil_hourly(self):
        '''Test the regular expressions of the mean_stencil method - hourly'''
        func.logtest('Assert hourly pattern matching of mean_stencil:')
        patt = re.compile(self.meanstencil['General']('6h', None, None, ''))
        sixhr_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(sixhr_set,
                         [fname for fname in self.files if '.6h.' in fname])

    def test_mean_stencil_daily(self):
        '''Test the regular expressions of the mean_stencil method - daily'''
        func.logtest('Assert daily pattern matching of mean_stencil:')
        patt = re.compile(self.meanstencil['General']('10d', None, None, ''))
        tenday_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(tenday_set,
                         [fname for fname in self.files if '.10d.' in fname])

    def test_mean_stencil_monthly(self):
        '''Test the regular expressions of the mean_stencil method - monthly'''
        func.logtest('Assert monthly pattern matching of mean_stencil:')
        args = (self.date[0], '11', None, '')
        patt = re.compile(self.meanstencil['Monthly'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '.1m.' in fname])

    def test_mean_stencil_seasonal(self):
        '''Test the regexes of the mean_stencil method - seasonal'''
        func.logtest('Assert seasonal pattern matching of mean_stencil:')
        args = (self.date[0], self.date[1], self.ssn, '')
        patt = re.compile(self.meanstencil['Seasonal'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '.1s.' in fname])

    def test_mean_stencil_annual(self):
        '''Test the regular expressions of the mean_stencil method - annual'''
        func.logtest('Assert annual pattern matching of mean_stencil:')
        args = (self.date[0], None, None, '')
        patt = re.compile(self.meanstencil['Annual'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if
                          '.1y.' in fname and self.date[0] + '-11.' in fname])

    def test_mean_stencil_all_years(self):
        '''Test the regex of the mean_stencil method - all years'''
        func.logtest('Assert all years pattern matching of mean_stencil:')
        args = ('.*', None, None, '')
        patt = re.compile(self.meanstencil['Annual'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '.1y.' in fname])
