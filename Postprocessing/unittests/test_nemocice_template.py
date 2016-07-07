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
import os
import mock
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'common'))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'nemocice'))

import runtime_environment
runtime_environment.setup_env()
import testing_functions as func

import modeltemplate


class PeriodTests(unittest.TestCase):
    '''Unit tests relating to the "get period files" methods'''

    def setUp(self):
        with mock.patch('nlist.loadNamelist'):
            with mock.patch('suite.SuiteEnvironment'):
                self.model = modeltemplate.ModelTemplate()
        self.inputs = modeltemplate.RegexArgs(period=modeltemplate.RR,
                                              field='FIELD')
        self.model.nl.restart_directory = os.getcwd()

    def tearDown(self):
        pass

    def test_periodset(self):
        '''Test function of the periodset method'''
        func.logtest('Assert pattern produced by periodset method:')
        with mock.patch('modeltemplate.ModelTemplate.set_stencil') as mock_set:
            mock_set['PERIOD'].__get__ = \
                lambda y, m, s, f: '^yr{}_mth_{}ssn{}_field{}.nc$'.format(
                    y, m, s, f)
            with mock.patch('utils.get_subset') as mock_subset:
                self.model.periodset(self.inputs)
            mock_set['PERIOD'].assert_called_with(self.inputs.date[0],
                                                  self.inputs.date[1],
                                                  None,
                                                  'FIELD')
            mock_subset.assert_called_with(os.getcwd(),
                                           mock_set.__getitem__()())

    def test_periodset_datadir(self):
        '''Test function of the periodset method with datadir'''
        func.logtest('Assert periodset method pattern with datadir:')
        with mock.patch('modeltemplate.ModelTemplate.set_stencil') as mock_set:
            mock_set['PERIOD'].__get__ = \
                lambda y, m, s, f: '^yr{}_mth_{}ssn{}_field{}.nc$'.format(
                    y, m, s, f)
            with mock.patch('utils.get_subset') as mock_subset:
                self.model.periodset(self.inputs, datadir='TestDir')
            mock_subset.assert_called_with('TestDir', mock_set.__getitem__()())

    def test_periodset_arch_annual(self):
        '''Test function of the periodset method for annual archive'''
        func.logtest('Assert periodset method pattern for annual archive:')
        self.inputs.period = 'Annual'
        with mock.patch('modeltemplate.ModelTemplate.mean_stencil') as \
                mock_mean:
            mock_mean['PERIOD'].__get__ = \
                lambda y, m, s, f: '^yr{}_mth_{}ssn{}_field{}.nc$'.format(
                    y, m, s, f)
            with mock.patch('utils.get_subset'):
                self.model.periodset(self.inputs, archive=True)
            mock_mean['PERIOD'].assert_called_with('.*', '.*', '.*', 'FIELD')

    def test_periodend(self):
        '''Test function of the periodend method'''
        func.logtest('Assert pattern produced by periodend method:')
        with mock.patch('modeltemplate.ModelTemplate.end_stencil') as mock_end:
            mock_end['PERIOD'].__get__ = \
                lambda y, m, s, f: r'^season{}_field{}\.nc$'.format(s, f)
            with mock.patch('utils.get_subset') as mock_subset:
                self.model.periodend(self.inputs)
            mock_end['PERIOD'].assert_called_with(None, 'FIELD')
            mock_subset.assert_called_with(os.getcwd(),
                                           mock_end.__getitem__()())

    def test_periodend_datadir(self):
        '''Test function of the periodend method with datadir'''
        func.logtest('Assert periodend method pattern with datadir:')
        with mock.patch('modeltemplate.ModelTemplate.end_stencil') as mock_end:
            mock_end['PERIOD'].__get__ = \
                lambda y, m, s, f: r'^season{}_field{}\.nc$'.format(s, f)
            with mock.patch('utils.get_subset') as mock_subset:
                self.model.periodend(self.inputs, datadir='TestDir')
            mock_end['PERIOD'].assert_called_with(None, 'FIELD')
            mock_subset.assert_called_with('TestDir', mock_end.__getitem__()())

    def test_periodend_arch_annual(self):
        '''Test function of the periodend method for annual archive'''
        func.logtest('Assert periodend method pattern for annual archive:')
        self.inputs.period = 'Annual'
        rtnval = self.model.periodend(self.inputs, archive=True)
        self.assertEqual(rtnval, [None, ])


class MeansTests(unittest.TestCase):
    '''Unit tests relating to creation of means'''

    def setUp(self):
        with mock.patch('nlist.loadNamelist'):
            with mock.patch('suite.SuiteEnvironment'):
                self.model = modeltemplate.ModelTemplate()
        self.model.suite.envars.CYLC_SUITE_INITIAL_CYCLE_POINT = \
            '19950821T0000Z'
        self.model.nl.debug = False
        self.model.nl.restart_directory = os.getcwd()
        self.model.nl.base_component = '10d'

        self.model.move_to_share = mock.Mock()
        self.model.loop_inputs = mock.Mock()
        self.model.loop_inputs.return_value = \
            [modeltemplate.RegexArgs(period='Annual')]
        self.model.periodend = mock.Mock()
        self.model.periodend.return_value = ['setend']
        self.model.get_date = mock.Mock()
        self.model.get_date.return_value = ('1996', '09', '01')
        self.model.periodset = mock.Mock()
        self.model.periodset.return_value = ['file1', 'file2',
                                             'file3', 'file4']
        self.model.meantemplate = mock.Mock()
        self.model.meantemplate.return_value = 'meanfilename'
        self.model.fix_mean_time = mock.Mock()

    def tearDown(self):
        try:
            os.remove('nemocicepp.nl')
        except OSError:
            pass

    @mock.patch('os.path')
    @mock.patch('utils.exec_subproc')
    def test_create_annual_mean(self, mock_exec, mock_path):
        '''Test successful creation of annual mean'''
        func.logtest('Assert successful creation of annual mean:')
        mock_exec.return_value = (0, '')
        mock_path.return_value = True
        self.model.create_means()
        self.assertIn('Created .* Annual mean for 1996', func.capture())

    @mock.patch('utils.remove_files')
    @mock.patch('os.path')
    @mock.patch('utils.exec_subproc')
    def test_create_monthly_mean_10d(self, mock_exec, mock_path, mock_rm):
        '''Test successful creation of monthly mean - 10day base'''
        func.logtest('Assert successful creation of monthly mean - 10d base:')
        self.model.loop_inputs.return_value = \
            [modeltemplate.RegexArgs(period='Monthly')]
        self.model.periodset.return_value = ['file1', 'file2', 'file3']
        mock_exec.return_value = (0, '')
        mock_path.return_value = True

        self.model.create_means()
        self.assertIn('Created .* Monthly mean for', func.capture())
        mock_rm.assert_called_with(self.model.periodset.return_value,
                                   path=os.getcwd())

    @mock.patch('utils.remove_files')
    @mock.patch('os.path')
    @mock.patch('utils.exec_subproc')
    def test_create_monthly_mean_5dbase(self, mock_exec, mock_path, mock_rm):
        '''Test successful creation of monthly mean - 5day base'''
        func.logtest('Assert successful creation of monthly mean - 5d base:')
        self.model.loop_inputs.return_value = \
            [modeltemplate.RegexArgs(period='Monthly')]
        self.model.nl.base_component = '5d'
        self.model.periodset.return_value = ['file1', 'file2', 'file3',
                                             'file4', 'file5', 'file6',]
        mock_exec.return_value = (0, '')
        mock_path.return_value = True

        self.model.create_means()
        self.assertIn('Created .* Monthly mean for', func.capture())
        mock_rm.assert_called_with(self.model.periodset.return_value,
                                   path=os.getcwd())

    @mock.patch('os.path')
    @mock.patch('utils.exec_subproc')
    def test_create_annual_mean_fail(self, mock_exec, mock_path):
        '''Test failed creation of annual mean'''
        func.logtest('Assert failed creation of annual mean:')
        mock_exec.return_value = (99, '')
        mock_path.return_value = True
        with self.assertRaises(SystemExit):
            self.model.create_means()
        self.assertIn('Error=99', func.capture('err'))

        self.model.nl.debug = True
        self.model.create_means()
        self.assertIn('Error=99', func.capture('err'))

    def test_create_means_partial(self):
        '''Test create_means function with partial period'''
        func.logtest('Assert create_means functionality with partial period:')
        self.model.periodset.return_value = ['file1', 'file2', 'file3']

        with self.assertRaises(SystemExit):
            self.model.create_means()
        self.assertIn('not possible as only got 3', func.capture('err'))

        self.model.nl.debug = True
        self.model.create_means()
        self.assertIn('not possible as only got 3', func.capture('err'))
        self.assertIn('[DEBUG]  Ignoring failed', func.capture())

    def test_create_means_spinup(self):
        '''Test create_means function in spinup mode'''
        func.logtest('Assert create_means functionality in spinup:')
        self.model.periodset.return_value = ['file1', 'file2', 'file3']
        self.model.get_date.return_value = ('1995', '09', '01')

        self.model.create_means()
        self.assertIn('in spinup mode', func.capture())
        self.assertIn('not possible as only got 3', func.capture())

    def test_annual_mean_spinup(self):
        '''Test Spinup period for annual means'''
        func.logtest('Assert initial spinup period for annual means:')

        self.assertTrue(self.model.means_spinup(
            'FIELD Annual mean for YYYY', ('1995', '12', '01')))
        self.assertFalse(self.model.means_spinup(
            'FIELD Annual mean for YYYY', ('1996', '12', '01')))

    def test_seasonal_mean_spinup(self):
        '''Test Spinup period for seasonal means'''
        func.logtest('Assert initial spinup period for seasonal means:')

        self.assertTrue(self.model.means_spinup(
            'FIELD Seasonal mean for SEASON YYYY', ('1995', '09', '01')))

        self.model.suite.envars.CYLC_SUITE_INITIAL_CYCLE_POINT = \
            '19950601T0000Z'
        self.assertFalse(self.model.means_spinup(
            'FIELD Seasonal mean for SEASON YYYY', ('1995', '09', '01')))
        self.assertFalse(self.model.means_spinup(
            'FIELD Seasonal mean for SEASON YYYY', ('1995', '12', '01')))

    def test_monthly_mean_spinup(self):
        '''Test Spinup period for monthly means'''
        func.logtest('Assert initial spinup period for monthly means:')

        self.assertTrue(self.model.means_spinup(
            'FIELD Monthly mean for MONTH YYYY', ('1995', '09', '01')))
        self.assertFalse(self.model.means_spinup(
            'FIELD Monthly mean for MONTH YYYY', ('1995', '10', '01')))

        self.model.suite.envars.CYLC_SUITE_INITIAL_CYCLE_POINT = \
            '19950901T0000Z'
        self.assertFalse(self.model.means_spinup(
            'FIELD Monthly mean for MONTH YYYY', ('1995', '10', '01')))

    def test_spinup_invalid(self):
        '''Test Spinup period for invalid means'''
        func.logtest('Assert initial spinup period for invalid means:')
        self.assertFalse(self.model.means_spinup(
            'FIELD INVALID mean for YYYY', ('1995', '10', '01')))
        self.assertIn('[WARN]', func.capture('err'))
        self.assertIn('unknown meantype', func.capture('err'))


class ArchiveTests(unittest.TestCase):
    '''Unit tests relating to archiving of files'''

    def setUp(self):
        with mock.patch('nlist.loadNamelist'):
            with mock.patch('suite.SuiteEnvironment'):
                self.model = modeltemplate.ModelTemplate()
        self.model.suite.envars.CYLC_SUITE_INITIAL_CYCLE_POINT = \
            '19950821T0000Z'
        self.model.nl.debug = False
        self.model.nl.restart_directory = os.getcwd()
        self.model.nl.buffer_archive = None
        self.model.nl.compression_level = 0

        self.model.suite = mock.Mock()
        self.model.suite.archive_file.return_value = 0
        self.model.loop_inputs = mock.Mock()
        self.model.loop_inputs.return_value = \
            [modeltemplate.RegexArgs(period='Annual')]
        self.model.periodend = mock.Mock()
        self.model.periodend.return_value = ['']
        self.model.periodset = mock.Mock()
        self.model.periodset.return_value = ['file1', 'file2']
        self.model.get_date = mock.Mock()
        self.model.get_date.return_value = ('1996', '05', '01')
        self.model.timestamps = mock.Mock()

    def tearDown(self):
        for fname in ['12h_field1', 'xd_field2']:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_buffer_archive(self):
        '''Test return of archive buffer property'''
        func.logtest('Assert return of archive buffer property:')
        self.assertEqual(self.model.buffer_archive, 0)
        self.model.nl.buffer_archive = 5
        self.assertEqual(self.model.buffer_archive, 5)

    def test_archive_means(self):
        '''Test archive means function'''
        func.logtest('Assert list of means to archive:')
        self.model.archive_files = mock.Mock()
        self.model.archive_files.return_value = {
            'file1': 'SUCCESS',
            'file2': 'SUCCESS'
            }
        with mock.patch('modeltemplate.ModelTemplate.additional_means',
                        new_callable=mock.PropertyMock, return_value=[]):
            with mock.patch('utils.remove_files') as mock_rm:
                self.model.archive_means()
                mock_rm.assert_called_with(['file1', 'file2'],
                                           os.getcwd())
        self.model.archive_files.assert_called_with(['file1', 'file2'])

    def test_archive_additional_means(self):
        '''Test archive additional means for archive'''
        func.logtest('Assert list of additional means to archive:')
        self.model.archive_files = mock.Mock()
        self.model.archive_files.return_value = {}
        self.model.periodset.return_value = []
        self.model.nl.means_to_archive = ['12h', '1d']
        self.model.nl.base_component = '10d'
        files = ['12h_field1', 'xd_field2']
        for fname in files:
            open(fname, 'w').close()

        with mock.patch('modeltemplate.ModelTemplate.mean_stencil',
                        new_callable=mock.PropertyMock,
                        return_value={'General': lambda y, m, s, f:
                                                 r'{}_{}'.format(y, f)}):
            with mock.patch('modeltemplate.ModelTemplate.fields',
                            new_callable=mock.PropertyMock,
                            return_value=('field1', 'field2')):
                self.model.archive_means()

        self.model.archive_files.assert_called_with(['12h_field1'])
        self.assertFalse(os.path.exists('12h_field1'))
        self.assertTrue(os.path.exists('xd_field2'))

    def test_archive_means_compress(self):
        '''Test archive means with compression'''
        func.logtest('Assert compression of archived means:')
        self.model.archive_files = mock.Mock()
        self.model.archive_files.return_value = {
            'file1': 'SUCCESS',
            'file2': 'SUCCESS'
            }
        self.model.nl.compression_level = 5
        self.model.compress_file = mock.Mock(return_value=0)
        with mock.patch('modeltemplate.ModelTemplate.additional_means',
                        new_callable=mock.PropertyMock, return_value=[]):
            with mock.patch('utils.remove_files') as mock_rm:
                self.model.archive_means()
                mock_rm.assert_called_with(['file1', 'file2'],
                                           os.getcwd())
        self.model.archive_files.assert_called_with(['file1', 'file2'])
        self.model.compress_file.assert_called_with(
            'file2', self.model.nl.compress_means)

    def test_archive_means_partial_fail(self):
        '''Test archive means function with partial failure'''
        func.logtest('Assert partially successful archive of file list:')
        self.model.archive_files = mock.Mock()
        self.model.archive_files.return_value = {
            'file1': 'SUCCESS',
            'file2': 'FAILED'
            }
        with mock.patch('modeltemplate.ModelTemplate.additional_means',
                        new_callable=mock.PropertyMock, return_value=[]):
            with mock.patch('utils.remove_files') as mock_rm:
                self.model.archive_means()
                self.assertEqual(len(mock_rm.mock_calls), 0)

    def test_no_means_to_archive(self):
        '''Test report with no means to archive'''
        func.logtest('Assert report with no means to archive:')
        self.model.periodset.return_value = []
        with mock.patch('modeltemplate.ModelTemplate.additional_means',
                        new_callable=mock.PropertyMock, return_value=[]):
            self.model.archive_means()
        self.assertIn('Nothing to archive', func.capture())

    def test_archive_restarts(self):
        '''Test archive means function'''
        func.logtest('Assert list of restart files to archive:')
        self.model.timestamps.return_value = True
        with mock.patch('utils.remove_files') as mock_rm:
            self.model.archive_restarts()
            mock_rm.assert_called_with(['file2', 'file1'],
                                       os.getcwd())
        self.assertNotIn('Only archiving periodic', func.capture())

    def test_archive_restarts_periodic(self):
        '''Test archive means function'''
        func.logtest('Assert list of restart files to archive:')
        self.model.timestamps.return_value = False
        with mock.patch('utils.remove_files'):
            self.model.archive_restarts()
        self.assertIn('Only archiving periodic', func.capture())

    def test_archive_nothing(self):
        '''Test archive means function - nothing to archive'''
        func.logtest('Assert function with nothing to archive:')
        self.model.periodset.return_value = []
        with mock.patch('utils.remove_files'):
            self.model.archive_restarts()
        self.assertIn(' -> Nothing to archive', func.capture())
        self.assertNotIn('Deleting', func.capture())

    def test_archive_rst_partial_fail(self):
        '''Test archiving restarts with partial success'''
        func.logtest('Assert deletion of files with successful archive:')
        self.model.archive_files = mock.Mock()
        self.model.archive_files.return_value = {
            'file1': 'SUCCESS',
            'file2': 'FAILED'
            }
        with mock.patch('utils.remove_files') as mock_rm:
            self.model.archive_restarts()
            mock_rm.assert_called_with(['file1'], os.getcwd())

    def test_archive_single_file(self):
        '''Test archive a single file'''
        func.logtest('Assert ability to archive a single file')
        returnfiles = self.model.archive_files('file1')
        self.assertEqual(returnfiles, {'file1': 'SUCCESS'})
        self.assertIn('Archive successful', func.capture())

    def test_archive_multiple_files(self):
        '''Test archive multiple files'''
        func.logtest('Assert ability to archive multiple files')
        returnfiles = self.model.archive_files(['file1', 'file2'])
        self.assertEqual(returnfiles, {'file1': 'SUCCESS',
                                       'file2': 'SUCCESS'})

    def test_archive_fail(self):
        '''Test unsuccessful archive of file'''
        func.logtest('Assert failure to archive file')
        self.model.suite.archive_file.return_value = None
        returnfiles = self.model.archive_files('file1')
        self.assertEqual(returnfiles, {'file1': 'FAILED'})
        self.assertIn('Failed to archive file: file1', func.capture('err'))


class PreprocessTests(unittest.TestCase):
    '''Unit tests relating to pre-processing of files prior to archive'''

    def setUp(self):
        with mock.patch('nlist.loadNamelist'):
            with mock.patch('suite.SuiteEnvironment'):
                self.model = modeltemplate.ModelTemplate()

    def tearDown(self):
        pass

    def test_compress_file_nccopy(self):
        '''Test call to file compression method - nccopy'''
        func.logtest('Assert call to file compression method nccopy:')
        self.model.nl.restart_directory = os.getcwd()
        self.model.nl.compression_level = 5
        self.model.nl.chunking_arguments = ['a/1', 'b/2', 'c/3']
        self.model.compress_file('meanfile', 'nccopy')
        self.model.suite.preprocess_file.assert_called_with(
            'nccopy',
            os.path.join(os.getcwd(), 'meanfile'),
            compression=5,
            chunking=['a/1', 'b/2', 'c/3']
            )

    def test_compress_file_unknown(self):
        '''Test call to file compression method - failure'''
        func.logtest('Assert call to file compression method - fail:')
        self.model.nl.restart_directory = os.getcwd()
        self.model.nl.compression_level = 5
        self.model.nl.chunking_arguments = ['a/1', 'b/2', 'c/3']
        with self.assertRaises(SystemExit):
            self.model.compress_file('meanfile', 'utility')
        self.assertIn('command not yet implemented', func.capture('err'))

    def test_fix_mean_time_one_var(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - single time var')
        self.model.nl.time_vars = 'time_counter'
        self.model.nl.correct_time_variables = True
        self.model.nl.correct_time_bounds_variables = True
        self.model.nl.time_bounds_suffix = '_bounds'
        with mock.patch('netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile', 'time_counter',
                                        do_time=True, do_bounds=True)

    def test_fix_mean_time_multi_var(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - single time var')
        self.model.nl.time_vars = 'time_counter', 'time_centered'
        self.model.nl.correct_time_variables = True
        self.model.nl.correct_time_bounds_variables = True
        with mock.patch('netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile',
                                        'time_centered',
                                        do_time=True, do_bounds=True)

    def test_fix_mean_time_only(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - time var only')
        self.model.nl.time_vars = 'time_counter', 'time_centered'
        self.model.nl.correct_time_variables = True
        self.model.nl.correct_time_bounds_variables = False
        with mock.patch('netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile',
                                        'time_centered', do_time=True,
                                        do_bounds=False)

    def test_fix_mean_bounds_only(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - bounds var only')
        self.model.nl.time_vars = 'time'
        self.model.nl.correct_time_variables = False
        self.model.nl.correct_time_bounds_variables = True
        with mock.patch('netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile', 'time',
                                        do_time=False, do_bounds=True)


class MethodsTests(unittest.TestCase):
    '''Unit tests relating to ModelTemplate methods'''

    def setUp(self):
        with mock.patch('nlist.loadNamelist'):
            with mock.patch('suite.SuiteEnvironment'):
                self.model = modeltemplate.ModelTemplate()
                self.model.nl.restart_directory = 'ShareDir'
                self.model.nl.means_directory = 'WorkDir'

        myyear = modeltemplate.PDICT
        self.period = ['Monthly'] + \
            ['Seasonal']*len(myyear['Seasonal'].keys()) + \
            ['Annual']
        self.subperiod = ['Month'] + myyear['Seasonal'].keys() + ['Year']
        self.spvals = [None] + [x for x in myyear['Seasonal'].values()] + \
            [None]

    def tearDown(self):
        pass

    @mock.patch('utils.move_files')
    @mock.patch('utils.get_subset', return_value=['WkFile1'])
    def test_no_move_to_share(self, mock_set, mock_mv):
        '''Test move_to_share functionality - share==work'''
        func.logtest('Assert null behaviour of move_to_share method:')
        self.model.nl.means_directory = 'ShareDir'
        self.model.meantemplate = mock.Mock()
        self.model.move_to_share()
        self.assertEqual(len(mock_mv.mock_calls), 0)
        self.assertEqual(len(mock_set.mock_calls), 1)

    @mock.patch('utils.move_files')
    @mock.patch('utils.get_subset', return_value=['WkFile1', 'WkFile2'])
    def test_move_to_share(self, mock_set, mock_mv):
        '''Test move_to_share functionality'''
        func.logtest('Assert behaviour of move_to_share method:')
        with mock.patch('modeltemplate.ModelTemplate.mean_stencil',
                        new_callable=mock.PropertyMock,
                        return_value={'General': lambda y, m, s, f:
                                                 r'{}_{}'.format(y, m)}):
            self.model.move_to_share()
        mock_mv.assert_called_with(['WkFile1', 'WkFile2'], 'ShareDir',
                                   originpath='WorkDir')
        mock_set.assert_called_with('WorkDir', r'None_None')
        self.assertEqual(len(mock_set.mock_calls), 1)

    @mock.patch('utils.move_files')
    @mock.patch('utils.get_subset')
    def test_move_to_share_nofiles(self, mock_set, mock_mv):
        '''Test move_to_share functionality - no files'''
        func.logtest('Assert no files behaviour of move_to_share method:')
        mock_set.return_value = []
        with mock.patch('modeltemplate.ModelTemplate.mean_stencil',
                        new_callable=mock.PropertyMock,
                        return_value={'General': lambda y, m, s, f:
                                                 r'{}_{}'.format(y, m)}):
            self.model.move_to_share()
        self.assertEqual(len(mock_mv.mock_calls), 0)
        mock_set.assert_called_with('WorkDir', r'None_None')
        self.assertEqual(len(mock_set.mock_calls), 1)

    @mock.patch('utils.move_files')
    @mock.patch('utils.get_subset')
    def test_move_to_share_pattern(self, mock_set, mock_mv):
        '''Test move_to_share functionality'''
        func.logtest('Assert behaviour of move_to_share method:')
        mock_set.return_value = []
        self.model.move_to_share(pattern=r'[abc]+')
        self.assertEqual(len(mock_mv.mock_calls), 0)
        mock_set.assert_called_with('WorkDir', r'[abc]+')

    def test_loop_inputs(self):
        '''Test loop_inputs functionality'''
        func.logtest('Assert behaviour of loop_inputs method:')
        yield_field = []
        yield_period = []
        yield_subp = []
        yield_spvals = []
        for loop_yield in self.model.loop_inputs(['field1']):
            yield_field.append(loop_yield.field)
            yield_period.append(loop_yield.period)
            yield_subp.append(loop_yield.subperiod)
            yield_spvals.append(loop_yield.spvals)
        self.assertEqual(['field1']*len(self.period), yield_field)
        self.assertEqual(self.period, yield_period)
        self.assertEqual(self.subperiod, yield_subp)
        self.assertEqual(self.spvals, yield_spvals)

    def test_loop_inputs_multifield(self):
        '''Test loop_inputs functionality - multiple fields'''
        func.logtest('Assert behaviour of loop_inputs method - multifield:')
        yield_field = []
        yield_period = []
        yield_subp = []
        yield_spvals = []
        for loop_yield in self.model.loop_inputs(['field1', 'field2']):
            yield_field.append(loop_yield.field)
            yield_period.append(loop_yield.period)
            yield_subp.append(loop_yield.subperiod)
            yield_spvals.append(loop_yield.spvals)
        self.assertEqual(
            ['field1']*len(self.period) + ['field2']*len(self.period),
            yield_field
            )
        self.assertEqual(self.period + self.period, yield_period)
        self.assertEqual(self.subperiod + self.subperiod, yield_subp)
        self.assertEqual(self.spvals + self.spvals, yield_spvals)

class PropertyTests(unittest.TestCase):
    '''Unit tests relating to ModelTemplate properties'''

    def setUp(self):
        with mock.patch('nlist.loadNamelist'):
            with mock.patch('suite.SuiteEnvironment'):
                self.model = modeltemplate.ModelTemplate()
                self.model.nl.restart_directory = 'ShareDir'
                self.model.nl.means_directory = 'WorkDir'

    def tearDown(self):
        pass

    def test_additional_means(self):
        '''Test additional_means property value'''
        func.logtest('Assert return of additional means list:')
        self.model.nl.means_to_archive = None
        self.assertEqual(self.model.additional_means, [None])
        self.model.nl.means_to_archive = '12h'
        self.assertEqual(self.model.additional_means, ['12h'])
        self.model.nl.means_to_archive = ['12h', '10d']
        self.assertEqual(self.model.additional_means, ['12h', '10d'])


def main():
    '''Main function'''
    unittest.main(buffer=True)


if __name__ == '__main__':
    main()
