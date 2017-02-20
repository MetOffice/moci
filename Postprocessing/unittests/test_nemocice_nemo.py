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

# Import of nemo requires 'RUNID' from runtime environment
# Import of nemoNamelist requires 'DATAM' from runtime environment
runtime_environment.setup_env()
import nemo
import nemoNamelist


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

    def test_set_stencil_restarts(self):
        '''Test the regular expressions of the set_stencil method - restarts'''
        func.logtest('Assert restart pattern matching of set_stencil:')
        patt = re.compile(self.nemo.set_stencil['Restarts'](('', '')))
        nemo_rst = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(nemo_rst,
                         [fname for fname in self.files if 'restart' in fname
                          and 'iceberg' not in fname and '_trc' not in fname])

    def test_set_stencil_iceberg_rsts(self):
        '''Test the regex of the set_stencil method - iceberg restarts'''
        func.logtest('Assert iceberg restart pattern matching of set_stencil:')
        patt = re.compile(self.nemo.set_stencil['Restarts']
                          (self.nemo.rsttypes[1]))
        ice_rst = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(ice_rst,
                         [fname for fname in self.files if 'iceberg' in fname])

    def test_set_stencil_tracer_rsts(self):
        '''Test the regex of the set_stencil method - tracer restarts'''
        func.logtest('Assert tracer restart pattern matching of set_stencil:')
        patt = re.compile(self.nemo.set_stencil['Restarts']
                          (self.nemo.rsttypes[2]))
        ice_rst = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(ice_rst,
                         [fname for fname in self.files if '_trc' in fname])

    def test_mean_stencil_general(self):
        '''Test the regular expressions of the mean_stencil method - general'''
        func.logtest('Assert general pattern matching of mean_stencil:')
        patt = re.compile(self.nemo.mean_stencil['General']('FIELD'))
        sixhr_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(sixhr_set,
                         [fname for fname in self.files if
                          'restart' not in fname])

    def test_mean_stencil_general_6hr(self):
        '''Test the regular expressions of the mean_stencil method - 6 hourly'''
        func.logtest('Assert hourly pattern matching of mean_stencil - hourly:')
        patt = re.compile(self.nemo.mean_stencil['General']('FIELD', base='6h'))
        sixhr_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(sixhr_set,
                         [fname for fname in self.files if '6h_' in fname])


class Propertytests(unittest.TestCase):
    '''Tests relating to the NEMO properties'''

    def setUp(self):
        self.nemo = nemo.NemoPostProc()
        self.nemo.suite = mock.Mock()
        self.nemo.naml = nemoNamelist.NemoNamelist()

    def tearDown(self):
        try:
            os.remove('nemocicepp.nl')
        except OSError:
            pass

    def test_fields_property_default(self):
        '''Test the return value of the fields property - default'''
        func.logtest('Assert return value of fields property:')
        self.assertEqual(self.nemo.naml.means_fieldsfiles, None)
        self.assertEqual(self.nemo._fields, ('diad_T', 'diaptr', 'grid_T',
                                             'grid_U', 'grid_V', 'grid_W',
                                             'ptrc_T', 'scalar', 'trnd3d',))

    def test_fields_property_single(self):
        '''Test the return value of the fields property - single'''
        func.logtest('Assert return of the fields property - single supplied:')
        self.nemo.naml.means_fieldsfiles = 'grid_W'
        self.assertEqual(self.nemo._fields, ('grid_W',))

    def test_fields_property_list(self):
        '''Test the return value of the fields property - list'''
        func.logtest('Assert return of fields property - list supplied:')
        self.nemo.naml.means_fieldsfiles = ['grid_U', 'grid_T']
        self.assertEqual(self.nemo._fields, ('grid_T', 'grid_U'))


class RebuildTests(unittest.TestCase):
    '''Unit tests relating to the rebuilding of restart and means files'''
    def setUp(self):
        self.nemo = nemo.NemoPostProc()
        self.nemo.share = 'ShareDir'
        self.nemo.suite = mock.Mock()
        self.nemo.suite.prefix = 'RUNID'
        self.nemo.suite.finalcycle = False
        self.defaults = nemoNamelist.NemoNamelist()
        self.buffer_rst = self.nemo.buffer_rebuild('rst')
        self.buffer_mean = self.nemo.buffer_rebuild('mean')

    def tearDown(self):
        for fname in ['nam_rebuild'] + runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_call_rebuild_restarts(self):
        '''Test call to rebuild_restarts method'''
        func.logtest('Assert call to rebuild_fileset from rebuild_restarts:')
        with mock.patch('nemo.NemoPostProc.rebuild_fileset') as mock_fs:
            with mock.patch('nemo.NemoPostProc.rsttypes',
                            new_callable=mock.PropertyMock,
                            return_value=(self.nemo.rsttypes[0],)):
                self.nemo.rebuild_restarts()
            mock_fs.assert_called_with('ShareDir',
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
            mock_fs.assert_called_with('ShareDir',
                                       r'RUNIDo_icebergs_?\d{8}_restart(\.nc)?')

    def test_call_rebuild_tracer_rsts(self):
        '''Test call to rebuild_restarts method with tracer restart files'''
        func.logtest('Assert call to rebuild_fileset from rebuild_restarts:')
        self.assertIn('_trc', self.nemo.rsttypes[2])
        with mock.patch('nemo.NemoPostProc.rebuild_fileset') as mock_fs:
            with mock.patch('nemo.NemoPostProc.rsttypes',
                            new_callable=mock.PropertyMock,
                            return_value=(self.nemo.rsttypes[2],)):
                self.nemo.rebuild_restarts()
            mock_fs.assert_called_with('ShareDir',
                                       r'RUNIDo__?\d{8}_restart_trc(\.nc)?')

    def test_call_rebuild_means(self):
        '''Test call to rebuild_means method'''
        func.logtest('Assert call to rebuild_fileset from rebuild_means:')
        pattern = r'[a-z]*_runido_10d_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}_' + \
            self.nemo.fields[-1]
        with mock.patch('nemo.NemoPostProc.rebuild_fileset') as mock_fs:
            self.nemo.rebuild_means()
            mock_fs.assert_called_with('ShareDir', pattern, rebuildall=True)

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

    @mock.patch('nemo.utils.get_subset')
    def test_rbld_restart_not_required(self, mock_subset):
        '''Test rebuild restarts function retaining all files'''
        func.logtest('Assert restart files fewer than buffer are retained:')
        mock_subset.return_value = ['file1']
        self.nemo.rebuild_fileset('ShareDir', 'restart')
        self.assertIn('{} retained'.format(self.buffer_rst), func.capture())

    @mock.patch('nemo.utils.get_subset')
    def test_rebuild_mean_not_required(self, mock_subset):
        '''Test rebuild means function retaining all files'''
        func.logtest('Assert means files fewer than buffer (1) are retained:')
        mock_subset.return_value = ['file1']
        self.nemo.rebuild_fileset('ShareDir', 'field')
        self.assertIn('{} retained'.format(self.buffer_mean), func.capture())

    @mock.patch('nemo.utils.remove_files')
    @mock.patch('nemo.utils.get_subset')
    def test_rebuild_periodic_only(self, mock_subset, mock_rm):
        '''Test rebuild function for periodic files not found'''
        func.logtest('Assert only periodic files are rebuilt:')
        mock_subset.return_value = ['file1_19990101_', 'file2_19990101_']
        self.nemo.rebuild_fileset('ShareDir', 'field')
        self.assertIn('only rebuilding periodic', func.capture().lower())
        self.assertIn('deleting component files', func.capture().lower())
        mock_rm.assert_called_once_with(['file1_19990101_', 'file2_19990101_'],
                                        path='ShareDir')

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.NemoPostProc.global_attr_to_zonal')
    def test_rebuild_all(self, mock_attr, mock_subset, mock_nl):
        '''Test rebuild all function'''
        func.logtest('Assert rebuild all function:')
        mock_subset.side_effect = [['file_19980530_yyyymmdd_0000.nc',
                                    'file_19980630_yyyymmdd_0000.nc',
                                    'file_19980730_yyyymmdd_0000.nc'],
                                   ['f1_component1', 'f1_component2'],
                                   ['f2_component1', 'f2_component2']]
        self.nemo.rebuild_fileset('SourceDir', 'field', rebuildall=True)
        mock_nl.assert_called_with('SourceDir', 'file_19980630_yyyymmdd',
                                   2, omp=1, msk=False)
        self.assertEqual(mock_attr.mock_calls, [])

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.NemoPostProc.global_attr_to_zonal')
    def test_rebuild_all_shortdate(self, mock_attr, mock_subset, mock_nl):
        '''Test rebuild all function - short date format'''
        func.logtest('Assert rebuild all function:')
        mock_subset.side_effect = [['file_199805_yyyymmdd_0000.nc',
                                    'file_199806_yyyymmdd_0000.nc',
                                    'file_199807_yyyymmdd_0000.nc'],
                                   ['f1_component1', 'f1_component2'],
                                   ['f2_component1', 'f2_component2']]
        self.nemo.rebuild_fileset('SourceDir', 'field', rebuildall=True)
        mock_nl.assert_called_with('SourceDir', 'file_199806_yyyymmdd',
                                   2, omp=1, msk=False)
        self.assertEqual(mock_attr.mock_calls, [])

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
        self.nemo.rebuild_fileset(os.getcwd(), 'field')
        mock_nl.assert_called_with(os.getcwd(),
                                   'RUNIDo_19980530_yyyymmdd_field',
                                   3, omp=1, msk=False)
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
        self.nemo.buffer_rebuild = mock.Mock()
        self.nemo.buffer_rebuild.return_value = 0
        for fname in myfiles:
            open(fname, 'w').close()

        self.nemo.rebuild_fileset(os.getcwd(),
                                  'RUNIDo_19980530_restart')
        mock_nl.assert_called_with(os.getcwd(),
                                   'RUNIDo_19980530_restart',
                                   3, omp=1, msk=False)
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
        self.nemo.buffer_rebuild = mock.Mock()
        self.nemo.buffer_rebuild.return_value = 0
        for fname in myfiles:
            open(fname, 'w').close()
        self.nemo.rebuild_fileset(os.getcwd(),
                                  'RUNIDo_icebergs_19980530_restart')
        mock_nl.assert_called_with(os.getcwd(),
                                   'RUNIDo_icebergs_19980530_restart',
                                   2, omp=1, msk=False)
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
        self.nemo.buffer_rebuild = mock.Mock()
        self.nemo.buffer_rebuild.return_value = 0
        for fname in myfiles:
            open(fname, 'w').close()
        self.nemo.rebuild_fileset(os.getcwd(),
                                  'RUNIDo_19980530_restart_trc')
        mock_nl.assert_called_with(os.getcwd(),
                                   'RUNIDo_19980530_restart_trc',
                                   2, omp=1, msk=False)
        for fname in myfiles:
            os.remove(fname)

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('nemo.utils.get_subset')
    def test_rebuild_rst_finalcycle(self, mock_subset, mock_nl):
        '''Test final cycle behaviour - deleting components of restarts'''
        func.logtest('Assert component files not deleted on final cycle:')
        mock_subset.side_effect = \
            [['file_11112233_restart_0000.nc'],
             ['file_restart_11112233_0000.nc', 'file_11112233_restart_0001.nc']]
        mock_nl.return_value = 0
        self.nemo.buffer_rebuild = mock.Mock()
        self.nemo.buffer_rebuild.return_value = 0
        self.nemo.suite.finalcycle = True
        self.nemo.rebuild_fileset('SourceDir', 'yyyymmdd_restart',
                                  rebuildall=True)
        mock_nl.assert_called_with('SourceDir', 'file_11112233_restart',
                                   2, omp=1, msk=False)
        self.assertNotIn('deleting component files', func.capture().lower())

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.remove_files')
    def test_rebuild_means_finalcycle(self, mock_rm, mock_subset, mock_nl):
        '''Test final cycle behaviour - deleting components of means'''
        func.logtest('Assert component files not deleted on final cycle:')
        mock_subset.side_effect = [['file_11112233_mean1_0000.nc',
                                    'file_11112233_mean2_0000.nc'],
                                   ['mean1_c1', 'mean1_c2'],
                                   ['mean2_c1', 'mean2_c2']]
        mock_nl.return_value = 0
        self.nemo.suite.finalcycle = True
        self.nemo.rebuild_fileset('SourceDir', 'mean', rebuildall=True)

        self.assertIn('deleting component files', func.capture().lower())
        nl_calls = [mock.call('SourceDir', 'file_11112233_mean1', 2,
                              omp=1, msk=False),
                    mock.call('SourceDir', 'file_11112233_mean2', 2,
                              omp=1, msk=False)]
        self.assertListEqual(mock_nl.mock_calls, nl_calls)
        rm_calls = [mock.call(['mean1_c1', 'mean1_c2'], path='SourceDir'),
                    mock.call(['mean2_c1', 'mean2_c2'], path='SourceDir')]
        self.assertListEqual(mock_rm.mock_calls, rm_calls)

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.NemoPostProc.global_attr_to_zonal')
    def test_rebuild_diaptr_means(self, mock_attr, mock_subset, mock_nl):
        '''Test rebuild all function - diaptr means'''
        func.logtest('Assert rebuild all function - diaptr means:')
        mock_subset.side_effect = [['file_19980530_yyyymmdd_diaptr_0000.nc',
                                    'file_19980630_yyyymmdd_diaptr_0000.nc'],
                                   ['component_file1', 'component_file2']]
        self.nemo.rebuild_fileset('SourceDir', 'f_diaptr', rebuildall=True)
        mock_nl.assert_called_once_with('SourceDir',
                                        'file_19980530_yyyymmdd_diaptr',
                                        2, omp=1, msk=False)
        mock_attr.assert_called_once_with(
            'SourceDir', ['component_file1', 'component_file2']
            )

    @mock.patch('nemo.utils.exec_subproc')
    @mock.patch('nemo.os.path.isfile')
    def test_rebuild_namelist(self, mock_isfile, mock_exec):
        '''Test rebuild namelist function'''
        func.logtest('Assert behaviour of rebuild_namelist function:')
        mock_exec.return_value = (0, '')
        mock_isfile.return_value = True
        with mock.patch('nemo.os.remove'):
            rtn = self.nemo.rebuild_namelist(os.getcwd(),
                                             'file_19980530_yyyymmdd',
                                             3)
        self.assertEqual(mock_exec.return_value[0], rtn)
        self.assertEqual(int(os.environ['OMP_NUM_THREADS']), 16)
        self.assertIn('successfully rebuilt', func.capture().lower())
        self.assertIn('file_19980530_yyyymmdd', func.capture().lower())
        mock_exec.assert_called_with(
            '{}'.format(os.path.join(os.getcwd(),
                                     self.defaults.exec_rebuild)),
            cwd=os.getcwd())
        self.assertTrue(os.path.exists('nam_rebuild'))
        txt = open('nam_rebuild', 'r').read()
        self.assertNotIn('dims=\'1\',\'2\'', txt)

    @mock.patch('nemo.utils.exec_subproc')
    @mock.patch('nemo.os.path.isfile')
    def test_rebuild_namelist_options(self, mock_isfile, mock_exec):
        '''Test rebuild namelist function with options'''
        func.logtest('Assert rebuild_namelist function with options:')
        mock_exec.return_value = (0, '')
        mock_isfile.return_value = True
        with mock.patch('nemo.os.remove'):
            rtn = self.nemo.rebuild_namelist(os.getcwd(),
                                             'file_19980530_yyyymmdd',
                                             3,
                                             omp=1, chunk='opt_chunk',
                                             dims=[1, 2],
                                             msk=True)
        self.assertEqual(int(os.environ['OMP_NUM_THREADS']), 1)
        self.assertEqual(rtn, 0)
        txt = open('nam_rebuild', 'r').read()
        self.assertIn('dims=\'1\',\'2\'', txt)
        self.assertIn('nchunksize=opt_chunk', txt)
        self.assertIn('l_maskout=.true.', txt)

    @mock.patch('nemo.NemoPostProc.rebuild_namelist')
    @mock.patch('nemo.utils.get_subset')
    def test_rebuild_mask(self, mock_subset, mock_nl):
        '''Test rebuild all function with mask option'''
        func.logtest('Assert rebuild all function with mask option:')
        # Buffer is 1 buy default - 1st subset side_effect must be list of 2.
        mock_subset.side_effect = [['file_19980530', 'file_19980630'],
                                   ['file_19980530_0000.nc',
                                    'file_19980530_0001.nc',
                                    'file_19980530_0002.nc']]
        self.nemo.naml.msk_rebuild = True
        self.nemo.rebuild_fileset(os.getcwd(), 'field', rebuildall=True)
        mock_nl.assert_called_with(os.getcwd(), 'file_19980530',
                                   3, omp=1, msk=True)

    @mock.patch('nemo.utils.exec_subproc')
    @mock.patch('nemo.os.path.isfile')
    def test_rbld_namelist_no_namelist(self, mock_isfile, mock_exec):
        '''Test failure to create namelist file'''
        func.logtest('Assert failure to create namelist file:')
        mock_exec.return_value = (0, '')
        mock_isfile.return_value = False
        rtn = self.nemo.rebuild_namelist(os.getcwd(),
                                         'file_19980530_yyyymmdd',
                                         3)
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
                                               'file_19980530_yyyymmdd', 3)
        self.assertIn('failed to rebuild file', func.capture('err').lower())
        self.assertIn('file_19980530_yyyymmdd', func.capture('err').lower())

    @mock.patch('nemo.utils.exec_subproc')
    def test_rebuild_nlist_fail_debug(self, mock_exec):
        '''Test failure mode of rebuild namelist function - debug_mode'''
        func.logtest('Assert debug behaviour of rebuild_namelist function:')
        mock_exec.return_value = (1, '')
        with mock.patch('nemo.utils.get_debugmode', return_value=True):
            with mock.patch('nemo.os.path.isfile', return_value=True):
                _ = self.nemo.rebuild_namelist(os.getcwd(),
                                               'file_19980530_yyyymmdd', 3)
        self.assertIn('failed to rebuild file', func.capture('err').lower())
        self.assertIn('file_19980530_yyyymmdd', func.capture('err').lower())

    def test_rebuild_icebergs_call(self):
        '''Test call to external iceberg rebuilding routine: icb_combrest'''
        func.logtest('Assert call to external iceberg rebuilding routine:')
        with mock.patch('nemo.utils.exec_subproc', return_value=(0, '')):
            with mock.patch('nemo.NemoPostProc.rebuild_icebergs') as mock_rbld:
                with mock.patch('nemo.os.path.isfile', return_value=True):
                    mock_rbld.return_value = 0
                    self.nemo.rebuild_namelist(os.getcwd(),
                                               'file_icebergs_yyyymmdd', 2)
        mock_rbld.assert_called_with(os.getcwd(),
                                     'file_icebergs_yyyymmdd', 2)
        self.assertIn('Successfully rebuilt', func.capture())

    def test_rebuild_icebergs_cmd(self):
        '''Test call to external iceberg rebuilding routine: icb_combrest'''
        func.logtest('Assert call to external iceberg rebuilding routine:')
        with mock.patch('nemo.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            self.nemo.rebuild_icebergs('TestDir', 'filebase', '1')
        cmd = 'python2.7 {} -f TestDir/filebase_ -n 1 -o TestDir/filebase.nc'.\
            format(self.defaults.exec_rebuild_icebergs)
        mock_exec.assert_called_with(cmd, cwd='TestDir')
        self.assertIn('Successfully rebuilt', func.capture())

    def test_rebuild_icebergs_fail(self):
        '''Test call to external iceberg rebuilding routine: icb_combrest'''
        func.logtest('Assert call to external iceberg rebuilding routine:')
        with mock.patch('nemo.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, 'err output')
            with self.assertRaises(SystemExit):
                self.nemo.rebuild_icebergs('TestDir', 'filebase', '1')
        self.assertIn('Failed to rebuild file', func.capture('err'))
        self.assertIn('err output', func.capture('err'))


class MeansProcessingTests(unittest.TestCase):
    '''Unit tests relating to the processing of means files'''
    def setUp(self):
        self.nemo = nemo.NemoPostProc()
        self.nemo.suite = mock.Mock()
        self.defaults = nemoNamelist.NemoNamelist()
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
        self.nemo.naml.exec_rebuild_iceberg_trajectory = 'ICB_PP'
        self.nemo.share = 'HERE'
        self.nemo.work = 'HERE'

    def tearDown(self):
        for fname in ['nam_rebuild'] + runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.exec_subproc', return_value=(0, ''))
    @mock.patch('nemo.utils.remove_files')
    def test_arch_iberg_trajectory(self, mock_rm, mock_exec, mock_set):
        '''Test call to iceberg_trajectory archive method'''
        func.logtest('Assert call to iceberg_trajectory archive method:')
        # Mock results for 3 calls to utils.get_subset
        mock_set.side_effect = [['file1_0000.nc'],
                                ['file1_0000.nc', 'file1_0001.nc'],
                                ['arch1.nc']]
        self.nemo.archive_files.return_value = {'arch1.nc': 'FAILED',
                                                'arch2.nc': 'SUCCEEDED'}

        self.nemo.naml.archive_iceberg_trajectory = True
        self.nemo.archive_general()

        cmd = 'python2.7 ICB_PP -t HERE/file1_ -n 2 -o HERE/RUNIDo_file1.nc'
        mock_exec.assert_called_once_with(cmd)
        removed = mock_rm.mock_calls
        self.assertEqual(len(removed), 2)
        self.assertEqual(mock.call(['file1_0000.nc', 'file1_0001.nc'],
                                   path='HERE'), removed[0])
        self.assertEqual(mock.call(['arch2.nc'], path='HERE'), removed[1])
        self.nemo.archive_files.assert_called_once_with(['arch1.nc'])
        self.assertIn('Successfully rebuilt iceberg trajectory',
                      func.capture())

    @mock.patch('nemo.utils.get_subset')
    @mock.patch('nemo.utils.exec_subproc', return_value=(0, ''))
    @mock.patch('nemo.utils.remove_files')
    @mock.patch('nemo.os.rename')
    def test_arch_iberg_traj_debug(self, mock_name, mock_rm,
                                   mock_exec, mock_set):
        '''Test call to iceberg_trajectory archive method - debug mode'''
        func.logtest('Assert call to iceberg_traj archive method - debug:')
        # Mock results for 3 calls to utils.get_subset
        mock_set.side_effect = [['file1_0000.nc'],
                                ['file1_0000.nc', 'file1_0001.nc'],
                                ['arch1.nc']]
        self.nemo.archive_files.return_value = {'arch1.nc': 'FAILED',
                                                'arch2.nc': 'SUCCEEDED',
                                                'arch3.nc': 'SUCCEEDED'}

        self.nemo.naml.archive_iceberg_trajectory = True
        with mock.patch('nemo.utils.get_debugmode', return_value=True):
            self.nemo.archive_general()

        cmd = 'python2.7 ICB_PP -t HERE/file1_ -n 2 -o HERE/RUNIDo_file1.nc'
        mock_exec.assert_called_once_with(cmd)
        mock_rm.assert_called_once_with(['file1_0000.nc', 'file1_0001.nc'],
                                        path='HERE')
        self.nemo.archive_files.assert_called_once_with(['arch1.nc'])
        self.assertIn('Successfully rebuilt iceberg trajectory',
                      func.capture())
        self.assertEqual(len(mock_name.mock_calls), 2)
        self.assertIn(mock.call('HERE/arch2.nc', 'HERE/arch2.nc_ARCHIVED'),
                      mock_name.mock_calls)
        self.assertIn(mock.call('HERE/arch3.nc', 'HERE/arch3.nc_ARCHIVED'),
                      mock_name.mock_calls)

    @mock.patch('nemo.utils.exec_subproc')
    @mock.patch('nemo.utils.get_subset')
    def test_arch_iberg_trajectory_fail(self, mock_set, mock_exec):
        '''Test call to iceberg_trajectory archive method - fail'''
        func.logtest('Assert failed call to iceberg_trajectory method:')
        # Mock results for 3 calls to utils.get_subset
        mock_set.side_effect = [['file1_0000.nc'],
                                ['file1_0000.nc', 'file1_0001.nc'],
                                ['arch1.nc']]
        mock_exec.return_value = (1, 'ICB_PP failed')
        self.nemo.naml.archive_iceberg_trajectory = True
        with self.assertRaises(SystemExit):
            self.nemo.archive_general()
        with self.assertRaises(AssertionError):
            self.nemo.archive_files.assert_called_with(mock.ANY)
        self.assertIn('Error=1\n\tICB_PP failed', func.capture('err'))

    @mock.patch('nemo.utils.exec_subproc')
    @mock.patch('nemo.utils.get_subset')
    def test_create_iberg_traj_debug(self, mock_set, mock_exec):
        '''Test call to iceberg_trajectory creation method - debug'''
        func.logtest('Assert debug build call to iceberg_trajectory method:')
        # Mock results for 3 calls to utils.get_subset
        mock_set.side_effect = [['file1_0000.nc'],
                                ['file1_0000.nc', 'file1_0001.nc'],
                                ['arch1.nc']]
        mock_exec.return_value = (1, 'ICB_PP failed')
        self.nemo.naml.archive_iceberg_trajectory = True
        with mock.patch('nemo.utils.get_debugmode', return_value=True):
            self.nemo.archive_general()
        self.assertIn('Error=1\n\tICB_PP failed', func.capture('err'))
        self.nemo.archive_files.assert_called_once_with(['arch1.nc'])

    @mock.patch('nemo.mt.ModelTemplate.move_to_share')
    def test_arch_iberg_trajectory_move(self, mock_mv):
        '''Test call to iceberg_trajectory archive method - move files'''
        func.logtest('Assert call to archive_iceberg_trajectory with move:')
        self.nemo.naml.archive_iceberg_trajectory = True
        self.nemo.share = 'THERE'
        with mock.patch('nemo.utils.get_subset'):
            self.nemo.archive_general()
        mock_mv.assert_called_once_with(
            pattern=r'trajectory_icebergs_\d{6}_\d{4}\.nc'
            )

    @mock.patch('nemo.utils.remove_files')
    def test_arch_iberg_traj_archpass(self, mock_rm):
        '''Test call to iceberg_trajectory archive method - arch pass'''
        func.logtest('Assert call to archive_iceberg_trajectory - arch pass:')
        self.nemo.naml.archive_iceberg_trajectory = True
        self.nemo.archive_files.return_value = {'arch1': 'SUCCESS'}
        with mock.patch('nemo.utils.get_subset'):
            self.nemo.archive_general()
        self.nemo.archive_files.assert_called_once_with(mock.ANY)
        mock_rm.assert_called_with(['arch1'], path='HERE')

    @mock.patch('nemo.utils.remove_files')
    def test_arch_iberg_traj_archfail(self, mock_rm):
        '''Test call to iceberg_trajectory archive method - arch fail'''
        func.logtest('Assert call to archive_iceberg_trajectory - arch fail:')
        self.nemo.naml.archive_iceberg_trajectory = True
        self.nemo.archive_files.return_value = {'arch1': 'FAILED'}
        with mock.patch('nemo.utils.get_subset'):
            self.nemo.archive_general()
        self.nemo.archive_files.assert_called_once_with(mock.ANY)
        with self.assertRaises(AssertionError):
            mock_rm.assert_called_with(mock.ANY)


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

    @mock.patch('nemo.NemoPostProc.rebuild_means')
    @mock.patch('nemo.mt.ModelTemplate.move_to_share')
    def test_move_to_share(self, mock_mt, mock_rbld):
        '''Test NEMO Specific move_to_share functionality'''
        func.logtest('Assert additional move_to_share processing in NEMO:')
        self.nemo.move_to_share()
        mock_mt.assert_called_once_with(pattern=None)
        mock_rbld.assert_called_once_with()

    @mock.patch('nemo.NemoPostProc.rebuild_means')
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
