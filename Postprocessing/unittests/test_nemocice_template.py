#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2016 Met Office. All rights reserved.

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
import re
import mock

import testing_functions as func
import runtime_environment

import utils
import netcdf_filenames

# Import of modeltemplate requires 'RUNID' from runtime environment
runtime_environment.setup_env()
import modeltemplate


class StencilTests(unittest.TestCase):
    '''Unit tests relating to the MODEL output filename stencils'''
    def setUp(self):
        self.files = [
            'model_runido_2d_19950905-19950907_FIELD.nc',
            'model_runido_2d_19950929-19951001_FIELD.nc',
            'model_runido_10d_19950901-19950911_FIELD.nc',
            'model_runido_10d_19950921-19951001_FIELD.nc',
            'model_runido_1m_19951101-19951201_FIELD.nc',
            'model_runido_1s_19960901-19961201_FIELD.nc',
            'model_runido_1y_19941201-19951201_FIELD.nc',
            'model_runido_1y_19951201-19961201_FIELD.nc',
            ]

        with mock.patch('nlist.loadNamelist'):
            self.model = modeltemplate.ModelTemplate()
        self.ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'o',
                                               base='XX',
                                               start_date=('1995', '09', '11'),
                                               custom='_FIELD')

    def tearDown(self):
        for fname in runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_set_stencil_monthly_10days(self):
        '''Test the regex of the set_stencil method - monthly (10days)'''
        func.logtest('Assert monthly (10d) pattern matching of set_stencil:')
        self.ncf.base = '10d'
        patt = re.compile(self.model.set_stencil['1m'](self.ncf))
        month_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(month_set,
                         [fname for fname in self.files if '10d_' in fname])

    def test_set_stencil_monthly_2days(self):
        '''Test the regex of the set_stencil method - monthly (2days)'''
        func.logtest('Assert monthly (10d) pattern matching of set_stencil:')
        self.ncf.base = '2d'
        patt = re.compile(self.model.set_stencil['1m'](self.ncf))
        month_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(month_set,
                         [fname for fname in self.files if '2d_' in fname])

    def test_set_stencil_seasonal(self):
        '''Test the regex of the set_stencil method - seasonal'''
        func.logtest('Assert seasonal pattern matching of set_stencil:')
        self.ncf.start_date = ('1995', '11', '01')
        patt = re.compile(self.model.set_stencil['1s'](self.ncf))
        season_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(season_set,
                         [fname for fname in self.files if '1m_' in fname])

    def test_set_stencil_annual(self):
        '''Test the regex of the set_stencil method - annual'''
        func.logtest('Assert annual pattern matching of set_stencil:')
        self.ncf.start_date = ('1996', '09', '01')
        patt = re.compile(self.model.set_stencil['1y'](self.ncf))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '1s_' in fname])

    def test_end_stencil_monthly(self):
        '''Test the regex of the end_stencil method - monthly'''
        func.logtest('Assert monthly pattern matching of end_stencil:')
        self.ncf.base = '2d'
        patt = re.compile(self.model.end_stencil['1m'](self.ncf))
        month_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(month_set,
                         [fname for fname in self.files if '01_FIELD' in fname
                          and '2d' in fname])

    def test_end_stencil_seasonal(self):
        '''Test the regex of the end_stencil method - seasonal'''
        func.logtest('Assert seasonal pattern matching of end_stencil:')
        patt = re.compile(self.model.end_stencil['1s'](self.ncf))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '1m_' in fname])

    def test_end_stencil_annual(self):
        '''Test the regex of the end_stencil method - annual'''
        func.logtest('Assert annual pattern matching of end_stencil:')
        patt = re.compile(self.model.end_stencil['1y'](self.ncf))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '1s_' in fname])

    def test_mean_stencil_monthly(self):
        '''Test the regular expressions of the mean_stencil method - monthly'''
        func.logtest('Assert monthly pattern matching of mean_stencil:')
        self.ncf.base = '1m'
        self.ncf.start_date = ('1995', '11', '01')
        patt = re.compile(self.model.mean_stencil['1m'](self.ncf))
        month_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(month_set,
                         [fname for fname in self.files if '1m_' in fname])

    def test_mean_stencil_seasonal(self):
        '''Test the regexes of the mean_stencil method - seasonal'''
        func.logtest('Assert seasonal pattern matching of mean_stencil:')
        self.ncf.base = '1s'
        self.ncf.start_date = ('1996', '09', '01')
        patt = re.compile(self.model.mean_stencil['1s'](self.ncf))
        ssn_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(ssn_set,
                         [fname for fname in self.files if '1s_' in fname])

    def test_mean_stencil_annual(self):
        '''Test the regular expressions of the mean_stencil method - annual'''
        func.logtest('Assert annual pattern matching of mean_stencil:')
        self.ncf.base = '1y'
        self.ncf.start_date = ('1995', '12', '01')
        patt = re.compile(self.model.mean_stencil['1y'](self.ncf))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if
                          '1y_' in fname and '19951201-' in fname])

    def test_mean_stencil_all_years(self):
        '''Test the regex of the mean_stencil method - all years'''
        func.logtest('Assert all years pattern matching of mean_stencil:')
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'o',
                                          base='1y', custom='_FIELD')
        patt = re.compile(self.model.mean_stencil['1y'](ncf))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '1y_' in fname])


class PeriodTests(unittest.TestCase):
    '''Unit tests relating to the "get period files" methods'''

    def setUp(self):
        modeltemplate.ModelTemplate._directory = mock.Mock()
        with mock.patch('nlist.loadNamelist'):
            self.model = modeltemplate.ModelTemplate()
            self.model.share = 'ShareDir'
            self.model.naml.base_component = '10d'

        self.basefile = netcdf_filenames.NCFilename(
            'MODEL', 'RUNID', 'X',
            start_date=('2001', '01', '01'), base='10d', custom='_FIELD'
            )
        self.mfile = netcdf_filenames.NCFilename(
            'MODEL', 'RUNID', 'X',
            start_date=('2001', '01', '01'), base='1m', custom='_FIELD'
            )
        self.sfile = netcdf_filenames.NCFilename(
            'MODEL', 'RUNID', 'X',
            start_date=('2001', '01', '01'), base='1s', custom='_FIELD'
            )
        self.yfile = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X',
                                                 base='1y')

    def tearDown(self):
        pass

    @mock.patch('utils.get_subset')
    def test_periodset_monthly(self, mock_subset):
        '''Test function of the periodset method - month'''
        func.logtest('Assert pattern produced by periodset method - month:')
        _ = self.model.periodset(self.mfile)
        mock_subset.assert_called_with(
            'ShareDir', netcdf_filenames.month_set(self.basefile)
            )

    @mock.patch('utils.get_subset')
    def test_periodset_seasonal(self, mock_subset):
        '''Test function of the periodset method - season'''
        func.logtest('Assert pattern produced by periodset method - season:')
        _ = self.model.periodset(self.sfile)
        mock_subset.assert_called_with('ShareDir',
                                       netcdf_filenames.season_set(self.sfile))

    @mock.patch('utils.get_subset')
    def test_periodset_annual(self, mock_subset):
        '''Test function of the periodset method - year'''
        func.logtest('Assert pattern produced by periodset method - year:')
        _ = self.model.periodset(self.yfile)
        mock_subset.assert_called_with('ShareDir',
                                       netcdf_filenames.year_set(self.yfile))

    @mock.patch('utils.get_subset')
    def test_periodset_datadir(self, mock_subset):
        '''Test function of the periodset method - with datadir'''
        func.logtest('Assert pattern produced by periodset method - datadir:')
        _ = self.model.periodset(self.mfile, datadir='MyDir')
        mock_subset.assert_called_with(
            'MyDir', netcdf_filenames.month_set(self.basefile)
            )

    @mock.patch('utils.get_subset')
    def test_periodset_restarts(self, mock_subset):
        '''Test function of the periodset method - with restart file'''
        func.logtest('Assert pattern produced by periodset method - restart:')
        with mock.patch('modeltemplate.ModelTemplate.set_stencil',
                        new_callable=mock.PropertyMock,
                        return_value={'Restarts':
                                      lambda rst: r'{}_date'.format(rst)}):
            _ = self.model.periodset('restart-type')
        mock_subset.assert_called_with('ShareDir', 'restart-type_date')

    @mock.patch('utils.get_subset')
    def test_periodset_arch_monthly(self, mock_subset):
        '''Test function of the periodset method - monthly archive'''
        func.logtest('Assert pattern produced by periodset - archive month:')
        _ = self.model.periodset(self.mfile, archive=True)
        mock_subset.assert_called_with(
            'ShareDir', netcdf_filenames.season_set(self.basefile)
            )

    @mock.patch('utils.get_subset')
    def test_periodset_arch_seasonal(self, mock_subset):
        '''Test function of the periodset method - seasonal archive'''
        func.logtest('Assert pattern produced by periodset - archive season:')
        _ = self.model.periodset(self.sfile, archive=True)
        mock_subset.assert_called_with('ShareDir',
                                       netcdf_filenames.year_set(self.sfile))

    @mock.patch('utils.get_subset')
    def test_periodset_arch_annual(self, mock_subset):
        '''Test function of the periodset method - annual archive'''
        func.logtest('Assert pattern produced by periodset - archive year:')
        _ = self.model.periodset(self.yfile, archive=True)
        mock_subset.assert_called_with(
            'ShareDir', netcdf_filenames.mean_stencil(self.yfile)
            )

    @mock.patch('utils.get_subset')
    def test_periodend_monthly(self, mock_subset):
        '''Test function of the periodend method - month'''
        func.logtest('Assert pattern produced by periodend method - month:')
        _ = self.model.periodend(self.mfile)
        mock_subset.assert_called_with(
            'ShareDir', netcdf_filenames.month_end(self.basefile)
            )

    @mock.patch('utils.get_subset')
    def test_periodend_seasonal(self, mock_subset):
        '''Test function of the periodend method - season'''
        func.logtest('Assert pattern produced by periodend method - season:')
        _ = self.model.periodend(self.sfile)
        mock_subset.assert_called_with('ShareDir',
                                       netcdf_filenames.season_end(self.sfile))

    @mock.patch('utils.get_subset')
    def test_periodend_annual(self, mock_subset):
        '''Test function of the periodend method - year'''
        func.logtest('Assert pattern produced by periodend method - year:')
        _ = self.model.periodend(self.yfile)
        mock_subset.assert_called_with('ShareDir',
                                       netcdf_filenames.year_end(self.yfile))

    @mock.patch('utils.get_subset')
    def test_periodend_datadir(self, mock_subset):
        '''Test function of the periodend method - with datadir'''
        func.logtest('Assert pattern produced by periodend method - datadir:')
        _ = self.model.periodend(self.mfile, datadir='MyDir')
        mock_subset.assert_called_with(
            'MyDir', netcdf_filenames.month_end(self.basefile)
            )

    @mock.patch('utils.get_subset')
    def test_periodend_arch_monthly(self, mock_subset):
        '''Test function of the periodend method - monthly archive'''
        func.logtest('Assert pattern produced by periodend - archive month:')
        _ = self.model.periodend(self.mfile, archive=True)
        mock_subset.assert_called_with(
            'ShareDir', netcdf_filenames.season_end(self.basefile)
            )

    @mock.patch('utils.get_subset')
    def test_periodend_arch_seasonal(self, mock_subset):
        '''Test function of the periodend method - seasonal archive'''
        func.logtest('Assert pattern produced by periodend - archive season:')
        _ = self.model.periodend(self.sfile, archive=True)
        mock_subset.assert_called_with('ShareDir',
                                       netcdf_filenames.year_end(self.sfile))

    @mock.patch('utils.get_subset')
    def test_periodend_arch_annual(self, mock_subset):
        '''Test function of the periodend method - annual archive'''
        func.logtest('Assert pattern produced by periodend - archive year:')
        rtnval = self.model.periodend(self.yfile, archive=True)
        self.assertEqual(mock_subset.mock_calls, [])
        self.assertEqual(rtnval, [None, ])


class MeansTests(unittest.TestCase):
    '''Unit tests relating to creation of means'''

    def setUp(self):
        modeltemplate.ModelTemplate._directory = mock.Mock()
        with mock.patch('nlist.loadNamelist') as mock_nl:
            mock_nl().modeltemplate.pp_run = False
            self.model = modeltemplate.ModelTemplate()
        self.model.share = 'ShareDir'
        self.model.naml.base_component = '10d'

        self.model.loop_inputs = mock.Mock()
        self.model.get_date = mock.Mock(return_value=('1996', '09', '01'))
        self.model.periodend = mock.Mock(return_value=['setend'])
        self.model.periodset = mock.Mock(return_value=['file1', 'file2',
                                                       'file3'])
        self.model.describe_mean = mock.Mock()
        self.model.fix_mean_time = mock.Mock()

        self.model.suite = mock.Mock()
        self.model.suite.envars.INITCYCLE_OVERRIDE = '19950821T0000Z'

    def tearDown(self):
        for fname in runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass

    @mock.patch('modeltemplate.os.path')
    @mock.patch('utils.exec_subproc', side_effect=[(0, 'None')])
    def test_create_annual_mean(self, mock_exec, mock_path):
        '''Test successful creation of annual mean'''
        func.logtest('Assert successful creation of annual mean:')
        mock_path.isfile.side_effect = [False, True]
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X',
                                          base='1y')
        self.model.loop_inputs.return_value = [ncf]
        self.model.periodset.return_value.append('File4')

        with mock.patch('modeltemplate.ModelTemplate.mean_stencil',
                        new_callable=mock.PropertyMock,
                        return_value={'1y': lambda a: 'AnnualMean'}):
            self.model.create_means()
        self.assertIn('[ OK ]  Created', func.capture())
        self.assertIn(': AnnualMean', func.capture())
        cmd = str(self.model.means_cmd) + ' file1 file2 file3 File4 AnnualMean'
        mock_exec.assert_called_once_with(cmd, cwd='ShareDir')

    @mock.patch('utils.remove_files')
    @mock.patch('modeltemplate.os.path')
    @mock.patch('utils.exec_subproc', side_effect=[(0, 'None')])
    def test_create_monthly_mean_10d(self, mock_exec, mock_path, mock_rm):
        '''Test successful creation of monthly mean - 10day base'''
        func.logtest('Assert successful creation of monthly mean - 10d base:')
        mock_path.isfile.side_effect = [False, True]
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1m')
        self.model.loop_inputs = mock.Mock(return_value=[ncf])

        with mock.patch('modeltemplate.ModelTemplate.mean_stencil',
                        new_callable=mock.PropertyMock,
                        return_value={'1m': lambda a: 'MonthlyMean'}):
            self.model.create_means()
        self.assertIn('[ OK ]  Created', func.capture())
        self.assertIn(': MonthlyMean', func.capture())
        mock_rm.assert_called_with(self.model.periodset.return_value,
                                   path='ShareDir')
        cmd = str(self.model.means_cmd) + ' file1 file2 file3 MonthlyMean'
        mock_exec.assert_called_once_with(cmd, cwd='ShareDir')

    @mock.patch('utils.remove_files')
    @mock.patch('modeltemplate.os.path')
    @mock.patch('utils.exec_subproc', side_effect=[(0, 'None')])
    def test_create_monthly_mean_5dbase(self, mock_exec, mock_path, mock_rm):
        '''Test successful creation of monthly mean - 5day base'''
        func.logtest('Assert successful creation of monthly mean - 5d base:')
        mock_path.isfile.side_effect = [False, True]
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1m')
        self.model.loop_inputs = mock.Mock(return_value=[ncf])
        self.model.naml.base_component = '5d'
        self.model.periodset.return_value = ['file1', 'file2', 'file3',
                                             'file4', 'file5', 'file6']

        with mock.patch('modeltemplate.ModelTemplate.mean_stencil',
                        new_callable=mock.PropertyMock,
                        return_value={'1m': lambda a: 'MonthlyMean'}):
            self.model.create_means()
        self.assertIn('[ OK ]  Created', func.capture())
        self.assertIn(': MonthlyMean', func.capture())
        mock_rm.assert_called_with(self.model.periodset.return_value,
                                   path='ShareDir')
        cmd = str(self.model.means_cmd) + \
            ' file1 file2 file3 file4 file5 file6 MonthlyMean'
        mock_exec.assert_called_once_with(cmd, cwd='ShareDir')

    @mock.patch('modeltemplate.os.path')
    @mock.patch('utils.exec_subproc', side_effect=[(99, 'None')])
    def test_create_annual_mean_fail(self, mock_exec, mock_path):
        '''Test failed creation of annual mean'''
        func.logtest('Assert failed creation of annual mean:')
        mock_path.isfile.return_value = False
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1y')
        self.model.loop_inputs.return_value = [ncf]
        self.model.periodset.return_value.append('file4')

        with mock.patch('modeltemplate.ModelTemplate.mean_stencil',
                        new_callable=mock.PropertyMock,
                        return_value={'1y': lambda a: 'AnnualMean'}):
            with self.assertRaises(SystemExit):
                self.model.create_means()
        self.assertIn('Error=99', func.capture('err'))
        cmd = str(self.model.means_cmd) + ' file1 file2 file3 file4 AnnualMean'
        mock_exec.assert_called_once_with(cmd, cwd='ShareDir')

    def test_create_means_partial(self):
        '''Test create_means function with partial period'''
        func.logtest('Assert create_means functionality with partial period:')
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1y')
        self.model.loop_inputs.return_value = [ncf]
        with self.assertRaises(SystemExit):
            self.model.create_means()
        self.assertIn('not possible as only got 3', func.capture('err'))

    def test_create_means_spinup(self):
        '''Test create_means function in spinup mode'''
        func.logtest('Assert create_means functionality in spinup:')
        self.model.naml.base_component = '5d'
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X', base='1m')
        self.model.loop_inputs.return_value = [ncf]
        self.model.means_spinup = mock.Mock(return_value=True)

        self.model.create_means()
        self.assertIn('in spinup mode', func.capture())
        self.assertIn('not possible as only got 3', func.capture())

    def test_annual_mean_spinup(self):
        '''Test Spinup period for annual means'''
        func.logtest('Assert initial spinup period for annual means:')

        for startdate in ['19941211T0000Z', '19951201T0000Z']:
            self.model.suite.envars.INITCYCLE_OVERRIDE = startdate
            func.logtest('Annual mean - Testing start date:' + startdate)
            self.assertTrue(self.model.means_spinup(
                'FIELD Annual mean for YYYY', ('1995', '12', 'DD')
                ))

        for startdate in ['19941201T0000Z', '19941111T0000Z']:
            self.model.suite.envars.INITCYCLE_OVERRIDE = startdate
            func.logtest('Annual mean - Testing start date:' + startdate)
            self.assertFalse(self.model.means_spinup(
                'FIELD Annual mean for YYYY', ('1995', '12', 'DD')
                ))

    def test_seasonal_mean_spinup_yr1(self):
        '''Test Spinup period for seasonal means - first year'''
        func.logtest('Assert initial spinup period for seasonal means - yr1:')

        for startdate in ['19950911T0000Z', '19951001T0000Z',
                          '19951101T0000Z']:
            self.model.suite.envars.INITCYCLE_OVERRIDE = startdate
            func.logtest('Autumn mean - Testing start date:' + startdate)
            self.assertTrue(self.model.means_spinup(
                'FIELD Seasonal mean for SEASON YYYY', ('1995', '11', 'DD')
                ))

        for startdate in ['19950801T0000Z', '19950901T0000Z']:
            self.model.suite.envars.INITCYCLE_OVERRIDE = startdate
            func.logtest('Autumn mean - Testing start date:' + startdate)
            self.assertFalse(self.model.means_spinup(
                'FIELD Seasonal mean for SEASON YYYY', ('1995', '11', 'DD')
                ))

    def test_seasonal_mean_spinup_yr2(self):
        '''Test Spinup period for seasonal means - second year'''
        func.logtest('Assert initial spinup period for seasonal means - yr2:')

        for startdate in ['19951211T0000Z', '19951221T0000Z']:
            self.model.suite.envars.INITCYCLE_OVERRIDE = startdate
            func.logtest('Autumn mean - Testing start date:' + startdate)
            self.assertTrue(self.model.means_spinup(
                'FIELD Seasonal mean for SEASON YYYY', ('1996', '02', 'DD')
                ))

        for startdate in ['19951201T0000Z', '19951001T0000Z']:
            self.model.suite.envars.INITCYCLE_OVERRIDE = startdate
            func.logtest('Autumn mean - Testing start date:' + startdate)
            self.assertFalse(self.model.means_spinup(
                'FIELD Seasonal mean for SEASON YYYY', ('1996', '02', 'DD')
                ))

        for startdate in ['199512211T0000Z', '19950901T0000Z']:
            self.model.suite.envars.INITCYCLE_OVERRIDE = startdate
            func.logtest('Autumn mean - Testing start date:' + startdate)
            self.assertFalse(self.model.means_spinup(
                'FIELD Seasonal mean for SEASON YYYY', ('1996', '05', 'DD')
                ))

    def test_monthly_mean_spinup(self):
        '''Test Spinup period for monthly means'''
        func.logtest('Assert initial spinup period for monthly means:')
        self.assertTrue(self.model.means_spinup(
            'FIELD Monthly mean for MONTH YYYY', ('1995', '08', 'DD')))
        self.assertFalse(self.model.means_spinup(
            'FIELD Monthly mean for MONTH YYYY', ('1995', '09', 'DD')))

        self.model.suite.envars.INITCYCLE_OVERRIDE = '19950901T0000Z'
        self.assertFalse(self.model.means_spinup(
            'FIELD Monthly mean for MONTH YYYY', ('1995', '09', 'DD')))

    def test_spinup_invalid(self):
        '''Test Spinup period for invalid means'''
        func.logtest('Assert initial spinup period for invalid means:')
        self.assertFalse(self.model.means_spinup(
            'FIELD INVALID mean for YYYY', ('1995', '10', 'DD')))
        self.assertIn('[WARN]', func.capture('err'))
        self.assertIn('unknown meantype', func.capture('err'))


class ArchiveTests(unittest.TestCase):
    '''Unit tests relating to archiving of files'''

    def setUp(self):
        utils.set_debugmode(False)
        with mock.patch('nlist.loadNamelist') as mock_nl:
            mock_nl().modeltemplate.pp_run = False
            self.model = modeltemplate.ModelTemplate()
            self.model.share = os.getcwd()

        self.model.naml.buffer_archive = None
        self.model.naml.compression_level = 0

        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X')
        self.model.loop_inputs = mock.Mock(return_value=[ncf])
        self.model.periodend = mock.Mock(return_value=[''])
        self.model.periodset = mock.Mock(return_value=['file1', 'file2'])
        self.model.get_date = mock.Mock(return_value=('1996', '05', '01'))
        self.model.timestamps = mock.Mock()

        self.model.suite = mock.Mock()
        self.model.suite.archive_file.return_value = 0

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
        self.model.naml.buffer_archive = 5
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

    def test_archive_means_debug(self):
        '''Test archive means function - debug mode'''
        func.logtest('Assert list of means files to archive - debug:')
        utils.set_debugmode(True)
        self.model.archive_files = mock.Mock()
        self.model.archive_files.return_value = {
            'file1': 'SUCCESS',
            'file2': 'SUCCESS'
            }
        infiles = [os.path.join(os.getcwd(), fn) for fn in ['file2', 'file1']]
        outfiles = [fn + '_ARCHIVED' for fn in infiles]
        with mock.patch('modeltemplate.ModelTemplate.additional_means',
                        new_callable=mock.PropertyMock, return_value=[]):
            with mock.patch('os.rename') as mock_rm:
                self.model.archive_means()
                self.assertEqual(sorted(mock_rm.mock_calls),
                                 sorted([mock.call(infiles[0], outfiles[0]),
                                         mock.call(infiles[1], outfiles[1])]))
        self.model.archive_files.assert_called_with(['file1', 'file2'])

    def test_archive_additional_means(self):
        '''Test archive additional means for archive'''
        func.logtest('Assert list of additional means to archive:')
        self.model.archive_files = mock.Mock()
        self.model.archive_files.return_value = {}
        self.model.periodset.return_value = []
        self.model.naml.means_to_archive = ['12h', '1d']
        self.model.naml.base_component = '10d'
        self.model.component = mock.Mock(return_value='component')
        all_stencil = {'All': lambda a: '{}_{}'.format(a.base, a.custom)}

        files = ['12h_field1', 'xd_field2']
        for fname in files:
            open(fname, 'w').close()

        self.model.fields = ('field1', 'field2')
        with mock.patch('modeltemplate.ModelTemplate.model_realm',
                        new_callable=mock.PropertyMock,
                        return_value='x'):
            with mock.patch('modeltemplate.ModelTemplate.mean_stencil',
                            new_callable=mock.PropertyMock,
                            return_value=all_stencil):
                self.model.archive_means()

        self.model.archive_files.assert_called_once_with(['12h_field1'])
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
        self.model.naml.compression_level = 5
        self.model.compress_file = mock.Mock(return_value=0)
        with mock.patch('modeltemplate.ModelTemplate.additional_means',
                        new_callable=mock.PropertyMock, return_value=[]):
            with mock.patch('utils.remove_files') as mock_rm:
                self.model.archive_means()
                mock_rm.assert_called_with(['file1', 'file2'],
                                           os.getcwd())
        self.model.archive_files.assert_called_with(['file1', 'file2'])
        self.model.compress_file.assert_called_with(
            'file2', self.model.naml.compress_means)

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
        '''Test archive restarts function'''
        func.logtest('Assert list of restart files to archive:')
        self.model.timestamps.return_value = True
        with mock.patch('utils.remove_files') as mock_rm:
            self.model.archive_restarts()
            mock_rm.assert_called_with(['file2', 'file1'],
                                       os.getcwd())
        self.assertNotIn('Only archiving periodic', func.capture())

    def test_archive_restarts_debug(self):
        '''Test archive restarts function - debug mode'''
        func.logtest('Assert list of restart files to archive - debug:')
        self.model.timestamps.return_value = True
        utils.set_debugmode(True)
        infiles = [os.path.join(os.getcwd(), fn) for fn in ['file2', 'file1']]
        outfiles = [fn + '_ARCHIVED' for fn in infiles]
        with mock.patch('os.rename') as mock_rm:
            self.model.archive_restarts()
            self.assertEqual(sorted(mock_rm.mock_calls),
                             sorted([mock.call(infiles[0], outfiles[0]),
                                     mock.call(infiles[1], outfiles[1])]))
            self.assertNotIn('Only archiving periodic', func.capture())

    def test_archive_restarts_periodic(self):
        '''Test archive restarts function'''
        func.logtest('Assert list of restart files to archive:')
        self.model.timestamps.return_value = False
        with mock.patch('utils.remove_files'):
            self.model.archive_restarts()
        self.assertIn('Only archiving periodic', func.capture())

    def test_archive_nothing(self):
        '''Test archive restarts function - nothing to archive'''
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
        modeltemplate.ModelTemplate._directory = mock.Mock()
        with mock.patch('nlist.loadNamelist'):
            with mock.patch('suite.SuiteEnvironment'):
                self.model = modeltemplate.ModelTemplate()
                self.model.share = 'ShareDir'

    def tearDown(self):
        pass

    def test_compress_file_nccopy(self):
        '''Test call to file compression method - nccopy'''
        func.logtest('Assert call to file compression method nccopy:')
        self.model.naml.compression_level = 5
        self.model.naml.chunking_arguments = ['a/1', 'b/2', 'c/3']
        self.model.compress_file('meanfile', 'nccopy')
        self.model.suite.preprocess_file.assert_called_with(
            'nccopy',
            os.path.join('ShareDir', 'meanfile'),
            compression=5,
            chunking=['a/1', 'b/2', 'c/3']
            )

    def test_compress_file_unknown(self):
        '''Test call to file compression method - failure'''
        func.logtest('Assert call to file compression method - fail:')
        self.model.naml.compression_level = 5
        self.model.naml.chunking_arguments = ['a/1', 'b/2', 'c/3']
        with self.assertRaises(SystemExit):
            self.model.compress_file('meanfile', 'utility')
        self.assertIn('command not yet implemented', func.capture('err'))

    def test_fix_mean_time_one_var(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - single time var')
        self.model.naml.time_vars = 'time_counter'
        self.model.naml.correct_time_variables = True
        self.model.naml.correct_time_bounds_variables = True
        self.model.naml.time_bounds_suffix = '_bounds'
        with mock.patch('netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile', 'time_counter',
                                        do_time=True, do_bounds=True)

    def test_fix_mean_time_multi_var(self):
        '''Test call to netcdf_utils '''
        func.logtest('Assert call to netcdf_utils - single time var')
        self.model.naml.time_vars = 'time_counter', 'time_centered'
        self.model.naml.correct_time_variables = True
        self.model.naml.correct_time_bounds_variables = True
        with mock.patch('netcdf_utils.fix_times') as mock_fix:
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
        with mock.patch('netcdf_utils.fix_times') as mock_fix:
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
        with mock.patch('netcdf_utils.fix_times') as mock_fix:
            self.model.fix_mean_time('Filename', 'meanfile')
            mock_fix.assert_called_with('Filename', 'meanfile', 'time',
                                        do_time=False, do_bounds=True)


class MethodsTests(unittest.TestCase):
    '''Unit tests relating to ModelTemplate methods'''

    def setUp(self):
        with mock.patch('nlist.loadNamelist') as mock_nl:
            mock_nl().suitegen.prefix = 'RUNID'
            mock_nl().modeltemplate.debug = False
            modeltemplate.ModelTemplate._directory = mock.Mock()
            self.model = modeltemplate.ModelTemplate()
            self.model.share = 'ShareDir'
            self.model.work = 'WorkDir'

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
        self.model.move_to_share()
        mock_mv.assert_called_with(['WkFile1', 'WkFile2'], 'ShareDir',
                                   originpath='WorkDir')
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call('WorkDir'), mock.call('ShareDir')])
        self.assertListEqual(self.model.filename_components.mock_calls,
                             [mock.call('ShFile1'),
                              mock.call().rename_ncf('ShareDir/ShFile1'),
                              mock.call('ShFile2'),
                              mock.call().rename_ncf('ShareDir/ShFile2')])
        self.assertTupleEqual(self.model.fields, ('',))

    @mock.patch('modeltemplate.ModelTemplate.get_raw_output')
    @mock.patch('modeltemplate.utils.move_files')
    def test_move_to_share_newfields(self, mock_mv, mock_set):
        '''Test move_to_share functionality - rename fields'''
        func.logtest('Assert no files behaviour of move_to_share method:')
        mock_set.return_value = []
        self.model.fields = ('GRID_1', 'GRID_2')
        self.model.move_to_share()
        self.assertEqual(len(mock_mv.mock_calls), 0)
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call('WorkDir'), mock.call('ShareDir')])
        self.assertTupleEqual(self.model.fields, ('GRID-1', 'GRID-2'))

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

    def test_describe_mean_summer(self):
        '''Test compostion of mean description - seasonal'''
        func.logtest('Assert correct composition of seasonal mean description:')
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X',
                                          start_date=('1111', '06', '01'),
                                          base='1s')
        self.assertIn('Seasonal mean for Summer 1111',
                      self.model.describe_mean(ncf))

    def test_describe_mean_winter(self):
        '''Test compostion of mean description - seasonal'''
        func.logtest('Assert correct composition of seasonal mean description:')
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X',
                                          start_date=('1111', '12', '01'),
                                          base='1s')
        self.assertIn('Seasonal mean for Winter, ending 1112',
                      self.model.describe_mean(ncf))

    def test_describe_mean_annual(self):
        '''Test compostion of mean description - annual'''
        func.logtest('Assert correct composition of annual mean description:')
        ncf = netcdf_filenames.NCFilename('MODEL', 'RUNID', 'X',
                                          start_date=('1111', '09', '01'),
                                          base='1y')
        self.assertIn('Annual mean for year ending December 1111',
                      self.model.describe_mean(ncf))

    @mock.patch('netcdf_filenames.NCFilename')
    def test_components(self, mock_ncf):
        '''Test component extraction'''
        func.logtest('Assert correct extraction of filename components:')
        with mock.patch('modeltemplate.ModelTemplate.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'model': ['F_1', 'F_2']}):
            with mock.patch('modeltemplate.ModelTemplate.model_realm',
                            new_callable=mock.PropertyMock,
                            return_value='x'):
                _ = self.model.filename_components(
                    'RUNIDx.Xp.11112233_44445566_F_1.nc'
                    )
        mock_ncf.assert_called_once_with('model', 'RUNID', 'x', base='Xp',
                                         start_date=('1111', '22', '33'),
                                         custom='F-1')

    @mock.patch('netcdf_filenames.NCFilename')
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
                    'RUNIDx.Xp.11112233.44445566.nc'
                    )
        mock_ncf.assert_called_once_with('model', 'RUNID', 'x', base='Xp',
                                         start_date=('1111', '22', '33'),
                                         custom='')

    @mock.patch('netcdf_filenames.NCFilename')
    def test_components_rebuild(self, mock_ncf):
        '''Test component extraction - with rebuild suffix'''
        func.logtest('Assert correct extraction of components - rebld suffix:')
        testfile = 'RUNIDx_Xp_11111111_22222222_F_1-33333333_444444444_9876.nc'
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

        mock_ncf.assert_called_once_with('model', 'RUNID', 'x', base='Xp',
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
                    'RUNIDx.Xp.11112233_44445566_FIELD.nc'
                    )
        self.assertIn('unable to extract "component"', func.capture('err'))

    @mock.patch('netcdf_filenames.NCFilename.__init__', return_value=None)
    def test_components_fail_debug(self, mock_ncf):
        '''Test component extraction - failure in model identification'''
        func.logtest('Assert failure in model identification:')
        utils.set_debugmode(True)
        with mock.patch('modeltemplate.ModelTemplate.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'model': ['field1', 'field2']}):
            ncf = self.model.filename_components(
                'RUNIDx_10m_11112233_44445566_FIELD.nc'
                )
            self.assertTrue(isinstance(ncf, netcdf_filenames.NCFilename))
        self.assertIn('unable to extract "component"', func.capture('err'))
        mock_ncf.assert_called_once_with('component', 'PREFIX', 'R')

    def test_archive_timetamps_single(self):
        '''Test return of timestamps method - archive single'''
        func.logtest('Assert return of timestamps method - archive single:')
        self.model.naml.archive_timestamps = '12-01'
        print self.model.naml.archive_timestamps
        self.assertTrue(self.model.timestamps('12', '01'))
        self.assertFalse(self.model.timestamps('06', '01'))

    def test_archive_timetamps_list(self):
        '''Test return of timestamps method - archive list'''
        func.logtest('Assert return of timestamps method - archive list:')
        self.model.naml.archive_timestamps = ['06-01', '12-01']
        print self.model.naml.archive_timestamps
        self.assertTrue(self.model.timestamps('06', '01'))
        self.assertTrue(self.model.timestamps('12', '01'))
        self.assertFalse(self.model.timestamps('11', '01'))

    def test_rebuild_timetamps_single(self):
        '''Test return of timestamps method - rebuild single'''
        func.logtest('Assert return of timestamps method - rebuild single:')
        self.model.naml.rebuild_timestamps = '12-01'
        print self.model.naml.rebuild_timestamps
        self.assertTrue(self.model.timestamps('12', '01', process='rebuild'))
        self.assertFalse(self.model.timestamps('06', '01', process='rebuild'))

    def test_rebuild_timetamps_list(self):
        '''Test return of timestamps method - rebuild list'''
        func.logtest('Assert return of timestamps method - rebuild list:')
        self.model.naml.rebuild_timestamps = ['06-01', '12-01']
        print self.model.naml.rebuild_timestamps
        self.assertTrue(self.model.timestamps('06', '01', process='rebuild'))
        self.assertTrue(self.model.timestamps('12', '01', process='rebuild'))
        self.assertFalse(self.model.timestamps('11', '01', process='rebuild'))


class PropertyTests(unittest.TestCase):
    '''Unit tests relating to ModelTemplate properties'''

    def setUp(self):
        with mock.patch('nlist.loadNamelist'):
            modeltemplate.ModelTemplate._directory = mock.Mock()
            self.model = modeltemplate.ModelTemplate()

    def tearDown(self):
        pass

    def test_methods(self):
        '''Test return value of the methods property'''
        func.logtest('Assert correct return from methods property:')
        all_methods = ['archive_restarts', 'move_to_share',
                       'create_means', 'archive_means',
                       'archive_general', 'finalise_debug']
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
