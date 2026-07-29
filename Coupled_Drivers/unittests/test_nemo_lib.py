#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    test_nemo_lib.py

DESCRIPTION
    Test the non 'namelist' functions in the NEMO library
'''

import unittest
import unittest.mock as mock

import dr_env_lib.nemo_def
import nemo_lib
import error


class TestSetupDates(unittest.TestCase):
    '''
    Test the setting up of dates for NEMO model run
    '''
    def setUp(self):
        '''
        Set up common_env dictionary containing model basis, run start,
        run length. Calendar type to be added later
        '''
        self.common_env = {'MODELBASIS': '2020,12,12,0,0,0',
                           'TASKSTART': '2021,01,02,0,0,0',
                           'TASKLENGTH': '3,4,5,0,0,0'}
        # return values
        self.basisls = [2020, 12, 12, 0, 0, 0]
        self.startls = [2021, 1, 2, 0, 0, 0]
        self.lenls = [3, 4, 5, 0, 0, 0]

    @mock.patch('nemo_lib.sys.stderr.write')
    def test_setup_dates_invalid_calendar(self, mock_stderr):
        '''Test failure if calendar is invalid'''
        common_env = {'CALENDAR': 'invalid_calendar'}
        with self.assertRaises(SystemExit) as context:
            nemo_lib.setup_dates(common_env)
        self.assertEqual(context.exception.code, error.INVALID_EVAR_ERROR)
        mock_stderr.assert_called_once_with(
            '[FAIL] Calendar type %s not recognised\n' % common_env['CALENDAR'])

    @mock.patch('nemo_lib.inc_days.inc_days', return_value='rundays')
    def test_setup_dates_gregorian(self, mock_inc_days):
        '''Test correct behaviour for gregorian calendar'''
        common_env = {**{'CALENDAR': 'gregorian'}, **self.common_env}
        expected_return = (1, self.basisls, self.startls, self.lenls, 'rundays')
        self.assertEqual(expected_return, nemo_lib.setup_dates(common_env))
        mock_inc_days.assert_called_once_with(2021, 1, 2, 3, 4, 5, 'gregorian')

    @mock.patch('nemo_lib.inc_days.inc_days', return_value='rundays')
    def test_setup_dates_360d(self, mock_inc_days):
        '''Test correct behaviour for 360 day calendar'''
        common_env = {**{'CALENDAR': '360day'}, **self.common_env}
        expected_return = (30, self.basisls, self.startls,
                           self.lenls, 'rundays')
        self.assertEqual(expected_return, nemo_lib.setup_dates(common_env))
        mock_inc_days.assert_called_once_with(2021, 1, 2, 3, 4, 5, '360')

    @mock.patch('nemo_lib.inc_days.inc_days', return_value='rundays')
    def test_setup_dates_365d(self, mock_inc_days):
        '''Test correct behaviour for 365 day calendar'''
        common_env = {**{'CALENDAR': '365day'}, **self.common_env}
        expected_return = (0, self.basisls, self.startls,
                           self.lenls, 'rundays')
        self.assertEqual(expected_return, nemo_lib.setup_dates(common_env))
        mock_inc_days.assert_called_once_with(2021, 1, 2, 3, 4, 5, '365')




class TestSetupNemoRunlen(unittest.TestCase):
    '''
    Test the setting up of NEMO runlength for climate and coupled nwp style
    cycling
    '''
    def test_setup_nemo_runlen_climate_cycling(self):
        '''Test the correct behaviour when CONTINUE_FROM_FAIL is false'''
        common_env = {'CONTINUE_FROM_FAIL': 'false'}
        run_days = 1
        run_length = [None, None, None, 1, 1, 1]
        nemo_step_int = 1200.
        nemo_last_step = 2232
        self.assertEqual(2307,
                         nemo_lib.setup_nemo_runlen(
                             common_env, None, None, nemo_step_int, run_days,
                             run_length, None, nemo_last_step))

    def test_setup_nemo_runlen_cnwp_cycling(self):
        '''Test the correct behaviour when CONTINUE_FROM_FAIL is true
        and the warning is not called'''
        common_env = {'CONTINUE_FROM_FAIL': 'true',
                      'LAST_DUMP_HOURS': '2'}
        run_start = [2020, 1, 1, 1, 0, 0]
        model_basis = [2019, 11, 1, 0, 0, 0]
        nemo_step_int = 1200.
        run_days = 1
        run_length = [None, None, None, 1, 1, 1]
        nemo_next_step = 4402
        self.assertEqual(4470,
                         nemo_lib.setup_nemo_runlen(
                             common_env, run_start, model_basis, nemo_step_int,
                             run_days, run_length, nemo_next_step, None))

    @mock.patch('nemo_lib.sys.stderr.write')
    def test_setup_nemo_runlen_cnwp_cycling_failure(self, mock_stderr):
        '''Test the correct behaviour when CONTINUE_FROM_FAIL is true and the
        warning is called'''
        common_env = {'CONTINUE_FROM_FAIL': 'true',
                      'LAST_DUMP_HOURS': '2'}
        run_start = [2020, 1, 1, 1, 0, 0]
        model_basis = [2019, 11, 1, 0, 0, 0]
        nemo_step_int = 1200.
        run_days = 1
        run_length = [None, None, None, 1, 1, 1]
        nemo_next_step = 4401
        with self.assertRaises(SystemExit) as context:
            nemo_lib.setup_nemo_runlen(
                common_env, run_start, model_basis, nemo_step_int,
                run_days, run_length, nemo_next_step, None)
        self.assertEqual(context.exception.code, error.RESTART_FILE_ERROR)
        mock_stderr.assert_called_once_with(
            '[FAIL] Last NEMO restarts not at correct time\n'
            ' Last completed timestep 4401\n'
            ' Expected next step 4402\n'
            ' Actual next step 4401\n')
