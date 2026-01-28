#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2023-2026 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''

import unittest
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
    import mock

import io
import os
import cpmip_utils

class TestGetComponentResolution(unittest.TestCase):
    '''
    Test the construction of component resolution from namelist
    '''
    @mock.patch('cpmip_utils.common.exec_subproc')
    def test_get_component_resolution(self, mock_subproc):
        '''
        Test construction of total resolution
        '''
        res_vars = ('i_dim', 'j_dim', 'k_dim')
        subproc_return_values = [(0, 'i_dim=10'),
                                 (0, 'j_dim=20'),
                                 (0, 'k_dim=30')]
        mock_subproc.side_effect = subproc_return_values
        self.assertEqual(cpmip_utils.get_component_resolution('NEMO_NL',
                                                              res_vars),
                         6000)
        subproc_calls = []
        for res_var in res_vars:
            subproc_calls.append(mock.call(['grep', res_var, 'NEMO_NL'],
                                           verbose=True))
        mock_subproc.assert_has_calls(subproc_calls)


class TestGlobUsage(unittest.TestCase):
    '''
    Test the determination of disk usage using globs
    '''
    @mock.patch('cpmip_utils.glob.glob', return_value=[])
    def test_get_glob_usage_nofile(self, mock_glob):
        '''
        Test glob usage if there are no files
        '''
        expected_output = '[WARN] Attepting to find the size of files' \
                          ' described by glob expression a*b*. There are' \
                          ' no files found'
        with mock.patch('sys.stderr', new=io.StringIO()) as patch_output:
            dusize = cpmip_utils.get_glob_usage('a*b*')
            self.assertEqual(dusize, 0.0)
            self.assertEqual(patch_output.getvalue(), expected_output)

    @mock.patch('cpmip_utils.glob.glob', return_value=['file1', 'file2'])
    @mock.patch('cpmip_utils.common.exec_subproc_timeout',
                return_value=(0, '\n128 file1\n128 file2\n256 total\n'))
    def test_get_glob_usage(self, mock_subproc, mock_glob):
        '''
        Test file size from glob
        '''
        self.assertEqual(cpmip_utils.get_glob_usage('a*b*'),
                         256.0)

class TestNCDFOutput(unittest.TestCase):
    '''
    Test measurment of NCDF file sizes
    '''
    @mock.patch('cpmip_utils.os.listdir', return_value=[])
    @mock.patch('cpmip_utils.common.exec_subproc_timeout',
                return_value=(1, None))
    def test_no_files_output(self, mock_subproc, mock_ncdffiles):
        '''
        Test what happens if we cant find any files
        '''
        self.assertEqual(cpmip_utils.get_workdir_netcdf_output(), -1.0)

    @mock.patch('cpmip_utils.os.listdir', return_value=['file1.nc',
                                                        'file2.nc'])
    @mock.patch('cpmip_utils.common.exec_subproc_timeout',
                return_value=(0, '\n128 file1.nc\n128 file2.nc\n256 total\n'))
    def test_files_output(self, mock_subproc, mock_ncdffiles):
        '''
        Check to see if the function can get the correct total value
        '''
        self.assertEqual(cpmip_utils.get_workdir_netcdf_output(), 256.0)


class TestTimeFunctions(unittest.TestCase):
    '''
    Test the time related functions
    '''
    def test_seconds_to_days_halfday(self):
        '''
        Test half a day of seconds
        '''
        self.assertEqual(cpmip_utils.seconds_to_days(43200.0), 0.5)

    def test_seconds_to_days_twodays(self):
        '''
        Test two full days of seconds
        '''
        self.assertEqual(cpmip_utils.seconds_to_days(172800.0), 2.0)

    def test_tasklength_to_years(self):
        '''
        Test tasklength to years, pass in all ones, to check everything
        '''
        self.assertEqual(cpmip_utils.tasklength_to_years(
            '0001,01,01,01,01,01'), 1.0362288130144035)

class TestPBSJobFileXc40Case(unittest.TestCase):
    '''
    Test the reading of an example PBS job file
    '''
    def setUp(self):
        '''
        Create an example jobfile
        '''
        self.jobfile_name = 'test_jobfile'
        example_input = '''
# DIRECTIVES:
#PBS -N coupled.19600101T0000Z.mi-ba962_compiler_upgrade_877
#PBS -o cylc-run/mi-ba962_compiler_upgrade_877/log/job/19600101T0000Z/coupled/01/job.out
#PBS -e cylc-run/mi-ba962_compiler_upgrade_877/log/job/19600101T0000Z/coupled/01/job.err
#PBS -l walltime=02:30:00
#PBS -W umask=0022
#PBS -l select=36:subproject=ukesmdev:funding=hccp:coretype=broadwell
#PBS -q high
# N.B. CYLC_DIR has been updated on the remote host
export CYLC_DIR='/common/fcm/cylc-7.8.6'
    '''
        with open(self.jobfile_name, 'w') as test_jobfile:
            test_jobfile.write(example_input)

    def tearDown(self):
        '''
        Remove the example job file at end of test
        '''
        try:
            os.remove(self.jobfile_name)
        except OSError:
            pass

    def test_jobfile(self):
        '''
        Test the retrival of the pbs -l directives is correct. As this is a
        double underscore function, we need to apply the name mangling rule
        '''
        expected_result = {'walltime': '02:30:00',
                           'select': '36',
                           'subproject': 'ukesmdev',
                           'funding': 'hccp',
                           'coretype': 'broadwell'}

        result = cpmip_utils.get_jobfile_info(self.jobfile_name)
        self.assertEqual(result, expected_result)


class TestPBSJobFileExCase(unittest.TestCase):
    '''
    Test the reading of an example PBS job file
    '''
    def setUp(self):
        '''
        Create example jobfiles
        '''
        # A fully fledged jobfile
        self.jobfile_name = 'test_jobfile'
        example_input = '''# DIRECTIVES:
#PBS -N coupled.19780901T0000Z.mi-bd155_add_cpmip_metrics
#PBS -o cylc-run/mi-bd155_add_cpmip_metrics/log/job/19780901T0000Z/coupled/01/job.out
#PBS -e cylc-run/mi-bd155_add_cpmip_metrics/log/job/19780901T0000Z/coupled/01/job.err
#PBS -l walltime=900
#PBS -q normal
#PBS -l select=2:ncpus=256:mpiprocs=90+5:ncpus=256:mpiprocs=120+1:ncpus=256:mpiprocs=6
# N.B. CYLC_DIR has been updated on the remote host
    '''
        with open(self.jobfile_name, 'w') as test_jobfile:
            test_jobfile.write(example_input)

        # A jobfile with one model
        self.onemodel_jobfile_name = 'test_onemodel_jobfile'
        example_input='''#PBS -l select=24:ncpus=256'''
        with open(self.onemodel_jobfile_name, 'w') as test_jobfile:
            test_jobfile.write(example_input)

    def tearDown(self):
        '''
        Remove the example job file at end of test
        '''
        jobfiles = (self.jobfile_name, self.onemodel_jobfile_name)
        for jobfile in jobfiles:
            try:
                os.remove(jobfile)
            except OSError:
                pass

    def test_jobfile(self):
        '''
        Test the retrival of the pbs -l select directive for nodes for each
        model in MPMD mode is correct
        '''
        expected_result = ([2, 5, 1], 'milan')
        result = cpmip_utils.get_select_nodes(self.jobfile_name)
        self.assertEqual(result, expected_result)

    def test_jobfile_one_model(self):
        '''
        Test the correct retrieval for a single model in the -l select directive
        '''
        expected_result = ([24], 'milan')
        result = cpmip_utils.get_select_nodes(self.onemodel_jobfile_name)
        self.assertEqual(result, expected_result)

class TestIncrementDump(unittest.TestCase):
    '''
    Test the increment of the dump date to the end of cycle
    '''
    def test_one_day_increment(self):
        '''
        Test increment of one day
        '''
        self.assertEqual(cpmip_utils.increment_dump('20200115', 1, 'd'),
                         '20200116')

    def test_thirty_five_day_increment(self):
        '''
        Test increment of 35 days, to ensure that the month rolls over
        '''
        self.assertEqual(cpmip_utils.increment_dump('20200101', 35, 'd'),
                         '20200206')

    def test_one_month_increment(self):
        '''
        Test increment of one month - from not the first of the month testing
        a month rollover
        '''
        self.assertEqual(cpmip_utils.increment_dump('20200115', 1, 'm'),
                         '20200215')

    def test_three_month_increment(self):
        '''
        Test increment of three months
        '''
        self.assertEqual(cpmip_utils.increment_dump('20200115', 3, 'M'),
                         '20200415')

    def test_thirteen_month_increment(self):
        '''
        Test increment of three months - testing a month and a year rollover
        '''
        self.assertEqual(cpmip_utils.increment_dump('20200115', 13, 'M'),
                         '20210215')
