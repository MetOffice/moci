'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2022 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    test_nemo_driver.py

DESCRIPTION
    Contains unit tests for the nemo_driver.py module.
'''
import unittest
import unittest.mock as mock
import datetime
import io
import os
import pathlib
import shutil
import cf_units

import nemo_driver

TEMPDIR = os.getenv('TMPDIR')


class TestCalcModelDate(unittest.TestCase):
    """Unit tests for the _calc_current_model_date function."""
    def setUp(self):
        self.calendar = 'gregorian'
        self.model_step_start = datetime.datetime(1993, 11, 1)

        # NEMO timestep in seconds
        self.nemo_step_int = 1200

        # Timestep number at the end of a model step. Corresponds
        # to a 15-day run.
        self.nemo_last_step = 1080

    def test_model_date(self):
        """Check that the correct restart date is returned for a
        Gregorian calendar."""
        expected_restart_date = datetime.datetime(1993, 11, 16)

        self.assertEqual(
            expected_restart_date,
            nemo_driver._calc_current_model_date(
                self.model_step_start, self.nemo_step_int,
                self.nemo_last_step, self.calendar)
            )

    def test_model_date_new_year(self):
        """Check that the correct date is returned when crossing the
        new-year boundary."""
        model_step_start = datetime.datetime(1993, 12, 17)
        expected_restart_date = datetime.datetime(1994, 1, 1)

        self.assertEqual(
            expected_restart_date,
            nemo_driver._calc_current_model_date(
                model_step_start, self.nemo_step_int,
                self.nemo_last_step, self.calendar)
            )

    def test_model_date_leap_year(self):
        """Check that the correct restart date is returned for a
        February date during a leap year."""
        expected_restart_date = datetime.datetime(2016, 2, 29)
        model_step_start = datetime.datetime(2016, 2, 14)

        self.assertEqual(
            expected_restart_date,
            nemo_driver._calc_current_model_date(
                model_step_start, self.nemo_step_int,
                self.nemo_last_step, self.calendar)
            )

    def test_model_date_360day(self):
        """Check that the correct date is returned for a 360-day calendar."""
        expected_restart_date = cf_units.cftime.Datetime360Day(2016, 2, 30)
        model_step_start = datetime.datetime(2016, 2, 15)
        calendar = '360day'

        self.assertEqual(
            expected_restart_date,
            nemo_driver._calc_current_model_date(
                model_step_start, self.nemo_step_int,
                self.nemo_last_step, calendar)
            )

    def test_model_date_365day(self):
        """Check that the correct date is returned for a 365 day calendar"""
        expected_restart_date = cf_units.cftime.DatetimeNoLeap(1993, 11, 16)
        calendar = '365day'
        
        self.assertEqual(
            expected_restart_date,
            nemo_driver._calc_current_model_date(
                self.model_step_start, self.nemo_step_int,
                self.nemo_last_step, calendar)
            )


class TestVerifyFixRestart(unittest.TestCase):
    """Unit tests for the _verify_fix_restart function"""
    def setUp(self):
        self.calendar = 'gregorian'
        self.nemo_step_int = 1200
        self.nemo_last_step = 1080
        self.model_step_start = '19931101'
        self.model_restart_date = '19931116'
        self.nemo_rst = os.path.join(TEMPDIR, 'restarts')

        # Create some dummy ocean and iceberg restart data to check
        # that function behaves as expected if the restart date model
        # step end date do not match.
        self.restarts = [
            f'cplhco_{restart_type}{date}_restart_0050.nc'
            for restart_type in ['icebergs_', '']
            for date in ['19931116', '19931201', '19931216']
            ]

        for restart in self.restarts:
            if not os.path.isdir(self.nemo_rst):
                os.mkdir(self.nemo_rst)

            pathlib.Path(os.path.join(self.nemo_rst, restart)).touch()

    def tearDown(self):
        shutil.rmtree(self.nemo_rst)

    def test_verify_fix_rst_success(self):
        """Check that the function behaves correctly when the restart
        date and model step end date match."""
        restart_date = '19931116'
        expected_msg = '[INFO] Validated NEMO restart date\n'

        with mock.patch('sys.stdout', new=io.StringIO()) as output:
            corrected_restart_date = nemo_driver._verify_fix_rst(
                restart_date, self.nemo_rst, self.model_step_start,
                self.nemo_step_int, self.nemo_last_step, self.calendar)

        self.assertEqual(output.getvalue(), expected_msg)
        self.assertEqual(self.model_restart_date, corrected_restart_date)

    def test_verify_fix_rst_fail(self):
        """Check that the function correctly throws a warning if there is
        a mismatch between the restart date and the model date, and that
        restart files are removed as required."""
        restart_date = '19931201'

        expected_msg = '[WARN] The NEMO restart data does not match the ' \
            ' current model time\n.' \
            '   Current model date is %s\n' \
            '   NEMO restart time is %s\n' \
            '[WARN] Automatically removing NEMO dumps ahead of ' \
            'the current model date, and pick up the dump at ' \
            'this time\n' % (self.model_restart_date, restart_date)

        expected_files = [
            'cplhco_19931116_restart_0050.nc',
            'cplhco_icebergs_19931116_restart_0050.nc'
            ]

        with mock.patch('sys.stdout', new=io.StringIO()) as output:
            corrected_restart_date = nemo_driver._verify_fix_rst(
                restart_date, self.nemo_rst, self.model_step_start,
                self.nemo_step_int, self.nemo_last_step, self.calendar)

        self.assertEqual(output.getvalue(), expected_msg)
        self.assertEqual(self.model_restart_date, corrected_restart_date)

        # Check that any restarts whose dates are after the model step
        # end date have been removed.
        file_list = os.listdir(self.nemo_rst)
        self.assertCountEqual(file_list, expected_files)
