#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2017 Met Office. All rights reserved.

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
import copy
import mock

import testing_functions as func
import runtime_environment

import netcdf_filenames

# Import of modeltemplate requires 'RUNID' from runtime environment
runtime_environment.setup_env()
import modeltemplate


class StencilTests(unittest.TestCase):
    '''Unit tests relating to the MODEL output filename stencils'''
    def setUp(self):
        with mock.patch('modeltemplate.nlist.loadNamelist') as mock_nl:
            mock_nl().suitegen.mean_reference_date = [0, 12, 1]
            mock_nl().modeltemplate.base_component = '10d'
            mock_nl().modeltemplate.debug = False
            self.model = modeltemplate.ModelTemplate()

        self.ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X')

    def tearDown(self):
        for fname in runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass

    @mock.patch('modeltemplate.netcdf_filenames.period_set')
    def test_set_stencil_monthly(self, mock_set):
        '''Test the regex of the set_stencil method - monthly (2days)'''
        func.logtest('Assert monthly (10d) pattern matching of set_stencil:')
        _ = self.model.set_stencil('1m', self.ncf)
        mock_set.assert_called_once_with('1m', self.ncf)

    @mock.patch('modeltemplate.netcdf_filenames.period_set')
    def test_set_stencil_seasonal(self, mock_set):
        '''Test the regex of the set_stencil method - seasonal'''
        func.logtest('Assert seasonal pattern matching of set_stencil:')
        _ = self.model.set_stencil('1s', self.ncf)
        mock_set.assert_called_once_with('1s', self.ncf)

    @mock.patch('modeltemplate.netcdf_filenames.period_set')
    def test_set_stencil_annual(self, mock_set):
        '''Test the regex of the set_stencil method - annual'''
        func.logtest('Assert annual pattern matching of set_stencil:')
        _ = self.model.set_stencil('1y', self.ncf)
        mock_set.assert_called_once_with('1y', self.ncf)

    @mock.patch('modeltemplate.netcdf_filenames.period_end')
    def test_end_stencil_monthly(self, mock_end):
        '''Test the call to period_end by the end_stencil method - monthly'''
        func.logtest('Assert monthly pattern matching of end_stencil:')
        _ = self.model.end_stencil('1m', self.ncf)
        mock_end.assert_called_once_with('1m', self.ncf, [0, 12, 1])

    @mock.patch('modeltemplate.netcdf_filenames.period_end')
    def test_end_stencil_seasonal(self, mock_end):
        '''Test the call to period_end by end_stencil method - seasonal'''
        func.logtest('Assert seasonal pattern matching of end_stencil:')
        _ = self.model.end_stencil('1s', self.ncf)
        mock_end.assert_called_once_with('1s', self.ncf, [0, 12, 1])

    @mock.patch('modeltemplate.netcdf_filenames.period_end')
    def test_end_stencil_annual(self, mock_end):
        '''Test the call to period_end by end_stencil method - annual'''
        func.logtest('Assert annual pattern matching of end_stencil:')
        _ = self.model.end_stencil('1y', self.ncf)
        mock_end.assert_called_once_with('1y', self.ncf, [0, 12, 1])

    @mock.patch('modeltemplate.netcdf_filenames.mean_stencil')
    def test_mean_stencil_ncf_filename(self, mock_stencil):
        '''Test the regular expressions of the mean_stencil method - monthly'''
        func.logtest('Assert monthly pattern matching of mean_stencil:')
        _ = self.model.mean_stencil(self.ncf, base='NA')
        mock_stencil.assert_called_once_with(self.ncf)

    @mock.patch('modeltemplate.ModelTemplate.general_mean_stencil')
    def test_mean_stencil_general(self, mock_stencil):
        '''Test the regexes of the mean_stencil method - seasonal'''
        func.logtest('Assert seasonal pattern matching of mean_stencil:')
        _ = self.model.mean_stencil('CALL1')
        _ = self.model.mean_stencil('CALL2', base='1m')

        self.assertEqual(mock_stencil.mock_calls,
                         [mock.call('CALL1', base=None),
                          mock.call('CALL2', base='1m')])


class PeriodTests(unittest.TestCase):
    '''Unit tests relating to the "get period files" methods'''

    def setUp(self):
        with mock.patch('modeltemplate.nlist.loadNamelist') as mock_nl:
            mock_nl().suitegen.mean_reference_date = [0, 12, 1]
            mock_nl().modeltemplate.base_component = '10d'
            mock_nl().modeltemplate.debug = False
            self.model = modeltemplate.ModelTemplate()
            self.model.share = 'ShareDir'

        self.ncf = netcdf_filenames.NCFilename(
            'MODEL', 'RUNID', 'X',
            start_date=('2001', '01', '21'), base='1m', custom='_FIELD'
            )

    def tearDown(self):
        pass

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_set_monthly(self, mock_subset):
        '''Test function of the periodfiles method - month set'''
        func.logtest('Assert pattern from periodfiles method - month set:')
        ncf = copy.copy(self.ncf)
        _ = self.model.periodfiles(ncf, 'set')
        mock_subset.assert_called_with('ShareDir',
                                       r'^model_runidx_10d_(20010101|20010111|'
                                       r'20010121)(\d{2})?-\d{8,10}_FIELD\.nc$')

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_set_seasonal(self, mock_subset):
        '''Test function of the periodfiles method - season set'''
        func.logtest('Assert pattern from periodfiles method - season set:')
        ncf = copy.copy(self.ncf)
        ncf.start_date = ('2001', '02', '01')
        ncf.base = '1s'
        _ = self.model.periodfiles(ncf, 'set')
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_1m_(20001201|20010101|20010201)(\d{2})?-\d{8,10}'
            r'_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_set_annual(self, mock_subset):
        '''Test function of the periodfiles method - year set'''
        func.logtest('Assert pattern from periodfiles method - year set:')
        ncf = copy.copy(self.ncf)
        ncf.start_date = ('2001', '02', '01')
        ncf.base = '1y'
        _ = self.model.periodfiles(ncf, 'set')
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_1s_(20000501|20000801|20001101|20010201)(\d{2})?'
            r'-\d{8,10}_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_set_annual_no_1s(self, mock_subset):
        '''Test function of the periodfiles method - year set with seasons'''
        func.logtest('Assert pattern from periodfiles method - year set:')
        self.model.meansets['1s'] = (None,)
        self.model.meansets['1y'] = ('1m',)
        ncf = copy.copy(self.ncf)
        ncf.start_date = ('2001', '02', '01')
        ncf.base = '1y'
        _ = self.model.periodfiles(ncf, 'set')
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_1m_(20000301|20000401|20000501|20000601|20000701|'
            r'20000801|20000901|20001001|20001101|20001201|20010101|20010201)'
            r'(\d{2})?-\d{8,10}_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_set_datadir(self, mock_subset):
        '''Test function of the periodfiles set method - with datadir'''
        func.logtest('Assert pattern produced by periodfiles set - datadir:')
        _ = self.model.periodfiles(self.ncf, 'set', datadir='MyDir')
        mock_subset.assert_called_once_with(
            'MyDir',
            r'^model_runidx_10d_(20010101|20010111|20010121)(\d{2})?-\d{8,10}'
            r'_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    @mock.patch('modeltemplate.ModelTemplate.rst_set_stencil')
    def test_period_set_restarts(self, mock_stencil, mock_subset):
        '''Test function of the periodfiles method - restart file set'''
        func.logtest('Assert pattern produced by periodset method - restart:')
        _ = self.model.periodfiles('restart-type', 'set')
        mock_stencil.assert_called_once_with('restart-type')
        mock_subset.assert_called_once_with('ShareDir',
                                            mock_stencil.return_value)

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_set_arch_monthly(self, mock_subset):
        '''Test function of the periodfiles method - monthly set archive'''
        func.logtest('Assert pattern by periodfiles - archive month set:')
        ncf = copy.copy(self.ncf)
        ncf.start_date = ('2001', '01', '15')
        _ = self.model.periodfiles(ncf, 'set', archive_mean=True)
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_1m_(20001115|20001215|20010115)(\d{2})?'
            r'-\d{8,10}_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_set_arch_seasonal(self, mock_subset):
        '''Test function of the periodfiles method - seasonal archive set'''
        func.logtest('Assert pattern by periodset - archive season set:')
        ncf = copy.copy(self.ncf)
        ncf.start_date = ('2001', '09', '01')
        ncf.base = '1s'
        _ = self.model.periodfiles(ncf, 'set', archive_mean=True)
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_1s_(20001201|20010301|20010601|20010901)(\d{2})?'
            r'-\d{8,10}_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_set_arch_annual(self, mock_subset):
        '''Test function of the periodfiles method - annual archive set'''
        func.logtest('Assert pattern by periodfiles - archive year set:')
        ncf = copy.copy(self.ncf)
        ncf.start_date = ('2001', '09', '01')
        ncf.base = '1y'
        _ = self.model.periodfiles(ncf, 'set', archive_mean=True)
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'model_runidx_1y_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}_FIELD.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_end_monthly(self, mock_subset):
        '''Test function of the periodfiles method - month end'''
        func.logtest('Assert pattern by periodfiles method - month end:')
        ncf = copy.copy(self.ncf)
        _ = self.model.periodfiles(ncf, 'end')
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_10d_\d{8,10}-\d{4}(\d{2}01)(00)?_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_end_seasonal(self, mock_subset):
        '''Test function of the periodfiles method - season end'''
        func.logtest('Assert pattern by periodfiles method - season end:')
        ncf = copy.copy(self.ncf)
        ncf.base = '1s'
        _ = self.model.periodfiles(ncf, 'end')
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_1m_\d{8,10}-\d{4}(0301|0601|0901|1201)(00)'
            r'?_FIELD\.nc$'
            )

        ncf = copy.copy(self.ncf)
        ncf.base = '1s'
        with mock.patch('modeltemplate.suite.SuiteEnvironment.meanref',
                        new_callable=mock.PropertyMock,
                        return_value=[2000, 1, 1]):
            _ = self.model.periodfiles(ncf, 'end')
        mock_subset.assert_called_with(
            'ShareDir',
            r'^model_runidx_1m_\d{8,10}-\d{4}(0101|0401|0701|1001)(00)'
            r'?_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_end_annual(self, mock_subset):
        '''Test function of the periodfiles method - year end'''
        func.logtest('Assert pattern by periodfiles method - year end:')
        ncf = copy.copy(self.ncf)
        ncf.base = '1y'
        _ = self.model.periodfiles(ncf, 'end')
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_1s_\d{8,10}-\d{4}(1201)(00)?_FIELD\.nc$'
            )

        ncf = copy.copy(self.ncf)
        ncf.base = '1y'
        with mock.patch('modeltemplate.suite.SuiteEnvironment.meanref',
                        new_callable=mock.PropertyMock,
                        return_value=[2000, 1, 1]):
            _ = self.model.periodfiles(ncf, 'end')
        mock_subset.assert_called_with(
            'ShareDir',
            r'^model_runidx_1s_\d{8,10}-\d{4}(0101)(00)?_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_end_datadir(self, mock_subset):
        '''Test function of the periodfiles end method - with datadir'''
        func.logtest('Assert pattern by periodfiles end method - datadir:')
        ncf = copy.copy(self.ncf)
        _ = self.model.periodfiles(ncf, 'end', datadir='MyDir')
        mock_subset.assert_called_once_with(
            'MyDir',
            r'^model_runidx_10d_\d{8,10}-\d{4}(\d{2}01)(00)?_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_end_arch_monthly(self, mock_subset):
        '''Test function of the periodfiles method - month end archive'''
        func.logtest('Assert pattern by periodfiles - archive month end:')
        ncf = copy.copy(self.ncf)
        ncf.base = '1m'
        _ = self.model.periodfiles(ncf, 'end', archive_mean=True)
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_1m_\d{8,10}-\d{4}(0301|0601|0901|1201)(00)'
            r'?_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_end_arch_seasonal(self, mock_subset):
        '''Test function of the periodfiles method - season end archive'''
        func.logtest('Assert pattern by periodfiles - archive season end:')
        ncf = copy.copy(self.ncf)
        ncf.base = '1s'
        _ = self.model.periodfiles(ncf, 'end', archive_mean=True)
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_1s_\d{8,10}-\d{4}(1201)(00)?_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_end_arch_annual(self, mock_subset):
        '''Test function of the periodfiles method - year end archive'''
        func.logtest('Assert pattern by periodfiles - archive year end:')
        ncf = copy.copy(self.ncf)
        ncf.base = '1y'
        _ = self.model.periodfiles(ncf, 'end', archive_mean=True)
        mock_subset.assert_called_with(
            'ShareDir',
            r'model_runidx_1y_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}_FIELD.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_periodfiles_arch_1s_only(self, mock_subset):
        '''Test function of the periodfiles method - archive 1s only'''
        func.logtest('Assert pattern by periodfiles - archive 1s only:')
        ncf = copy.copy(self.ncf)
        ncf.base = '1s'
        self.model.requested_means = ['1s']

        _ = self.model.periodfiles(ncf, 'set', archive_mean=True)
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'model_runidx_1s_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}_FIELD.nc$'
            )

        _ = self.model.periodfiles(ncf, 'end', archive_mean=True)
        mock_subset.assert_called_with(
            'ShareDir',
            r'model_runidx_1s_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}_FIELD.nc$'
            )


class MeansTests(unittest.TestCase):
    '''Unit tests relating to creation of means'''

    def setUp(self):
        with mock.patch('modeltemplate.nlist.loadNamelist') as mock_nl:
            mock_nl().modeltemplate.base_component = '2d'
            mock_nl().suitegen.mean_reference_date = [0, 1, 1]
            mock_nl().modeltemplate.debug = False
            self.model = modeltemplate.ModelTemplate()

        self.model.share = 'ShareDir'

        self.model.loop_inputs = mock.Mock()
        self.model.get_date = mock.Mock(return_value=('1996', '09', '01'))
        self.model.periodfiles = mock.Mock()
        self.model.describe_mean = mock.Mock()
        self.model.fix_mean_time = mock.Mock()

        self.model.suite = mock.Mock()
        self.model.suite.envars = {}
        self.model.suite.initpoint = [0]*5

    def tearDown(self):
        for fname in runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass
        for dirname in [self.model.diagsdir, 'ModelDir']:
            try:
                os.rmdir(dirname)
            except OSError:
                pass

    @mock.patch('modeltemplate.os.path')
    @mock.patch('modeltemplate.utils.exec_subproc', side_effect=[(0, 'None')])
    @mock.patch('modeltemplate.utils.move_files')
    @mock.patch('modeltemplate.ModelTemplate.mean_stencil')
    def test_create_annual_mean(self, mock_stencil, mock_mv, mock_exec,
                                mock_path):
        '''Test successful creation of annual mean'''
        func.logtest('Assert successful creation of annual mean:')
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X',
                                          base='1y')
        self.model.loop_inputs.return_value = [ncf]
        self.model.periodfiles.side_effect = [['setend'],
                                              ['ssn1', 'ssn2', 'ssn3', 'ssn4']]
        mock_path.isfile.side_effect = [False, True]
        mock_stencil.return_value = 'AnnualMean'

        with mock.patch('modeltemplate.utils.create_dir'):
            self.model.create_means()
        self.assertIn('[ OK ]  Created', func.capture())
        self.assertIn(': AnnualMean', func.capture())

        cmd = '{} ssn1 ssn2 ssn3 ssn4 AnnualMean'.format(self.model.means_cmd)
        mock_exec.assert_called_once_with(cmd, cwd='ShareDir')
        mock_mv.assert_called_once_with(['ssn1', 'ssn2', 'ssn3', 'ssn4'],
                                        'ModelDir/archive_ready',
                                        originpath='ShareDir')

    @mock.patch('modeltemplate.utils.remove_files')
    @mock.patch('modeltemplate.os.path')
    @mock.patch('modeltemplate.utils.exec_subproc', side_effect=[(0, 'None')])
    @mock.patch('modeltemplate.ModelTemplate.mean_stencil')
    def test_create_monthly_mean_10d(self, mock_stencil, mock_exec, mock_path,
                                     mock_rm):
        '''Test successful creation of monthly mean - 10day base'''
        func.logtest('Assert successful creation of monthly mean - 10d base:')
        self.model.meansets['1m'] = ('10d', 3)
        mock_path.isfile.side_effect = [False, True]
        mock_stencil.return_value = 'MonthlyMean'
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1m')
        self.model.loop_inputs = mock.Mock(return_value=[ncf])
        self.model.periodfiles.side_effect = [['setend'],
                                              ['10d1', '10d2', '10d3']]

        with mock.patch('modeltemplate.utils.create_dir'):
            self.model.create_means()
        self.assertIn('[ OK ]  Created', func.capture())
        self.assertIn(': MonthlyMean', func.capture())
        mock_rm.assert_called_once_with(['10d1', '10d2', '10d3'],
                                        path='ShareDir')
        cmd = '{} 10d1 10d2 10d3 MonthlyMean'.format(self.model.means_cmd)
        mock_exec.assert_called_once_with(cmd, cwd='ShareDir')

    @mock.patch('modeltemplate.utils.remove_files')
    @mock.patch('modeltemplate.os.path')
    @mock.patch('modeltemplate.utils.exec_subproc', side_effect=[(0, 'None')])
    @mock.patch('modeltemplate.ModelTemplate.mean_stencil')
    def test_create_monthly_mean_5dbase(self, mock_stencil, mock_exec,
                                        mock_path, mock_rm):
        '''Test successful creation of monthly mean - 5day base'''
        func.logtest('Assert successful creation of monthly mean - 5d base:')
        mock_path.isfile.side_effect = [False, True]
        mock_stencil.return_value = 'MonthlyMean'
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1m')
        self.model.loop_inputs = mock.Mock(return_value=[ncf])
        self.model.meansets['1m'] = ('5d', 6)
        self.model.periodfiles.side_effect = [['setend'],
                                              ['5d1', '5d2', '5d3',
                                               '5d4', '5d5', '5d6']]

        with mock.patch('modeltemplate.utils.create_dir'):
            self.model.create_means()
        self.assertIn('[ OK ]  Created', func.capture())
        self.assertIn(': MonthlyMean', func.capture())
        self.assertIn('Deleting component means', func.capture())
        mock_rm.assert_called_once_with(
            ['5d1', '5d2', '5d3', '5d4', '5d5', '5d6'], path='ShareDir'
            )
        cmd = '{} 5d1 5d2 5d3 5d4 5d5 5d6 MonthlyMean'.\
            format(self.model.means_cmd)
        mock_exec.assert_called_once_with(cmd, cwd='ShareDir')

    def test_create_monthly_mean_1mbase(self):
        '''Test successful creation of monthly mean - 1m base'''
        func.logtest('Assert successful creation of monthly mean - 1m base:')
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1m')
        self.model.loop_inputs = mock.Mock(return_value=[ncf])
        self.model.meansets['1m'] = ('1m', 1)
        self.model.periodfiles.side_effect = [['setend'], ['1m']]

        with mock.patch('modeltemplate.utils.create_dir'):
            self.model.create_means()
        self.assertIn('1m mean output directly by the model.', func.capture())
        self.assertNotIn('Deleting component means', func.capture())

    @mock.patch('modeltemplate.os.path')
    @mock.patch('modeltemplate.utils.exec_subproc', side_effect=[(99, 'None')])
    @mock.patch('modeltemplate.ModelTemplate.mean_stencil')
    def test_create_annual_mean_fail(self, mock_stencil, mock_exec, mock_path):
        '''Test failed creation of annual mean'''
        func.logtest('Assert failed creation of annual mean:')
        mock_path.isfile.return_value = False
        mock_stencil.return_value = 'AnnualMean'
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1y')
        self.model.loop_inputs.return_value = [ncf]
        self.model.periodfiles.side_effect = [['setend'],
                                              ['ssn1', 'ssn2', 'ssn3', 'ssn4']]

        with mock.patch('modeltemplate.utils.create_dir'):
            with self.assertRaises(SystemExit):
                self.model.create_means()
        self.assertIn('Error=99', func.capture('err'))
        cmd = '{} ssn1 ssn2 ssn3 ssn4 AnnualMean'.format(self.model.means_cmd)
        mock_exec.assert_called_once_with(cmd, cwd='ShareDir')

    def test_create_means_partial(self):
        '''Test create_means function with partial period'''
        func.logtest('Assert create_means functionality with partial period:')
        self.model.periodfiles.side_effect = [['setend'],
                                              ['ssn1', 'ssn2', 'ssn3']]
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1y')
        self.model.loop_inputs.return_value = [ncf]
        with mock.patch('modeltemplate.ModelTemplate.means_spinup',
                        return_value=False):
            with self.assertRaises(SystemExit):
                self.model.create_means()
        self.assertIn('not possible as only got 3', func.capture('err'))

    @mock.patch('modeltemplate.utils.remove_files')
    def test_create_means_spinup_del(self, mock_rm):
        '''Test create_means function in spinup mode (remove components)'''
        func.logtest('Assert create_means functionality in spinup (remove):')
        self.model.meansets['1m'] = ('5d', 6)
        self.model.periodfiles.side_effect = [['setend'],
                                              ['5d1', '5d2', '5d3']]
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1m')
        self.model.loop_inputs.return_value = [ncf]
        with mock.patch('modeltemplate.ModelTemplate.means_spinup',
                        return_value=True):
            self.model.create_means()
        self.assertIn('in spinup mode', func.capture())
        self.assertIn('not possible as only got 3', func.capture())
        mock_rm.assert_called_once_with(['5d1', '5d2', '5d3'], path='ShareDir')

    @mock.patch('modeltemplate.utils.move_files')
    def test_create_means_spinup_move(self, mock_mv):
        '''Test create_means function in spinup mode (move components)'''
        func.logtest('Assert create_means functionality in spinup (move):')
        self.model.requested_means = ['1d', '1m']
        self.model.meansets['1m'] = ('5d', 6)
        self.model.periodfiles.side_effect = [['setend'],
                                              ['5d1', '5d2', '5d3']]
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1m')
        self.model.loop_inputs.return_value = [ncf]
        with mock.patch('modeltemplate.ModelTemplate.means_spinup',
                        return_value=True):
            self.model.create_means()
        self.assertIn('in spinup mode', func.capture())
        self.assertIn('not possible as only got 3', func.capture())
        mock_mv.assert_called_once_with(['5d1', '5d2', '5d3'],
                                        'ModelDir/archive_ready',
                                        originpath='ShareDir')

    def test_annual_mean_spinup(self):
        '''Test Spinup period for annual means'''
        func.logtest('Assert initial spinup period for annual means:')

        for startdate in [1994, 12, 11], [1995, 12, 1]:
            func.logtest('Autumn mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.model.suite.initpoint = startdate
            self.assertTrue(self.model.means_spinup(
                'FIELD Annual mean for YYYY', ('1995', '12', '01')
                ))

        for startdate in [1994, 12, 1], [1994, 11, 11]:
            func.logtest('Autumn mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.model.suite.initpoint = startdate
            self.assertFalse(self.model.means_spinup(
                'FIELD Annual mean for YYYY', ('1995', '12', '01')
                ))

    def test_seasonal_mean_spinup_yr1(self):
        '''Test Spinup period for seasonal means - first year'''
        func.logtest('Assert initial spinup period for seasonal means - yr1:')

        for startdate in [1995, 9, 11], [1995, 10, 1], [1995, 11, 1]:
            func.logtest('Autumn mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.model.suite.initpoint = startdate
            self.assertTrue(self.model.means_spinup(
                'FIELD Seasonal mean for SEASON YYYY', ('1995', '12', '01')
                ))

        for startdate in [1995, 8, 1], [1995, 9, 1]:
            func.logtest('Autumn mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.model.suite.initpoint = startdate
            self.assertFalse(self.model.means_spinup(
                'FIELD Seasonal mean for SEASON YYYY', ('1995', '12', '01')
                ))

    def test_seasonal_mean_spinup_yr2(self):
        '''Test Spinup period for seasonal means - second year'''
        func.logtest('Assert initial spinup period for seasonal means - yr2:')

        for startdate in [1995, 12, 11], [1995, 12, 21]:
            func.logtest('Autumn mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.model.suite.initpoint = startdate
            self.assertTrue(self.model.means_spinup(
                'FIELD Seasonal mean for SEASON YYYY', ('1996', '03', '01')
                ))

        for startdate in [1995, 12, 1], [1995, 10, 1]:
            func.logtest('Autumn mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.model.suite.initpoint = startdate
            self.assertFalse(self.model.means_spinup(
                'FIELD Seasonal mean for SEASON YYYY', ('1996', '03', '01')
                ))

        for startdate in [1995, 12, 21], [1995, 9, 1]:
            func.logtest('Autumn mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.model.suite.initpoint = startdate
            self.assertFalse(self.model.means_spinup(
                'FIELD Seasonal mean for SEASON YYYY', ('1996', '06', '01')
                ))

    def test_monthly_mean_spinup(self):
        '''Test Spinup period for monthly means'''
        func.logtest('Assert initial spinup period for monthly means:')
        self.model.suite.initpoint = [1995, 8, 1, 0, 0]
        self.assertTrue(self.model.means_spinup(
            'FIELD Monthly mean for MONTH YYYY', ('1995', '08', '01')))
        self.assertTrue(self.model.means_spinup(
            'FIELD Monthly mean for MONTH YYYY', ('1995', '08', '11')))
        self.assertFalse(self.model.means_spinup(
            'FIELD Monthly mean for MONTH YYYY', ('1995', '09', '01')))

        self.model.suite.initpoint = [1995, 8, 11, 0, 0]
        self.assertTrue(self.model.means_spinup(
            'FIELD Monthly mean for MONTH YYYY', ('1995', '09', '01')))
        self.assertFalse(self.model.means_spinup(
            'FIELD Monthly mean for MONTH YYYY', ('1995', '09', '11')))

    def test_spinup_invalid(self):
        '''Test Spinup period for invalid means'''
        func.logtest('Assert initial spinup period for invalid means:')
        self.model.suite.initpoint = [1995, 8, 1, 0, 0]
        self.assertFalse(self.model.means_spinup(
            'FIELD INVALID mean for YYYY', ('1995', '10', '01')))
        self.assertIn('[WARN]', func.capture('err'))
        self.assertIn('unknown meantype', func.capture('err'))


class ArchiveTests(unittest.TestCase):
    '''Unit tests relating to archiving of files'''

    def setUp(self):
        modeltemplate.ModelTemplate._directory = mock.\
            Mock(return_value='ModelDir')
        with mock.patch('modeltemplate.nlist.loadNamelist') as mock_nl:
            mock_nl().modeltemplate.base_component = '10d'
            mock_nl().modeltemplate.debug = False
            self.model = modeltemplate.ModelTemplate()
            self.model.share = os.getcwd()
            self.model._debug_mode(False)

        self.model.naml.buffer_archive = None
        self.model.naml.compression_level = 0
        self.model.naml.means_to_archive = []

        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X')
        self.model.loop_inputs = mock.Mock(return_value=[ncf])
        self.model.get_date = mock.Mock(return_value=('1996', '05', '01'))
        self.model.timestamps = mock.Mock()
        self.model.component = mock.Mock(return_value='component')

        self.model.suite = mock.Mock()
        self.model.suite.finalcycle = False
        self.model.suite.archive_file.return_value = 0

    def tearDown(self):
        for fname in ['12h_field1', '10d_field1', 'xd_field2',
                      os.path.join(self.model.diagsdir, 'runid_xd_field1.nc'),
                      os.path.join(self.model.diagsdir, 'runid_xd_field2.nc'),
                      '1m_field1', '1s_field1', '1y_field2', '1x_field2']:
            try:
                os.remove(fname)
            except OSError:
                pass
        for dirname in [self.model.diagsdir, 'ModelDir']:
            try:
                os.rmdir(dirname)
            except OSError:
                pass

    def test_buffer_archive(self):
        '''Test return of archive buffer property'''
        func.logtest('Assert return of archive buffer property:')
        self.assertEqual(self.model.buffer_archive, 0)
        self.model.naml.buffer_archive = 5
        self.assertEqual(self.model.buffer_archive, 5)

    def test_buffer_archive_finalcycle(self):
        '''Test return of archive buffer property - final cycle'''
        func.logtest('Assert return of archive buffer - final cycle:')
        self.model.naml.buffer_archive = 5
        self.model.suite.finalcycle = True
        self.assertEqual(self.model.buffer_archive, 0)

    @mock.patch('modeltemplate.utils.remove_files')
    def test_archive_means(self, mock_rm):
        '''Test archive means function'''
        func.logtest('Assert list of means to archive:')
        self.model.periodfiles = mock.Mock()
        self.model.periodfiles.side_effect = [['setend'], ['mean1', 'mean2']]
        self.model.archive_files = mock.Mock()
        self.model.archive_files.side_effect = [{'mean1': 'SUCCESS'},
                                                {'mean2': 'SUCCESS'}]
        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        new_callable=mock.PropertyMock, return_value='x'):
            self.model.archive_means()

        self.assertListEqual(mock_rm.mock_calls,
                             [mock.call(['mean1'], path=os.getcwd()),
                              mock.call(['mean2'], path=os.getcwd())])
        self.assertListEqual(self.model.archive_files.mock_calls,
                             [mock.call(os.path.join(os.getcwd(), 'mean1')),
                              mock.call(os.path.join(os.getcwd(), 'mean2'))])

    @mock.patch('modeltemplate.os.rename')
    def test_archive_means_debug(self, mock_rm):
        '''Test archive means function'''
        func.logtest('Assert list of means to archive:')
        self.model._debug_mode(True)
        self.model.periodfiles = mock.Mock()
        self.model.periodfiles.side_effect = [['setend'], ['mean1', 'mean2']]
        self.model.archive_files = mock.Mock()
        self.model.archive_files.side_effect = [{'mean1': 'SUCCESS'},
                                                {'mean2': 'SUCCESS'}]

        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        new_callable=mock.PropertyMock, return_value='x'):
            self.model.archive_means()

        infiles = [os.path.join(os.getcwd(), fn) for fn in ['mean1', 'mean2']]
        outfiles = [fn + '_ARCHIVED' for fn in infiles]
        call_rename = []
        for i, fname in enumerate(infiles):
            call_rename.append(mock.call(os.path.join(os.getcwd(), fname),
                                         outfiles[i]))
        self.assertListEqual(mock_rm.mock_calls, call_rename)
        self.assertListEqual(self.model.archive_files.mock_calls,
                             [mock.call(os.path.join(os.getcwd(), 'mean1')),
                              mock.call(os.path.join(os.getcwd(), 'mean2'))])

    def test_archive_means_readyset(self):
        '''Test archive means function - files in "ready" directory'''
        func.logtest('Assert list of means files to archive - ready:')
        self.model.suite.prefix = 'RUNID'
        os.makedirs(self.model.diagsdir)
        self.model.periodfiles = mock.Mock(side_effect=[[]])
        self.model.archive_files = mock.Mock()
        self.model.archive_files.side_effect = [
            {'ModelDir/archive_ready/runid_xd_field{}.nc'.format(i):
                 'SUCCESS'} for i in range(1, 4)
            ]
        files = ['ModelDir/archive_ready/runid_xd_field{}.nc'.format(i)
                 for i in range(1, 3)]
        for fname in files:
            open(fname, 'w').close()
        self.model.mean_fields = ('field1', 'field2')
        self.model.naml.means_to_archive = []
        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        new_callable=mock.PropertyMock, return_value='x'):
            self.model.archive_means()
        self.assertListEqual(self.model.archive_files.mock_calls,
                             [mock.call(files[0]), mock.call(files[1])])

    @mock.patch('modeltemplate.ModelTemplate.mean_stencil')
    def test_archive_additional_means(self, mock_stencil):
        '''Test archive additional means for archive'''
        func.logtest('Assert list of additional means to archive:')
        self.model.periodfiles = mock.Mock(side_effect=[[]])
        self.model.archive_files = mock.Mock()
        self.model.archive_files.side_effect = [{'12h_field1': 'SUCCESS'},
                                                {'xd_field2': 'SUCCESS'}]
        self.model.naml.means_to_archive = ['12h', '1d', '10d']
        self.model.component = mock.Mock(return_value='component')
        self.model.mean_fields = ('field1', 'field2')
        arch_add = [p for p in self.model.naml.means_to_archive
                    if p != self.model.base_component]
        mock_stencil.return_value = r'({})_field\d'.format('|'.join(arch_add))

        files = ['12h_field1', '10d_field1', 'xd_field2']
        for fname in files:
            open(fname, 'w').close()

        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        new_callable=mock.PropertyMock,
                        return_value='x'):
            self.model.archive_means()

        self.model.archive_files.assert_called_once_with(
            os.path.join(os.getcwd(), '12h_field1')
            )
        self.assertFalse(os.path.exists('12h_field1'))
        self.assertTrue(os.path.exists('10d_field1'))
        self.assertTrue(os.path.exists('xd_field2'))

    @mock.patch('modeltemplate.ModelTemplate.mean_stencil')
    def test_archive_means_finalcycle(self, mock_stencil):
        '''Test archive additional means for archive - final cycle'''
        func.logtest('Assert list of means to archive - final cycle:')
        self.model.suite.finalcycle = True
        self.model.periodfiles = mock.Mock(side_effect=[[]])
        self.model.archive_files = mock.Mock()
        files = ['1m_field1', '1s_field1', '1y_field2', '1x_field2']
        mock_stencil.return_value = r'1[ms]_field\d'
        self.model.archive_files.side_effect = [{files[0]: 'SUCCESS'},
                                                {files[1]: 'SUCCESS'},
                                                {files[2]: 'SUCCESS'}]
        for fname in files:
            open(fname, 'w').close()
        print 'LIST:', os.listdir(os.getcwd())
        self.model.mean_fields = ('field1', 'field2')

        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        new_callable=mock.PropertyMock, return_value='x'):
            self.model.archive_means()

        self.assertListEqual(self.model.archive_files.mock_calls,
                             [mock.call(os.path.join(os.getcwd(), files[0])),
                              mock.call(os.path.join(os.getcwd(), files[1]))])
        # Calls to mean_stencil - '1m' & '1s' for 'field1' and 'field2'
        self.assertEqual(len(mock_stencil.mock_calls), 4)
        for fname in files:
            func.logtest('Asserting existence of {}...'.format(fname))
            self.assertTrue(os.path.exists(fname))

    @mock.patch('modeltemplate.utils.remove_files')
    def test_archive_means_compress(self, mock_rm):
        '''Test archive means with compression'''
        func.logtest('Assert compression of archived means:')
        self.model.periodfiles = mock.Mock()
        self.model.periodfiles.side_effect = [['setend'],
                                              ['file1', 'DDIR/file2']]
        self.model.archive_files = mock.Mock()
        self.model.archive_files.side_effect = [{'file1': 'SUCCESS'},
                                                {'DDIR/file2': 'SUCCESS'}]
        self.model.naml.compress_netcdf = 'comp_util'
        self.model.naml.compression_level = 5
        self.model.naml.chunking_arguments = 'chunks'
        self.model.compress_file = mock.Mock(return_value=0)
        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        new_callable=mock.PropertyMock, return_value='x'):
            self.model.archive_means()

        self.assertListEqual(mock_rm.mock_calls,
                             [mock.call(['file1'], path=os.getcwd()),
                              mock.call(['DDIR/file2'], path='DDIR')])
        self.assertListEqual(self.model.archive_files.mock_calls,
                             [mock.call('DDIR/file2'),
                              mock.call(os.path.join(os.getcwd(), 'file1'))])
        call_compress = []
        for fname in ['DDIR/file2', os.path.join(os.getcwd(), 'file1')]:
            call_compress.append(mock.call(fname, 'comp_util',
                                           compression=5, chunking='chunks'))
        self.assertListEqual(self.model.compress_file.mock_calls, call_compress)

    def test_archive_means_comp_fail(self):
        '''Test archive means with compression - fail to compress'''
        func.logtest('Assert compression of archived means - fail to compress:')
        self.model.periodfiles = mock.Mock()
        self.model.periodfiles.side_effect = [['setend'], ['mean1', 'mean2']]
        self.model.archive_files = mock.Mock()
        self.model.naml.compress_netcdf = 'comp_util'
        self.model.naml.compression_level = 5
        self.model.naml.chunking_arguments = 'chunks'
        self.model.compress_file = mock.Mock(return_value=99)
        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        new_callable=mock.PropertyMock, return_value='x'):
            self.model.archive_means()
        self.assertListEqual(self.model.archive_files.mock_calls, [])
        call_compress = []
        for fname in ['mean1', 'mean2']:
            call_compress.append(mock.call(os.path.join(os.getcwd(), fname),
                                           'comp_util',
                                           compression=5,
                                           chunking='chunks'))
        self.assertListEqual(self.model.compress_file.mock_calls, call_compress)

    @mock.patch('modeltemplate.utils.remove_files')
    def test_archive_means_partial_fail(self, mock_rm):
        '''Test archive means function with partial failure'''
        func.logtest('Assert partially successful archive of file list:')
        self.model.periodfiles = mock.Mock()
        self.model.periodfiles.side_effect = [['setend'], ['mean1', 'mean2']]
        self.model.archive_files = mock.Mock()
        self.model.archive_files.side_effect = [{'mean1': 'SUCCESS'},
                                                {'mean2': 'FAILED'}]
        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        new_callable=mock.PropertyMock, return_value='x'):
            self.model.archive_means()
        mock_rm.assert_called_once_with(['mean1'], path=os.getcwd())

    @mock.patch('modeltemplate.ModelTemplate.periodfiles')
    def test_no_means_to_archive(self, mock_pf):
        '''Test report with no means to archive'''
        func.logtest('Assert report with no means to archive:')
        mock_pf.return_value = []
        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        new_callable=mock.PropertyMock, return_value='x'):
            self.model.archive_means()
        self.assertIn('Nothing to archive', func.capture())

    @mock.patch('modeltemplate.ModelTemplate.periodfiles',
                return_value=['rst1', 'rst2'])
    @mock.patch('modeltemplate.utils.remove_files')
    def test_archive_restarts(self, mock_rm, mock_set):
        '''Test archive restarts function'''
        func.logtest('Assert list of restart files to archive:')
        self.model.timestamps.return_value = True
        self.model.archive_restarts()
        mock_rm.assert_called_once_with(['rst1', 'rst2'], path=os.getcwd())
        self.assertNotIn('Only archiving periodic', func.capture())
        mock_set.assert_called_once_with('', 'set')

    @mock.patch('modeltemplate.ModelTemplate.periodfiles',
                return_value=['rst1', 'rst2'])
    @mock.patch('modeltemplate.utils.remove_files')
    def test_archive_restarts_final(self, mock_rm, mock_set):
        '''Test archive restarts function - finalcycle'''
        func.logtest('Assert restart files to archive - final cycle:')
        self.model.timestamps.return_value = False
        self.model.suite.finalcycle = True
        self.model.archive_restarts()
        self.assertListEqual(mock_rm.mock_calls,
                             [mock.call('rst1', path=os.getcwd())])
        mock_set.assert_called_once_with('', 'set')

    @mock.patch('modeltemplate.ModelTemplate.periodfiles',
                return_value=['rst1', 'rst2'])
    def test_archive_restarts_debug(self, mock_set):
        '''Test archive restarts function - debug mode'''
        func.logtest('Assert list of restart files to archive - debug:')
        self.model.timestamps.return_value = True
        self.model._debug_mode(True)
        infiles = [os.path.join(os.getcwd(), fn) for fn in ['rst2', 'rst1']]
        outfiles = [fn + '_ARCHIVED' for fn in infiles]
        with mock.patch('modeltemplate.os.rename') as mock_rm:
            self.model.archive_restarts()
            self.assertEqual(sorted(mock_rm.mock_calls),
                             sorted([mock.call(infiles[0], outfiles[0]),
                                     mock.call(infiles[1], outfiles[1])]))
            self.assertNotIn('Only archiving periodic', func.capture())
        mock_set.assert_called_once_with('', 'set')

    @mock.patch('modeltemplate.ModelTemplate.periodfiles',
                return_value=['rst1', 'rst2'])
    def test_archive_restarts_periodic(self, mock_set):
        '''Test archive restarts function'''
        func.logtest('Assert list of restart files to archive:')
        self.model.timestamps.return_value = False
        with mock.patch('modeltemplate.utils.remove_files'):
            self.model.archive_restarts()
        self.assertIn('Only archiving periodic', func.capture())
        mock_set.assert_called_once_with('', 'set')

    def test_archive_nothing(self):
        '''Test archive restarts function - nothing to archive'''
        func.logtest('Assert function with nothing to archive:')
        with mock.patch('modeltemplate.ModelTemplate.periodfiles',
                        return_value=[]):
            with mock.patch('modeltemplate.utils.remove_files'):
                self.model.archive_restarts()
        self.assertIn(' -> Nothing to archive', func.capture())
        self.assertNotIn('Deleting', func.capture())

    @mock.patch('modeltemplate.ModelTemplate.periodfiles')
    @mock.patch('modeltemplate.ModelTemplate.archive_files')
    def test_archive_rst_partial_fail(self, mock_arch, mock_pf):
        '''Test archiving restarts with partial success'''
        func.logtest('Assert deletion of files with successful archive:')
        mock_pf.return_value = ['file1', 'file2']
        mock_arch.return_value = {'file1': 'SUCCESS',
                                  'file2': 'FAILED'}
        with mock.patch('modeltemplate.utils.remove_files') as mock_rm:
            self.model.archive_restarts()
            mock_rm.assert_called_with(['file1'], path=os.getcwd())
        mock_pf.assert_called_once_with('', 'set')
        mock_arch.assert_called_once_with(['file1', 'file2'])

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
        modeltemplate.ModelTemplate._directory = mock.\
            Mock(return_value='ModelDir')
        with mock.patch('modeltemplate.nlist.loadNamelist') as mock_nl:
            mock_nl().modeltemplate.base_component = '10d'
            mock_nl().modeltemplate.debug = False
            with mock.patch('modeltemplate.suite.SuiteEnvironment'):
                with mock.patch('modeltemplate.utils.CylcCycle'):
                    self.model = modeltemplate.ModelTemplate()
                    self.model.share = 'ShareDir'
                    self.model._debug_mode(False)

    def tearDown(self):
        pass

    def test_compress_file_nccopy(self):
        '''Test call to file compression method - nccopy'''
        func.logtest('Assert call to file compression method nccopy:')
        _ = self.model.compress_file('meanfile', 'nccopy',
                                     compression=5,
                                     chunking=['a/1', 'b/2', 'c/3'])
        self.model.suite.preprocess_file.assert_called_with(
            'nccopy', 'meanfile',
            compression=5, chunking=['a/1', 'b/2', 'c/3']
            )

    def test_compress_file_nccopy_noarg(self):
        '''Test call to file compression method - nccopy - no arguments'''
        func.logtest('Assert call to file compression method nccopy - no args:')
        _ = self.model.compress_file('meanfile', 'nccopy')
        self.model.suite.preprocess_file.assert_called_with(
            'nccopy', 'meanfile',
            compression=0, chunking=None
            )

    def test_compress_file_badcmd(self):
        '''Test call to file compression method - failure'''
        func.logtest('Assert call to file compression method - fail:')
        self.model.naml.compression_level = 5
        self.model.naml.chunking_arguments = ['a/1', 'b/2', 'c/3']
        with self.assertRaises(SystemExit):
            _ = self.model.compress_file('meanfile', 'utility')
        self.assertIn('command not yet implemented', func.capture('err'))

    def test_compress_file_bad_debug(self):
        '''Test call to file compression method - debug failure'''
        func.logtest('Assert call to file compression method - debug fail:')
        self.model._debug_mode(True)
        self.model.naml.compression_level = 5
        self.model.naml.chunking_arguments = ['a/1', 'b/2', 'c/3']
        rcode = self.model.compress_file('meanfile', 'utility')
        self.assertIn('command not yet implemented', func.capture('err'))
        self.assertEqual(rcode, 99)

    def test_fix_mean_time_one_var(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - single time var')
        self.model.naml.time_vars = 'time_counter'
        self.model.naml.correct_time_variables = True
        self.model.naml.correct_time_bounds_variables = True
        self.model.naml.time_bounds_suffix = '_bounds'
        with mock.patch('modeltemplate.netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile', 'time_counter',
                                        do_time=True, do_bounds=True)

    def test_fix_mean_time_multi_var(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - single time var')
        self.model.naml.time_vars = 'time_counter', 'time_centered'
        self.model.naml.correct_time_variables = True
        self.model.naml.correct_time_bounds_variables = True
        with mock.patch('modeltemplate.netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile',
                                        'time_centered',
                                        do_time=True, do_bounds=True)

    def test_fix_mean_time_only(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - time var only')
        self.model.naml.time_vars = 'time_counter', 'time_centered'
        self.model.naml.correct_time_variables = True
        self.model.naml.correct_time_bounds_variables = False
        with mock.patch('modeltemplate.netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile',
                                        'time_centered', do_time=True,
                                        do_bounds=False)

    def test_fix_mean_bounds_only(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - bounds var only')
        self.model.naml.time_vars = 'time'
        self.model.naml.correct_time_variables = False
        self.model.naml.correct_time_bounds_variables = True
        with mock.patch('modeltemplate.netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile', 'time',
                                        do_time=False, do_bounds=True)


class MethodsTests(unittest.TestCase):
    '''Unit tests relating to ModelTemplate methods'''

    def setUp(self):
        with mock.patch('modeltemplate.nlist.loadNamelist') as mock_nl:
            mock_nl().suitegen.prefix = 'RUNID'
            mock_nl().suitegen.mean_reference_date = [0, 12, 1]
            mock_nl().modeltemplate.base_component = '10d'
            mock_nl().modeltemplate.debug = False
            self.model = modeltemplate.ModelTemplate()
            self.model.share = 'ShareDir'
            self.model.work = 'WorkDir'

        self.ncf = netcdf_filenames.NCFilename(
            'MODEL', 'RUNID', 'X',
            start_date=('2001', '01', '21'), base='1m', custom='_FIELD'
            )

    def tearDown(self):
        pass

    @mock.patch('modeltemplate.ModelTemplate.get_raw_output')
    @mock.patch('modeltemplate.utils.move_files')
    def test_no_move_to_share(self, mock_mv, mock_set):
        '''Test move_to_share functionality - share==work'''
        func.logtest('Assert null behaviour of move_to_share method:')
        self.model.work = 'ShareDir'
        mock_set.side_effect = [['WkFile1'], []]
        self.model.move_to_share()
        self.assertEqual(len(mock_mv.mock_calls), 0)
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call('ShareDir'), mock.call('ShareDir')])

    @mock.patch('modeltemplate.ModelTemplate.get_raw_output')
    @mock.patch('modeltemplate.utils.move_files')
    def test_move_to_share(self, mock_mv, mock_set):
        '''Test move_to_share functionality'''
        func.logtest('Assert behaviour of move_to_share method:')
        mock_set.side_effect = [['WkFile1', 'WkFile2'],
                                ['ShFile1', 'ShFile2']]
        self.model.filename_components = mock.Mock()
        self.model.datestamp_period = mock.Mock(return_value='xd')
        self.model.move_to_share()
        mock_mv.assert_called_with(['WkFile1', 'WkFile2'], 'ShareDir',
                                   originpath='WorkDir')
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call('WorkDir'), mock.call('ShareDir')])
        self.assertListEqual(self.model.filename_components.mock_calls,
                             [mock.call('ShFile1'),
                              mock.call().rename_ncf('ShareDir/ShFile1',
                                                     target='xd'),
                              mock.call('ShFile2'),
                              mock.call().rename_ncf('ShareDir/ShFile2',
                                                     target='xd')])
        self.assertListEqual(self.model.mean_fields, [''])

    @mock.patch('modeltemplate.ModelTemplate.get_raw_output')
    @mock.patch('modeltemplate.utils.move_files')
    def test_move_to_share_newfields(self, mock_mv, mock_set):
        '''Test move_to_share functionality - rename fields'''
        func.logtest('Assert no files behaviour of move_to_share method:')
        mock_set.return_value = []
        self.model.mean_fields = ['MEAN_1', 'MEAN_2']
        self.model.inst_fields = ['INST_1']
        self.model.move_to_share()
        self.assertEqual(len(mock_mv.mock_calls), 0)
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call('WorkDir'), mock.call('ShareDir')])
        self.assertListEqual(self.model.mean_fields, ['MEAN-1', 'MEAN-2'])
        self.assertListEqual(self.model.inst_fields, ['INST-1'])

    @mock.patch('modeltemplate.ModelTemplate.get_raw_output')
    @mock.patch('modeltemplate.utils.move_files')
    def test_move_to_share_nofiles(self, mock_mv, mock_set):
        '''Test move_to_share functionality - no files'''
        func.logtest('Assert no files behaviour of move_to_share method:')
        mock_set.return_value = []
        self.model.move_to_share()
        self.assertEqual(len(mock_mv.mock_calls), 0)
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call('WorkDir'), mock.call('ShareDir')])

    @mock.patch('modeltemplate.utils.move_files')
    @mock.patch('modeltemplate.utils.get_subset')
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
        yield_prefix = []
        yield_field = []
        yield_period = []
        with mock.patch('modeltemplate.ModelTemplate.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'mod1': ['g1'], 'mod2': ['g2']}):
            with mock.patch('modeltemplate.ModelTemplate.model_realm',
                            new_callable=mock.PropertyMock,
                            return_value='X'):
                for loop_yield in self.model.loop_inputs(['f1']):
                    yield_prefix.append(loop_yield.prefix)
                    yield_field.append(loop_yield.custom)
                    yield_period.append(loop_yield.base)
        self.assertEqual(['mod1_runidx']*3 + ['mod2_runidx']*3, yield_prefix)
        self.assertEqual(['_f1']*3 + ['_f1']*3, yield_field)
        self.assertEqual(['1m', '1s', '1y']*2, yield_period)

    def test_loop_inputs_multifield(self):
        '''Test loop_inputs functionality - multiple fields'''
        func.logtest('Assert behaviour of loop_inputs method - multifield:')
        yield_prefix = []
        yield_field = []
        yield_period = []
        with mock.patch('modeltemplate.ModelTemplate.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'mod1': ['g1'], 'mod2': ['g2']}):
            with mock.patch('modeltemplate.ModelTemplate.model_realm',
                            new_callable=mock.PropertyMock,
                            return_value='X'):
                for loop_yield in self.model.loop_inputs(['f1', 'f2']):
                    yield_prefix.append(loop_yield.prefix)
                    yield_field.append(loop_yield.custom)
                    yield_period.append(loop_yield.base)
        self.assertEqual(['mod1_runidx']*6 + ['mod2_runidx']*6, yield_prefix)
        self.assertEqual(['_f1']*3 + ['_f2']*3 + ['_f1']*3 + ['_f2']*3,
                         yield_field)
        self.assertEqual(['1m', '1s', '1y']*4, yield_period)

    def test_describe_mean_monthly(self):
        '''Test compostion of mean description - monthly'''
        func.logtest('Assert correct composition of monthly mean description:')
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X',
                                          start_date=('1111', '06', '01'),
                                          base='1m')
        self.assertIn('Monthly mean for June 1111',
                      self.model.describe_mean(ncf))

    def test_describe_mean_mth_field(self):
        '''Test compostion of mean description - monthly field'''
        func.logtest('Assert correct composition of monthly mean description:')
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X',
                                          start_date=('1111', '06', '01'),
                                          base='1m',
                                          custom='_FIELD')
        self.assertIn('FIELD Monthly mean for June 1111',
                      self.model.describe_mean(ncf))

    def test_describe_mean_seasonal(self):
        '''Test compostion of mean description - seasonal'''
        func.logtest('Assert correct composition of seasonal mean description:')
        ncf = copy.copy(self.ncf)
        ncf.base = '1s'
        ncf.start_date = ('1111', '06', '01')
        self.assertIn('Seasonal mean for Jun-Jul-Aug 1111',
                      self.model.describe_mean(ncf))

        ncf.start_date = ('1111', '12', '01')
        self.assertIn('Seasonal mean for Dec-Jan-Feb, ending 1112',
                      self.model.describe_mean(ncf))

        ncf.start_date = ('1111', '02', '01')
        with mock.patch('modeltemplate.suite.SuiteEnvironment.meanref',
                        new_callable=mock.PropertyMock,
                        return_value=[None, 2, None]):
            self.assertIn('Seasonal mean for Feb-Mar-Apr 1111',
                          self.model.describe_mean(ncf))

    def test_describe_mean_annual(self):
        '''Test compostion of mean description - annual'''
        func.logtest('Assert correct composition of annual mean description:')
        ncf = copy.copy(self.ncf)
        ncf.base = '1y'
        self.assertIn('Annual mean for year ending December 2002',
                      self.model.describe_mean(ncf))

        with mock.patch('modeltemplate.suite.SuiteEnvironment.meanref',
                        new_callable=mock.PropertyMock,
                        return_value=[None, 3, 15]):
            self.assertIn('Annual mean for year ending March 2002',
                          self.model.describe_mean(ncf))

    @mock.patch('modeltemplate.netcdf_filenames.NCFilename')
    def test_components(self, mock_ncf):
        '''Test component extraction'''
        func.logtest('Assert correct extraction of filename components:')
        self.model.suite = mock.Mock()
        self.model.suite.prefix = 'u_RUNID'
        with mock.patch('modeltemplate.ModelTemplate.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'model': ['F_1', 'F_2']}):
            with mock.patch('modeltemplate.ModelTemplate.model_realm',
                            new_callable=mock.PropertyMock,
                            return_value='x'):
                _ = self.model.filename_components(
                    'u_RUNIDx.1x.11112233_44445566_F_1.nc'
                    )
        mock_ncf.assert_called_once_with('model', 'u_RUNID', 'x', base='1x',
                                         start_date=('1111', '22', '33'),
                                         custom='F-1')

    @mock.patch('modeltemplate.netcdf_filenames.NCFilename')
    def test_components_nofields(self, mock_ncf):
        '''Test component extraction - no fields'''
        func.logtest('Assert correct extraction of filename components:')
        with mock.patch('modeltemplate.ModelTemplate.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'model': ['']}):
            with mock.patch('modeltemplate.ModelTemplate.model_realm',
                            new_callable=mock.PropertyMock,
                            return_value='x'):
                _ = self.model.filename_components(
                    'RUNIDx.10x.11112233.44445566.nc'
                    )
        mock_ncf.assert_called_once_with('model', 'RUNID', 'x', base='10x',
                                         start_date=('1111', '22', '33'),
                                         custom='')

    @mock.patch('modeltemplate.netcdf_filenames.NCFilename')
    def test_components_rebuild(self, mock_ncf):
        '''Test component extraction - with rebuild suffix'''
        func.logtest('Assert correct extraction of components - rebld suffix:')
        testfile = 'RUNIDx_1x_11111111_22222222_F_1-33333333_444444444_9876.nc'
        with mock.patch('modeltemplate.ModelTemplate.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'model': ['F_1']}):
            with mock.patch('modeltemplate.ModelTemplate.model_realm',
                            new_callable=mock.PropertyMock,
                            return_value='x'):
                with mock.patch('modeltemplate.ModelTemplate.rebuild_suffix',
                                new_callable=mock.PropertyMock,
                                return_value={'REGEX': r'_\d{4}\.nc'}):
                    _ = self.model.filename_components(testfile)

        mock_ncf.assert_called_once_with('model', 'RUNID', 'x', base='1x',
                                         start_date=('3333', '33', '33'),
                                         custom='F-1_9876')

    def test_components_fail_model(self):
        '''Test component extraction - failure in model identification'''
        func.logtest('Assert failure in model identification:')
        with mock.patch('modeltemplate.ModelTemplate.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'model': ['field1', 'field2']}):
            with self.assertRaises(SystemExit):
                _ = self.model.filename_components(
                    'RUNIDx.1x.11112233_44445566_FIELD.nc'
                    )
        self.assertIn('unable to extract "component"', func.capture('err'))

    @mock.patch('modeltemplate.netcdf_filenames.NCFilename.__init__',
                return_value=None)
    def test_components_fail_debug(self, mock_ncf):
        '''Test component extraction - failure in model identification'''
        func.logtest('Assert failure in model identification:')
        self.model._debug_mode(True)
        with mock.patch('modeltemplate.ModelTemplate.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'model': ['field1', 'field2']}):
            ncf = self.model.filename_components(
                'RUNIDx_10m_11112233_44445566_FIELD.nc'
                )
            self.assertTrue(isinstance(ncf, netcdf_filenames.NCFilename))
        self.assertIn('unable to extract "component"', func.capture('err'))
        mock_ncf.assert_called_once_with('component', 'PREFIX', 'R')

    def test_datastamp_period_cf(self):
        '''Test datestamp_period extraction from filename - cf compliant'''
        func.logtest('Assert data period from fname - cf compliant:')
        target = self.model.datestamp_period(
            'RUNIDx_1m_19901001_19910101_FIELD.nc'
            )
        self.assertEqual(target, '3m')

        target = self.model.datestamp_period(
            'RUNIDx_1d_19901001_19901006_FIELD.nc'
            )
        self.assertEqual(target, '5d')

    def test_datastamp_period_cf_modify(self):
        '''Test datestamp_period from filename - cf compliant, modified'''
        func.logtest('Assert modified data period from fname - cf compliant:')
        target = self.model.datestamp_period(
            'RUNIDx_6h_1990010100_1990010200_FIELD.nc'
            )
        self.assertEqual(target, '1d')

        with mock.patch('modeltemplate.utils.calendar',
                        return_value='gregorian'):
            target = self.model.datestamp_period(
                'RUNIDx_10d_19901001_19901101_FIELD.nc'
                )
            self.assertEqual(target, '30d')

        with mock.patch('modeltemplate.utils.calendar',
                        return_value='360day'):
            target = self.model.datestamp_period(
                'RUNIDx_10d_19901001_19901101_FIELD.nc'
                )
            self.assertEqual(target, '1m')

            target = self.model.datestamp_period(
                'RUNIDx_12h_19901001_19901101_FIELD.nc'
                )
            self.assertEqual(target, '1m')

    def test_dstamp_period_noncf_base(self):
        '''Test datestamp_period from filename - non-cf, base target'''
        func.logtest('Assert extraction of base from fname - non-cf:')

        with mock.patch('modeltemplate.ModelTemplate.cfcompliant_output',
                        new_callable=mock.PropertyMock,
                        return_value=False):
            target = self.model.datestamp_period(
                'RUNIDx_1h_1990090112_1990090112_FIELD.nc'
                )
            self.assertEqual(target, '1h')

            target = self.model.datestamp_period(
                'RUNIDo_1d_19900901_19900930_FIELD_19900901-19900901.nc'
                )
            self.assertEqual(target, '1d')

            target = self.model.datestamp_period(
                'RUNIDx_1m_1990090101_1990090130_FIELD.nc'
                )
            self.assertEqual(target, '1m')

    def test_datestamp_period_noncf_mod(self):
        '''Test datestamp_period from filename - non-cf, new target'''
        func.logtest('Assert extraction of target from fname - non-cf:')

        with mock.patch('modeltemplate.ModelTemplate.cfcompliant_output',
                        new_callable=mock.PropertyMock,
                        return_value=False):
            target = self.model.datestamp_period(
                'RUNIDo_1d_19900901_19900910_FIELD.nc'
                )
            self.assertEqual(target, '10d')

            target = self.model.datestamp_period(
                'RUNIDo_1d_19900901_19900930_FIELD.nc'
                )
            self.assertEqual(target, '1m')

            target = self.model.datestamp_period(
                'RUNIDx_6h_1990090100_1990090111_FIELD.nc'
                )
            self.assertEqual(target, '12h')

            target = self.model.datestamp_period(
                'RUNIDo_12h_21280801_21280830_FIELD-A.nc'
                )
            self.assertEqual(target, '1m')

    def test_datestamp_period_shortdate(self):
        '''Test datestamp_period from filename - non-cf, new target'''
        func.logtest('Assert extraction of target from fname - non-cf:')

        with mock.patch('modeltemplate.ModelTemplate.cfcompliant_output',
                        new_callable=mock.PropertyMock,
                        return_value=False):
            target = self.model.datestamp_period(
                'RUNIDo_1d_19500901_19501230_FIELD_195011-195011.nc'
                )
            self.assertEqual(target, '1m')

    def test_archive_timetamps_single(self):
        '''Test return of timestamps method - archive single'''
        func.logtest('Assert return of timestamps method - archive single:')
        self.model.naml.archive_timestamps = '12-01'
        self.assertTrue(self.model.timestamps('12', '01'))
        self.assertFalse(self.model.timestamps('06', '01'))

    def test_archive_timetamps_list(self):
        '''Test return of timestamps method - archive list'''
        func.logtest('Assert return of timestamps method - archive list:')
        self.model.naml.archive_timestamps = ['06-01', '12-01']
        self.assertTrue(self.model.timestamps('06', '01'))
        self.assertTrue(self.model.timestamps('12', '01'))
        self.assertFalse(self.model.timestamps('11', '01'))

    def test_rebuild_timetamps_single(self):
        '''Test return of timestamps method - rebuild single'''
        func.logtest('Assert return of timestamps method - rebuild single:')
        self.model.naml.rebuild_timestamps = '12-01'
        self.assertTrue(self.model.timestamps('12', '01', process='rebuild'))
        self.assertFalse(self.model.timestamps('06', '01', process='rebuild'))

    def test_rebuild_timetamps_list(self):
        '''Test return of timestamps method - rebuild list'''
        func.logtest('Assert return of timestamps method - rebuild list:')
        self.model.naml.rebuild_timestamps = ['06-01', '12-01']
        self.assertTrue(self.model.timestamps('06', '01', process='rebuild'))
        self.assertTrue(self.model.timestamps('12', '01', process='rebuild'))
        self.assertFalse(self.model.timestamps('11', '01', process='rebuild'))


class PropertyTests(unittest.TestCase):
    '''Unit tests relating to ModelTemplate properties'''

    def setUp(self):
        with mock.patch('modeltemplate.nlist.loadNamelist') as mock_nl:
            mock_nl().modeltemplate.base_component = '10d'
            mock_nl().modeltemplate.debug = False
            self.model = modeltemplate.ModelTemplate()

    def tearDown(self):
        pass

    def test_methods(self):
        '''Test return value of the methods property'''
        func.logtest('Assert correct return from methods property:')
        all_methods = ['archive_restarts', 'move_to_share',
                       'create_general', 'create_means',
                       'archive_general', 'archive_means', 'finalise_debug']
        self.assertListEqual(self.model.methods.keys(), all_methods)

    def test_additional_mean_single(self):
        '''Test additional_means property value - single value'''
        func.logtest('Assert return of additional means - single value:')
        self.model.naml.means_to_archive = None
        self.assertEqual(self.model.additional_means, [])
        self.model.naml.means_to_archive = '12h'
        self.assertEqual(self.model.additional_means, ['12h'])

    def test_additional_means_list(self):
        '''Test additional_means property value - list'''
        func.logtest('Assert return of additional means - list:')
        self.model.naml.means_to_archive = ['12h', '10d']
        self.assertEqual(self.model.additional_means, ['12h', '10d'])
