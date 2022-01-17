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
    test_um_driver.py

DESCRIPTION
    Contains unit tests for the um_driver.py module.
'''
import unittest
import unittest.mock as mock
import datetime
import os
import io
import shutil
import cf_units

import um_driver
import error

TEMPDIR = os.getenv('TMPDIR')


class TestExpandNamelist(unittest.TestCase):
    """Unit tests for the _expand_fortran_namelists function."""
    def test_expands_pattern(self):
        """Test whether entries are expanded as expected."""
        collapsed_text = "variable=5*0.9"
        expected_text = "variable=0.9, 0.9, 0.9, 0.9, 0.9"
        self.assertEqual(
            um_driver._expand_fortran_namelist(collapsed_text),
            expected_text
        )

    def test_no_pattern(self):
        """Test the correct text is returned when no extries to expand."""
        orig_text = "variable=0.9, 0.9"
        self.assertEqual(
            um_driver._expand_fortran_namelist(orig_text), orig_text
        )


class TestGrabFileInfo(unittest.TestCase):
    """Unit tests to check information is correctly retrieved from an
    input file."""
    def setUp(self):
        self.calendar = 'gregorian'
        self.cycle_date = '20190104T0000Z'
        self.task_name = 'gshc_model_m1_s02'
        self.workdir = os.path.join(TEMPDIR, self.task_name)
        self.task_param_run = '2'
        self.temp_hist_stub = 'temp_hist'
        self.prev_work_dir = os.path.join(TEMPDIR, 'gshc_model_m1_s01')
        self.history_archive = os.path.join(
            self.prev_work_dir, 'history_archive')
        self.xhist_arch = os.path.join(self.history_archive, 'temp_hist.0001')

        # Create a temporary xhist file with dummy entries
        self.xhist_content = (
            "CHECKPOINT_DUMP_IM = 'path/to/dump/cplfca.da20190317_00'\n"
            "MODEL_DATA_TIME = 2019,  1,  4,  3*0,\n"
            "H_STEPIM = 6912,"
            )

        if not os.path.exists(self.prev_work_dir):
            os.makedirs(self.prev_work_dir)

        if not os.path.exists(self.history_archive):
            os.makedirs(self.history_archive)

        self.xhist = os.path.join(TEMPDIR, 'cplfca.xhist')
        with open(self.xhist, 'w') as handle:
            handle.write(self.xhist_content)

        # Create a dummy ATMOSCNTL namelist file
        self.nml_content = (
            "steps_per_periodim=96,\n"
            "secs_per_periodim=86400,"
            )

        self.atmoscntl = os.path.join(self.prev_work_dir, 'ATMOSCNTL')
        with open(self.atmoscntl, 'w') as handle:
            handle.write(self.nml_content)

    def tearDown(self):
        os.remove(self.xhist)
        shutil.rmtree(self.prev_work_dir)

    def test_grab_xhist_date(self):
        """Check that the UM checkpoint dump date is correctly retrieved."""
        self.assertEqual(
            um_driver._grab_xhist_date(self.xhist),
            '20190317'
            )

    def test_grab_xhist_start_date(self):
        """Check that the model start date is correctly retrieved."""
        self.assertEqual(
            um_driver._grab_xhist_start_date(self.xhist),
            datetime.datetime(2019, 1, 4)
            )

    def test_grab_xhist_completed_steps(self):
        """Check that the number of completed UM steps is correctly
        retrieved."""
        self.assertEqual(
            um_driver._grab_xhist_completed_steps(self.xhist),
            6912
            )

    def test_no_pattern_found(self):
        """Check that an error is raised if a pattern cannot be found in
        a file."""
        pattern = r"NOT_A_PATTERN\s*=\s*'\S*da(\d{7})"
        expected_err = "Pattern %s not found in file %s" % (
            pattern, self.xhist)

        with mock.patch('sys.stderr', new=io.StringIO()) as output:
            with self.assertRaises(SystemExit) as context:
                um_driver._grab_file_info(self.xhist, pattern)

        self.assertEqual(context.exception.code, error.IOERROR)
        self.assertEqual(output.getvalue(), expected_err)

    def test_grab_atmos_timestep_info(self):
        """Check that the model time-step information from the ATMOSCNTL
        namelist file is correctly retrieved."""
        expected_values = (96, 86400)

        self.assertEqual(
            expected_values,
            um_driver._grab_atmos_timestep_info(self.atmoscntl)
            )

    def test_calc_current_model_date(self):
        """Check that the current UM model step date is returned for a
        Gregorian calendar."""
        expected_value = datetime.datetime(2019, 3, 17)

        self.assertEqual(
            expected_value,
            um_driver._calc_current_model_date(
                self.xhist, self.calendar, self.prev_work_dir)
            )

    def test_calc_current_model_date_360day(self):
        """Check that the current UM model step date is returned for a
        360-day calendar."""
        expected_value = cf_units.cftime.Datetime360Day(2019, 3, 16)
        calendar = '360day'

        self.assertEqual(
            expected_value,
            um_driver._calc_current_model_date(
                self.xhist, calendar, self.prev_work_dir)
            )

    def test_calc_current_model_date_365day(self):
        """Check that the current UM model step date is returned for a
        365-day calendar."""
        expected_value = cf_units.cftime.DatetimeNoLeap(2019, 3, 17)
        calendar = '365day'

        self.assertEqual(
            expected_value,
            um_driver._calc_current_model_date(
                self.xhist, calendar, self.prev_work_dir)
            )

    def test_verify_rst_fix_dates_match(self):
        """Check that the function correctly validates the dump if the dump
        date and model progress match.

        """
        expected_msg = '[INFO] Validated UM restart date\n'

        with mock.patch('sys.stdout', new=io.StringIO()) as output:
            um_driver.verify_fix_rst(
                self.xhist, self.cycle_date, self.workdir,
                self.task_name, self.temp_hist_stub, self.calendar,
                self.task_param_run)

        self.assertEqual(output.getvalue(), expected_msg)

    def test_verify_rst_fix_dates_no_match(self):
        """Check that an error is returned if the model progress and dump
        dates don't match."""
        expected_mismatch_msg = (
            '[WARN] The UM restart data does not match the '
            ' current model time\n.'
            ' Current model date is 20190302\n'
            ' UM restart time is 20190317\n')

        expected_fix_msg = (
            '[WARN] Automatically attempting to fix UM'
            ' restart data, by using the xhist file:\n'
            '    {xhist_archived}\n'
            ' from the previous cycle\n'.format(xhist_archived=self.xhist_arch))

        # Create a atmosphere control namelist file whose time-step information
        # doesn't match the dump date.
        nml_content = (
            "steps_per_periodim=120,\n"
            "secs_per_periodim=86400,"
            )

        wrong_atmoscntl = os.path.join(self.prev_work_dir, 'ATMOSCNTL')
        with open(wrong_atmoscntl, 'w') as handle:
            handle.write(nml_content)

        # Create an archived xhist file, whose information matches the expected
        # model progress.
        xhist_content = (
            "CHECKPOINT_DUMP_IM = 'path/to/dump/cplfca.da20190302_00'\n"
            "MODEL_DATA_TIME = 2019,  1,  4,  3*0,\n"
            "H_STEPIM = 6912,"
            )

        with open(self.xhist_arch, 'w') as handle:
            handle.write(xhist_content)

        with mock.patch('sys.stdout', new=io.StringIO()) as output:
            um_driver.verify_fix_rst(
                self.xhist, self.cycle_date, self.workdir,
                self.task_name, self.temp_hist_stub, self.calendar,
                self.task_param_run)

        self.assertTrue(expected_mismatch_msg in output.getvalue())
        self.assertTrue(expected_fix_msg in output.getvalue())
