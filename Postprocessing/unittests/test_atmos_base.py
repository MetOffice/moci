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

# Import of atmos requires RUNID from runtime_environment
runtime_environment.setup_env()
import atmos


class ArchiveDeleteTests(unittest.TestCase):
    '''Unit tests relating to the atmosphere archive and delete methods'''
    def setUp(self):
        self.atmos = atmos.AtmosPostProc()
        self.atmos.share = os.getcwd()
        self.atmos.work = 'WorkDir'
        self.atmos.ff_pattern = r'(RUNID)?a\.[pm][{}]\d{{4}}.*$'
        self.atmos.suite = mock.Mock()
        self.atmos.suite.logfile = 'logfile'
        self.atmos.suite.prefix = 'RUNID'
        self.dfiles = ['RUNIDa.YYYYMMDD_00']
        self.ffiles = ['RUNIDa.paYYYYjan', 'RUNIDa.pb1111jan',
                       'RUNIDa.pc1111jan', 'RUNIDa.pd1111jan']
        self.ppfiles = [f + '.pp' for f in self.ffiles[1:]]
        self.ncfiles = ['atmos_RUNIDa_1x_YYYYMMDD-YYYYMMDD_XXXX.nc']

    def tearDown(self):
        files = ['logfile', self.dfiles[0], self.ffiles[0],
                 self.ffiles[0] + '.pp']
        for fname in runtime_environment.RUNTIME_FILES + files:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_do_archive(self):
        '''Test do_archive functionality'''
        func.logtest('Assert call to archive_file')
        self.atmos.naml.archiving.archive_pp = True
        with mock.patch('atmos.AtmosPostProc.diags_to_process',
                        return_value=['path/a.pa2000', 'path/a.pb2000.pp',
                                      'path/FF_noconv']) as mock_pp:
            with mock.patch('atmos.AtmosPostProc.dumps_to_archive',
                            return_value=['DumpFile']) as mock_dump:
                self.atmos.do_archive()
        self.assertListEqual(
            sorted(self.atmos.suite.archive_file.mock_calls),
            sorted([mock.call('path/a.pa2000', preproc=True),
                    mock.call('path/a.pb2000.pp', preproc=True),
                    mock.call('path/FF_noconv', preproc=False),
                    mock.call('DumpFile', preproc=False)])
            )
        mock_dump.assert_called_once_with(mock.ANY)
        mock_pp.assert_called_once_with(False, log_file=mock.ANY)

    @mock.patch('atmos.AtmosPostProc.diags_to_process',
                return_value=['path/a.pa2000', 'path/a.pb2000.pp',
                              'path/FF_noconv'])
    @mock.patch('atmos.AtmosPostProc.dumps_to_archive', return_value=[])
    def test_do_archive_convpp_off(self, mock_dump, mock_pp):
        '''Test do_archive - archiving system to convert all ff to pp'''
        func.logtest('Assert call to archive_file, arch.sys. to convert to pp')
        self.atmos.naml.archiving.archive_pp = True
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.do_archive()
        self.assertListEqual(
            sorted(self.atmos.suite.archive_file.mock_calls),
            sorted([mock.call('path/a.pa2000', preproc=True),
                    mock.call('path/a.pb2000.pp', preproc=True),
                    mock.call('path/FF_noconv', preproc=True)])
            )
        mock_dump.assert_called_once_with(mock.ANY)
        mock_pp.assert_called_once_with(False, log_file=mock.ANY)

    @mock.patch('atmos.AtmosPostProc.diags_to_process',
                return_value=['path/a.pa2000', 'path/a.pb2000.pp'])
    @mock.patch('atmos.AtmosPostProc.dumps_to_archive',
                return_value=['DumpFile'])
    @mock.patch('atmos.utils.remove_files')
    def test_do_archive_finalcycle(self, mock_rm, mock_dump, mock_pp):
        '''Test do_archive functionality - final cycle'''
        func.logtest('Assert call to archive_file - final cycle')
        self.atmos.naml.archiving.archive_pp = True
        self.atmos.suite.archive_file.return_value = 0
        self.atmos.do_archive(finalcycle=True)
        arch_calls = [mock.call('path/a.pa2000', preproc=True),
                      mock.call('path/a.pb2000.pp', preproc=True)]
        self.assertListEqual(sorted(self.atmos.suite.archive_file.mock_calls),
                             sorted(arch_calls))
        self.assertListEqual(mock_dump.mock_calls, [])
        mock_rm.assert_called_once_with('path/a.pb2000.pp')
        self.assertListEqual(
            sorted(self.atmos.suite.archive_file.mock_calls),
            sorted([mock.call('path/a.pa2000', preproc=True),
                    mock.call('path/a.pb2000.pp', preproc=True)])
            )
        self.assertListEqual(mock_dump.mock_calls, [])
        mock_pp.assert_called_once_with(True, log_file=mock.ANY)

    @mock.patch('atmos.AtmosPostProc.diags_to_process',
                return_value=['path/a.pa2000', 'path/a.pb2000.pp'])
    @mock.patch('atmos.AtmosPostProc.dumps_to_archive',
                return_value=['DumpFile'])
    @mock.patch('atmos.os.rename')
    def test_do_archive_final_debug(self, mock_mv, mock_dump, mock_pp):
        '''Test do_archive functionality - final cycle, debug'''
        func.logtest('Assert call to archive_file - final cycle debug')
        self.atmos.naml.archiving.archive_pp = True
        self.atmos.suite.archive_file.return_value = 0
        with mock.patch('atmos.utils.get_debugmode', return_value=True):
            self.atmos.do_archive(finalcycle=True)
        arch_calls = [mock.call('path/a.pa2000', preproc=True),
                      mock.call('path/a.pb2000.pp', preproc=True)]
        self.assertListEqual(sorted(self.atmos.suite.archive_file.mock_calls),
                             sorted(arch_calls))
        self.assertListEqual(mock_dump.mock_calls, [])
        mock_pp.assert_called_once_with(True, log_file=mock.ANY)
        mock_mv.assert_called_once_with('path/a.pb2000.pp',
                                        'path/a.pb2000.pp_ARCHIVED')
    def test_do_archive_pp_off(self):
        '''Test nothing to archive (pp archive off and finalcycle)'''
        func.logtest('Assert no archive necessary with pp archive off:')
        self.atmos.naml.archiving.archive_pp = False
        self.atmos.do_archive(finalcycle=True)
        self.assertListEqual(self.atmos.suite.archive_file.mock_calls, [])
        self.assertIn('Nothing to archive', func.capture())

    def test_do_archive_fail_logfile(self):
        '''Test failure mode when creating log file'''
        func.logtest('Assert system exit with failure to create log:')
        self.atmos.suite.logfile = '/MyLog'
        with self.assertRaises(SystemExit):
            self.atmos.do_archive()
        self.assertIn('Failed to open archive log', func.capture('err'))

    def test_archive_dump(self):
        '''Test do_archive - dump files list'''
        func.logtest('Assert dump files list created for do_archive:')
        self.atmos.naml.archiving.archive_dumps = True
        open(self.dfiles[0], 'w').close()
        with mock.patch('atmos.validation.make_dump_name',
                        return_value=self.dfiles) as mock_name:
            with mock.patch('atmos.validation.verify_header',
                            return_value=True) as mock_hdr:
                with open(self.atmos.suite.logfile, 'w') as log:
                    dumps = self.atmos.dumps_to_archive(log)
                mock_hdr.assert_called_once_with(
                    mock.ANY, os.path.join(os.getcwd(), self.dfiles[0]),
                    mock.ANY, logfile=mock.ANY
                    )
            mock_name.assert_called_once_with(self.atmos)
        self.assertListEqual(dumps, [self.dfiles[0]])

    def test_archive_dump_non_existent(self):
        '''Test do_archive - dump files list - file non-existent'''
        func.logtest('Assert dumpfiles for do_archive - file non existent:')
        self.atmos.naml.archiving.archive_dumps = True
        with mock.patch('atmos.validation.make_dump_name',
                        return_value=self.dfiles) as mock_name:
            with open(self.atmos.suite.logfile, 'w') as log:
                dumps = self.atmos.dumps_to_archive(log)
            mock_name.assert_called_once_with(self.atmos)
        self.assertListEqual(dumps, [])

    @mock.patch('atmos.housekeeping.get_marked_files')
    def test_select_ff_diags(self, mock_getfiles):
        '''Test select fieldsfile diagnostic list for processing'''
        func.logtest('Assert fieldsfile diagnostics list created:')
        mock_getfiles.return_value = self.ffiles[1:]

        with mock.patch('atmos.os.path.exists', return_value=True):
            with mock.patch('atmos.validation.verify_header',
                            return_value=True):
                with open(self.atmos.suite.logfile, 'w') as log:
                    ppfiles = self.atmos.diags_to_process(False, log_file=log)

        self.assertListEqual(ppfiles, [os.path.join(os.getcwd(), fn) for
                                       fn in self.ffiles[1:]])
        mock_getfiles.assert_called_once_with('WorkDir', mock.ANY, '.arch')


    @mock.patch('atmos.housekeeping.get_marked_files')
    def test_select_diags_tidy_pp(self, mock_getfiles):
        '''Test do_archive functionality - tidy up ppfiles left on disk'''
        func.logtest('Assert do_archive method - tidy left over ppfile:')
        self.atmos.naml.archiving.archive_pp = True
        fnfull = os.path.join(os.getcwd(), self.ffiles[0])
        open(self.ffiles[0] + '.pp', 'w').close()
        mock_getfiles.return_value = [self.ffiles[0]]

        with open(self.atmos.suite.logfile, 'w') as log:
            ppfiles = self.atmos.diags_to_process(False, log_file=log)
        mock_getfiles.assert_called_once_with('WorkDir', mock.ANY, '.arch')
        self.assertListEqual(ppfiles, [fnfull + '.pp'])

    @mock.patch('atmos.housekeeping.get_marked_files')
    @mock.patch('atmos.housekeeping.utils.get_subset')
    def test_select_netcdf_diags(self, mock_set, mock_getfiles):
        '''Test select netCDF diagnostic file list for processing'''
        func.logtest('Assert netCDF diagnostics files list created:')
        mock_getfiles.return_value = []
        mock_set.return_value = self.ncfiles

        ncfiles = self.atmos.diags_to_process(False)
        self.assertListEqual(ncfiles,
                             [os.path.join(os.getcwd(), self.ncfiles[0])])
        mock_getfiles.assert_called_once_with('WorkDir', mock.ANY, '.arch')
        mock_set.assert_called_once_with(
            os.getcwd(),
            r'atmos_RUNIDa_\d+[hdmsyx]_\d{8}-\d{8}.*.nc$'
            )

    @mock.patch('atmos.housekeeping.get_marked_files')
    def test_select_diags_non_existent(self, mock_getfiles):
        '''Test select diags files list - file non-existent'''
        func.logtest('Assert pp files list - file non existent:')
        mock_getfiles.return_value = ['FileNotHere']

        ppfiles = self.atmos.diags_to_process(False)
        self.assertListEqual(ppfiles, [])
        self.assertIn('{}/FileNotHere does not exist'.format(os.getcwd()),
                      func.capture('err'))

    @mock.patch('atmos.housekeeping.get_marked_files')
    @mock.patch('atmos.validation.verify_header', return_value=True)
    def test_select_diags_finalcycle(self, mock_verify, mock_getfiles):
        '''Test select diags file list on final cycle, pre-conversion ON'''
        func.logtest('Assert final cycle pp files list created:')

        mock_getfiles.return_value = self.ffiles[1:] + self.ppfiles

        with mock.patch('atmos.os.path.exists', return_value=True):
            with open(self.atmos.suite.logfile, 'w') as log:
                ppfiles = self.atmos.diags_to_process(True, log_file=log)

        self.assertListEqual(ppfiles, [os.path.join(os.getcwd(), fn) for
                                       fn in self.ffiles[1:] + self.ppfiles])
        mock_getfiles.assert_called_once_with(os.getcwd(), mock.ANY, '')
        verify_calls = [mock.call(mock.ANY, os.path.join(os.getcwd(), f),
                                  mock.ANY, logfile=mock.ANY)
                        for f in self.ffiles[1:]]
        self.assertListEqual(mock_verify.mock_calls, verify_calls)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.housekeeping.convert_to_pp')
    def test_transform_convpp_sel(self, mock_convpp, mock_getfiles):
        '''Test do_transform - pp files list - selected pre-conversion to pp'''
        func.logtest('Assert pp files list for do_transform - some convpp:')

        self.atmos.convpp_streams = '^d-f^1'
        mock_getfiles.return_value = self.ffiles[1:]
        mock_convpp.side_effect = [fn + '.pp' for fn in self.ffiles[1:]]

        self.atmos.do_transform()

        mock_getfiles.assert_called_once_with(False)
        for fname in self.ffiles[1:]:
            func.logtest('Testing filename: ' + fname)
            if fname == self.ffiles[-1]:
                self.assertNotIn(mock.call(fname, mock.ANY, False),
                                 mock_convpp.mock_calls)
            else:
                self.assertIn(mock.call(fname, mock.ANY, False),
                              mock_convpp.mock_calls)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.housekeeping.convert_to_pp')
    def test_transform_pp_convert_none(self, mock_convpp, mock_getfiles):
        '''Test do_transform - pp files list - no conversion to pp'''
        func.logtest('Assert pp files list for do_transform - ppconvert:')
        self.atmos.convpp_streams = '^a-z'
        mock_getfiles.return_value = self.ffiles[1:]

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        self.assertListEqual(mock_convpp.mock_calls, [])

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.housekeeping.convert_to_pp')
    def test_transform_pp_convert_off(self, mock_convpp, mock_getfiles):
        '''Test do_transform - pp files list - convpp OFF'''
        func.logtest('Assert pp files list for do_transform - convpp OFF:')
        self.atmos.convpp_streams = '^a'
        self.atmos.naml.atmospp.convert_pp = False
        mock_getfiles.return_value = self.ffiles[1:]

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        self.assertListEqual(mock_convpp.mock_calls, [])

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.housekeeping.extract_to_netcdf', return_value=0)
    def test_transform_netcdf(self, mock_ncf, mock_getfiles):
        '''Test do_transform - collect netCDF files'''
        func.logtest('Assert netCDF files list for do_tranform:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.netcdf_streams = 'b'
        self.atmos.naml.atmospp.fields_to_netcdf = ['field1', 'F1']
        mock_getfiles.return_value = self.ffiles

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        mock_ncf.assert_called_once_with(self.ffiles[1], {'field1': 'F1'},
                                         'NETCDF4', None)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.housekeeping.extract_to_netcdf', return_value=0)
    def test_transform_netcdf_options(self, mock_ncf, mock_getfiles):
        '''Test do_transform - collect netCDF files'''
        func.logtest('Assert netCDF files list for do_tranform:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.netcdf_streams = 'b'
        self.atmos.naml.atmospp.fields_to_netcdf = ['fieldA', 'FA']
        self.atmos.naml.atmospp.netcdf_compression = 5
        self.atmos.naml.atmospp.netcdf_filetype = 'MY_NCF'
        mock_getfiles.return_value = self.ffiles

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        mock_ncf.assert_called_once_with(self.ffiles[1], {'fieldA': 'FA'},
                                         'MY_NCF', 5)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.housekeeping.extract_to_netcdf', return_value=0)
    def test_transform_netcdf_nostreams(self, mock_ncf, mock_getfiles):
        '''Test do_transform - collect netCDF files - no streams'''
        func.logtest('Assert netCDF files list for do_tranform - no streams:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.netcdf_streams = None
        mock_getfiles.return_value = self.ffiles

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)

        self.atmos.netcdf_streams = ''
        self.atmos.do_transform()
        self.assertEqual(mock_ncf.call_count, 0)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.housekeeping.extract_to_netcdf', return_value=0)
    def test_transform_netcdf_nofields(self, mock_ncf, mock_getfiles):
        '''Test do_transform - collect netCDF files - no streams'''
        func.logtest('Assert netCDF files list for do_tranform - no streams:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.netcdf_streams = 'b'
        self.atmos.naml.atmospp.fields_to_netcdf = None
        mock_getfiles.return_value = self.ffiles

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        mock_ncf.assert_called_once_with(self.ffiles[1], {}, 'NETCDF4', None)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.housekeeping.extract_to_netcdf', return_value=1)
    def test_transform_netcdf_fail(self, mock_ncf, mock_getfiles):
        '''Test do_transform - collect netCDF files'''
        func.logtest('Assert netCDF files list for do_tranform:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.netcdf_streams = 'b'
        self.atmos.naml.atmospp.fields_to_netcdf = ['field1', 'F1']
        mock_getfiles.return_value = self.ffiles

        with self.assertRaises(SystemExit):
            self.atmos.do_transform()
        self.assertIn('Field extraction to netCDF failed',
                      func.capture('err'))
        mock_ncf.assert_called_once_with(self.ffiles[1], {'field1': 'F1'},
                                         'NETCDF4', None)


class PropertyTests(unittest.TestCase):
    '''Unit tests relating to the atmosphere property methods'''
    def setUp(self):
        self.atmos = atmos.AtmosPostProc()
        self.atmos.suite = mock.Mock()

    def tearDown(self):
        for fname in ['atmospp.nl']:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_convpp_single(self):
        '''Test _convpp_streams calculation of regular expression - single'''
        func.logtest('Assert _convpp_streams calculation of regex - single:')
        self.atmos.naml.atmospp.archive_as_fieldsfiles = 'a'
        self.assertEqual(self.atmos._convpp_streams, '^a')

    def test_convpp_list(self):
        '''Test _convpp_streams calculation of regular expression - single'''
        func.logtest('Assert _convpp_streams calculation of regex - single:')
        self.atmos.naml.atmospp.archive_as_fieldsfiles = ['a', '1-2', 4]
        self.assertEqual(self.atmos._convpp_streams, '^a^1-2^4')

    def test_convpp_all(self):
        '''Test convpp_streams calculation of regular expression - single'''
        func.logtest('Assert convpp_streams calculation of regex - single:')
        for value in [None, '']:
            self.atmos.naml.atmospp.archive_as_fieldsfiles = value
            self.assertEqual(self.atmos.convpp_streams, 'a-z1-9')

    def test_convpp_none(self):
        '''Test convpp_streams calculation of regular expression - none'''
        func.logtest('Assert convpp_streams calculation of regex - none:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.naml.atmospp.archive_as_fieldsfiles = 'a'
        self.assertEqual(self.atmos.convpp_streams, 'a-z1-9')

    def test_streams_property(self):
        '''Test the return value of the streams property'''
        func.logtest('Assert return value of the streams property:')
        self.assertEqual(self.atmos.naml.atmospp.process_streams, None)
        self.assertEqual(self.atmos.streams, '1-9a-ln-rt-xz')
        self.atmos.naml.atmospp.process_streams = 'at-z'
        self.assertEqual(self.atmos.streams, 'at-z')
        self.atmos.naml.atmospp.process_streams = ''
        self.assertEqual(self.atmos.streams, '')

    def test_means_property(self):
        '''Test the return value of the means property'''
        func.logtest('Assert return value of the means property:')
        self.assertEqual(self.atmos.naml.atmospp.process_means, None)
        self.assertEqual(self.atmos.means, 'msy')
        self.atmos.naml.atmospp.process_means = 'at-z'
        self.assertEqual(self.atmos.means, 'at-z')

    @mock.patch('atmos.suite.SuiteEnvironment')
    def test_ff_pattern(self, mock_suite):
        '''Test the fieldsfile regular expression'''
        func.logtest('Assert correct return of fields file regex:')

        mock_suite().finalcycle = False
        mock_suite().prefix = 'RUNID'

        with mock.patch('atmos.AtmosPostProc.runpp',
                        new_callable=mock.PropertyMock,
                        return_value=True):
            with mock.patch('atmos.AtmosPostProc._directory',
                            return_value='ModelDir'):
                with mock.patch('atmos.utils.loadEnv'):
                    with mock.patch('atmos.utils.set_debugmode'):
                        myatmos = atmos.AtmosPostProc()

        ff_pattern = r'^RUNIDa\.[pm][{}]\d{{4}}(\d{{4}}|\w{{3}})' \
            r'(_\d{{2}})?(\.pp)?(\.arch)?$'

        self.assertEqual(myatmos.ff_pattern, ff_pattern)
        ppfiles = ['RUNIDa.pa11112233.pp', 'RUNIDa.pb11112233_44.arch',
                   'RUNIDa.pc1111mmm', 'RUNIDa.pd12345678.pp.arch']
        for fname in ppfiles:
            self.assertIsNotNone(re.match(ff_pattern.format('a-e'), fname))
        badfiles = ['RUNIDa.pz11112233.pp', 'GARBAGE']
        for fname in badfiles:
            self.assertIsNone(re.match(ff_pattern.format('a-e'), fname))

    def test_netcdf_streams_single(self):
        '''Test netcdf_streams calculation of regular expression - single'''
        func.logtest('Assert netcdf_streams calculation of regex - single:')
        self.atmos.naml.atmospp.streams_to_netcdf = 'a'
        self.assertEqual(self.atmos._netcdf_streams, 'a')

    def test_netcdf_streams_list(self):
        '''Test netcdf_streams calculation of regular expression - single'''
        func.logtest('Assert netcdf_streams calculation of regex - single:')
        self.atmos.naml.atmospp.streams_to_netcdf = ['a', 'b', 3]
        self.assertEqual(self.atmos._netcdf_streams, 'ab3')

    def test_netcdf_streams_none(self):
        '''Test netcdf_streams calculation of regular expression - single'''
        func.logtest('Assert netcdf_streams calculation of regex - single:')
        self.atmos.naml.atmospp.streams_to_netcdf = ''
        self.assertEqual(self.atmos._netcdf_streams, '')

        self.atmos.naml.atmospp.streams_to_netcdf = None
        self.assertEqual(self.atmos._netcdf_streams, None)

    def test_netcdf_fields_single(self):
        '''Test netcdf_fields dctionary construction - single field'''
        func.logtest('Assert netcdf_fields dictionary construction - single:')
        self.atmos.netcdf_streams = 'a'
        self.atmos.naml.atmospp.fields_to_netcdf = ['field1', 'F1']
        self.assertEqual(self.atmos.netcdf_fields, {'field1': 'F1'})

    def test_ncffields_multi(self):
        '''Test netcdf_fields dctionary construction - multi fields'''
        func.logtest('Assert netcdf_fields dictionary construction - multi:')
        self.atmos.netcdf_streams = 'a'
        self.atmos.naml.atmospp.fields_to_netcdf = ['field1', 'F1',
                                                    'field2', 'F2']
        self.assertEqual(self.atmos.netcdf_fields, {'field1': 'F1',
                                                    'field2': 'F2'})

    def test_netcdf_fields_none(self):
        '''Test netcdf_fields dctionary construction - multi fields'''
        func.logtest('Assert netcdf_fields dictionary construction - multi:')
        self.atmos.netcdf_streams = 'a'
        self.atmos.naml.atmospp.fields_to_netcdf = None
        self.assertEqual(self.atmos.netcdf_fields, {})

    def test_netcdf_fields_badlist(self):
        '''Test netcdf_fields dctionary construction - badly constructed list'''
        func.logtest('Assert netcdf_fields dictionary construction - bad list:')
        self.atmos.netcdf_streams = 'a'
        self.atmos.naml.atmospp.fields_to_netcdf = ['field1']
        self.assertEqual(self.atmos.netcdf_fields, {})
        self.assertIn('Incorrect format of &atmospp/fields_to_netcdf',
                      func.capture('err'))
