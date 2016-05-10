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

import runtimeEnvironment
import testing_functions as func
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'common'))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'nemocice'))
import nemo
import nemoNamelist


class StencilTests(unittest.TestCase):
    '''Unit tests relating to the NEMO output filename stencils'''
    def setUp(self):
        self.files = [
            'RUNIDo_19951130_restart.nc',
            'RUNIDo_icebergs_19951130_restart.nc',
            'RUNIDo_6h_1995090101_1995091006_FIELD.nc',
            'RUNIDo_2d_19950905_19950906_FIELD.nc',
            'RUNIDo_2d_19950929_19950930_FIELD.nc',
            'RUNIDo_10d_19950901_19950910_FIELD.nc',
            'RUNIDo_10d_19950921_19950930_FIELD.nc',
            'RUNIDo_1m_19951101_19951130_FIELD.nc',
            'RUNIDo_1s_19950901_19951130_FIELD.nc',
            'RUNIDo_1y_19941201_19951130_FIELD.nc',
            'RUNIDo_1y_19951201_19961130_FIELD.nc',
            ]
        self.nemo = nemo.NemoPostProc()
        self.nemo.suite = mock.Mock()
        self.nemo.suite.prefix = 'RUNID'
        self.date = ('1995', '09')
        self.ssn = ('09', '10', '11', 0)
        self.setstencil = self.nemo.set_stencil
        self.endstencil = self.nemo.end_stencil
        self.meanstencil = self.nemo.mean_stencil

    def tearDown(self):
        try:
            os.remove('nemocicepp.nl')
        except OSError:
            pass

    def test_set_stencil_restarts(self):
        '''Test the regular expressions of the set_stencil method - restarts'''
        func.logtest('Assert restart pattern matching of set_stencil:')
        patt = re.compile(self.setstencil['Restarts']('', None, None, ''))
        nemo_rst = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(nemo_rst,
                         [fname for fname in self.files if 'restart' in fname
                          and 'ice' not in fname])

    def test_set_stencil_iceberg_rsts(self):
        '''Test the regex of the set_stencil method - iceberg restarts'''
        func.logtest('Assert iceberg restart pattern matching of set_stencil:')
        args = (None, None, None, 'icebergs')
        patt = re.compile(self.setstencil['Restarts'](*args))
        ice_rst = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(ice_rst,
                         [fname for fname in self.files if 'iceberg' in fname])

    def test_set_stencil_monthly_10days(self):
        '''Test the regex of the set_stencil method - monthly (10days)'''
        func.logtest('Assert monthly (10d) pattern matching of set_stencil:')
        args = (self.date[0], self.date[1], None, 'FIELD')
        patt = re.compile(self.setstencil['Monthly'](*args))
        month_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(month_set,
                         [fname for fname in self.files if '10d_' in fname])

    def test_set_stencil_monthly_2days(self):
        '''Test the regex of the set_stencil method - monthly (2days)'''
        func.logtest('Assert monthly (10d) pattern matching of set_stencil:')
        args = (self.date[0], self.date[1], None, 'FIELD')
        self.nemo.nl.base_component = '2d'
        patt = re.compile(self.setstencil['Monthly'](*args))
        month_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(month_set,
                         [fname for fname in self.files if '2d_' in fname])

    def test_set_stencil_seasonal(self):
        '''Test the regex of the set_stencil method - seasonal'''
        func.logtest('Assert seasonal pattern matching of set_stencil:')
        args = (self.date[0], None, self.ssn, 'FIELD')
        patt = re.compile(self.setstencil['Seasonal'](*args))
        season_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(season_set,
                         [fname for fname in self.files if '1m_' in fname])

    def test_set_stencil_annual(self):
        '''Test the regex of the set_stencil method - annual'''
        func.logtest('Assert annual pattern matching of set_stencil:')
        args = (self.date[0], None, None, 'FIELD')
        patt = re.compile(self.setstencil['Annual'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '1s_' in fname])

    def test_end_stencil_restarts(self):
        '''Test the regular expressions of the set_stencil method - restarts'''
        func.logtest('Assert restart pattern matching of end_stencil:')
        self.assertEqual(self.endstencil['Restarts'], None)

    def test_end_stencil_monthly(self):
        '''Test the regex of the end_stencil method - monthly'''
        func.logtest('Assert monthly pattern matching of end_stencil:')
        args = (None, 'FIELD')
        patt = re.compile(self.endstencil['Monthly'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if
                          '10d_' in fname and '30_FIELD' in fname])

    def test_end_stencil_seasonal(self):
        '''Test the regex of the end_stencil method - seasonal'''
        func.logtest('Assert seasonal pattern matching of end_stencil:')
        args = (self.ssn, 'FIELD')
        patt = re.compile(self.endstencil['Seasonal'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '1m_' in fname])

    def test_end_stencil_annual(self):
        '''Test the regex of the end_stencil method - annual'''
        func.logtest('Assert annual pattern matching of end_stencil:')
        args = (None, 'FIELD')
        patt = re.compile(self.endstencil['Annual'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '1s_' in fname])

    def test_mean_stencil_hourly(self):
        '''Test the regular expressions of the mean_stencil method - hourly'''
        func.logtest('Assert hourly pattern matching of mean_stencil:')
        patt = re.compile(self.meanstencil['General']('6h', None,
                                                      None, 'FIELD'))
        sixhr_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(sixhr_set,
                         [fname for fname in self.files if '_6h_' in fname])

    def test_mean_stencil_daily(self):
        '''Test the regular expressions of the mean_stencil method - daily'''
        func.logtest('Assert daily pattern matching of mean_stencil:')
        patt = re.compile(self.meanstencil['General']('10d', None,
                                                      None, 'FIELD'))
        tenday_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(tenday_set,
                         [fname for fname in self.files if '_10d_' in fname])

    def test_mean_stencil_monthly(self):
        '''Test the regular expressions of the mean_stencil method - monthly'''
        func.logtest('Assert monthly pattern matching of mean_stencil:')
        args = (self.date[0], '11', None, 'FIELD')
        patt = re.compile(self.meanstencil['Monthly'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '1m_' in fname])

    def test_mean_stencil_seasonal(self):
        '''Test the regexes of the mean_stencil method - seasonal'''
        func.logtest('Assert seasonal pattern matching of mean_stencil:')
        args = (self.date[0], self.date[1], self.ssn, 'FIELD')
        patt = re.compile(self.meanstencil['Seasonal'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '1s_' in fname])

    def test_mean_stencil_annual(self):
        '''Test the regular expressions of the mean_stencil method - annual'''
        func.logtest('Assert annual pattern matching of mean_stencil:')
        args = (self.date[0], None, None, 'FIELD')
        patt = re.compile(self.meanstencil['Annual'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if
                          '1y_' in fname and self.date[0] + '1130' in fname])

    def test_mean_stencil_all_years(self):
        '''Test the regex of the mean_stencil method - all years'''
        func.logtest('Assert all years pattern matching of mean_stencil:')
        args = ('.*', None, None, 'FIELD')
        patt = re.compile(self.meanstencil['Annual'](*args))
        annual_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(annual_set,
                         [fname for fname in self.files if '1y_' in fname])


class RebuildTests(unittest.TestCase):
    '''Unit tests relating to the rebuilding of restart and means files'''
    def setUp(self):
        self.nemo = nemo.NemoPostProc()
        self.nemo.suite = mock.Mock()
        self.nemo.suite.finalcycle = False
        self.defaults = nemoNamelist.NemoNamelist()
        self.buffer_rst = self.nemo.buffer_rebuild('rst')
        self.buffer_mean = self.nemo.buffer_rebuild('mean')

    def tearDown(self):
        for fname in ('nemocicepp.nl', 'nam_rebuild'):
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_call_rebuild_restarts(self):
        '''Test call to rebuild_restarts method'''
        func.logtest('Assert call to rebuild_fileset from rebuild_restarts:')
        with mock.patch('nemo.NemoPostProc.rebuild_fileset') as mock_fs:
            with mock.patch.object(nemo.NemoPostProc, 'rsttypes') as mock_rst:
                mock_rst.__get__ = mock.Mock(return_value=('',))
                mynemo = nemo.NemoPostProc()
                mynemo.suite = mock.Mock()
                mynemo.suite.prefix = os.environ['RUNID']
                mynemo.rebuild_restarts()
        mock_fs.assert_called_with(
            os.environ['PWD'],
            r'{}o_{}_?\d{{8}}_restart(\.nc)?'.format(os.environ['RUNID'], '')
            )

    def test_call_rebuild_iceberg_rsts(self):
        '''Test call to rebuild_restarts method with iceberg restart files'''
        func.logtest('Assert call to rebuild_fileset from rebuild_restarts:')
        self.nemo.suite.prefix = os.environ['RUNID']
        with mock.patch('nemo.NemoPostProc.rebuild_fileset') as mock_fs:
            self.nemo.rebuild_restarts()
        mock_fs.assert_called_with(
            os.environ['PWD'],
            r'{}o_{}_?\d{{8}}_restart(\.nc)?'.format(os.environ['RUNID'],
                                                     self.nemo.rsttypes[-1])
            )

    def test_call_rebuild_means(self):
        '''Test call to rebuild_means method'''
        func.logtest('Assert call to rebuild_fileset from rebuild_means:')
        self.nemo.suite.prefix = os.environ['RUNID']
        pattern = r'{}o_{}_\d{{8,10}}_\d{{8,10}}_{}(\.nc)?'.format(
            os.environ['RUNID'], '10d', self.nemo.fields[-1])
        with mock.patch('nemo.NemoPostProc.rebuild_fileset') as mock_fs:
            self.nemo.rebuild_means()
        mock_fs.assert_called_with(os.environ['PWD'], pattern,
                                   rebuildall=True)

    def test_namlist_properties(self):
        '''Test definition of NEMO namelist properties'''
        func.logtest('Assert NEMO namelist properties:')
        self.assertEqual(self.defaults.exec_rebuild, self.nemo.rebuild_cmd)
        self.assertEqual(self.defaults.means_cmd, self.nemo.means_cmd)

    def test_buffer_rebuild(self):
        '''Test rebuild buffer value extraction'''
        func.logtest('Assert given value for rebuild buffer:')
        self.assertEqual(self.defaults.buffer_rebuild_rst, self.buffer_rst)
        self.assertEqual(self.defaults.buffer_rebuild_mean, self.buffer_mean)

    @mock.patch('utils.get_subset')
    def test_rbld_restart_not_required(self, mock_subset):
        '''Test rebuild restarts function retaining all files'''
        func.logtest('Assert restart files fewer than buffer are retained:')
        mock_subset.return_value = ['file1']
        self.nemo.rebuild_fileset(os.environ['PWD'], 'restart')
        self.assertIn('{} retained'.format(self.buffer_rst), func.capture())

    @mock.patch('utils.get_subset')
    def test_rebuild_mean_not_required(self, mock_subset):
        '''Test rebuild means function retaining all files'''
        func.logtest('Assert means files fewer than buffer (1) are retained:')
        mock_subset.return_value = ['file1']
        self.nemo.rebuild_fileset(os.environ['PWD'], 'field')
        self.assertIn('{} retained'.format(self.buffer_mean), func.capture())

    @mock.patch('utils.get_subset')
    def test_rebuild_periodic_only(self, mock_subset):
        '''Test rebuild function for periodic files not found'''
        func.logtest('Assert only periodic files are rebuilt:')
        mock_subset.return_value = ['file1_19990101', 'file2_19990101']
        with mock.patch('nemo.NemoPostProc.check_fileformat'):
            self.nemo.rebuild_fileset(os.environ['PWD'], 'field')
        self.assertIn('only rebuilding periodic', func.capture().lower())
        self.assertIn('deleting component files', func.capture().lower())

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('utils.get_subset')
    def test_rebuild_all(self, mock_subset, mock_nl):
        '''Test rebuild all function'''
        func.logtest('Assert rebuild all function:')
        mock_subset.return_value = ['file_19980530_yyyymmdd_0000.nc',
                                    'file_19980630_yyyymmdd_0000.nc',
                                    'file_19980730_yyyymmdd_0000.nc']
        self.nemo.rebuild_fileset(os.environ['PWD'], 'field', rebuildall=True)
        mock_nl.assert_called_with(os.environ['PWD'], 'file_19980630_yyyymmdd',
                                   1, omp=1)

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    def test_rebuild_pattern(self, mock_nl):
        '''Test rebuild pattern matching function'''
        func.logtest('Assert rebuild pattern matching function:')
        myfiles = ['RUNIDo_19980530_restart_0000.nc',
                   'RUNIDo_19980530_yyyymmdd_field_0000.nc',
                   'RUNIDo_19980530_yyyymmdd_field_0001.nc',
                   'RUNIDo_19980530_yyyymmdd_field_0002.nc',
                   'RUNIDo_19980530_yyyymmdd_field.nc',
                   'RUNIDo_19981130_yyyymmdd_field_0000.nc']
        for fname in myfiles:
            open(fname, 'w').close()
        self.nemo.rebuild_fileset(os.environ['PWD'], 'field')
        mock_nl.assert_called_with(os.environ['PWD'],
                                   'RUNIDo_19980530_yyyymmdd_field',
                                   3, omp=1)
        for fname in myfiles:
            os.remove(fname)

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    def test_rebuild_pattern_restarts(self, mock_nl):
        '''Test rebuild restarts pattern matching function'''
        func.logtest('Assert rebuild restarts pattern matching function:')
        myfiles = ['RUNIDo_19980530_restart_0000.nc',
                   'RUNIDo_19980530_restart_0001.nc',
                   'RUNIDo_19980530_restart_0002.nc',
                   'RUNIDo_19980530_restart.nc',
                   'RUNIDo_19981130_restart_0000.nc',
                   'RUNIDo_icebergs_19980530_restart_0000.nc']
        self.nemo.buffer_rebuild = mock.Mock()
        self.nemo.buffer_rebuild.return_value = 0
        for fname in myfiles:
            open(fname, 'w').close()

        self.nemo.rebuild_fileset(os.environ['PWD'],
                                  'RUNIDo_19980530_restart')
        mock_nl.assert_called_with(os.environ['PWD'],
                                   'RUNIDo_19980530_restart',
                                   3, omp=1)
        for fname in myfiles:
            os.remove(fname)

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    def test_rebuild_pattern_icebergs(self, mock_nl):
        '''Test rebuild icebergs restarts pattern matching function'''
        func.logtest('Assert rebuild iceberg rsts pattern matching function:')
        myfiles = ['RUNIDo_19980530_yyyymmdd_field_0000.nc',
                   'RUNIDo_19980530_restart_0000.nc',
                   'RUNIDo_19980530_restart_0001.nc',
                   'RUNIDo_19980530_restart_0002.nc',
                   'RUNIDo_icebergs_19980530_restart_0000.nc',
                   'RUNIDo_icebergs_19980530_restart_0001.nc']
        self.nemo.buffer_rebuild = mock.Mock()
        self.nemo.buffer_rebuild.return_value = 0
        for fname in myfiles:
            open(fname, 'w').close()
        self.nemo.rebuild_fileset(os.environ['PWD'],
                                  'RUNIDo_icebergs_19980530_restart')
        mock_nl.assert_called_with(os.environ['PWD'],
                                   'RUNIDo_icebergs_19980530_restart',
                                   2, omp=1)
        for fname in myfiles:
            os.remove(fname)

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('utils.get_subset')
    def test_rebuild_rst_final_cycle(self, mock_subset, mock_nl):
        '''Test final cycle behaviour - deleting components of restarts'''
        func.logtest('Assert component files not deleted on final cycle:')
        mock_subset.side_effect = \
            [['file_restart_0000.nc'],
             ['file_restart_0000.nc', 'file_restart_0001.nc']]
        mock_nl.return_value = 0
        self.nemo.buffer_rebuild = mock.Mock()
        self.nemo.buffer_rebuild.return_value = 0
        self.nemo.suite.finalcycle = True
        self.nemo.rebuild_fileset(os.environ['PWD'], 'yyyymmdd_restart',
                                  rebuildall=True)
        mock_nl.assert_called_with(os.environ['PWD'], 'file_restart', 2, omp=1)
        self.assertNotIn('deleting component files', func.capture().lower())

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('utils.get_subset')
    def test_rebuild_means_final_cycle(self, mock_subset, mock_nl):
        '''Test final cycle behaviour - deleting components of means'''
        func.logtest('Assert component files not deleted on final cycle:')
        mock_subset.return_value = ['file_mean1_0000.nc', 'file_mean2_0000.nc']
        mock_nl.return_value = 0
        self.nemo.suite.finalcycle = True
        self.nemo.rebuild_fileset(os.environ['PWD'], 'mean', rebuildall=True)
        mock_nl.assert_called_with(os.environ['PWD'], 'file_mean1', 1, omp=1)
        self.assertIn('deleting component files', func.capture().lower())

    @mock.patch('utils.exec_subproc')
    @mock.patch('os.path.isfile')
    def test_rebuild_namelist(self, mock_isfile, mock_exec):
        '''Test rebuild namelist function'''
        func.logtest('Assert behaviour of rebuild_namelist function:')
        mock_exec.return_value = (0, '')
        mock_isfile.return_value = True
        with mock.patch('os.remove'):
            rtn = self.nemo.rebuild_namelist(os.environ['PWD'],
                                             'file_19980530_yyyymmdd',
                                             3)
        self.assertEqual(mock_exec.return_value[0], rtn)
        self.assertEqual(int(os.environ['OMP_NUM_THREADS']), 16)
        self.assertIn('successfully rebuilt', func.capture().lower())
        self.assertIn('file_19980530_yyyymmdd', func.capture().lower())
        mock_exec.assert_called_with(
            '{}'.format(os.path.join(os.environ['PWD'],
                                     self.defaults.exec_rebuild)),
            cwd=os.environ['PWD'])
        self.assertTrue(os.path.exists('nam_rebuild'))
        txt = open('nam_rebuild', 'r').read()
        self.assertNotIn('dims=\'1\',\'2\'', txt)

    @mock.patch('utils.exec_subproc')
    @mock.patch('os.path.isfile')
    def test_rebuild_namelist_options(self, mock_isfile, mock_exec):
        '''Test rebuild namelist function with options'''
        func.logtest('Assert rebuild_namelist function with options:')
        mock_exec.return_value = (0, '')
        mock_isfile.return_value = True
        with mock.patch('os.remove'):
            rtn = self.nemo.rebuild_namelist(os.environ['PWD'],
                                             'file_19980530_yyyymmdd',
                                             3,
                                             omp=1, chunk='opt_chunk',
                                             dims=[1, 2])
        self.assertEqual(int(os.environ['OMP_NUM_THREADS']), 1)
        self.assertEqual(rtn, 0)
        txt = open('nam_rebuild', 'r').read()
        self.assertIn('dims=\'1\',\'2\'', txt)
        self.assertIn('nchunksize=opt_chunk', txt)

    @mock.patch('utils.exec_subproc')
    @mock.patch('os.path.isfile')
    def test_rbld_namelist_no_namelist(self, mock_isfile, mock_exec):
        '''Test failure to create namelist file'''
        func.logtest('Assert failure to create namelist file:')
        mock_exec.return_value = (0, '')
        mock_isfile.return_value = False
        rtn = self.nemo.rebuild_namelist(os.environ['PWD'],
                                         'file_19980530_yyyymmdd',
                                         3)
        self.assertNotEqual(rtn, 0)
        self.assertIn('failed to create namelist file',
                      func.capture('err').lower())

    @mock.patch('utils.exec_subproc')
    def test_rebuild_namelist_fail(self, mock_exec):
        '''Test failure mode of rebuild namelist function'''
        func.logtest('Assert failure behaviour of rebuild_namelist function:')
        mock_exec.return_value = (1, '')
        os.path.isfile = mock.Mock(return_value=True)
        with self.assertRaises(SystemExit):
            self.nemo.rebuild_namelist(os.environ['PWD'],
                                       'file_19980530_yyyymmdd',
                                       3)
        self.assertIn('failed to rebuild file', func.capture('err').lower())
        self.assertIn('file_19980530_yyyymmdd', func.capture('err').lower())

    def test_rebuild_icebergs_call(self):
        '''Test call to external iceberg rebuilding routine: icb_combrest'''
        func.logtest('Assert call to external iceberg rebuilding routine:')
        os.path.isfile = mock.Mock(return_value=True)
        with mock.patch('utils.exec_subproc', return_value=(0, '')):
            with mock.patch('nemo.NemoPostProc.rebuild_icebergs') as mock_rbld:
                mock_rbld.return_value = 0
                self.nemo.rebuild_namelist(os.environ['PWD'],
                                           'file_icebergs_yyyymmdd', 2)
        mock_rbld.assert_called_with(os.environ['PWD'],
                                     'file_icebergs_yyyymmdd', 2)
        self.assertIn('Successfully rebuilt', func.capture())

    def test_rebuild_icebergs_cmd(self):
        '''Test call to external iceberg rebuilding routine: icb_combrest'''
        func.logtest('Assert call to external iceberg rebuilding routine:')
        with mock.patch('utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            self.nemo.rebuild_icebergs('TestDir', 'filebase', '1')
        cmd = 'python2.7 {} -f TestDir/filebase_ -n 1 -o TestDir/filebase.nc'.\
            format(self.defaults.exec_rebuild_icebergs)
        mock_exec.assert_called_with(cmd, cwd='TestDir')
        self.assertIn('Successfully rebuilt', func.capture())

    def test_rebuild_icebergs_fail(self):
        '''Test call to external iceberg rebuilding routine: icb_combrest'''
        func.logtest('Assert call to external iceberg rebuilding routine:')
        with mock.patch('utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, 'err output')
            with self.assertRaises(SystemExit):
                self.nemo.rebuild_icebergs('TestDir', 'filebase', '1')
        self.assertIn('Failed to rebuild file', func.capture('err'))
        self.assertIn('err output', func.capture('err'))

    def test_check_fileformat_10dmean(self):
        '''Test check_fileformat functionality - 10d means'''
        func.logtest('Assert check_fileformat method with 10d means:')
        self.nemo.suite.prefix = 'RUNID'
        date = ('YYYY', 'MM', '01')
        template = r'RUNIDo_10d_YYYYMM01_YYYYMM10_grid_V.nc'
        with mock.patch('os.rename') as mock_mv:
            self.nemo.check_fileformat('RUNIDo_10d_DATE.nc',
                                       date, 'type_grid_V')
            mock_mv.assert_called_with(
                'RUNIDo_10d_DATE.nc',
                os.path.join(os.environ['PWD'], template)
                )

    def test_check_fileformat_2dmean(self):
        '''Test check_fileformat functionality - 2d means'''
        func.logtest('Assert check_fileformat method with 2d means:')
        self.nemo.suite.prefix = 'RUNID'
        date = ('YYYY', 'MM', '05')
        template = r'RUNIDo_2d_YYYYMM05_YYYYMM06_grid_V.nc'
        with mock.patch('os.rename') as mock_mv:
            self.nemo.check_fileformat('RUNIDo_2d_DATE.nc',
                                       date, 'type_grid_V')
            mock_mv.assert_called_with(
                'RUNIDo_2d_DATE.nc',
                os.path.join(os.environ['PWD'], template)
                )

    def test_check_format_10d_nochange(self):
        '''Test check_fileformat functionality - no change'''
        func.logtest('Assert check_fileformat method with no change:')
        self.nemo.suite.prefix = 'RUNID'
        with mock.patch('os.rename') as mock_mv:
            self.nemo.check_fileformat('RUNIDo_10d_11112201_11112210_grid_V.nc',
                                       ('1111', '22', '01'), 'type_grid_V')
            self.assertEqual(mock_mv.mock_calls, [])

    def test_check_format_10d_badfield(self):
        '''Test check_fileformat functionality - unknown field'''
        func.logtest('Assert check_fileformat method with unknown field:')
        with mock.patch('os.rename'):
            with self.assertRaises(SystemExit):
                self.nemo.check_fileformat('RUNIDo_10d_field.nc',
                                           ('Y', 'M', 'D'), 'type_any')

    def test_check_fileformat_otherfile(self):
        '''Test check_fileformat functionality - any file but 10d mean'''
        func.logtest('Assert check_fileformat method with any file but 10d:')
        with mock.patch('nemo.NemoPostProc.set_stencil') as mock_set:
            self.nemo.check_fileformat('InFile', ('Y', 'M', 'D'), 'type_any')
            self.assertEqual(mock_set.mock_calls, [])


class MeansProcessingTests(unittest.TestCase):
    '''Unit tests relating to the processing of means files'''
    def setUp(self):
        self.nemo = nemo.NemoPostProc()
        self.nemo.suite = mock.Mock()
        self.defaults = nemoNamelist.NemoNamelist()
        self.ncdumpout = '''
  DOMAIN_size_global = x, 1207;
  dummy arg = some value;
  DOMAIN_position_last = x, 151;
  DOMAIN_position_first = x, 1;
  dummy arg2 = some other value;
'''

    def tearDown(self):
        try:
            os.remove('nemocicepp.nl')
        except OSError:
            pass

    def test_global_attr_to_zonal(self):
        '''Test method to transform global attributes to zonal ones'''
        func.logtest('Assert functionality of global_attr_to_zonal method:')
        self.nemo.suite.preprocess_file.return_value = self.ncdumpout
        with mock.patch('utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            self.nemo.global_attr_to_zonal('TestDir', 'File1')
        mock_exec.assert_called_with(' '.join([
            self.defaults.ncatted_cmd,
            '-a DOMAIN_size_global,global,m,l,1,1207',
            '-a DOMAIN_position_first,global,m,l,1,1',
            '-a DOMAIN_position_last,global,m,l,1,151',
            '-a ibegin,global,m,l,1', 'TestDir/File1',
            ]))
        self.assertIn('Changing nc file attributes using', func.capture())
        self.assertIn('ncatted - Successful', func.capture())

    def test_global_to_zonal_multifile(self):
        '''Test transform global attributes to zonal - multiple files'''
        func.logtest('Assert global_attr_to_zonal method - multiple files:')
        self.nemo.suite.preprocess_file.return_value = self.ncdumpout
        with mock.patch('utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            self.nemo.global_attr_to_zonal('TestDir', ['File1', 'File2'])
        mock_exec.assert_called_with(' '.join([
            self.defaults.ncatted_cmd,
            '-a DOMAIN_size_global,global,m,l,1,1207',
            '-a DOMAIN_position_first,global,m,l,1,1',
            '-a DOMAIN_position_last,global,m,l,1,151',
            '-a ibegin,global,m,l,1', 'TestDir/File2'
            ]))
        self.assertIn('Changing nc file attributes', func.capture())
        self.assertIn('ncatted - Successful', func.capture())

    def test_global_to_zonal_fail(self):
        '''Test method to transform global attributes to zonal - failure'''
        func.logtest('Assert failure of global_attr_to_zonal method:')
        self.nemo.suite.preprocess_file.return_value = self.ncdumpout
        with mock.patch('utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, '')
            with self.assertRaises(SystemExit):
                self.nemo.global_attr_to_zonal('TestDir', 'File1')
        self.assertIn('Changing nc file attributes', func.capture('err'))
        self.assertIn('ncatted - Failed', func.capture('err'))

    def test_global_to_zonal_missing(self):
        '''Test method global attributes to zonal ones - missing attributes'''
        func.logtest('Assert missing attributes with global_attr_to_zonal:')
        ncdumpout = '''
  dummy arg = some value;
  DOMAIN_position_last = x, 151;
  DOMAIN_position_first = x, 1;
  dummy arg2 = some other value;
'''
        self.nemo.suite.preprocess_file.return_value = ncdumpout
        with mock.patch('utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, '')
            with self.assertRaises(SystemExit):
                self.nemo.global_attr_to_zonal('TestDir', 'File1')
            self.assertEqual(mock_exec.mock_calls, [])

        self.assertIn('attribute(s) DOMAIN_size_global not found',
                      func.capture('err'))
        self.assertIn('DOMAIN_size_global', func.capture('err'))


def main():
    '''Main function'''
    unittest.main(buffer=True)


if __name__ == '__main__':
    main()
