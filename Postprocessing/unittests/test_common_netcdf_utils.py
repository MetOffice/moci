#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2022 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''
import unittest
# mock is integrated into unittest as of Python3.3, but is a stand alone
# package (back-ported) at earlier versions.
try:
    import unittest.mock as mock
except ImportError:
    import mock
import numpy

# netcdftime has been superseeded by the cftime, but one is avaliable
# with python2.7 and the other with python3 in the Met Office
try:
    import cftime as NCDF_time_module
except ImportError:
    from netCDF4 import netcdftime as NCDF_time_module

import runtime_environment
import testing_functions as func

import netcdf_utils

runtime_environment.setup_env()


class DatasetTests(unittest.TestCase):
    '''Unit tests for methods manipulating netcdf Dataset.variables'''
    def setUp(self):
        self.dummy = 'myattribute'

    def tearDown(self):
        pass

    def test_get_dataset(self):
        '''Test get_dataset method'''
        func.logtest('Assert return from get_dataset method:')
        with mock.patch('netcdf_utils.Dataset') as mock_dataset:
            dataset = netcdf_utils.get_dataset('Filename')
            mock_dataset.assert_called_with('Filename', 'r')
            self.assertEqual(dataset, mock_dataset.return_value)

    def test_get_dataset_fail(self):
        '''Test get_dataset method - failure'''
        func.logtest('Assert failure return from get_dataset method:')
        with self.assertRaises(SystemExit):
            _ = netcdf_utils.get_dataset('Filename')
        self.assertIn('No such file', func.capture('err'))

    def test_get_vardata_no_attribute(self):
        '''Test get_vardata method with no attribute'''
        func.logtest('Assert return from get_vardata method with no attr:')
        mock_data = mock.Mock(netcdf_utils.Dataset)
        mock_data.variables = {'timevar': self}
        rtnval = netcdf_utils.get_vardata(mock_data, 'timevar')
        self.assertEqual(rtnval, self)

    def test_get_vardata_attribute(self):
        '''Test get_vardata method with attribute'''
        func.logtest('Assert return from get_vardata method with attr:')
        mock_data = mock.Mock(netcdf_utils.Dataset)
        mock_data.variables = {'timevar': self}
        rtnval = netcdf_utils.get_vardata(mock_data, 'timevar',
                                          attribute='dummy')
        self.assertEqual(rtnval, 'myattribute')

    def test_get_vardata_fail(self):
        '''Test get_vardata method with failure'''
        func.logtest('Assert return from get_vardata method with failure:')
        mock_data = mock.Mock(netcdf_utils.Dataset)
        mock_data.variables = {}
        with self.assertRaises(SystemExit):
            _ = netcdf_utils.get_vardata(mock_data, 'timevar')
        self.assertIn('"timevar" not found in dataset', func.capture('err'))


class FixTimeTests(unittest.TestCase):
    '''Unit tests of functions used by fix_times'''
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_time_bounds_date_noleap(self):
        '''Test of the time_bounds_var_to_date method'''
        func.logtest('Assert correct return from time_bounds_var_to_date:')
        with mock.patch('netcdf_utils.get_dataset') as mock_data:
            mock_data().__enter__().variables[''].units = \
                'seconds since 1950-01-01 00:00:00'
            mock_data().__enter__().variables[''].calendar = 'NoLeap'
            mock_data().__enter__().variables[''].__getitem__.side_effect = \
                [numpy.array([0., 86400])]
            date = netcdf_utils.time_bounds_var_to_date('fname', 'timevar')
            # assertEqual doesn't work for dates so test string representation
            try:
                # NCDF_time_module.__version__ >= 1.4.1
                rtnval = str([NCDF_time_module._cftime.DatetimeNoLeap
                              (1950, 1, 1, 0, 0, 0, 0, 6, 1),
                              NCDF_time_module._cftime.DatetimeNoLeap
                              (1950, 1, 2, 0, 0, 0, 0, 0, 2)])
            except AttributeError:
                # Prior to introduction of NCDF_time_module._NCDF_time_module
                # attribute
                rtnval = '[1950-01-01 00:00:00, 1950-01-02 00:00:00]'
            self.assertEqual(date.__repr__(), rtnval)

    def test_time_bounds_date_gregorian(self):
        '''Test of the time_bounds_var_to_date method with gregorian calendar'''
        func.logtest('Assert correct calls in periodset method:')
        with mock.patch('netcdf_utils.get_dataset') as mock_data:
            mock_data().__enter__().variables[''].units = \
                'seconds since 1950-01-01 00:00:00'
            mock_data().__enter__().variables[''].calendar = 'gregorian'
            mock_data().__enter__().variables[''].bounds = 'time_counter_bounds'
            mock_data().__enter__().variables[''].__getitem__.side_effect = \
                [numpy.array([0., 86400])]
            bounds = netcdf_utils.time_bounds_var_to_date('fname', 'timevar')
            self.assertListEqual(
                [bounds[0].year, bounds[0].month, bounds[0].day],
                [1950, 1, 1]
            )
            self.assertListEqual(
                [bounds[-1].year, bounds[-1].month, bounds[-1].day],
                [1950, 1, 2]
            )

    def test_first_and_last(self):
        '''Test of results from first_and_last_dates'''
        func.logtest('Assert correct return from first_and_last_dates:')
        dates = [NCDF_time_module.datetime(2000, 1, 1),
                 NCDF_time_module.datetime(2000, 2, 1),
                 NCDF_time_module.datetime(1999, 3, 1),
                 NCDF_time_module.datetime(1999, 4, 1)]
        values = netcdf_utils.first_and_last_dates(
            dates, 'seconds since 2000-01-01 00:00:00', '360_day')
        self.assertEqual(values[0], -25920000.)
        self.assertEqual(values[1], 2592000.)

    def test_fix_times_calls_gregorian(self):
        '''Test of error handling if variable doesn't exist in mean file'''
        func.logtest('Assert correct_time called correctly:')
        with mock.patch('netcdf_utils.Dataset') as mock_dataset:
            mock_dataset().variables[''].units = \
                'seconds since 1950-01-01 00:00:00'
            mock_dataset().variables[''].calendar = 'gregorian'
            with mock.patch('netcdf_utils.correct_time') as mock_time:
                with mock.patch('netcdf_utils.correct_bounds'):
                    netcdf_utils.fix_times('meanset', 'meanfile',
                                           'time_counter',
                                           'time_counter_bounds')
                mock_time.assert_called_with(
                    'meanset', 'time_counter',
                    'seconds since 1950-01-01 00:00:00',
                    'gregorian')

    def test_fix_times_calls_noleap(self):
        '''Test call to fix_times with the 365cal'''
        func.logtest('Assert correct_time called correctly (365cal):')
        with mock.patch('netcdf_utils.Dataset') as mock_dataset:
            mock_dataset().variables[''].units = \
                'seconds since 1950-01-01 00:00:00'
            mock_dataset().variables[''].calendar = 'NoLeap'
            with mock.patch('netcdf_utils.correct_time') as mock_time:
                with mock.patch('netcdf_utils.correct_bounds'):
                    netcdf_utils.fix_times('meanset', 'meanfile',
                                           'time_counter',
                                           'time_counter_bounds')
                mock_time.assert_called_with(
                    'meanset', 'time_counter',
                    'seconds since 1950-01-01 00:00:00',
                    'noleap')
