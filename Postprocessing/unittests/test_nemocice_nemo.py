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
import re
import mock

import testing_functions as func
import runtime_environment

# Import of nemo requires 'RUNID' from runtime environment
# Import of nemo_namelist requires 'DATAM' from runtime environment
runtime_environment.setup_env()
import nemo
import nemo_namelist


class StencilTests(unittest.TestCase):
    '''Unit tests relating to the NEMO output filename stencils'''
    def setUp(self):
        self.files = [
            'RUNIDo_19951130_restart.nc',
            'RUNIDo_icebergs_19951130_restart.nc',
            'RUNIDo_19951130_restart_trc.nc',
            'RUNIDo_6h_1995090101_1995090106_FIELD.nc',
            'RUNIDo_2d_19950902_19950903_FIELD_0000.nc',
            'RUNIDo_10d_19910601_19910630_FIELD_19910610-19910620_9999.nc',
            'RUNIDo_1m_19950901_19950930_FIELD_1234.nc',
            ]

        self.nemo = nemo.NemoPostProc()
        self.nemo.suite = mock.Mock()
        self.nemo.suite.prefix = 'RUNID'

    def tearDown(self):
        for fname in runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_rst_set_stencil(self):
        '''Test the regular expressions of the rst_set_stencil method'''
        func.logtest('Assert pattern matching of rst_set_stencil:')
        patt = re.compile(self.nemo.rst_set_stencil(('', '')))
        nemo_rst = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(nemo_rst,
                         [fname for fname in self.files if 'restart' in fname
                          and 'iceberg' not in fname and '_trc' not in fname])

    def test_rst_set_stencil_iceberg(self):
        '''Test the regex of the rst_set_stencil method - iceberg restarts'''
        func.logtest('Assert iceberg pattern matching of rst_set_stencil:')
        patt = re.compile(self.nemo.rst_set_stencil(self.nemo.rsttypes[1]))
        ice_rst = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(ice_rst,
                         [fname for fname in self.files if 'iceberg' in fname])

    def test_rst_set_stencil_tracer(self):
        '''Test the regex of the rst_set_stencil method - tracer restarts'''
        func.logtest('Assert tracer pattern matching of rst_set_stencil:')
        patt = re.compile(self.nemo.rst_set_stencil(self.nemo.rsttypes[2]))
        ice_rst = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(ice_rst,
                         [fname for fname in self.files if '_trc' in fname])

    def test_general_mean_stencil(self):
        '''Test the regular expressions of the general_mean_stencil method'''
        func.logtest('Assert pattern matching of general_mean_stencil:')
        patt = re.compile(self.nemo.general_mean_stencil('FIELD'))
        sixhr_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(sixhr_set,
                         [fname for fname in self.files if
                          'restart' not in fname])

    def test_general_mean_stencil_6hr(self):
        '''Test the regular expressions of general_mean_stencil - 6 hourly'''
        func.logtest('Assert hourly pattern matching of general_mean_stencil:')
        patt = re.compile(self.nemo.general_mean_stencil('FIELD', base='6h'))
        sixhr_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(sixhr_set,
                         [fname for fname in self.files if '6h_' in fname])


class Propertytests(unittest.TestCase):
    '''Tests relating to the NEMO properties'''

    def setUp(self):
        self.nemo = nemo.NemoPostProc()
        self.nemo.suite = mock.Mock()
        self.nemo.naml.processing = nemo_namelist.Processing()

    def tearDown(self):
        try:
            os.remove('nemocicepp.nl')
        except OSError:
            pass

    def test_fields_property_default(self):
        '''Test the return value of the fields property - default'''
        func.logtest('Assert return value of fields property:')
        self.assertEqual(self.nemo.naml.processing.means_fieldsfiles, None)
        self.assertListEqual(self.nemo.mean_fields,
                             ['diad_T', 'diaptr', 'grid_T',
                              'grid_U', 'grid_V', 'grid_W',
                              'ptrc_T', 'ptrd_T', 'scalar', 'trnd3d'])
        self.assertEqual(self.nemo.naml.processing.region_fieldsfiles, None)
        self.assertListEqual(self.nemo.inst_fields, [])

    def test_fields_property_single(self):
        '''Test the return value of the fields property - single'''
        func.logtest('Assert return of the fields property - single supplied:')
        self.nemo.naml.processing.means_fieldsfiles = 'grid_W'
        self.assertListEqual(self.nemo._mean_fields, ['grid_W'])

    def test_fields_property_list(self):
        '''Test the return value of the fields property - list'''
        func.logtest('Assert return of fields property - list supplied:')
        self.nemo.naml.processing.means_fieldsfiles = ['grid_U', 'grid_T']
        self.assertListEqual(self.nemo._mean_fields, ['grid_T', 'grid_U'])

    def test_region_fields_property(self):
        '''Test the return value of the fields property - regional inst'''
        func.logtest('Assert return value of fields property (regional):')
        self.nemo.naml.processing.extract_region = True
        self.assertListEqual(self.nemo._region_fields,
                             ['UK_shelf_T', 'UK_shelf_U', 'UK_shelf_V'])
        self.nemo.naml.processing.region_fieldsfiles = ''
        self.assertListEqual(self.nemo._region_fields, [])
        self.nemo.naml.processing.region_fieldsfiles = 'region_T'
        self.assertListEqual(self.nemo._region_fields, ['region_T'])
        self.nemo.naml.processing.region_fieldsfiles = ['reg_T', 'reg_V']
        self.assertListEqual(self.nemo._region_fields, ['reg_T', 'reg_V'])


class RebuildTests(unittest.TestCase):
    '''Unit tests relating to the rebuilding of restart and means files'''
    def setUp(self):
        self.nemo = nemo.NemoPostProc()
        self.nemo.share = 'ShareDir'
        self.nemo.suite = mock.Mock()
        self.nemo.suite.prefix = 'RUNID'
        self.nemo.suite.finalcycle = False
        self.nemo.suite.cyclepoint = \
            nemo.utils.CylcCycle(cyclepoint='20000901T0000Z')
        self.defaults = nemo_namelist.Processing()

    def tearDown(self):
        for fname in runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass
        for directory in [f for f in os.listdir(os.getcwd())
                          if re.match('rebuilding.*', f)]:
            for fname in os.listdir(directory):
                os.remove(os.path.join(directory, fname))
            os.rmdir(directory)

    def test_call_rebuild_restarts(self):
        '''Test call to rebuild_restarts method'''
        func.logtest('Assert call to rebuild_fileset from rebuild_restarts:')
        with mock.patch('nemo.NemoPostProc.rebuild_fileset') as mock_fs:
            with mock.patch('nemo.NemoPostProc.rsttypes',
                            new_callable=mock.PropertyMock,
                            return_value=(self.nemo.rsttypes[0],)):
                self.nemo.rebuild_restarts()
            mock_fs.assert_called_once_with('ShareDir',
                                            r'RUNIDo__?\d{8}_restart(\.nc)?')

    def test_call_rebuild_iceberg_rsts(self):
        '''Test call to rebuild_restarts method with iceberg restart files'''
        func.logtest('Assert call to rebuild_fileset from rebuild_restarts:')
        self.assertIn('icebergs', self.nemo.rsttypes[1])
        with mock.patch('nemo.NemoPostProc.rebuild_fileset') as mock_fs:
            with mock.patch('nemo.NemoPostProc.rsttypes',
                            new_callable=mock.PropertyMock,
                            return_value=(self.nemo.rsttypes[1],)):
                self.nemo.rebuild_restarts()
            mock_fs.assert_called_once_with(
                'ShareDir',
                r'RUNIDo_icebergs_?\d{8}_restart(\.nc)?'
                )

    def test_call_rebuild_tracer_rsts(self):
        '''Test call to rebuild_restarts method with tracer restart files'''
        func.logtest('Assert call to rebuild_fileset from rebuild_restarts:')
        self.assertIn('_trc', self.nemo.rsttypes[2])
        with mock.patch('nemo.NemoPostProc.rebuild_fileset') as mock_fs:
            with mock.patch('nemo.NemoPostProc.rsttypes',
                            new_callable=mock.PropertyMock,
                            return_value=(self.nemo.rsttypes[2],)):
                self.nemo.rebuild_restarts()
            mock_fs.assert_called_once_with(
                'ShareDir',
                r'RUNIDo__?\d{8}_restart_trc(\.nc)?'
                )

    def test_call_rebuild_diagnostics(self):
        '''Test call to rebuild_diagnostics method'''
        func.logtest('Assert call to rebuild_fileset from rebuild_diagnostics:')
        pattern = r'[a-z]*_runido_10d_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}_'
        with mock.patch('nemo.NemoPostProc.rebuild_fileset') as mock_fs:
            self.nemo.rebuild_diagnostics(['FIELD'], bases=['10d'])
            mock_fs.assert_called_once_with('ShareDir', pattern + 'FIELD')

    def test_namlist_properties(self):
        '''Test definition of NEMO namelist properties'''
        func.logtest('Assert NEMO namelist properties:')
        self.assertEqual(self.defaults.exec_rebuild, self.nemo.rebuild_cmd)
        self.assertEqual(self.defaults.means_cmd, self.nemo.means_cmd)

    def test_buffer_rebuild(self):
        '''Test rebuild buffer value extraction'''
        func.logtest('Assert given value for rebuild buffer:')
        self.assertEqual(0, self.nemo.buffer_rebuild('restart'))
        self.assertEqual(0, self.nemo.buffer_rebuild('mean'))

        self.nemo.naml.processing.rebuild_restart_buffer = 2
        self.nemo.naml.processing.rebuild_mean_buffer = 2
        self.assertEqual(2, self.nemo.buffer_rebuild('restart'))
        self.assertEqual(2, self.nemo.buffer_rebuild('mean'))

    @mock.patch('nemo.utils.get_subset')
    def test_rbld_restart_not_required(self, mock_subset):
        '''Test rebuild restarts function retaining all files'''
        func.logtest('Assert restart files fewer than buffer are retained:')
        mock_subset.side_effect = [[], ['file1']]
        self.nemo.naml.processing.rebuild_restart_buffer = 5
        with mock.patch('nemo.NemoPostProc.get_date',
                        return_value=('1990', '01', '01')):
            self.nemo.rebuild_fileset('ShareDir', 'restart')
        self.assertIn('5 retained', func.capture())

    @mock.patch('nemo.utils.get_subset')
    def test_rbld_restart_beyond_cpoint(self, mock_subset):
        '''Test rebuild restarts function retaining files beyond cyclepoint'''
        func.logtest('Assert restart files beyond cyclepoint are retained:')
        mock_subset.side_effect = [[], ['file1']]
        with mock.patch('nemo.NemoPostProc.get_date',
                        return_value=('2001', '01', '01')):
            self.nemo.rebuild_fileset('ShareDir', 'restart')
        self.assertNotIn('Nothing to rebuild', func.capture())

    @mock.patch('nemo.utils.get_subset')
    def test_rebuild_mean_not_required(self, mock_subset):
        '''Test rebuild means function retaining all files'''
        func.logtest('Assert means files fewer than buffer (1) are retained:')
        mock_subset.side_effect = [[], ['file1']]
        self.nemo.naml.processing.rebuild_mean_buffer = 1
        with mock.patch('nemo.NemoPostProc.get_date',
                        return_value=('1990', '01', '01')):
            self.nemo.rebuild_fileset('ShareDir', 'field')
        self.assertIn('1 retained', func.capture())

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.move_files')
    @mock.patch('nemo.shutil.rmtree')
    def test_rebuild_recover_tmp_dirs(self, mock_rm, mock_mv, mock_subset):
        '''Test rebuild_fileset recovery from components left in tmp dirs'''
        func.logtest('Assert recovery of rebuild components left in tmp dirs:')
        mock_subset.side_effect = [['rebuilding_FILETYPE'], ['cmpt1', 'cmpt2'],
                                   []]
        self.nemo.rebuild_fileset('ShareDir', 'field')

        self.assertListEqual(
            mock_subset.mock_calls,
            [mock.call('ShareDir', 'rebuilding_.*FIELD'),
             mock.call('ShareDir/rebuilding_FILETYPE', r'^.*_\d{4}\.nc$'),
             mock.call('ShareDir', r'^.*field_0000.nc$')]
            )
        mock_mv.assert_called_once_with(
            ['cmpt1', 'cmpt2'], 'ShareDir',
            originpath=os.path.join('ShareDir', 'rebuilding_FILETYPE')
            )
        mock_rm.assert_called_once_with(os.path.join('ShareDir',
                                                     'rebuilding_FILETYPE'))

    @mock.patch('utils.remove_files')
    @mock.patch('utils.get_subset')
    def test_rebuild_periodic_only(self, mock_subset, mock_rm):
        '''Test rebuild function for periodic files not found'''
        func.logtest('Assert only periodic files are rebuilt:')
        tmp_dirs = []
        rebuild_zero = ['file1_19990101_0000.nc', 'file2_19990101_0000.nc']
        rbld_set1 = ['f1_cmpt1', 'f1_cmpt2']
        rbld_set2 = ['f2_cmpt1', 'f2_cmpt2']
        mock_subset.side_effect = [tmp_dirs, rebuild_zero, rbld_set1, rbld_set2]
        self.nemo.rebuild_fileset('ShareDir', 'restartfile')
        self.assertIn('only rebuilding periodic', func.capture().lower())
        self.assertIn('deleting component files', func.capture().lower())
        self.assertListEqual(
            mock_rm.mock_calls,
            [mock.call(['f1_cmpt1', 'f1_cmpt2'], path='ShareDir'),
             mock.call(['f2_cmpt1', 'f2_cmpt2'], path='ShareDir')]
            )

    @mock.patch('nemo.NemoPostProc.rebuild_namelist', return_value=1, msk=False)
    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.NemoPostProc.global_attr_to_zonal')
    def test_rebuild_all(self, mock_attr, mock_subset, mock_nl):
        '''Test rebuild all function'''
        func.logtest('Assert rebuild all function:')
        self.nemo.naml.processing.rebuild_mean_buffer = 1
        tmps_dirs = []
        rebuild_zero = ['file_19980530_ymd_0000.nc',
                        'file_19980630_ymd_0000.nc',
                        'file_19980730_ymd_0000.nc']
        rebuild_set1 = ['f1_component1', 'f1_component2']
        rebuild_set2 = ['f2_component1', 'f2_component2']
        mock_subset.side_effect = [tmps_dirs, rebuild_zero,
                                   rebuild_set1, rebuild_set2]
        self.nemo.rebuild_fileset('SourceDir', 'field')
        self.assertListEqual(
            mock_nl.mock_calls, [mock.call('SourceDir', 'file_19980530_ymd',
                                           rebuild_set1, omp=1, msk=False),
                                 mock.call('SourceDir', 'file_19980630_ymd',
                                           rebuild_set2, omp=1, msk=False)]
            )
        self.assertEqual(mock_attr.mock_calls, [])

    @mock.patch('nemo.NemoPostProc.rebuild_namelist', return_value=1, msk=False)
    @mock.patch('nemo.utils.get_subset')
    def test_rebuild_all_shortdate(self, mock_subset, mock_nl):
        '''Test rebuild all function - short date format'''
        func.logtest('Assert rebuild all function:')
        self.nemo.naml.processing.rebuild_mean_buffer = 1
        tmp_dirs = []
        rebuild_zero = ['file_199805_yyyymmdd_0000.nc',
                        'file_199806_yyyymmdd_0000.nc',
                        'file_199807_yyyymmdd_0000.nc']
        rebuild_set1 = ['f1_component1', 'f1_component2']
        rebuild_set2 = ['f2_component1', 'f2_component2']
        mock_subset.side_effect = [tmp_dirs, rebuild_zero,
                                   rebuild_set1, rebuild_set2]
        self.nemo.rebuild_fileset('SourceDir', 'field')
        self.assertListEqual(
            mock_nl.mock_calls, [mock.call('SourceDir', 'file_199805_yyyymmdd',
                                           rebuild_set1, omp=1, msk=False),
                                 mock.call('SourceDir', 'file_199806_yyyymmdd',
                                           rebuild_set2, omp=1, msk=False)]
            )

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    def test_rebuild_pattern(self, mock_nl):
        '''Test rebuild pattern matching function'''
        func.logtest('Assert rebuild pattern matching function:')
        self.nemo.naml.processing.rebuild_mean_buffer = 1
        myfiles = ['RUNIDo_19980530_restart_0000.nc',
                   'RUNIDo_19980530_yyyymmdd_field_0000.nc',
                   'RUNIDo_19980530_yyyymmdd_field_0001.nc',
                   'RUNIDo_19980530_yyyymmdd_field_0002.nc',
                   'RUNIDo_19980530_yyyymmdd_field.nc',
                   'RUNIDo_19981130_yyyymmdd_field_0000.nc']
        cmpts = [f for f in myfiles if '530_yyyymmdd_field_0' in f]
        for fname in myfiles:
            open(fname, 'w').close()
        self.nemo.rebuild_fileset(os.getcwd(), 'field')
        mock_nl.assert_called_once_with(os.getcwd(),
                                        'RUNIDo_19980530_yyyymmdd_field',
                                        cmpts, omp=1, msk=False)
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
                   'RUNIDo_icebergs_19980530_restart_0000.nc',
                   'RUNIDo_19980530_restart_trc_0000.nc']
        cmpts = [f for f in myfiles if 'o_19980530_restart_0' in f]
        for fname in myfiles:
            open(fname, 'w').close()

        self.nemo.rebuild_fileset(os.getcwd(),
                                  'RUNIDo_19980530_restart')
        mock_nl.assert_called_once_with(os.getcwd(),
                                        'RUNIDo_19980530_restart',
                                        cmpts, omp=1, msk=False)
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
                   'RUNIDo_icebergs_19980530_restart_0001.nc',
                   'RUNIDo_19980530_restart_trc_0000.nc']
        cmpts = [f for f in myfiles if 'bergs_19980530_restart_0' in f]
        for fname in myfiles:
            open(fname, 'w').close()
        self.nemo.rebuild_fileset(os.getcwd(),
                                  'RUNIDo_icebergs_19980530_restart')
        mock_nl.assert_called_once_with(os.getcwd(),
                                        'RUNIDo_icebergs_19980530_restart',
                                        cmpts, omp=1, msk=False)
        for fname in myfiles:
            os.remove(fname)

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    def test_rebuild_pattern_tracers(self, mock_nl):
        '''Test rebuild tracer restarts pattern matching function'''
        func.logtest('Assert rebuild tracer rsts pattern matching function:')
        myfiles = ['RUNIDo_19980530_yyyymmdd_field_0000.nc',
                   'RUNIDo_19980530_restart_0000.nc',
                   'RUNIDo_19980530_restart_trc_0000.nc',
                   'RUNIDo_19980530_restart_trc_0001.nc',
                   'RUNIDo_icebergs_19980530_restart_0000.nc']
        for fname in myfiles:
            open(fname, 'w').close()
        self.nemo.rebuild_fileset(os.getcwd(),
                                  'RUNIDo_19980530_restart_trc')
        mock_nl.assert_called_once_with(os.getcwd(),
                                        'RUNIDo_19980530_restart_trc',
                                        ['RUNIDo_19980530_restart_trc_0000.nc',
                                         'RUNIDo_19980530_restart_trc_0001.nc'],
                                        omp=1, msk=False)
        for fname in myfiles:
            os.remove(fname)

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('nemo.utils.get_subset')
    def test_rebuild_rst_finalcycle(self, mock_subset, mock_nl):
        '''Test final cycle behaviour - deleting components of restarts'''
        func.logtest('Assert component files not deleted on final cycle:')
        tmp_dirs = []
        rebuild_zero = ['file_11112233_restart_0000.nc']
        rebuild_set = ['file_restart_11112233_0000.nc',
                       'file_restart_11112233_0001.nc']
        mock_subset.side_effect = [tmp_dirs, rebuild_zero, rebuild_set]
        mock_nl.return_value = 0
        self.nemo.suite.finalcycle = True
        self.nemo.rebuild_fileset('SourceDir', 'yyyymmdd_restart')
        mock_nl.assert_called_once_with('SourceDir', 'file_11112233_restart',
                                        rebuild_set, omp=1, msk=False)
        self.assertNotIn('deleting component files', func.capture().lower())

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.remove_files')
    def test_rebuild_diags_finalcycle(self, mock_rm, mock_subset, mock_nl):
        '''Test final cycle behaviour - deleting components of means'''
        func.logtest('Assert component files not deleted on final cycle:')
        tmp_dirs = []
        rebuild_zero = ['file_11112233_mean1_0000.nc',
                        'file_11112233_mean2_0000.nc']
        rebuild_set1 = ['mean1_c1', 'mean1_c2']
        rebuild_set2 = ['mean2_c1', 'mean2_c2']
        mock_subset.side_effect = [tmp_dirs, rebuild_zero,
                                   rebuild_set1, rebuild_set2]
        mock_nl.return_value = 0
        self.nemo.suite.finalcycle = True
        self.nemo.rebuild_fileset('SourceDir', 'mean')

        self.assertIn('deleting component files', func.capture().lower())
        nl_calls = [mock.call('SourceDir', 'file_11112233_mean1',
                              rebuild_set1, omp=1, msk=False),
                    mock.call('SourceDir', 'file_11112233_mean2',
                              rebuild_set2, omp=1, msk=False)]
        self.assertListEqual(mock_nl.mock_calls, nl_calls)
        rm_calls = [mock.call(rebuild_set1, path='SourceDir'),
                    mock.call(rebuild_set2, path='SourceDir')]
        self.assertListEqual(mock_rm.mock_calls, rm_calls)

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.NemoPostProc.global_attr_to_zonal')
    def test_rebuild_diaptr_means(self, mock_attr, mock_subset, mock_nl):
        '''Test rebuild all function - diaptr means'''
        func.logtest('Assert rebuild all function - diaptr means:')
        self.nemo.naml.processing.rebuild_mean_buffer = 1
        tmp_dirs = []
        rebuild_zero = ['file_19980530_yyyymmdd_diaptr_0000.nc',
                        'file_19980630_yyyymmdd_diaptr_0000.nc']
        rebuild_set = ['component_file1', 'component_file2']
        mock_subset.side_effect = [tmp_dirs, rebuild_zero, rebuild_set]
        self.nemo.rebuild_fileset('SourceDir', 'f_diaptr')
        mock_nl.assert_called_once_with('SourceDir',
                                        'file_19980530_yyyymmdd_diaptr',
                                        rebuild_set, omp=1, msk=False)
        mock_attr.assert_called_once_with(
            'SourceDir', ['component_file1', 'component_file2']
            )

    @mock.patch('nemo.utils.exec_subproc')
    @mock.patch('nemo.os.path.isfile')
    def test_rebuild_namelist(self, mock_isfile, mock_exec):
        '''Test rebuild namelist function writing in temp directory'''
        func.logtest('Assert behaviour of rebuild_namelist function - tmpdir:')
        mock_exec.return_value = (0, '')
        mock_isfile.return_value = True
        with mock.patch('nemo.utils.remove_files'):
            with mock.patch('nemo.shutil.rmtree'):
                rtn = self.nemo.rebuild_namelist(
                    os.getcwd(), 'file_19980530_ymd',
                    ['f1', 'f2', 'f3'])
        self.assertEqual(mock_exec.return_value[0], rtn)
        self.assertEqual(int(os.environ['OMP_NUM_THREADS']), 16)
        self.assertIn('successfully rebuilt', func.capture().lower())
        self.assertIn('file_19980530_ymd', func.capture().lower())
        mock_exec.assert_called_once_with(
            self.defaults.exec_rebuild,
            cwd=os.path.join(os.getcwd(), 'rebuilding_FILE_19980530_YMD')
            )
        self.assertTrue(os.path.isdir('rebuilding_FILE_19980530_YMD'))
        txt = open(os.path.join('rebuilding_FILE_19980530_YMD', 'nam_rebuild'),
                   'r').read()
        self.assertNotIn('dims=\'1\',\'2\'', txt)

    @mock.patch('nemo.utils.exec_subproc')
    @mock.patch('nemo.os.path.isfile')
    def test_rebuild_userdef_namelist(self, mock_isfile, mock_exec):
        '''Test rebuild namelist function writing to bespoke namelist file'''
        func.logtest('Assert behaviour of rebuild_namelist - bespoke nl:')
        mock_exec.return_value = (0, '')
        mock_isfile.return_value = True
        with mock.patch('nemo.NemoPostProc.rebuild_cmd',
                        new_callable=mock.PropertyMock,
                        return_value='utility mynaml'):
            with mock.patch('nemo.utils.remove_files'):
                rtn = self.nemo.rebuild_namelist(os.getcwd(),
                                                 'file_19980530_ymd',
                                                 ['f1', 'f2', 'f3'])
        txt = open('mynaml', 'r').read()
        os.remove('mynaml')
        self.assertNotIn('dims=\'1\',\'2\'', txt)
        self.assertEqual(mock_exec.return_value[0], rtn)
        self.assertEqual(int(os.environ['OMP_NUM_THREADS']), 16)
        self.assertIn('successfully rebuilt', func.capture().lower())
        self.assertIn('file_19980530_ymd', func.capture().lower())
        mock_exec.assert_called_once_with('utility mynaml', cwd=os.getcwd())
        self.assertFalse(os.path.isdir('rebuilding_FILE_19980530_YMD'))

    @mock.patch('nemo.utils.exec_subproc')
    @mock.patch('nemo.os.path.isfile')
    def test_rebuild_filetype_namelist(self, mock_isfile, mock_exec):
        '''Test rebuild namelist function writing to naml file by filetype'''
        func.logtest('Assert behaviour of rebuild_namelist - filetype nl:')
        mock_exec.return_value = (0, '')
        mock_isfile.return_value = True
        with mock.patch('nemo.NemoPostProc.rebuild_cmd',
                        new_callable=mock.PropertyMock,
                        return_value='utility %F'):
            with mock.patch('nemo.utils.remove_files'):
                rtn = self.nemo.rebuild_namelist(os.getcwd(),
                                                 'file_19980530_ymd',
                                                 ['f1', 'f2', 'f3'])
        txt = open('rebuild_FILE_19980530_YMD', 'r').read()
        os.remove('rebuild_FILE_19980530_YMD')
        self.assertNotIn('dims=\'1\',\'2\'', txt)
        self.assertEqual(mock_exec.return_value[0], rtn)
        self.assertEqual(int(os.environ['OMP_NUM_THREADS']), 16)
        self.assertIn('successfully rebuilt', func.capture().lower())
        self.assertIn('file_19980530_ymd', func.capture().lower())
        mock_exec.assert_called_once_with('utility rebuild_FILE_19980530_YMD',
                                          cwd=os.getcwd())
        self.assertFalse(os.path.isdir('rebuilding_FILE_19980530_YMD'))

    @mock.patch('nemo.utils.exec_subproc')
    @mock.patch('nemo.os.path.isfile')
    def test_rebuild_namelist_options(self, mock_isfile, mock_exec):
        '''Test rebuild namelist function with options'''
        func.logtest('Assert rebuild_namelist function with options:')
        mock_exec.return_value = (0, '')
        mock_isfile.return_value = True
        with mock.patch('nemo.utils.move_files'):
            with mock.patch('nemo.utils.remove_files'):
                with mock.patch('nemo.shutil.rmtree'):
                    rtn = self.nemo.rebuild_namelist(
                        os.getcwd(), 'file_19980530_ymd',
                        ['f1', 'f2', 'f3'],
                        omp=1, chunk='opt_chunk', dims=[1, 2], msk=True
                        )
        self.assertEqual(int(os.environ['OMP_NUM_THREADS']), 1)
        self.assertEqual(rtn, 0)
        txt = open(os.path.join('rebuilding_FILE_19980530_YMD',
                                'nam_rebuild'), 'r').read()
        self.assertIn('dims=\'1\',\'2\'', txt)
        self.assertIn('nchunksize=opt_chunk', txt)
        self.assertIn('l_maskout=.true.', txt)

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('nemo.utils.get_subset')
    def test_rebuild_mask(self, mock_subset, mock_nl):
        '''Test rebuild all function with mask option'''
        func.logtest('Assert rebuild all function with mask option:')
        self.nemo.naml.processing.rebuild_mean_buffer = 1
        # Buffer is 1 - 1st subset side_effect must be list of 2.
        tmp_dirs = []
        rebuild_zero = ['file_19980530', 'file_19980630']
        rebuild_set = ['file_19980530_0000.nc', 'file_19980530_0001.nc',
                       'file_19980530_0002.nc']
        mock_subset.side_effect = [tmp_dirs, rebuild_zero, rebuild_set]
        self.nemo.naml.processing.msk_rebuild = True
        self.nemo.rebuild_fileset(os.getcwd(), 'field')
        mock_nl.assert_called_once_with(os.getcwd(), 'file_19980530',
                                        rebuild_set,
                                        omp=1, msk=True)

    @mock.patch('nemo.utils.exec_subproc')
    @mock.patch('nemo.os.path.isfile')
    def test_rbld_namelist_no_namelist(self, mock_isfile, mock_exec):
        '''Test failure to create namelist file'''
        func.logtest('Assert failure to create namelist file:')
        mock_exec.return_value = (0, '')
        mock_isfile.return_value = False
        rtn = self.nemo.rebuild_namelist(os.getcwd(),
                                         'file_19980530_yyyymmdd',
                                         ['f1', 'f2', 'f3'])
        self.assertEqual(rtn, 910)
        self.assertIn('failed to create namelist file',
                      func.capture('err').lower())

    @mock.patch('nemo.utils.exec_subproc')
    def test_rebuild_namelist_fail(self, mock_exec):
        '''Test failure mode of rebuild namelist function'''
        func.logtest('Assert failure behaviour of rebuild_namelist function:')
        mock_exec.return_value = (1, '')
        with mock.patch('nemo.os.path.isfile', return_value=True):
            with self.assertRaises(SystemExit):
                _ = self.nemo.rebuild_namelist(os.getcwd(),
                                               'file_19980530_yyyymmdd',
                                               ['f1', 'f2', 'f3'])
        self.assertIn('failed to rebuild file', func.capture('err').lower())
        self.assertIn('file_19980530_yyyymmdd', func.capture('err').lower())

    @mock.patch('nemo.utils.exec_subproc')
    def test_rebuild_nlist_fail_debug(self, mock_exec):
        '''Test failure mode of rebuild namelist function - debug_mode'''
        func.logtest('Assert debug behaviour of rebuild_namelist function:')
        mock_exec.return_value = (1, '')
        with mock.patch('nemo.utils.get_debugmode', return_value=True):
            with mock.patch('nemo.os.path.isfile', return_value=True):
                _ = self.nemo.rebuild_namelist(os.getcwd(), 'file_19980530_ymd',
                                               ['f1', 'f2', 'f3'])
        self.assertIn('failed to rebuild file', func.capture('err').lower())
        self.assertIn('file_19980530_ymd', func.capture('err').lower())

    def test_rebuild_icebergs_call(self):
        '''Test call to external iceberg rebuilding routine: icb_combrest'''
        func.logtest('Assert call to external iceberg rebuilding routine:')
        fbase = 'file_icebergs_yyyymmdd'
        with mock.patch('utils.exec_subproc', return_value=(0, '')):
            with mock.patch('nemo.NemoPostProc.rebuild_icebergs') as mock_rbld:
                mock_rbld.return_value = 0
                with mock.patch('nemo.os.path.isfile', return_value=True):
                    self.nemo.rebuild_namelist(os.getcwd(), fbase, ['f1', 'f2'])
                mock_rbld.assert_called_once_with(
                    os.path.join(os.getcwd(), 'rebuilding_' + fbase.upper()),
                    fbase, 2
                    )
        self.assertIn('Successfully rebuilt', func.capture())

    def test_rebuild_icebergs_cmd(self):
        '''Test call to external iceberg rebuilding routine: icb_combrest'''
        func.logtest('Assert call to external iceberg rebuilding routine:')
        with mock.patch('nemo.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            self.nemo.rebuild_icebergs('TestDir', 'filebase', '1')
        cmd = 'python2.7 {} -f TestDir/filebase_ -n 1 -o TestDir/filebase.nc'.\
            format(self.defaults.exec_rebuild_icebergs)
        mock_exec.assert_called_once_with(cmd, cwd='TestDir')
        self.assertIn('Successfully rebuilt', func.capture())

    def test_rebuild_icebergs_fail(self):
        '''Test call to external iceberg rebuilding routine: icb_combrest'''
        func.logtest('Assert call to external iceberg rebuilding routine:')
        with mock.patch('nemo.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, 'err output')
            self.nemo.rebuild_icebergs('TestDir', 'filebase', '1')
        self.assertIn('Failed to rebuild file', func.capture('err'))
        self.assertIn('err output', func.capture('err'))


class MeansProcessingTests(unittest.TestCase):
    '''Unit tests relating to the processing of means files'''
    def setUp(self):
        self.nemo = nemo.NemoPostProc()
        self.nemo.suite = mock.Mock()
        self.defaults = nemo_namelist.Processing()
        self.ncdumpout = '''
  :DOMAIN_size_global = x, 1207;
  :dummy arg = some value;
  :DOMAIN_position_last = x, 151;
  :DOMAIN_position_first = x, 1;
  :dummy arg2 = some other value;
  :history = "Wed Jul 20 18:06:21 2016: \
/projects/ocean/hadgem3/nco/nco-4.4.7/bin/ncatted \
-a DOMAIN_size_global,global,m,l,1,1021 \
-a DOMAIN_position_first,global,m,l,1,1 \
-a DOMAIN_position_last,global,m,l,1,43 \
-a ibegin,global,m,l,1 /home/jwalto/cylc-run/u-ae710/share/data/\
History_Data/NEMOhist/ae710o_10d_19780901_19780910_diaptr_0000.nc";
'''

    def tearDown(self):
        for fname in runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_global_attr_to_zonal(self):
        '''Test method to transform global attributes to zonal ones'''
        func.logtest('Assert functionality of global_attr_to_zonal method:')
        self.nemo.suite.preprocess_file.return_value = self.ncdumpout
        with mock.patch('nemo.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            self.nemo.global_attr_to_zonal('TestDir', 'File1')
        mock_exec.assert_called_once_with(' '.join([
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
        with mock.patch('nemo.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            self.nemo.global_attr_to_zonal('TestDir', ['File1', 'File2'])
            mock_exec.assert_called_with(
                ' '.join([self.defaults.ncatted_cmd,
                          '-a DOMAIN_size_global,global,m,l,1,1207',
                          '-a DOMAIN_position_first,global,m,l,1,1',
                          '-a DOMAIN_position_last,global,m,l,1,151',
                          '-a ibegin,global,m,l,1', 'TestDir/File2'])
                )
        self.assertIn('Changing nc file attributes', func.capture())
        self.assertIn('ncatted - Successful', func.capture())

    def test_global_to_zonal_fail(self):
        '''Test method to transform global attributes to zonal - failure'''
        func.logtest('Assert failure of global_attr_to_zonal method:')
        self.nemo.suite.preprocess_file.return_value = self.ncdumpout
        with mock.patch('nemo.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, '')
            with self.assertRaises(SystemExit):
                self.nemo.global_attr_to_zonal('TestDir', 'File1')
        self.assertIn('Changing nc file attributes', func.capture('err'))
        self.assertIn('ncatted - Failed', func.capture('err'))

    def test_global_to_zonal_missing(self):
        '''Test method global attributes to zonal ones - missing attributes'''
        func.logtest('Assert missing attributes with global_attr_to_zonal:')
        ncdumpout = '''
  :dummy arg = some value;
  :DOMAIN_position_last = x, 151;
  :DOMAIN_position_first = x, 1;
  :dummy arg2 = some other value;
'''
        self.nemo.suite.preprocess_file.return_value = ncdumpout
        with mock.patch('nemo.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, '')
            with self.assertRaises(SystemExit):
                self.nemo.global_attr_to_zonal('TestDir', 'File1')
            self.assertEqual(mock_exec.mock_calls, [])

        self.assertIn('attribute(s) DOMAIN_size_global not found',
                      func.capture('err'))
        self.assertEqual(len(mock_exec.mock_calls), 0)


class AdditionalArchiveTests(unittest.TestCase):
    '''Unit tests relating to the archiving additional file'''
    def setUp(self):
        self.nemo = nemo.NemoPostProc()
        self.nemo.suite = mock.Mock()
        self.nemo.suite.prefix = 'RUNID'
        self.nemo.archive_files = mock.Mock(return_value={})
        self.nemo.naml.processing.exec_rebuild_iceberg_trajectory = 'ICB_PP'
        self.nemo.share = 'HERE'
        self.nemo.work = 'HERE'

    def tearDown(self):
        for fname in runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.exec_subproc', return_value=(0, ''))
    @mock.patch('nemo.utils.remove_files')
    def test_create_iberg_trajectory(self, mock_rm, mock_exec, mock_set):
        '''Test call to iceberg_trajectory creation method'''
        func.logtest('Assert call to iceberg_trajectory creation method:')
        # Mock results for 2 calls to utils.get_subset
        mock_set.side_effect = [['file1_0000.nc'],
                                ['file1_0000.nc', 'file1_0001.nc']]

        self.nemo.naml.archiving.archive_iceberg_trajectory = True
        self.nemo.create_general()

        cmd = 'python2.7 ICB_PP -t HERE/file1_ -n 2 -o HERE/RUNIDo_file1.nc'
        mock_exec.assert_called_once_with(cmd)
        mock_rm.assert_called_once_with(['file1_0000.nc', 'file1_0001.nc'],
                                        path='HERE')
        self.assertIn('Successfully rebuilt iceberg trajectory',
                      func.capture())

    @mock.patch('nemo.utils.exec_subproc')
    @mock.patch('nemo.utils.get_subset')
    def test_create_iberg_traj_fail(self, mock_set, mock_exec):
        '''Test call to iceberg_trajectory archive method - fail'''
        func.logtest('Assert failed call to iceberg_trajectory method:')
        # Mock results for 3 calls to utils.get_subset
        mock_set.side_effect = [['file1_0000.nc'],
                                ['file1_0000.nc', 'file1_0001.nc'],
                                ['arch1.nc']]
        mock_exec.return_value = (1, 'ICB_PP failed')
        self.nemo.naml.archiving.archive_iceberg_trajectory = True
        with self.assertRaises(SystemExit):
            self.nemo.create_general()
        with self.assertRaises(AssertionError):
            self.nemo.archive_files.assert_called_once_with(mock.ANY)
        self.assertIn('Error=1\n\tICB_PP failed', func.capture('err'))

    @mock.patch('nemo.utils.exec_subproc')
    @mock.patch('nemo.utils.get_subset')
    def test_create_iberg_traj_debug(self, mock_set, mock_exec):
        '''Test call to iceberg_trajectory creation method - debug'''
        func.logtest('Assert debug build call to iceberg_trajectory method:')
        # Mock results for 2 calls to utils.get_subset
        mock_set.side_effect = [['file1_0000.nc'],
                                ['file1_0000.nc', 'file1_0001.nc']]
        mock_exec.return_value = (1, 'ICB_PP failed')
        self.nemo.naml.archiving.archive_iceberg_trajectory = True
        with mock.patch('nemo.utils.get_debugmode', return_value=True):
            self.nemo.create_general()
        self.assertIn('Error=1\n\tICB_PP failed', func.capture('err'))

    @mock.patch('nemo.mt.ModelTemplate.move_to_share')
    def test_create_iberg_traj_move(self, mock_mv):
        '''Test call to iceberg_trajectory archive method - move files'''
        func.logtest('Assert call to archive_iceberg_trajectory with move:')
        self.nemo.naml.archiving.archive_iceberg_trajectory = True
        self.nemo.share = 'THERE'
        with mock.patch('nemo.utils.get_subset'):
            self.nemo.create_general()
        iberg_pattern = r'trajectory_icebergs_\d{6,8}(-\d{8})?_\d{4}\.nc'
        mock_mv.assert_called_once_with(pattern=iberg_pattern)
        self.assertIsNotNone(re.match(iberg_pattern,
                                      'trajectory_icebergs_000720_0000.nc'))
        self.assertIsNotNone(
            re.match(iberg_pattern,
                     'trajectory_icebergs_11112233-44445566_0000.nc')
            )

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.mt.ModelTemplate.clean_archived_files')
    def test_arch_iberg_trajectory(self, mock_clean, mock_set):
        '''Test call to archive iceberg trajectory'''
        func.logtest('Assert call to archive iceberg trajectory')
        mock_set.side_effect = [['arch1.nc']]
        self.nemo.naml.archiving.archive_iceberg_trajectory = True
        self.nemo.archive_general()
        self.nemo.archive_files.assert_called_once_with(['arch1.nc'])
        iberg_pattern = r'^RUNIDo_trajectory_icebergs_\d{6,8}(-\d{8})?\.nc$'
        mock_set.assert_called_once_with('HERE', iberg_pattern)
        mock_clean.assert_called_once_with(self.nemo.archive_files.return_value,
                                           'iceberg_trajectory')

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.remove_files')
    @mock.patch('nemo.os.rename')
    def test_arch_iberg_traj_debug(self, mock_name, mock_rm, mock_set):
        '''Test call to iceberg_trajectory archive method - debug mode'''
        func.logtest('Assert call to iceberg_traj archive method - debug:')
        self.nemo.archive_files.return_value = {'arch1.nc': 'FAILED',
                                                'arch2.nc': 'SUCCESS',
                                                'arch3.nc': 'SUCCESS'}

        self.nemo.naml.archiving.archive_iceberg_trajectory = True
        with mock.patch('nemo.utils.get_debugmode', return_value=True):
            self.nemo.archive_general()

        self.nemo.archive_files.assert_called_once_with(mock_set.return_value)
        self.assertListEqual(mock_rm.mock_calls, [])

        self.assertEqual(len(mock_name.mock_calls), 2)
        self.assertIn(mock.call('HERE/arch2.nc', 'HERE/arch2.nc_ARCHIVED'),
                      mock_name.mock_calls)
        self.assertIn(mock.call('HERE/arch3.nc', 'HERE/arch3.nc_ARCHIVED'),
                      mock_name.mock_calls)
        self.assertIn('iceberg_trajectory: deleting archived file(s):',
                      func.capture())
        self.assertNotIn('arch1.nc', func.capture())
        self.assertIn('arch2.nc', func.capture())
        self.assertIn('arch3.nc', func.capture())

    @mock.patch('nemo.utils.remove_files')
    def test_arch_iberg_traj_archpass(self, mock_rm):
        '''Test call to iceberg_trajectory archive method - arch pass'''
        func.logtest('Assert call to archive_iceberg_trajectory - arch pass:')
        self.nemo.naml.archiving.archive_iceberg_trajectory = True
        self.nemo.archive_files.return_value = {'arch1': 'SUCCESS'}
        with mock.patch('nemo.utils.get_subset'):
            self.nemo.archive_general()
        self.nemo.archive_files.assert_called_once_with(mock.ANY)
        mock_rm.assert_called_once_with(['arch1'], path='HERE')

    @mock.patch('nemo.utils.remove_files')
    def test_arch_iberg_traj_archfail(self, mock_rm):
        '''Test call to iceberg_trajectory archive method - arch fail'''
        func.logtest('Assert call to archive_iceberg_trajectory - arch fail:')
        self.nemo.naml.archiving.archive_iceberg_trajectory = True
        self.nemo.archive_files.return_value = {'arch1': 'FAILED'}
        with mock.patch('nemo.utils.get_subset'):
            self.nemo.archive_general()
        self.nemo.archive_files.assert_called_once_with(mock.ANY)
        self.assertListEqual(mock_rm.mock_calls, [])

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.move_files')
    def test_create_region_extract(self, mock_mv, mock_set):
        '''Test call to create_regional_extraction method'''
        func.logtest('Assert call to create_regional_extraction:')
        self.nemo.naml.processing.extract_region = True
        self.nemo.region_fields = self.nemo._region_fields
        self.nemo.diagsdir = os.getcwd()
        mock_set.side_effect = [['fileT'], [], ['fileV1', 'fileV2']]
        self.nemo.suite.preprocess_file.side_effect = ['ncdump_outT',
                                                       (0, 'nkcs_outT'),
                                                       'ncdump_outV1',
                                                       (0, 'nkcs_outV1'),
                                                       'ncdump_outV2',
                                                       (0, 'nkcs_outV2')]
        self.nemo.create_general()

        pattern = r'[a-z]*_runido_\d+[hdmsyx]{{1}}_\d{{4}}\d{{2}}\d{{2}}' + \
            r'-\d{{4}}\d{{2}}\d{{2}}_{}.nc'
        mockset_calls = []
        for field in ['UK_shelf_T', 'UK_shelf_U', 'UK_shelf_V']:
            mockset_calls.append(mock.call('HERE', pattern.format(field)))
        self.assertListEqual(mock_set.mock_calls, mockset_calls)

        self.assertIn(mock.call('ncdump', 'HERE/fileT', h=''),
                      self.nemo.suite.preprocess_file.mock_calls)
        self.assertIn(mock.call('ncks', 'HERE/fileV1', O='', a='',
                                d_1='x,1055,1198', d_2='y,850,1040'),
                      self.nemo.suite.preprocess_file.mock_calls)

        mockmv_calls = [mock.call('HERE/fileT', os.getcwd()),
                        mock.call('HERE/fileV1', os.getcwd()),
                        mock.call('HERE/fileV2', os.getcwd())]
        self.assertListEqual(mock_mv.mock_calls, mockmv_calls)

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.move_files')
    def test_create_region_fielddim(self, mock_mv, mock_set):
        '''Test call to create_regional_extraction - field specific dims'''
        func.logtest('Assert call to create_regional_extraction - field dims:')
        self.nemo.naml.processing.extract_region = True
        self.nemo.naml.processing.region_dimensions = ['xgrid_%G', 1, 2,
                                                       'ygrid_%G', 3, 4]
        self.nemo.region_fields = ['shelf-T']
        self.nemo.diagsdir = os.getcwd()
        mock_set.side_effect = [['fileT']]
        self.nemo.suite.preprocess_file.side_effect = ['ncdump_outT',
                                                       (0, 'nkcs_outT')]
        self.nemo.create_general()

        pattern = r'[a-z]*_runido_\d+[hdmsyx]{{1}}_\d{{4}}\d{{2}}\d{{2}}' + \
            r'-\d{{4}}\d{{2}}\d{{2}}_{}.nc'
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call('HERE', pattern.format('shelf-T'))])

        self.assertEqual(self.nemo.suite.preprocess_file.mock_calls[0],
                         mock.call('ncdump', 'HERE/fileT', h=''))
        self.assertEqual(self.nemo.suite.preprocess_file.mock_calls[1],
                         mock.call('ncks', 'HERE/fileT', O='', a='',
                                   d_1='xgrid_T,1,2', d_2='ygrid_T,3,4'))

        self.assertListEqual(mock_mv.mock_calls,
                             [mock.call('HERE/fileT', os.getcwd())])

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.move_files')
    def test_create_region_pass(self, mock_mv, mock_set):
        '''Test call to create_regional_extraction - file already regional'''
        func.logtest('Assert call to create_regional_extraction - pass:')
        self.nemo.naml.processing.extract_region = True
        self.nemo.region_fields = ['shelf-T']
        self.nemo.diagsdir = os.getcwd()
        mock_set.side_effect = [['fileT']]
        self.nemo.suite.preprocess_file.side_effect = \
            ['ncdump_outT\nLine1\nLine2\n x = 144']
        self.nemo.create_general()

        self.assertListEqual(self.nemo.suite.preprocess_file.mock_calls,
                             [mock.call('ncdump', 'HERE/fileT', h='')])
        self.assertListEqual(mock_mv.mock_calls,
                             [mock.call('HERE/fileT', os.getcwd())])
        self.assertIn('No extraction necessary', func.capture())

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.mt.ModelTemplate.compress_file')
    @mock.patch('nemo.utils.move_files')
    def test_create_region_compress(self, mock_mv, mock_cmp, mock_set):
        '''Test call to create_regional_extraction - compress file'''
        func.logtest('Assert call to create_regional_extraction - compress:')
        self.nemo.naml.processing.extract_region = True
        self.nemo.region_fields = ['shelf-T']
        self.nemo.naml.processing.compression_level = 2
        self.nemo.diagsdir = os.getcwd()
        mock_set.side_effect = [['fileT']]
        self.nemo.suite.preprocess_file.side_effect = \
            ['ncdump_outT\nLine1\nLine2\n x = 144']
        self.nemo.create_general()

        mock_cmp.assert_called_once_with(
            'HERE/fileT', 'nccopy',
            chunking=['time_counter/1', 'y/191', 'x/144'],
            compression=2
            )
        self.assertListEqual(mock_mv.mock_calls, [])

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.move_files')
    def test_create_region_meanfield(self, mock_mv, mock_set):
        '''Test call to create_regional_extraction - future mean field'''
        func.logtest('Assert call to create_regional_extraction - mean field:')
        self.nemo.naml.processing.extract_region = True
        self.nemo.region_fields = ['shelf_T', 'grid_T']
        self.nemo.diagsdir = os.getcwd()
        mock_set.side_effect = [['shelfT'], ['gridT']]
        self.nemo.suite.preprocess_file.return_value = \
            'ncdump_outT \n Line1 \n Line2 \n x = 144'

        self.nemo.create_general()
        self.assertListEqual(mock_mv.mock_calls,
                             [mock.call('HERE/shelfT', os.getcwd())])

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.move_files')
    def test_create_region_nodims(self, mock_mv, mock_set):
        '''Test call to create_regional_extraction - no dims'''
        func.logtest('Assert call to create_regional_extraction - no dims:')
        self.nemo.naml.processing.extract_region = True
        self.nemo.naml.processing.region_dimensions = []
        self.nemo.region_fields = ['shelf-T']
        self.nemo.diagsdir = os.getcwd()
        mock_set.side_effect = [['fileT']]
        self.nemo.suite.preprocess_file.side_effect = ['ncdump_outT',
                                                       (0, 'nkcs_outT')]
        with self.assertRaises(SystemExit):
            self.nemo.create_general()

        pattern = r'[a-z]*_runido_\d+[hdmsyx]{{1}}_\d{{4}}\d{{2}}\d{{2}}' + \
            r'-\d{{4}}\d{{2}}\d{{2}}_{}.nc'
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call('HERE', pattern.format('shelf-T'))])

        self.assertListEqual(self.nemo.suite.preprocess_file.mock_calls, [])
        self.assertListEqual(mock_mv.mock_calls, [])
        self.assertIn('Unable to determine x-y dimensions', func.capture('err'))

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.move_files')
    def test_create_region_nodims_debug(self, mock_mv, mock_set):
        '''Test call to create_regional_extraction - no dims in debug mode'''
        func.logtest('Assert debug call to regional extraction - no dims:')
        self.nemo.naml.processing.extract_region = True
        self.nemo.naml.processing.region_dimensions = []
        self.nemo.region_fields = ['shelf-T']
        self.nemo.diagsdir = os.getcwd()
        mock_set.side_effect = [['fileT']]
        self.nemo.suite.preprocess_file.side_effect = ['ncdump_outT']
        with mock.patch('nemo.utils.get_debugmode', return_value=True):
            self.nemo.create_general()

        pattern = r'[a-z]*_runido_\d+[hdmsyx]{{1}}_\d{{4}}\d{{2}}\d{{2}}' + \
            r'-\d{{4}}\d{{2}}\d{{2}}_{}.nc'
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call('HERE', pattern.format('shelf-T'))])

        self.assertListEqual(self.nemo.suite.preprocess_file.mock_calls, [])
        self.assertListEqual(mock_mv.mock_calls, [])
        self.assertIn('Unable to determine x-y dimensions', func.capture('err'))

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.mt.ModelTemplate.clean_archived_files')
    def test_arch_region_extract(self, mock_clean, mock_set):
        '''Test call to archive_regional_extraction'''
        func.logtest('Assert call to archive_regional_extraction')
        mock_set.side_effect = [['archT1'], [], ['archV1', 'archV2']]
        self.nemo.naml.processing.extract_region = True
        self.nemo.region_fields = self.nemo._region_fields
        self.nemo.diagsdir = 'DDIR'
        with mock.patch('nemo.utils.check_directory', return_value='DDIR'):
            self.nemo.archive_general()

        self.assertListEqual(self.nemo.archive_files.mock_calls,
                             [mock.call(['DDIR/archT1']),
                              mock.call([]),
                              mock.call(['DDIR/archV1', 'DDIR/archV2'])])

        pattern = r'^[a-z]*_runido_\d+[hdmsyx]{{1}}_\d{{4}}\d{{2}}\d{{2}}-' + \
            r'\d{{4}}\d{{2}}\d{{2}}_{}.nc$'
        self.assertListEqual(mock_set.mock_calls,
                             [mock.call('DDIR', pattern.format('UK_shelf_T')),
                              mock.call('DDIR', pattern.format('UK_shelf_U')),
                              mock.call('DDIR', pattern.format('UK_shelf_V'))])
        for call in range(3):
            self.assertEqual(mock_clean.mock_calls[call],
                             mock.call(self.nemo.archive_files.return_value,
                                       'UK Shelf region'))
        self.assertEqual(len(mock_clean.mock_calls), 3)

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.remove_files')
    @mock.patch('nemo.os.rename')
    def test_arch_region_debug(self, mock_name, mock_rm, mock_set):
        '''Test call to archive_regional_extraction - debug mode'''
        func.logtest('Assert call to archive_regional_extraction - debug mode')
        self.nemo.archive_files.return_value = {'DDIR/arch1.nc': 'FAILED',
                                                'DDIR/arch2.nc': 'SUCCESS',
                                                'arch3.nc': 'SUCCESS'}
        self.nemo.naml.processing.extract_region = True
        self.nemo.region_fields = ['shelf-T']
        self.nemo.diagsdir = 'DDIR'
        with mock.patch('nemo.utils.get_debugmode', return_value=True):
            with mock.patch('nemo.utils.check_directory', return_value='DDIR'):
                self.nemo.archive_general()

        self.nemo.archive_files.assert_called_once_with([mock_set.return_value])
        self.assertListEqual(mock_rm.mock_calls, [])

        self.assertEqual(len(mock_name.mock_calls), 2)
        self.assertIn(mock.call('DDIR/arch2.nc', 'DDIR/arch2.nc_ARCHIVED'),
                      mock_name.mock_calls)
        self.assertIn(mock.call('DDIR/arch3.nc', 'DDIR/arch3.nc_ARCHIVED'),
                      mock_name.mock_calls)
        self.assertIn('UK Shelf region: deleting archived file(s):',
                      func.capture())
        self.assertNotIn('arch1.nc', func.capture())
        self.assertIn('arch2.nc', func.capture())
        self.assertIn('arch3.nc', func.capture())

    @mock.patch('nemo.utils.remove_files')
    def test_arch_region_archpass(self, mock_rm):
        '''Test call to archive_regional_extraction - arch pass'''
        func.logtest('Assert call to archive_regional_extraction - arch pass')
        self.nemo.naml.processing.extract_region = True
        self.nemo.region_fields = ['shelf-T']
        self.nemo.diagsdir = 'DDIR'
        self.nemo.archive_files.return_value = {'DDIR/arch1': 'SUCCESS'}
        with mock.patch('nemo.utils.check_directory', return_value='DDIR'):
            with mock.patch('nemo.utils.get_subset'):
                self.nemo.archive_general()
        self.nemo.archive_files.assert_called_once_with(mock.ANY)
        mock_rm.assert_called_once_with(['DDIR/arch1'], path='DDIR')

    @mock.patch('nemo.utils.remove_files')
    def test_arch_region_archfail(self, mock_rm):
        '''Test call to archive_regional_extraction - arch fail'''
        func.logtest('Assert call to archive_regional_extraction - arch fail')
        self.nemo.naml.processing.extract_region = True
        self.nemo.region_fields = ['shelf-T']
        self.nemo.diagsdir = 'DDIR'
        self.nemo.archive_files.return_value = {'arch1': 'FAILED'}
        with mock.patch('nemo.utils.check_directory', return_value='DDIR'):
            with mock.patch('nemo.utils.get_subset'):
                self.nemo.archive_general()
        self.nemo.archive_files.assert_called_once_with(mock.ANY)
        self.assertListEqual(mock_rm.mock_calls, [])


class UtilityMethodTests(unittest.TestCase):
    '''Unit tests relating to the NEMO utility methods'''
    def setUp(self):
        self.nemo = nemo.NemoPostProc()
        self.nemo.share = os.getcwd()
        self.nemo.suite = mock.Mock()
        self.nemo.suite.prefix = 'RUNID'

    def tearDown(self):
        try:
            os.remove('nemocicepp.nl')
        except OSError:
            pass

    def test_get_date_start(self):
        '''Test extraction of 6-10 digit strings from a filename - startdate'''
        func.logtest('Assert startdate returned from get_date:')
        fname = 'RUNIDo_Xf_1111-222222_33333333-4444444444_555555555555.nc'
        startdate = self.nemo.get_date(fname)
        self.assertTupleEqual(startdate, ('3333', '33', '33'))

    def test_get_date_end(self):
        '''Test extraction of 6-10 digit strings from a filename - enddate'''
        func.logtest('Assert enddate returned from get_date:')
        fname = 'RUNIDo_Xf_1111_222222_33333333_4444444444_555555555555.nc'
        enddate = self.nemo.get_date(fname, enddate=True)
        self.assertTupleEqual(enddate, ('4444', '44', '44', '44'))

    @mock.patch('nemo.NemoPostProc.rebuild_diagnostics')
    @mock.patch('nemo.mt.ModelTemplate.move_to_share')
    def test_move_to_share(self, mock_mt, mock_rbld):
        '''Test NEMO Specific move_to_share functionality'''
        func.logtest('Assert additional move_to_share processing in NEMO:')
        self.nemo.mean_fields = ['mean1', 'mean2']
        self.nemo.inst_fields = ['inst1']
        self.nemo.move_to_share()
        mock_mt.assert_called_once_with(pattern=None)
        self.assertListEqual(mock_rbld.mock_calls,
                             [mock.call(['mean1', 'mean2'], bases=['10d']),
                              mock.call(['inst1'])])

    @mock.patch('nemo.NemoPostProc.rebuild_diagnostics')
    @mock.patch('nemo.mt.ModelTemplate.move_to_share')
    def test_move_to_share_pattern(self, mock_mt, mock_rbld):
        '''Test move_to_share functionality - with pattern'''
        func.logtest('Assert pattern behaviour of move_to_share method:')
        mock_mt.return_value = ['FILE1']
        self.nemo.move_to_share(pattern=r'abcde')
        self.assertEqual(mock_rbld.mock_calls, [])
        mock_mt.assert_called_once_with(pattern='abcde')

    def test_components_nemo_model(self):
        '''Test component extraction - nemo model identification'''
        func.logtest('Assert NEMO in model identification:')
        with mock.patch('nemo.NemoPostProc.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'nemo': ['GRID', 'FIELD']}):
            ncf = self.nemo.filename_components(
                'RUNIDo_10d_20001201_20011210_FIELD.nc'
                )
        self.assertEqual(ncf.prefix, 'nemo_runido')
        self.assertEqual(ncf.base, '10d')
        self.assertEqual(ncf.start_date, ('2000', '12', '01'))
        self.assertEqual(ncf.calc_enddate(), ('2000', '12', '11'))

    @mock.patch('nemo.netcdf_filenames.NCFilename')
    def test_components_medusa_model(self, mock_ncf):
        '''Test component extraction - medusa model identification'''
        func.logtest('Assert MEDUSA in model identification:')
        with mock.patch('nemo.NemoPostProc.model_components',
                        new_callable=mock.PropertyMock,
                        return_value={'medusa': ['GRID', 'FIELD']}):
            self.nemo.filename_components(
                'RUNIDo_1m_11112233_44445566_FIELD.nc'
                )
        mock_ncf.assert_called_once_with('medusa', 'RUNID', 'o', base='1m',
                                         start_date=('1111', '22', '33'),
                                         custom='FIELD')

    @mock.patch('nemo.netcdf_filenames.NCFilename.__init__', return_value=None)
    def test_components_4date_format(self, mock_ncf):
        '''Test component extraction - 4 date format filename'''
        func.logtest('Assert correct date extraction - 4 date format:')
        fname = 'RUNIDo_10d_00000000_11111111_grid_V_22222222-33333333.nc'
        self.nemo.filename_components(fname)
        mock_ncf.assert_called_once_with('nemo', 'RUNID', 'o', base='10d',
                                         start_date=('2222', '22', '22'),
                                         custom='grid-V')

    @mock.patch('nemo.netcdf_filenames.NCFilename.__init__', return_value=None)
    def test_components_10digit_format(self, mock_ncf):
        '''Test component extraction - 4 date format filename'''
        func.logtest('Assert correct date extraction - 4 date format:')
        fname = 'RUNIDo_12h_0000000000_1111111111_grid_V' \
            '_2222222222-3333333333.nc'
        self.nemo.filename_components(fname)
        mock_ncf.assert_called_once_with('nemo', 'RUNID', 'o', base='12h',
                                         start_date=('2222', '22', '22', '22'),
                                         custom='grid-V')
