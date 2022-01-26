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
import os
import copy
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
    import mock

import testing_functions as func
import runtime_environment

import netcdf_filenames

# Import of modeltemplate requires 'RUNID' from runtime environment
runtime_environment.setup_env()
import modeltemplate
import template_namelist

NLFILE = 'mt_namelist'

def create_namelist():
    '''
    Create a namelist file from the template namelist objects.
    Required because modeltemplate namelists are not called through control
    so we can't use the ususal nlist.py method create_example_nl().
    '''
    namelists = {'modeltemplate_pp' : template_namelist.TopLevel,
                 'modeltemplate_processing': template_namelist.Processing,
                 'modeltemplate_archiving': template_namelist.Archiving,
                 'suitegen': modeltemplate.suite.SuitePostProc,
                 'moose_arch': modeltemplate.utils.Variables}
    nl_text = ''
    for nlist in namelists:
        nl_text += '\n&' + nlist
        for attr in [a for a in dir(namelists[nlist])]:
            if attr.startswith('_'):
                continue
            val = getattr(namelists[nlist], attr)
            if isinstance(val, (tuple, list)):
                val = ','.join([str(x) for x in val])
            nl_text += '\n{}={},'.format(attr, str(val))
        nl_text += '\n/\n'

    with open(NLFILE, 'w') as outfile:
        outfile.write(nl_text)


class StencilTests(unittest.TestCase):
    '''Unit tests relating to the MODEL output filename stencils'''

    def setUp(self):
        with mock.patch('template_namelist.TopLevel.pp_run',
                        new_callable=mock.PropertyMock, return_value=True):
            create_namelist()
            with mock.patch('modeltemplate.ModelTemplate._directory',
                            return_value='.'):
                self.model = modeltemplate.ModelTemplate(input_nl=NLFILE)

        self.ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X')

    def tearDown(self):
        try:
            os.remove(NLFILE)
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

    @mock.patch('modeltemplate.netcdf_filenames.period_end')
    def test_end_stencil_decadal(self, mock_end):
        '''Test the call to period_end by end_stencil method - decadal'''
        func.logtest('Assert annual pattern matching of end_stencil:')
        _ = self.model.end_stencil('1x', self.ncf)
        mock_end.assert_called_once_with('1x', self.ncf, [0, 12, 1])

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
        with mock.patch('template_namelist.TopLevel.pp_run',
                        new_callable=mock.PropertyMock, return_value=True):
            create_namelist()
            with mock.patch('modeltemplate.ModelTemplate._directory',
                            return_value='ModelDir'):
                self.model = modeltemplate.ModelTemplate(input_nl=NLFILE)

        self.model.share = 'ShareDir'
        self.model.naml.processing.create_monthly_mean = True
        self.model.naml.processing.create_seasonal_mean = True
        self.model.naml.processing.create_annual_mean = True
        self.model.naml.processing.create_decadal_mean = True
        self.model.naml.processing.base_component = '10d'
        self.model.requested_means = modeltemplate.climatemean.available_means(
            self.model.naml.processing
            )

        self.ncf = netcdf_filenames.NCFilename(
            'MODEL', 'RUNID', 'X',
            start_date=('2001', '01', '21'), base='1m', custom='_FIELD'
            )

    def tearDown(self):
        try:
            os.remove(NLFILE)
        except OSError:
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
        self.model.naml.processing.create_monthly_mean = False
        self.model.naml.processing.create_seasonal_mean = False
        self.model.naml.processing.create_decadal_mean = False
        self.model.naml.processing.base_component = '1m'
        self.model.requested_means = modeltemplate.climatemean.available_means(
            self.model.naml.processing
            )
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
    def test_period_set_decadal(self, mock_subset):
        '''Test function of the periodfiles method - decade set'''
        func.logtest('Assert pattern from periodfiles method - decade set:')
        ncf = copy.copy(self.ncf)
        ncf.start_date = ('2001', '02', '01')
        ncf.base = '1x'
        _ = self.model.periodfiles(ncf, 'set')
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_1y_(19920201|19930201|19940201|19950201|19960201'
            r'|19970201|19980201|19990201|20000201|20010201)(\d{2})?'
            r'-\d{8,10}_FIELD\.nc$'
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
        func.logtest('Assert pattern by periodset - archive year set:')
        ncf = copy.copy(self.ncf)
        ncf.start_date = ('2001', '09', '01')
        ncf.base = '1y'
        _ = self.model.periodfiles(ncf, 'set', archive_mean=True)
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_1y_(19920901|19930901|19940901|19950901|19960901|'
            r'19970901|19980901|19990901|20000901|20010901)(\d{2})?'
            r'-\d{8,10}_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_set_arch_decadal(self, mock_subset):
        '''Test function of the periodfiles method - 10y (topmean) arch set'''
        func.logtest('Assert pattern by periodfiles - topmean decadal set:')
        ncf = copy.copy(self.ncf)
        ncf.start_date = ('2001', '09', '01')
        ncf.base = '1x'
        _ = self.model.periodfiles(ncf, 'set', archive_mean=True)
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'model_runidx_1x_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}_FIELD.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_end_monthly(self, mock_subset):
        '''Test function of the periodfiles method - month end'''
        func.logtest('Assert pattern by periodfiles method - month end:')
        ncf = copy.copy(self.ncf)
        _ = self.model.periodfiles(ncf, 'end')
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_10d_\d{8,10}-\d{4}\d{2}01(00)?_FIELD\.nc$'
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
            r'^model_runidx_1m_\d{8,10}-\d{4}(12|03|06|09)01(00)'
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
            r'^model_runidx_1m_\d{8,10}-\d{4}(01|04|07|10)01(00)'
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
            r'^model_runidx_1s_\d{8,10}-\d{4}1201(00)?_FIELD\.nc$'
            )

        ncf = copy.copy(self.ncf)
        ncf.base = '1y'
        with mock.patch('modeltemplate.suite.SuiteEnvironment.meanref',
                        new_callable=mock.PropertyMock,
                        return_value=[2000, 1, 1]):
            _ = self.model.periodfiles(ncf, 'end')
        mock_subset.assert_called_with(
            'ShareDir',
            r'^model_runidx_1s_\d{8,10}-\d{4}0101(00)?_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_end_decadal(self, mock_subset):
        '''Test function of the periodfiles method - decade end'''
        func.logtest('Assert pattern by periodfiles method - decade end:')
        ncf = copy.copy(self.ncf)
        ncf.base = '1x'
        _ = self.model.periodfiles(ncf, 'end')
        mock_subset.assert_called_once_with(
            'ShareDir',
            r'^model_runidx_1y_\d{8,10}-\d{3}01201(00)?_FIELD\.nc$'
            )

        ncf = copy.copy(self.ncf)
        ncf.base = '1x'
        with mock.patch('modeltemplate.suite.SuiteEnvironment.meanref',
                        new_callable=mock.PropertyMock,
                        return_value=[1978, 1, 1]):
            _ = self.model.periodfiles(ncf, 'end')
        mock_subset.assert_called_with(
            'ShareDir',
            r'^model_runidx_1y_\d{8,10}-\d{3}80101(00)?_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_end_datadir(self, mock_subset):
        '''Test function of the periodfiles end method - with datadir'''
        func.logtest('Assert pattern by periodfiles end method - datadir:')
        ncf = copy.copy(self.ncf)
        _ = self.model.periodfiles(ncf, 'end', datadir='MyDir')
        mock_subset.assert_called_once_with(
            'MyDir',
            r'^model_runidx_10d_\d{8,10}-\d{4}\d{2}01(00)?_FIELD\.nc$'
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
            r'^model_runidx_1m_\d{8,10}-\d{4}(12|03|06|09)01(00)'
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
            r'^model_runidx_1s_\d{8,10}-\d{4}1201(00)?_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_end_arch_annual(self, mock_subset):
        '''Test function of the periodfiles method - year end archive'''
        func.logtest('Assert pattern by periodfiles - archive year end:')
        ncf = copy.copy(self.ncf)
        self.model.suite.naml.mean_reference_date = [1234, 5, 67]
        ncf.base = '1y'
        _ = self.model.periodfiles(ncf, 'end', archive_mean=True)
        mock_subset.assert_called_with(
            'ShareDir',
            r'^model_runidx_1y_\d{8,10}-\d{3}40567(00)?_FIELD\.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_period_end_arch_decadal(self, mock_subset):
        '''Test function of the periodfiles method - decade end archive'''
        func.logtest('Assert pattern by periodfiles - archive decade end:')
        ncf = copy.copy(self.ncf)
        ncf.base = '1x'
        _ = self.model.periodfiles(ncf, 'end', archive_mean=True)
        mock_subset.assert_called_with(
            'ShareDir',
            r'model_runidx_1x_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}_FIELD.nc$'
            )

    @mock.patch('modeltemplate.utils.get_subset')
    def test_periodfiles_arch_1s_only(self, mock_subset):
        '''Test function of the periodfiles method - archive 1s only'''
        func.logtest('Assert pattern by periodfiles - archive 1s only:')
        ncf = copy.copy(self.ncf)
        ncf.base = '1s'
        self.model.naml.processing.create_monthly_mean = False
        self.model.naml.processing.create_annual_mean = False
        self.model.naml.processing.create_decadal_mean = False
        self.model.naml.processing.base_component = '1m'

        self.model.requested_means = modeltemplate.climatemean.available_means(
            self.model.naml.processing
            )

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
        with mock.patch('template_namelist.TopLevel.pp_run',
                        new_callable=mock.PropertyMock, return_value=True):
            create_namelist()
            with mock.patch('modeltemplate.ModelTemplate._directory',
                            return_value='ModelDir'):
                self.model = modeltemplate.ModelTemplate(input_nl=NLFILE)

        self.model.share = 'ShareDir'
        self.model.naml.processing.create_monthly_mean = True
        self.model.naml.processing.create_seasonal_mean = True
        self.model.naml.processing.create_annual_mean = True
        self.model.naml.processing.create_decadal_mean = True
        self.model.naml.processing.base_component = '10d'
        self.model.requested_means = modeltemplate.climatemean.available_means(
            self.model.naml.processing
            )


        self.model.loop_inputs = mock.Mock()
        self.model.get_date = mock.Mock(return_value=('1996', '09', '01'))
        self.model.periodfiles = mock.Mock()
        self.model.preprocess_meanset = mock.Mock()
        self.model.mean_stencil = mock.Mock(return_value='MeanFileName')
        self.model.fix_mean_time = mock.Mock()

        self.model.suite = mock.Mock()
        self.model.suite.initpoint = [0]*5

        self.ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1d')

    def tearDown(self):
        try:
            os.remove(NLFILE)
        except OSError:
            pass

        for dirname in [self.model.diagsdir, 'ModelDir']:
            try:
                os.rmdir(dirname)
            except OSError:
                pass

    @mock.patch('modeltemplate.os.path')
    @mock.patch('modeltemplate.utils.move_files')
    @mock.patch('modeltemplate.climatemean.create_mean', return_value=0)
    def test_create_means_mv_cmpts(self, mock_create, mock_mv, mock_path):
        '''Test successful creation of means - move components'''
        func.logtest('Assert successful creation of a mean - move components:')
        self.ncf.base = '1y'
        self.ncf.custom = 'FIELD'
        self.model.loop_inputs.return_value = [self.ncf]
        cmpt_files = ['ssn' + str(x) for x in range(1, 4)]
        self.model.periodfiles.side_effect = [['setend'], cmpt_files]
        mock_path.isfile.side_effect = [True]

        with mock.patch('modeltemplate.utils.create_dir'):
            self.model.create_means()

        self.model.preprocess_meanset.assert_called_once_with(cmpt_files)

        cmd = '{} {} MeanFileName'.format(self.model.means_cmd,
                                          ' '.join(cmpt_files))
        mock_create.assert_called_once_with(mock.ANY, cmd, [0]*5)
        self.assertTrue(isinstance(mock_create.call_args[0][0],
                                   modeltemplate.climatemean.MeanFile))
        self.assertEqual(mock_create.call_args[0][0].period, '1y')
        self.assertEqual(mock_create.call_args[0][0].component, '1s')
        self.assertEqual(mock_create.call_args[0][0].periodend,
                         ('1996', '09', '01'))
        self.assertEqual(mock_create.call_args[0][0].title, 'FIELD Annual')
        self.assertListEqual(mock_create.call_args[0][0].component_files,
                             cmpt_files)

        mock_mv.assert_called_once_with(cmpt_files,
                                        'ModelDir/archive_ready',
                                        originpath='ShareDir')
        self.assertEqual(len(self.model.fix_mean_time.mock_calls), 1)

    @mock.patch('modeltemplate.os.path')
    @mock.patch('modeltemplate.utils.remove_files')
    @mock.patch('modeltemplate.climatemean.create_mean', return_value=0)
    def test_create_means_del_cmpts(self, mock_create, mock_rm, mock_path):
        '''Test successful creation of means - delete base components'''
        func.logtest('Assert deletion of base components after means creation:')
        self.ncf.base = '1m'
        self.model.loop_inputs.return_value = [self.ncf]
        cmpt_files = ['month' + str(x) for x in range(1, 3)]
        self.model.periodfiles.side_effect = [['setend'], cmpt_files]
        mock_path.isfile.side_effect = [True]

        with mock.patch('modeltemplate.utils.create_dir'):
            self.model.create_means()

        self.model.preprocess_meanset.assert_called_once_with(cmpt_files)

        cmd = '{} {} MeanFileName'.format(self.model.means_cmd,
                                          ' '.join(cmpt_files))
        mock_create.assert_called_once_with(mock.ANY, cmd, [0]*5)
        self.assertTrue(isinstance(mock_create.call_args[0][0],
                                   modeltemplate.climatemean.MeanFile))
        self.assertEqual(mock_create.call_args[0][0].period, '1m')
        self.assertEqual(mock_create.call_args[0][0].component, '10d')
        self.assertEqual(mock_create.call_args[0][0].title, 'Monthly')
        self.assertListEqual(mock_create.call_args[0][0].component_files,
                             cmpt_files)

        mock_rm.assert_called_once_with(cmpt_files, path='ShareDir')
        self.assertIn('Deleting component means for MeanFileName',
                      func.capture())
        self.assertEqual(len(self.model.fix_mean_time.mock_calls), 1)


    @mock.patch('modeltemplate.os.path')
    @mock.patch('modeltemplate.utils.move_files')
    @mock.patch('modeltemplate.utils.remove_files')
    @mock.patch('modeltemplate.climatemean.create_mean', return_value=0)
    def test_create_means_leave_cmpts(self, mock_create, mock_rm, mock_mv,
                                      mock_path):
        '''Test successful creation of means - leave base components'''
        func.logtest('Assert base components untouched after means creation:')
        self.model.naml.processing.create_monthly_mean = False
        self.model.naml.processing.create_decadal_mean = False
        self.model.naml.processing.base_component = '1s'
        self.model.requested_means = modeltemplate.climatemean.available_means(
            self.model.naml.processing
            )

        self.ncf.base = '1s'
        self.model.loop_inputs.return_value = [self.ncf]
        cmpt_files = ['ssn' + str(x) for x in range(1, 3)]
        self.model.periodfiles.side_effect = [['setend'], cmpt_files]
        mock_path.isfile.side_effect = [True]

        with mock.patch('modeltemplate.utils.create_dir'):
            self.model.create_means()

        self.model.preprocess_meanset.assert_called_once_with(cmpt_files)

        cmd = '{} {} MeanFileName'.format(self.model.means_cmd,
                                          ' '.join(cmpt_files))
        mock_create.assert_called_once_with(mock.ANY, cmd, [0]*5)
        self.assertTrue(isinstance(mock_create.call_args[0][0],
                                   modeltemplate.climatemean.MeanFile))
        self.assertEqual(mock_create.call_args[0][0].period, '1s')
        self.assertEqual(mock_create.call_args[0][0].component, '1s')
        self.assertListEqual(mock_create.call_args[0][0].component_files,
                             cmpt_files)

        self.assertListEqual(mock_rm.mock_calls, [])
        self.assertListEqual(mock_mv.mock_calls, [])
        self.assertEqual(len(self.model.fix_mean_time.mock_calls), 1)

    @mock.patch('modeltemplate.os.path')
    @mock.patch('modeltemplate.climatemean.create_mean')
    def test_create_means_fail(self, mock_create, mock_path):
        '''Test successful creation of means - move components'''
        func.logtest('Assert successful creation of a mean - move components:')

        self.ncf.base = '1y'
        self.model.loop_inputs.return_value = [self.ncf]
        cmpt_files = ['ssn' + str(x) for x in range(1, 4)]
        self.model.periodfiles.side_effect = [['setend'], cmpt_files]
        mock_path.isfile.side_effect = [False]

        with mock.patch('modeltemplate.utils.create_dir'):
            self.model.create_means()

        cmd = '{} {} MeanFileName'.format(self.model.means_cmd,
                                          ' '.join(cmpt_files))
        mock_create.assert_called_once_with(mock.ANY, cmd, [0]*5)
        self.assertListEqual(self.model.fix_mean_time.mock_calls, [])


class ArchiveTests(unittest.TestCase):
    '''Unit tests relating to archiving of files'''

    def setUp(self):
        with mock.patch('template_namelist.TopLevel.pp_run',
                        new_callable=mock.PropertyMock, return_value=True):
            create_namelist()
            with mock.patch('modeltemplate.ModelTemplate._directory',
                            return_value='ModelDir'):
                self.model = modeltemplate.ModelTemplate(input_nl=NLFILE)

        self.model.share = os.getcwd()
        self.model.diagsdir = os.path.join('ModelDir', 'archive_ready')
        self.model.naml.processing.create_monthly_mean = True
        self.model.naml.processing.create_seasonal_mean = True
        self.model.naml.processing.create_annual_mean = True
        self.model.naml.processing.base_component = '10d'
        self.model.requested_means = modeltemplate.climatemean.available_means(
            self.model.naml.processing
            )

        self.model.suite = mock.Mock()
        self.model.suite.finalcycle = False
        self.model.suite.cyclepoint = \
            modeltemplate.utils.CylcCycle(cyclepoint='20000901T0000Z')
        self.model.suite.archive_file.return_value = 0

        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X')
        self.model.loop_inputs = mock.Mock(return_value=[ncf])
        self.model.get_date = mock.Mock(return_value=('1996', '05', '01'))
        self.model.component = mock.Mock(return_value='component')

    def tearDown(self):
        for fname in [NLFILE, '12h_field1', '10d_field1', 'xd_field2',
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
        self.model.naml.archiving.archive_restart_buffer = 5
        self.assertEqual(self.model.buffer_archive, 5)

    def test_buffer_archive_finalcycle(self):
        '''Test return of archive buffer property - final cycle'''
        func.logtest('Assert return of archive buffer - final cycle:')
        self.model.naml.archiving.archive_restart_buffer = 5
        self.model.suite.finalcycle = True
        self.assertEqual(self.model.buffer_archive, 0)

    def test_prepare_archive_restarts(self):
        ''' Test call to rebuild_restarts '''
        self.model.rebuild_restarts = mock.Mock()
        self.model.naml.archiving.archive_restarts = False
        self.model.prepare_archive()
        self.assertListEqual(self.model.rebuild_restarts.mock_calls, [])

        self.model.naml.archiving.archive_restarts = True
        self.model.prepare_archive()
        self.model.rebuild_restarts.assert_called_once_with()

    @mock.patch('modeltemplate.utils.move_files')
    def test_prepare_archive_means(self, mock_mv):
        '''Test prepare_archive'''
        func.logtest('Assert correct prepare_archive functionality:')
        self.model.diagsdir = 'DiagDir'
        self.model.periodfiles = mock.Mock(side_effect=[['setend'],
                                                        ['mean1', 'mean2']])
        self.model.compress_netcdf_files = mock.Mock()
        self.model.naml.archiving.archive_means = True

        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        return_value='x'):
            with mock.patch('modeltemplate.ModelTemplate.prefix',
                            new_callable=mock.PropertyMock,
                            return_value='RUNID'):
                self.model.prepare_archive()

        self.assertListEqual(mock_mv.mock_calls,
                             [mock.call(['mean1', 'mean2'], 'DiagDir',
                                        originpath=os.getcwd())])
        self.assertListEqual(self.model.compress_netcdf_files.mock_calls, [])

    @mock.patch('modeltemplate.utils.move_files')
    @mock.patch('modeltemplate.utils.get_subset')
    def test_prep_archive_means_add(self, mock_set, mock_mv):
        '''Test prepare_archive - additional files'''
        func.logtest('Assert prepare_archive - additional files:')
        mock_set.side_effect = [['add1', 'add2']]
        self.model.diagsdir = 'DiagDir'
        self.model.periodfiles = mock.Mock(side_effect=[[]])
        self.model.naml.archiving.archive_means = True
        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        return_value='x'):
            with mock.patch('modeltemplate.ModelTemplate.prefix',
                            new_callable=mock.PropertyMock,
                            return_value='RUNID'):
                with mock.patch('modeltemplate.ModelTemplate.additional_means',
                                new_callable=mock.PropertyMock,
                                return_value=['10x']):
                    self.model.prepare_archive()

        pattern = r'.*_runidx_(10x)_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}.nc'
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call(os.getcwd(), pattern)])
        self.assertListEqual(mock_mv.mock_calls,
                             [mock.call(['add1', 'add2'], 'DiagDir',
                                        originpath=os.getcwd())])

    @mock.patch('modeltemplate.utils.move_files')
    @mock.patch('modeltemplate.utils.get_subset')
    def test_prep_archive_means_addmore(self, mock_set, mock_mv):
        '''Test prepare_archive - additional files, multi field'''
        func.logtest('Assert prepare_archive - additional files, multi field:')
        mock_set.side_effect = [['addF1a', 'addF1b', 'addF2']]
        self.model.diagsdir = 'DiagDir'
        self.model.periodfiles = mock.Mock(side_effect=[[]])
        self.model.mean_fields = ['F1', 'F2']
        self.model.naml.archiving.archive_means = True
        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        return_value='x'):
            with mock.patch('modeltemplate.ModelTemplate.prefix',
                            new_callable=mock.PropertyMock,
                            return_value='RUNID'):
                with mock.patch('modeltemplate.ModelTemplate.additional_means',
                                new_callable=mock.PropertyMock,
                                return_value=['10x']):
                    self.model.prepare_archive()

        pattern = r'.*_runidx_(10x)_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}_(F1|F2).nc'
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call(os.getcwd(), pattern)])
        self.assertListEqual(mock_mv.mock_calls,
                             [mock.call(['addF1a', 'addF1b', 'addF2'],
                                        'DiagDir', originpath=os.getcwd())])

    @mock.patch('modeltemplate.shutil.copy2')
    @mock.patch('modeltemplate.utils.get_subset')
    def test_prep_archive_means_fcycle(self, mock_set, mock_cp):
        '''Test prepare_archive - final cycle'''
        func.logtest('Assert correct prepare_archive functionality - final:')
        mock_set.side_effect = [['1m_file1', '1m_file2',
                                 '1s_file1', '1s_file2']]
        self.model.diagsdir = 'DiagDir'
        self.model.periodfiles = mock.Mock(side_effect=[[]])
        self.model.naml.archiving.archive_means = True
        self.model.suite.finalcycle = True

        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        return_value='x'):
            with mock.patch('modeltemplate.ModelTemplate.prefix',
                            new_callable=mock.PropertyMock,
                            return_value='RUNID'):
                self.model.prepare_archive()

        pattern = r'.*_runidx_(1m|1s|1y)_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}.nc'
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call(os.getcwd(), pattern)])

        fname = os.path.join(os.getcwd(), '{}_file{}')
        self.assertListEqual(
            mock_cp.mock_calls,
            [mock.call(fname.format('1m', 1), 'DiagDir'),
             mock.call(fname.format('1m', 2), 'DiagDir'),
             mock.call(fname.format('1s', 1), 'DiagDir'),
             mock.call(fname.format('1s', 2), 'DiagDir')])

    @mock.patch('modeltemplate.utils.get_subset')
    def test_prep_archive_means_cpfail(self, mock_set):
        '''Test prepare_archive - final cycle with copy failure'''
        func.logtest('Assert prepare_archive functionality - final cp fail:')
        mock_set.side_effect = [['file_1m', 'file_1s',]]
        self.model.diagsdir = 'DiagDir'
        self.model.periodfiles = mock.Mock(side_effect=[[]])
        self.model.naml.archiving.archive_means = True
        self.model.suite.finalcycle = True

        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        return_value='x'):
            with mock.patch('modeltemplate.ModelTemplate.prefix',
                            new_callable=mock.PropertyMock,
                            return_value='RUNID'):
                with self.assertRaises(SystemExit):
                    self.model.prepare_archive()

        pattern = r'.*_runidx_(1m|1s|1y)_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}.nc'
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call(os.getcwd(), pattern)])
        self.assertIn('Failed to copy', func.capture('err'))

    def test_prep_arch_means_compress(self):
        '''Test prepare_archive with compression'''
        func.logtest('Assert compression of prepared means:')
        self.model.periodfiles = mock.Mock()
        self.model.periodfiles.side_effect = [[]]
        self.model.mean_fields = ['grid-1', 'scalar']
        self.model.compress_netcdf_files = mock.Mock()
        self.model.naml.archiving.archive_means = True
        self.model.naml.processing.compression_level = 5

        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        return_value='x'):
            self.model.prepare_archive()

        self.model.compress_netcdf_files.\
            assert_called_once_with('(1m|1s|1y)', 'grid-1')

    @mock.patch('modeltemplate.utils')
    @mock.patch('modeltemplate.os.rename')
    def test_compress_netcdf(self, mock_rename, mock_utils):
        '''Test compress_netcdf_files'''
        func.logtest('Assert behaviour of compress_netcdf_files:')

        self.model.naml.processing.compress_netcdf = 'comp_util'
        self.model.naml.processing.compression_level = 5
        self.model.naml.processing.chunking_arguments = 'chunks'

        self.model.compress_file = mock.Mock(return_value=0)

        mock_utils.add_path.return_value = ['f1', 'f2_COMPRESS_FAILED']

        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        return_value='x'):
            with mock.patch('modeltemplate.ModelTemplate.prefix',
                            new_callable=mock.PropertyMock,
                            return_value='RUNID'):
                self.model.compress_netcdf_files('1x', 'grid')

        mock_rename.assert_called_once_with('f2_COMPRESS_FAILED', 'f2')

        pattern = r'component_runidx_1x_\d{4}\d{2}\d{2}-' + \
            r'\d{4}\d{2}\d{2}_grid.nc(_COMPRESS_FAILED)?$'
        mock_utils.get_subset.assert_called_once_with('ModelDir/archive_ready',
                                                      pattern)

        call_compress = []
        for fname in ['f1', 'f2']:
            call_compress.append(mock.call(fname, 'comp_util',
                                           compression=5, chunking='chunks'))
        self.assertListEqual(self.model.compress_file.mock_calls, call_compress)

    @mock.patch('modeltemplate.utils')
    @mock.patch('modeltemplate.os.rename')
    def test_compress_netcdf_fail(self, mock_rename, mock_utils):
        '''Test compress_netcdf_files - fail'''
        func.logtest('Assert failure of compress_netcdf_files:')

        self.model.naml.processing.compress_netcdf = 'comp_util'
        self.model.naml.processing.compression_level = 5
        self.model.naml.processing.chunking_arguments = 'chunks'

        self.model.compress_file = mock.Mock(return_value=1)

        mock_utils.add_path.return_value = ['f1']

        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        return_value='x'):
            with mock.patch('modeltemplate.ModelTemplate.prefix',
                            new_callable=mock.PropertyMock,
                            return_value='RUNID'):
                self.model.compress_netcdf_files('[6h|1d]', 'grid')

        mock_rename.assert_called_once_with('f1', 'f1_COMPRESS_FAILED')

        pattern = r'component_runidx_[6h|1d]_\d{4}\d{2}\d{2}-' + \
            r'\d{4}\d{2}\d{2}_grid.nc(_COMPRESS_FAILED)?$'
        mock_utils.get_subset.assert_called_once_with('ModelDir/archive_ready',
                                                      pattern)

        self.assertListEqual(self.model.compress_file.mock_calls,
                             [mock.call('f1', 'comp_util',
                                        compression=5, chunking='chunks')])

    @mock.patch('modeltemplate.utils.get_subset')
    @mock.patch('modeltemplate.utils.add_path')
    @mock.patch('modeltemplate.ModelTemplate.archive_files')
    @mock.patch('modeltemplate.ModelTemplate.clean_archived_files')
    def test_archive_means(self, mock_clean, mock_arch,
                           mock_fullname, mock_set):
        '''Test archive_means'''
        func.logtest('Assert correct archive_means functionality:')

        mock_fullname.side_effect = [['file/one', 'file/two']]
        with mock.patch('modeltemplate.ModelTemplate.prefix',
                        new_callable=mock.PropertyMock,
                        return_value='RUNID'):
            with mock.patch('modeltemplate.os.path.exists',
                            return_value=True):
                self.model.archive_means()

        mock_set.assert_called_once_with('ModelDir/archive_ready',
                                         r'runid.*\.nc$')
        mock_fullname.assert_called_once_with(mock_set.return_value,
                                              'ModelDir/archive_ready')
        self.assertListEqual(mock_arch.mock_calls,
                             [mock.call('file/one'), mock.call('file/two')])
        mock_clean.assert_called_with(mock_arch.return_value, 'means files')

    @mock.patch('modeltemplate.utils.get_subset')
    @mock.patch('modeltemplate.utils.add_path')
    @mock.patch('modeltemplate.ModelTemplate.archive_files')
    @mock.patch('modeltemplate.ModelTemplate.clean_archived_files')
    def test_archive_means_multifield(self, mock_clean, mock_arch,
                                      mock_fullname, mock_set):
        '''Test archive_means with multiple fields'''
        func.logtest('Assert correct archive_means functionality:')

        self.model.mean_fields = ['F1', 'F2']
        mock_fullname.side_effect = [['file/one', 'file/two'],
                                     ['file/three', 'file/four']]
        with mock.patch('modeltemplate.ModelTemplate.prefix',
                        new_callable=mock.PropertyMock,
                        return_value='RUNID'):
            with mock.patch('modeltemplate.os.path.exists',
                            return_value=True):
                self.model.archive_means()

        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call('ModelDir/archive_ready', r'runid.*F1\.nc$'),
             mock.call('ModelDir/archive_ready', r'runid.*F2\.nc$')]
            )

        self.assertEqual(len(mock_fullname.mock_calls), 2)
        mock_fullname.assert_called_with(mock_set.return_value,
                                         'ModelDir/archive_ready')
        self.assertListEqual(mock_arch.mock_calls,
                             [mock.call('file/one'), mock.call('file/two'),
                              mock.call('file/three'), mock.call('file/four')])
        mock_clean.assert_called_with(mock_arch.return_value, 'means files')

    @mock.patch('modeltemplate.utils.get_subset')
    @mock.patch('modeltemplate.utils.add_path')
    @mock.patch('modeltemplate.ModelTemplate.archive_files')
    @mock.patch('modeltemplate.ModelTemplate.clean_archived_files')
    def test_archive_nothing(self, mock_clean, mock_arch,
                             mock_fullname, mock_set):
        '''Test archive_means - nothing to archive'''
        func.logtest('Assert correct archive_means functionality:')

        mock_fullname.side_effect = [['file/one', 'file/two']]
        with mock.patch('modeltemplate.ModelTemplate.prefix',
                        new_callable=mock.PropertyMock,
                        return_value='RUNID'):
            with mock.patch('modeltemplate.os.path.exists',
                            return_value=True):
                self.model.archive_means()

        mock_set.assert_called_once_with('ModelDir/archive_ready',
                                         r'runid.*\.nc$')
        mock_fullname.assert_called_once_with(mock_set.return_value,
                                              'ModelDir/archive_ready')
        self.assertListEqual(mock_arch.mock_calls,
                             [mock.call('file/one'), mock.call('file/two')])
        mock_clean.assert_called_with(mock_arch.return_value, 'means files')


    @mock.patch('modeltemplate.ModelTemplate.periodfiles',
                return_value=['rst1', 'rst2'])
    @mock.patch('modeltemplate.utils.remove_files')
    def test_archive_restarts(self, mock_rm, mock_set):
        '''Test archive restarts function'''
        func.logtest('Assert list of restart files to archive:')
        with mock.patch('modeltemplate.ModelTemplate.timestamps',
                        return_value=True):
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
        self.model.suite.finalcycle = True
        with mock.patch('modeltemplate.ModelTemplate.timestamps',
                        return_value=False):
            self.model.archive_restarts()
        self.assertListEqual(mock_rm.mock_calls,
                             [mock.call('rst1', path=os.getcwd())])
        mock_set.assert_called_once_with('', 'set')

    @mock.patch('modeltemplate.ModelTemplate.periodfiles',
                return_value=['rst1', 'rst2'])
    def test_archive_restarts_periodic(self, mock_set):
        '''Test archive restarts function'''
        func.logtest('Assert list of restart files to archive:')
        with mock.patch('modeltemplate.ModelTemplate.timestamps',
                        return_value=False):
            with mock.patch('modeltemplate.utils.remove_files'):
                self.model.archive_restarts()
        self.assertIn('Only archiving periodic', func.capture())
        mock_set.assert_called_once_with('', 'set')

    def test_archive_restarts_nothing(self):
        '''Test archive restarts function - nothing to archive'''
        func.logtest('Assert function with nothing to archive:')
        with mock.patch('modeltemplate.ModelTemplate.periodfiles',
                        return_value=[]):
            self.model.archive_restarts()
        self.assertIn(' -> Nothing to archive', func.capture())
        self.assertNotIn('Deleting', func.capture())

    def test_archive_restarts_retained(self):
        '''Test archive restarts function - files retained'''
        func.logtest('Assert function with files retained:')
        self.model.naml.archiving.archive_restart_buffer = 2
        with mock.patch('modeltemplate.ModelTemplate.periodfiles',
                        return_value=['rst1']):
            self.model.archive_restarts()
        self.assertIn('2 retained', func.capture())
        self.assertIn(' -> Nothing to archive', func.capture())
        self.assertNotIn('Deleting', func.capture())

    def test_archive_rst_beyond_cpoint(self):
        '''Test archive restarts function - all files beong cyclepoint'''
        func.logtest('Assert function with all files beyond cyclepoint:')
        self.model.suite.cyclepoint = \
            modeltemplate.utils.CylcCycle(cyclepoint='19960330T0000Z')
        self.model.naml.archiving.archive_restart_buffer = 2
        with mock.patch('modeltemplate.ModelTemplate.periodfiles',
                        return_value=['rst1']):
            self.model.archive_restarts()
        self.assertNotIn('retained', func.capture())
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
        with mock.patch('modeltemplate.ModelTemplate.timestamps',
                        return_value=True):
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

    @mock.patch('modeltemplate.utils.remove_files')
    def test_clean_archived_files(self, mock_rm):
        '''Test ability to clean successfully archived files'''
        func.logtest('Assert removal of successfully archived files:')
        arch_files = {'file1': 'SUCCESS', 'file2': 'FAILED',
                      'file3': 'MAYBE', 'file4': 'SUCCESS'}
        self.model.share = 'ShareDir'
        self.model.clean_archived_files(arch_files, 'my file')
        mock_rm.assert_called_once_with(['file1', 'file4'], path='ShareDir')
        self.assertIn('my file: deleting archived file(s): ', func.capture())

    @mock.patch('modeltemplate.utils.remove_files')
    def test_clean_archived_files_path(self, mock_rm):
        '''Test ability to clean successfully archived files - with PATH'''
        func.logtest('Assert removal of successfully archived files - PATH:')
        arch_files = {'file1': 'SUCCESS', 'file2': 'FAILED',
                      'file3': 'MAYBE', 'file4': 'SUCCESS'}
        self.model.clean_archived_files(arch_files, 'my file', path='PATH')
        mock_rm.assert_called_once_with(['file1', 'file4'], path='PATH')
        self.assertIn('my file: deleting archived file(s): ', func.capture())

    @mock.patch('modeltemplate.utils.remove_files')
    @mock.patch('modeltemplate.os.rename')
    def test_clean_archived_files_none(self, mock_remove, mock_rm):
        '''Test ability to clean archived files - nothing to do'''
        func.logtest('Assert removal of archived files - nothing to do:')
        arch_files = {'file2': 'FAILED', 'file3': 'MAYBE'}
        self.model.clean_archived_files(arch_files, 'my file')
        self.assertListEqual(mock_rm.mock_calls, [])
        self.assertListEqual(mock_remove.mock_calls, [])

    @mock.patch('modeltemplate.os.rename')
    def test_clean_archived_files_debug(self, mock_rename):
        '''Test ability to clean successfully archived files - debugmode'''
        func.logtest('Assert removal of successfully archived files - debug:')
        arch_files = {'file1': 'SUCCESS', 'file2': 'FAILED',
                      'file3': 'MAYBE', 'file4': 'SUCCESS'}
        self.model.share = 'ShareDir'
        with mock.patch('modeltemplate.utils.get_debugmode', return_value=True):
            self.model.clean_archived_files(arch_files, 'my file')
            self.assertListEqual(
                mock_rename.mock_calls,
                [mock.call('ShareDir/file1', 'ShareDir/file1_ARCHIVED'),
                 mock.call('ShareDir/file4', 'ShareDir/file4_ARCHIVED')]
                )

class PreprocessTests(unittest.TestCase):
    '''Unit tests relating to pre-processing of files prior to archive'''

    def setUp(self):
        with mock.patch('template_namelist.TopLevel.pp_run',
                        new_callable=mock.PropertyMock,
                        return_value=True):
            create_namelist()
            with mock.patch('modeltemplate.suite.SuiteEnvironment'):
                with mock.patch('modeltemplate.ModelTemplate._directory',
                                return_value='ModelDir'):
                    with mock.patch('modeltemplate.utils.CylcCycle'):
                        self.model = modeltemplate.ModelTemplate(
                            input_nl=NLFILE
                            )

        self.model.share = 'ShareDir'

    def tearDown(self):
        try:
            os.remove(NLFILE)
        except OSError:
            pass

    def test_compress_file_nccopy(self):
        '''Test call to file compression method - nccopy'''
        func.logtest('Assert call to file compression method nccopy:')
        _ = self.model.compress_file('meanfile', 'nccopy',
                                     compression=5,
                                     chunking=['a/1', 'b/2', 'c/3'])

        self.assertListEqual(
            self.model.suite.preprocess_file.mock_calls,
            [mock.call('ncdump', 'meanfile', hs='', printout=False),
             mock.ANY,      # Mock call to __contains__
             mock.call('nccopy', 'meanfile', compression=5,
                       chunking=['a/1', 'b/2', 'c/3'])]
        )

    def test_compress_file_nccopy_done(self):
        '''Test call to file compression method - nccopy - already compressed'''
        func.logtest('Assert call to file compression method nccopy - no need:')
        self.model.suite.preprocess_file.side_effect = [
            'ncdump_rtn: time_instant:_DeflateLevel = 5 ;',
            'nccopy_rtnval'
            ]
        _ = self.model.compress_file('meanfile', 'nccopy',
                                     compression=5,
                                     chunking=['a/1', 'b/2', 'c/3'])
        self.model.suite.preprocess_file.assert_called_once_with(
            'ncdump', 'meanfile', hs='', printout=False
            )
        self.assertIn('already compressed', func.capture())

    def test_compress_file_nccopy_noarg(self):
        '''Test call to file compression method - nccopy - no arguments'''
        func.logtest('Assert call to file compression method nccopy - no args:')
        _ = self.model.compress_file('meanfile', 'nccopy')
        self.assertListEqual(self.model.suite.preprocess_file.mock_calls, [])
        self.assertIn('Deflation = 0 requested', func.capture())

    def test_compress_file_badcmd(self):
        '''Test call to file compression method - failure'''
        func.logtest('Assert call to file compression method - fail:')
        self.model.naml.processing.compression_level = 5
        self.model.naml.processing.chunking_arguments = ['a/1', 'b/2', 'c/3']
        with self.assertRaises(SystemExit):
            _ = self.model.compress_file('meanfile', 'utility')
        self.assertIn('command not yet implemented', func.capture('err'))

    def test_compress_file_bad_debug(self):
        '''Test call to file compression method - debug failure'''
        func.logtest('Assert call to file compression method - debug fail:')
        self.model._debug_mode(True)
        self.model.naml.processing.compression_level = 5
        self.model.naml.processing.chunking_arguments = ['a/1', 'b/2', 'c/3']
        rcode = self.model.compress_file('meanfile', 'utility')
        self.assertIn('command not yet implemented', func.capture('err'))
        self.assertEqual(rcode, 99)

    def test_fix_mean_time_one_var(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - single time var')
        self.model.naml.processing.time_vars = 'time_counter'
        self.model.naml.processing.correct_time_variables = True
        self.model.naml.processing.correct_time_bounds_variables = True
        with mock.patch('modeltemplate.netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile', 'time_counter',
                                        do_time=True, do_bounds=True)

    def test_fix_mean_time_multi_var(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - single time var')
        self.model.naml.processing.time_vars = 'time_counter', 'time_centered'
        self.model.naml.processing.correct_time_variables = True
        self.model.naml.processing.correct_time_bounds_variables = True
        with mock.patch('modeltemplate.netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile',
                                        'time_centered',
                                        do_time=True, do_bounds=True)

    def test_fix_mean_time_only(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - time var only')
        self.model.naml.processing.time_vars = 'time_counter', 'time_centered'
        self.model.naml.processing.correct_time_variables = True
        with mock.patch('modeltemplate.netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile',
                                        'time_centered', do_time=True,
                                        do_bounds=False)

    def test_fix_mean_bounds_only(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - bounds var only')
        self.model.naml.processing.correct_time_bounds_variables = True
        with mock.patch('modeltemplate.netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile', 'time',
                                        do_time=False, do_bounds=True)


class MethodsTests(unittest.TestCase):
    '''Unit tests relating to ModelTemplate methods'''

    def setUp(self):
        with mock.patch('template_namelist.TopLevel.pp_run',
                        new_callable=mock.PropertyMock, return_value=True):
            create_namelist()
            with mock.patch('modeltemplate.ModelTemplate._directory',
                            return_value='WorkDir'):
                self.model = modeltemplate.ModelTemplate(input_nl=NLFILE)

        self.model.share = 'ShareDir'

    def tearDown(self):
        try:
            os.remove(NLFILE)
        except OSError:
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
        self.model.naml.processing.create_monthly_mean = True
        self.model.naml.processing.create_seasonal_mean = True
        self.model.naml.processing.create_annual_mean = True
        self.model.naml.processing.base_component = '10d'
        self.model.requested_means = modeltemplate.climatemean.available_means(
            self.model.naml.processing
            )

        yield_prefix = []
        yield_field = []
        yield_period = []
        with mock.patch('modeltemplate.ModelTemplate.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'mod1': ['g1'], 'mod2': ['g2']}):
            with mock.patch('modeltemplate.ModelTemplate.model_realm',
                            return_value='X'):
                for loop_yield in self.model.loop_inputs(['f1']):
                    yield_prefix.append(loop_yield.prefix)
                    yield_field.append(loop_yield.custom)
                    yield_period.append(loop_yield.base)
        self.assertEqual(['mod1_testpx']*3 + ['mod2_testpx']*3, yield_prefix)
        self.assertEqual(['_f1']*3 + ['_f1']*3, yield_field)
        self.assertEqual(['1m', '1s', '1y']*2, yield_period)

    def test_loop_inputs_multifield(self):
        '''Test loop_inputs functionality - multiple fields'''
        func.logtest('Assert behaviour of loop_inputs method - multifield:')
        self.model.naml.processing.create_monthly_mean = True
        self.model.naml.processing.create_seasonal_mean = True
        self.model.naml.processing.create_annual_mean = True
        self.model.naml.processing.base_component = '10d'
        self.model.requested_means = modeltemplate.climatemean.available_means(
            self.model.naml.processing
            )

        yield_prefix = []
        yield_field = []
        yield_period = []
        with mock.patch('modeltemplate.ModelTemplate.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'mod1': ['g1'], 'mod2': ['g2']}):
            with mock.patch('modeltemplate.ModelTemplate.model_realm',
                            return_value='X'):
                for loop_yield in self.model.loop_inputs(['f1', 'f2']):
                    yield_prefix.append(loop_yield.prefix)
                    yield_field.append(loop_yield.custom)
                    yield_period.append(loop_yield.base)
        self.assertEqual(['mod1_testpx']*6 + ['mod2_testpx']*6, yield_prefix)
        self.assertEqual(['_f1']*3 + ['_f2']*3 + ['_f1']*3 + ['_f2']*3,
                         yield_field)
        self.assertEqual(['1m', '1s', '1y']*4, yield_period)

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
                            return_value='x'):
                _ = self.model.filename_components(
                    'RUNIDx.10x.11112233.44445566.nc'
                    )
        mock_ncf.assert_called_once_with('model', 'TESTP', 'x', base='10x',
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
                            return_value='x'):
                with mock.patch('modeltemplate.ModelTemplate.rebuild_suffix',
                                new_callable=mock.PropertyMock,
                                return_value={'REGEX': r'_\d{4}\.nc'}):
                    _ = self.model.filename_components(testfile)

        mock_ncf.assert_called_once_with('model', 'TESTP', 'x', base='1x',
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

    def test_archive_timestamps_single(self):
        '''Test return of timestamps method - archive single'''
        func.logtest('Assert return of timestamps method - archive single:')
        self.model.naml.archiving.archive_restart_timestamps = '12-01'
        self.assertTrue(self.model.timestamps('12', '01'))
        self.assertFalse(self.model.timestamps('06', '01'))

    def test_archive_timestamps_list(self):
        '''Test return of timestamps method - archive list'''
        func.logtest('Assert return of timestamps method - archive list:')
        self.model.naml.archiving.archive_restart_timestamps = ['06-01',
                                                                '12-01']
        self.assertTrue(self.model.timestamps('06', '01'))
        self.assertTrue(self.model.timestamps('12', '01'))
        self.assertFalse(self.model.timestamps('11', '01'))

    def test_rebuild_timestamps_single(self):
        '''Test return of timestamps method - rebuild single'''
        func.logtest('Assert return of timestamps method - rebuild single:')
        self.model.naml.processing.rebuild_restart_timestamps = '12-01'
        self.assertTrue(self.model.timestamps('12', '01', process='rebuild'))
        self.assertFalse(self.model.timestamps('06', '01', process='rebuild'))

    def test_rebuild_timestamps_list(self):
        '''Test return of timestamps method - rebuild list'''
        func.logtest('Assert return of timestamps method - rebuild list:')
        self.model.naml.processing.rebuild_restart_timestamps = ['06-01',
                                                                 '12-01']
        self.assertTrue(self.model.timestamps('06', '01', process='rebuild'))
        self.assertTrue(self.model.timestamps('12', '01', process='rebuild'))
        self.assertFalse(self.model.timestamps('11', '01', process='rebuild'))


class PropertyTests(unittest.TestCase):
    '''Unit tests relating to ModelTemplate properties'''

    def setUp(self):
        with mock.patch('template_namelist.TopLevel.pp_run',
                        new_callable=mock.PropertyMock, return_value=True):
            create_namelist()
            with mock.patch('modeltemplate.ModelTemplate._directory',
                            return_value='.'):
                self.model = modeltemplate.ModelTemplate(input_nl=NLFILE)

    def tearDown(self):
        pass

    def test_methods(self):
        '''Test return value of the methods property'''
        func.logtest('Assert correct return from methods property:')
        all_methods = ['move_to_share', 'create_general', 'create_means',
                       'prepare_archive', 'archive_restarts',
                       'archive_general', 'archive_means', 'finalise_debug']
        self.assertListEqual(list(self.model.methods.keys()), all_methods)

    def test_additional_mean_single(self):
        '''Test additional_means property value - single value'''
        func.logtest('Assert return of additional means - single value:')
        self.model.naml.archiving.means_to_archive = None
        self.assertEqual(self.model.additional_means, [])
        self.model.naml.archiving.means_to_archive = '12h'
        self.assertEqual(self.model.additional_means, ['12h'])

    def test_additional_means_list(self):
        '''Test additional_means property value - list'''
        func.logtest('Assert return of additional means - list:')
        self.model.naml.archiving.means_to_archive = ['12h', '10d']
        self.assertEqual(self.model.additional_means, ['12h', '10d'])
