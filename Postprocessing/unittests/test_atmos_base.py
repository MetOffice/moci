#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2025 Met Office. All rights reserved.

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
import shutil
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
    OPEN_FUNC = 'builtins.open'
except ImportError:
    # mock is a standalone package (back-ported)
    import mock
    OPEN_FUNC = '__builtin__.open'

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
        self.atmos.suite = mock.Mock()
        self.atmos.suite.logfile = 'logfile'
        self.atmos.suite.prefix = 'R'
        self.atmos.suite.envars = {
            'CYLC_TASK_LOG_ROOT': os.environ['CYLC_TASK_LOG_ROOT']
            }
        self.dfiles = ['Ra.YYYYMMDD_00']
        self.ffiles = ['Ra.paYYYYjan', 'Ra.pb1111jan',
                       'Ra.pc1111jan', 'Ra.pd1111jan']
        self.ppfiles = [f + '.pp' for f in self.ffiles[1:]]
        self.ncfiles = ['atmos_Ra_1x_YYYYMMDD-YYYYMMDD_XXXX.nc']

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
                        return_value=['path/Ra.pa20000101',
                                      'path/Ra.pb20000101.pp',
                                      'path/FF_noconv']) as mock_pp:
            with mock.patch('atmos.AtmosPostProc.dumps_to_archive',
                            return_value=['DumpFile']) as mock_dump:
                self.atmos.do_archive()
        self.assertListEqual(
            sorted(self.atmos.suite.archive_file.mock_calls),
            sorted([mock.call('path/Ra.pa20000101', preproc=True),
                    mock.call('path/Ra.pb20000101.pp', preproc=True),
                    mock.call('path/FF_noconv', preproc=False),
                    mock.call('DumpFile', preproc=False)])
            )
        mock_dump.assert_called_once_with(mock.ANY)
        mock_pp.assert_called_once_with(False, log_file=mock.ANY)

    def test_do_archive_convpp_sel(self):
        '''Test do_archive functionality - convert selected to pp'''
        func.logtest('Assert call to archive_file - selected convpp')
        self.atmos.naml.archiving.archive_pp = True
        self.atmos.convpp_streams = self.atmos._stream_expr(['b', 'c'],
                                                            inverse=True)

        with mock.patch('atmos.AtmosPostProc.diags_to_process',
                        return_value=['path/Ra.pa20000101',
                                      'path/Ra.pb20000101.pp',
                                      'path/Ra.pc20000101',
                                      'path/Ra.pd20000101.pp']) as mock_pp:
            self.atmos.do_archive()

            self.assertListEqual(
                sorted(self.atmos.suite.archive_file.mock_calls),
                sorted([mock.call('path/Ra.pa20000101', preproc=True),
                        mock.call('path/Ra.pb20000101.pp', preproc=False),
                        mock.call('path/Ra.pc20000101', preproc=False),
                        mock.call('path/Ra.pd20000101.pp', preproc=True)])
                )
        mock_pp.assert_called_once_with(False, log_file=mock.ANY)

    @mock.patch('atmos.AtmosPostProc.diags_to_process',
                return_value=['path/Ra.pa20000101', 'path/Ra.pb20000101.pp',
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
            sorted([mock.call('path/Ra.pa20000101', preproc=True),
                    mock.call('path/Ra.pb20000101.pp', preproc=True),
                    mock.call('path/FF_noconv', preproc=True)])
            )
        mock_dump.assert_called_once_with(mock.ANY)
        mock_pp.assert_called_once_with(False, log_file=mock.ANY)

    @mock.patch('atmos.AtmosPostProc.diags_to_process',
                return_value=['path/Ra.pa20000101', 'path/Ra.pb20000101.pp',
                              'path/Ra.po2000.pp'])
    @mock.patch('atmos.AtmosPostProc.dumps_to_archive',
                return_value=['DumpFile'])
    @mock.patch('atmos.utils.remove_files')
    def test_do_archive_finalcycle(self, mock_rm, mock_dump, mock_pp):
        '''Test do_archive functionality - final cycle'''
        func.logtest('Assert call to archive_file - final cycle')
        self.atmos.naml.archiving.archive_pp = True
        self.atmos.naml.atmospp.ozone_output_stream = 'o'
        self.atmos.suite.archive_file.return_value = 0
        self.atmos.do_archive(finalcycle=True)
        arch_calls = [mock.call('path/Ra.pa20000101', preproc=True),
                      mock.call('path/Ra.pb20000101.pp', preproc=True),
                      mock.call('path/Ra.po2000.pp', preproc=True)]
        self.assertListEqual(sorted(self.atmos.suite.archive_file.mock_calls),
                             sorted(arch_calls))
        self.assertListEqual(mock_dump.mock_calls, [])
        mock_rm.assert_called_once_with('path/Ra.pb20000101.pp')
        self.assertListEqual(
            sorted(self.atmos.suite.archive_file.mock_calls),
            sorted(arch_calls)
            )
        self.assertListEqual(mock_dump.mock_calls, [])
        mock_pp.assert_called_once_with(True, log_file=mock.ANY)

    @mock.patch('atmos.AtmosPostProc.diags_to_process',
                return_value=['path/Ra.pa20000101', 'path/Ra.pb20000101.pp'])
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
        arch_calls = [mock.call('path/Ra.pa20000101', preproc=True),
                      mock.call('path/Ra.pb20000101.pp', preproc=True)]
        self.assertListEqual(sorted(self.atmos.suite.archive_file.mock_calls),
                             sorted(arch_calls))
        self.assertListEqual(mock_dump.mock_calls, [])
        mock_pp.assert_called_once_with(True, log_file=mock.ANY)
        mock_mv.assert_called_once_with('path/Ra.pb20000101.pp',
                                        'path/Ra.pb20000101.pp_ARCHIVED')

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
        mock_getfiles.side_effect = [self.ffiles[1:], []]

        with mock.patch('atmos.os.path.exists', return_value=True):
            with mock.patch('atmos.validation.verify_header',
                            return_value=True):
                with open(self.atmos.suite.logfile, 'w') as log:
                    ppfiles = self.atmos.diags_to_process(False,
                                                          log_file=log)

        self.assertListEqual(ppfiles, [os.path.join(os.getcwd(), fn) for
                                       fn in self.ffiles[1:]])
        self.assertListEqual(
            mock_getfiles.mock_calls,
            [mock.call('WorkDir',
                       self.atmos.ff_match(self.atmos.streams), '.arch'),
             mock.call('WorkDir',
                       self.atmos.ff_match(self.atmos.means), '.arch')]
            )

    @mock.patch('atmos.housekeeping.get_marked_files')
    def test_select_diags_tidy_pp(self, mock_getfiles):
        '''Test do_archive functionality - tidy up ppfiles left on disk'''
        func.logtest('Assert do_archive method - tidy left over ppfile:')
        self.atmos.naml.archiving.archive_pp = True
        fnfull = os.path.join(os.getcwd(), self.ffiles[0])
        open(self.ffiles[0] + '.pp', 'w').close()
        mock_getfiles.side_effect = [[], [self.ffiles[0]]]

        with open(self.atmos.suite.logfile, 'w') as log:
            ppfiles = self.atmos.diags_to_process(False, log_file=log)

        self.assertListEqual(
            mock_getfiles.mock_calls,
            [mock.call('WorkDir',
                       self.atmos.ff_match(self.atmos.streams), '.arch'),
             mock.call('WorkDir',
                       self.atmos.ff_match(self.atmos.means), '.arch')]
            )
        self.assertListEqual(ppfiles, [fnfull + '.pp'])

    @mock.patch('atmos.housekeeping.get_marked_files')
    @mock.patch('atmos.transform.utils.get_subset')
    def test_select_netcdf_diags(self, mock_set, mock_getfiles):
        '''Test select netCDF diagnostic file list for processing'''
        func.logtest('Assert netCDF diagnostics files list created:')
        mock_getfiles.return_value = []
        mock_set.return_value = self.ncfiles
        self.atmos.naml.archiving.archive_ncf = True

        ncfiles = self.atmos.diags_to_process(False)
        self.assertListEqual(ncfiles,
                             [os.path.join(os.getcwd(), self.ncfiles[0])])
        self.assertListEqual(
            mock_getfiles.mock_calls,
            [mock.call('WorkDir', self.atmos.ff_match(self.atmos.streams),
                       '.arch'),
             mock.call('WorkDir', self.atmos.ff_match(self.atmos.means),
                       '.arch')]
            )
        mock_set.assert_called_once_with(
            os.getcwd(),
            r'atmos_Ra_\d+[hdmsyx]_\d{8}(\d{2})?-\d{8}(\d{2})?.*.nc$'
            )
    @mock.patch('atmos.housekeeping.get_marked_files')
    @mock.patch('atmos.transform.utils.get_subset')
    def test_noarchive_netcdf_diags(self, mock_set, mock_getfiles):
        '''Test not archivng netCDF diagnostic files'''
        func.logtest('Assert netCDF diagnostics files list not created:')
        mock_getfiles.return_value = []
        self.atmos.naml.archiving.archive_ncf = False

        ncfiles = self.atmos.diags_to_process(False)
        self.assertListEqual(mock_set.mock_calls, [])
        self.assertListEqual(ncfiles, [])

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

        mock_getfiles.side_effect = [self.ffiles[1:] + self.ppfiles, []]

        with mock.patch('atmos.os.path.exists', return_value=True):
            with open(self.atmos.suite.logfile, 'w') as log:
                ppfiles = self.atmos.diags_to_process(True, log_file=log)

        self.assertListEqual(ppfiles, [os.path.join(os.getcwd(), fn) for
                                       fn in self.ffiles[1:] + self.ppfiles])
        self.assertListEqual(
            mock_getfiles.mock_calls,
            [mock.call(os.getcwd(), self.atmos.ff_match(self.atmos.streams),
                       r'(\.pp)?'),
             mock.call(os.getcwd(), self.atmos.ff_match(self.atmos.means),
                       r'(\.pp)?')]
            )
        verify_calls = [mock.call(mock.ANY, os.path.join(os.getcwd(), f),
                                  mock.ANY, logfile=mock.ANY)
                        for f in self.ffiles[1:]]
        self.assertListEqual(mock_verify.mock_calls, verify_calls)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.transform.convert_to_pp')
    def test_transform_convpp_sel(self, mock_convpp, mock_getfiles):
        '''Test do_transform - pp files list - selected pre-conversion to pp'''
        func.logtest('Assert pp files list for do_transform - some convpp:')

        self.atmos.convpp_streams = self.atmos._stream_expr(['d-f', 1],
                                                            inverse=True)
        mock_getfiles.return_value = self.ffiles[1:]
        mock_convpp.side_effect = [fn + '.pp' for fn in self.ffiles[1:]]

        self.atmos.do_transform()

        mock_getfiles.assert_called_once_with(False)
        for fname in self.ffiles[1:]:
            func.logtest('Testing filename: ' + fname)
            if fname == self.ffiles[-1]:
                self.assertNotIn(mock.call(fname, mock.ANY, None, False),
                                 mock_convpp.mock_calls)
            else:
                self.assertIn(mock.call(fname, mock.ANY, None, False),
                              mock_convpp.mock_calls)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.transform.convert_to_pp')
    def test_transform_pp_convert_none(self, mock_convpp, mock_getfiles):
        '''Test do_transform - pp files list - no conversion to pp'''
        func.logtest('Assert pp files list for do_transform - ppconvert:')
        mock_getfiles.return_value = self.ffiles[1:]
        self.atmos.convpp_streams = '([pm][a])'
        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        self.assertListEqual(mock_convpp.mock_calls, [])

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.transform.convert_to_pp')
    def test_transform_pp_convert_off(self, mock_convpp, mock_getfiles):
        '''Test do_transform - pp files list - convpp OFF'''
        func.logtest('Assert pp files list for do_transform - convpp OFF:')
        self.atmos.naml.atmospp.convert_pp = False
        mock_getfiles.return_value = self.ffiles[1:]

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        self.assertListEqual(mock_convpp.mock_calls, [])

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.transform.extract_to_netcdf', return_value=0)
    def test_transform_netcdf(self, mock_ncf, mock_getfiles):
        '''Test do_transform - collect netCDF files'''
        func.logtest('Assert netCDF files list for do_tranform:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.naml.atmospp.fields_to_netcdf = ['field1', 'F1']
        self.atmos.netcdf_streams = '([pm][b])'

        mock_getfiles.return_value = self.ffiles

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        mock_ncf.assert_called_once_with(self.ffiles[1], {'field1': 'F1'},
                                         'NETCDF4', None)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.transform.extract_to_netcdf', return_value=0)
    def test_transform_netcdf_ppfiles(self, mock_ncf, mock_getfiles):
        '''Test do_transform - collect netCDF files - pp available'''
        func.logtest('Assert netCDF files list for do_tranform:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.naml.atmospp.fields_to_netcdf = ['field1', 'F1']
        self.atmos.netcdf_streams = '([pm][b])'

        mock_getfiles.return_value = self.ppfiles

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        mock_ncf.assert_called_once_with(self.ppfiles[0], {'field1': 'F1'},
                                         'NETCDF4', None)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.transform.extract_to_netcdf', return_value=0)
    def test_transform_netcdf_options(self, mock_ncf, mock_getfiles):
        '''Test do_transform - collect netCDF files'''
        func.logtest('Assert netCDF files list for do_tranform:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.naml.atmospp.fields_to_netcdf = ['fieldA', 'FA']
        self.atmos.naml.atmospp.netcdf_compression = 5
        self.atmos.naml.atmospp.netcdf_filetype = 'MY_NCF'
        mock_getfiles.return_value = self.ffiles

        self.atmos.netcdf_streams = '([pm][b])'

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        mock_ncf.assert_called_once_with(self.ffiles[1], {'fieldA': 'FA'},
                                         'MY_NCF', 5)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.transform.extract_to_netcdf', return_value=0)
    def test_transform_netcdf_nostreams(self, mock_ncf, mock_getfiles):
        '''Test do_transform - collect netCDF files - no streams'''
        func.logtest('Assert netCDF files list for do_tranform - no streams:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.netcdf_streams = None
        mock_getfiles.return_value = self.ffiles

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        self.assertEqual(mock_ncf.call_count, 0)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.transform.extract_to_netcdf', return_value=0)
    def test_transform_netcdf_nofields(self, mock_ncf, mock_getfiles):
        '''Test do_transform - collect netCDF files - no streams'''
        func.logtest('Assert netCDF files list for do_tranform - no streams:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.naml.atmospp.fields_to_netcdf = None
        self.atmos.netcdf_streams = '([pm][b])'

        mock_getfiles.return_value = self.ffiles

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        mock_ncf.assert_called_once_with(self.ffiles[1], {}, 'NETCDF4', None)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.transform.extract_to_netcdf', return_value=1)
    def test_transform_netcdf_fail(self, mock_ncf, mock_getfiles):
        '''Test do_transform - collect netCDF files'''
        func.logtest('Assert netCDF files list for do_tranform:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.netcdf_streams = '([pm][b])'
        self.atmos.naml.atmospp.fields_to_netcdf = ['field1', 'F1']
        mock_getfiles.return_value = self.ffiles

        with self.assertRaises(SystemExit):
            self.atmos.do_transform()
        self.assertIn('Field extraction to netCDF failed',
                      func.capture('err'))
        mock_ncf.assert_called_once_with(self.ffiles[1], {'field1': 'F1'},
                                         'NETCDF4', None)

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.transform.cutout_subdomain')
    def test_transform_cutout(self, mock_cut, mock_getfiles):
        '''Test do_transform - collect cutout files'''
        func.logtest('Assert cutout files list for do_tranform:')
        self.atmos.naml.atmospp.convert_pp = False
        self.atmos.naml.atmospp.cutout_coords_type = 'CTYPE'
        self.atmos.naml.atmospp.cutout_coords = [1, 2]
        self.atmos.cutout_streams = '([pm][d])'
        mock_getfiles.return_value = self.ffiles

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        mock_cut.assert_called_once_with(self.ffiles[-1], None, 'CTYPE', [1, 2])

    @mock.patch('atmos.AtmosPostProc.diags_to_process')
    @mock.patch('atmos.transform.cutout_subdomain')
    def test_transform_cutout_none(self, mock_cut, mock_getfiles):
        '''Test do_transform - collect cutout files - no streams'''
        func.logtest('Assert cutout files list for do_tranform - no streams:')
        self.atmos.naml.atmospp.convert_pp = False
        mock_getfiles.return_value = self.ffiles

        self.atmos.do_transform()
        mock_getfiles.assert_called_once_with(False)
        self.assertListEqual(mock_cut.mock_calls, [])

class MeaningTests(unittest.TestCase):
    ''' Unit tests relating to the cretion of atmosphere means '''
    def setUp(self):
        self.atmos = atmos.AtmosPostProc()

        self.atmos.naml.atmospp.create_means = True
        self.atmos.naml.atmospp.create_monthly_mean = True
        self.atmos.naml.atmospp.create_annual_mean = True
        self.atmos.requested_means = self.atmos._requested_means()
        self.flagdir = os.path.join(os.getcwd(), 'mean_archflags')

        self.atmos.suite = mock.Mock()
        self.atmos.suite.finalcycle = False
        self.atmos.suite.meanref = [1978, 9, 1]
        self.atmos.suite.prefix = 'RUNID'
        self.atmos.share = os.getcwd()
        self.atmos.work = os.getcwd()

    def tearDown(self):
        try:
            shutil.rmtree('mean_archflags')
        except OSError:
            pass
        for date in ['m1990apr', 's1990jja', 's1990ond']:
            try:
                os.remove('RUNIDa.p{}.arch'.format(date))
            except OSError:
                pass

    def test_requested_means(self):
        ''' Test setup of requested means '''
        func.logtest('Assert initialisation of requested means:')
        rqst = self.atmos.requested_means
        self.assertListEqual(list(rqst.keys()), ['1m', '1y'])
        self.assertEqual(rqst['1m'].num_components, 1)
        self.assertEqual(rqst['1y'].num_components, 12)

        self.atmos.naml.atmospp.meanbase_period = '10d'
        rqst = self.atmos._requested_means()
        self.assertListEqual(list(rqst.keys()), ['1m', '1y'])
        self.assertEqual(rqst['1m'].num_components, 3)
        self.assertEqual(rqst['1y'].num_components, 12)

        self.atmos.naml.atmospp.create_monthly_mean = False
        self.atmos.naml.atmospp.create_seasonal_mean = True
        rqst = self.atmos._requested_means()
        self.assertListEqual(list(rqst.keys()), ['1s', '1y'])
        self.assertEqual(rqst['1s'].num_components, 9)
        self.assertEqual(rqst['1y'].num_components, 4)

    def test_requested_means_fail(self):
        ''' Test failure to setup of requested means '''
        func.logtest('Assert failure to initialise requested means:')
        self.atmos.naml.atmospp.meanbase_stream = 'a'
        with self.assertRaises(SystemExit):
            self.atmos.requested_means = self.atmos._requested_means()

        self.assertIn('Please set &atmospp/meanbase_period',
                      func.capture('err'))

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.os.path.isfile')
    @mock.patch('atmos.climatemean.create_mean')
    def test_do_meaning_ppfile(self, mock_create, mock_isfile, mock_set):
        ''' Test call to do_meaning - pre-existing pp format file found'''
        func.logtest('Assert call to do_meaning - pp file on disk:')

        self.atmos.naml.atmospp.create_monthly_mean = False
        self.atmos.naml.atmospp.create_seasonal_mean = True
        self.atmos.naml.atmospp.create_annual_mean = False
        self.atmos.naml.atmospp.create_decadal_mean = False
        self.atmos.requested_means = self.atmos._requested_means()

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing seasons set-ends
        #   [2] seasonal mean component files for Dec-Jan-Feb
        mock_set.side_effect = [[], ['RUNIDa.pm1990dec'], ['seasonsetOND']]
        # mock_isfile return [0] => .pp format mean file exists
        mock_isfile.sideeffect = [True]

        self.atmos.do_meaning()

        self.assertEqual(mock_create.call_count, 0)
        self.assertIn('The requested mean file already exists in pp format',
                      func.capture())
        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([p][m])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([p][m])\d{4}(aug|nov|feb|may).arch$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.([p][m])(1990oct|1990nov|1990dec)(\.pp)?$')]
            )

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean')
    def test_do_meaning_ppcmpt(self, mock_create, mock_set):
        ''' Test call to do_meaning - pre-existing pp format components'''
        func.logtest('Assert call to do_meaning - pp components on disk:')

        self.atmos.naml.atmospp.create_monthly_mean = False
        self.atmos.naml.atmospp.create_seasonal_mean = True
        self.atmos.naml.atmospp.create_annual_mean = False
        self.atmos.naml.atmospp.create_decadal_mean = False
        self.atmos.requested_means = self.atmos._requested_means()


        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing seasons set-ends
        #   [2] seasonal mean component files for Dec-Jan-Feb
        mock_set.side_effect = [[], ['RUNIDa.pm1990aug'], ['seasonsetJJA.pp']]

        self.atmos.do_meaning()

        self.assertEqual(mock_create.call_count, 0)
        self.assertIn('Component(s) of the requested mean file are already '
                      'in pp format', func.capture('err'))
        self.assertIn('RUNIDa.ps1990jja is assumed', func.capture('err'))
        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([p][m])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([p][m])\d{4}(aug|nov|feb|may).arch$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.([p][m])(1990jun|1990jul|1990aug)(\.pp)?$')]
            )
        self.assertTrue(os.path.isfile(os.path.join(os.getcwd(),
                                                    'RUNIDa.ps1990jja.arch')))

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean')
    @mock.patch('atmos.utils.move_files')
    def test_do_meaning_ffcmpt(self, mock_mv, mock_create, mock_set):
        ''' Test call to do_meaning - Check for fieldsfile components'''
        func.logtest('Assert call to do_meaning - pp components on disk:')
        self.atmos.requested_means = []

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        mock_set.side_effect = [['cmpt1', 'cmpt2', 'cmpt3']]

        with mock.patch('atmos.os.path.isfile',
                        side_effect=[False, True, False]):
            self.atmos.do_meaning()
        mock_mv.assert_not_called()

        self.assertEqual(mock_create.call_count, 0)
        mock_set.assert_called_once_with(
            os.getcwd(),
            r'^RUNIDa\.([p][m])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'
            )

        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([p][m])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$')]
            )

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean')
    def test_do_meaning_monthly_rqst(self, mock_create, mock_set):
        ''' Test call to do_meaning - request = model output'''
        func.logtest('Assert call to do_meaning - create monthly mean:')

        self.atmos.naml.atmospp.create_monthly_mean = True
        self.atmos.naml.atmospp.create_seasonal_mean = False
        self.atmos.naml.atmospp.create_annual_mean = False
        self.atmos.naml.atmospp.create_decadal_mean = False
        self.atmos.requested_means = self.atmos._requested_means()

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing month set-end
        #   [2] monthly mean component files for April
        mock_set.side_effect = [[], ['RUNIDa.pm1990apr'], ['monthsetAPR']]

        self.atmos.do_meaning()

        self.assertEqual(mock_create.call_count, 0)
        self.assertIn('The requested mean is a direct UM output',
                      func.capture())
        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([p][m])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([p][m])\d{4}(jan|feb|mar|apr|may|jun|'
                       r'jul|aug|sep|oct|nov|dec).arch$'),
             mock.call(os.getcwd(), r'^RUNIDa\.([p][m])(1990apr)(\.pp)?$')]
            )

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean', return_value=0)
    @mock.patch('atmos.utils.move_files')
    def test_do_meaning_monthly_base1m(self, mock_mv, mock_create, mock_set):
        ''' Test call to do_meaning - single component'''
        func.logtest('Assert call to do_meaning - create monthly mean:')
        self.atmos.naml.atmospp.create_monthly_mean = True
        self.atmos.naml.atmospp.create_seasonal_mean = False
        self.atmos.naml.atmospp.create_annual_mean = False
        self.atmos.naml.atmospp.create_decadal_mean = False

        self.atmos.naml.atmospp.meanbase_stream = 'a'
        self.atmos.naml.atmospp.meanbase_period = '1m'
        self.atmos.requested_means = self.atmos._requested_means()
        meanfile = self.atmos.requested_means['1m']

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing month set-end
        #   [2] monthly mean component files for April
        mock_set.side_effect = [['MoveToFlag'], ['RUNIDa.pa1990apr'],
                                ['monthsetAPR']]
        with mock.patch('atmos.os.path.isfile',
                        side_effect=[True, False, True]):
            self.atmos.do_meaning()

        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([pm][a])\d{4}(jan|feb|mar|apr|may|jun|'
                       r'jul|aug|sep|oct|nov|dec).arch$'),
             mock.call(os.getcwd(), r'^RUNIDa\.([pm][a])(1990apr)(\.pp)?$')]
            )
        meanfile.set_filename('RUNIDa.pm1990apr', os.getcwd())
        self.assertEqual(mock_create.call_args[0][0].fname, meanfile.fname)
        self.assertEqual(mock_create.call_args[0][0].periodend,
                         ('1990', '05', '01'))
        self.assertEqual(mock_create.call_args[0][0].component_files,
                         [os.path.join(os.getcwd(), 'monthsetAPR')])
        self.assertTrue(os.path.isfile(os.path.join(os.getcwd(),
                                                    'RUNIDa.pm1990apr.arch')))

        mock_mv.assert_called_once_with(['MoveToFlag.arch'], self.flagdir,
                                        originpath=os.getcwd())

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean')
    def test_do_meaning_monthly_base10d(self, mock_create, mock_set):
        ''' Test call to do_meaning - create monthly mean only, 10d base'''
        func.logtest('Assert call to do_meaning - create monthly mean:')
        self.atmos.naml.atmospp.create_monthly_mean = True
        self.atmos.naml.atmospp.create_seasonal_mean = False
        self.atmos.naml.atmospp.create_annual_mean = False
        self.atmos.naml.atmospp.create_decadal_mean = False

        self.atmos.naml.atmospp.meanbase_stream = 'a'
        self.atmos.naml.atmospp.meanbase_period = '10d'
        self.atmos.requested_means = self.atmos._requested_means()
        meanfile = self.atmos.requested_means['1m']

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing month set-end
        #   [2] monthly mean component files for December
        mock_set.side_effect = [[], ['RUNIDa.pa19901221'], ['monthsetDEC']]
        self.atmos.do_meaning()

        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([pm][a])\d{4}(01|02|03|04|05|06|07|08|'
                       '09|10|11|12)21.arch$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])(19901201|19901211|19901221)'
                       r'(\.pp)?$')]
            )
        meanfile.set_filename('RUNIDa.pm1990dec', os.getcwd())
        self.assertEqual(mock_create.call_args[0][0].fname, meanfile.fname)
        self.assertEqual(mock_create.call_args[0][0].periodend,
                         ('1991', '01', '01'))
        self.assertEqual(mock_create.call_args[0][0].component_files,
                         [os.path.join(os.getcwd(), 'monthsetDEC')])

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean')
    def test_do_meaning_monthly_base12h(self, mock_create, mock_set):
        ''' Test call to do_meaning - create monthly mean only, 12h base'''
        func.logtest('Assert call to do_meaning - create monthly mean:')
        self.atmos.naml.atmospp.create_monthly_mean = True
        self.atmos.naml.atmospp.create_seasonal_mean = False
        self.atmos.naml.atmospp.create_annual_mean = False
        self.atmos.naml.atmospp.create_decadal_mean = False

        self.atmos.naml.atmospp.meanbase_stream = 'a'
        self.atmos.naml.atmospp.meanbase_period = '12h'
        self.atmos.requested_means = self.atmos._requested_means()
        meanfile = self.atmos.requested_means['1m']

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing month set-end
        #   [2] monthly mean component files for December
        mock_set.side_effect = [[], ['RUNIDa.pa19901230_12'], ['monthsetDEC']]
        self.atmos.do_meaning()

        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([pm][a])\d{4}(01|02|03|04|05|06|07|08|'
                       r'09|10|11|12)30_12.arch$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])(19901201_00|19901201_12|'
                       r'19901202_00|19901202_12|19901203_00|19901203_12|'
                       r'19901204_00|19901204_12|19901205_00|19901205_12|'
                       r'19901206_00|19901206_12|19901207_00|19901207_12|'
                       r'19901208_00|19901208_12|19901209_00|19901209_12|'
                       r'19901210_00|19901210_12|19901211_00|19901211_12|'
                       r'19901212_00|19901212_12|19901213_00|19901213_12|'
                       r'19901214_00|19901214_12|19901215_00|19901215_12|'
                       r'19901216_00|19901216_12|19901217_00|19901217_12|'
                       r'19901218_00|19901218_12|19901219_00|19901219_12|'
                       r'19901220_00|19901220_12|19901221_00|19901221_12|'
                       r'19901222_00|19901222_12|19901223_00|19901223_12|'
                       r'19901224_00|19901224_12|19901225_00|19901225_12|'
                       r'19901226_00|19901226_12|19901227_00|19901227_12|'
                       r'19901228_00|19901228_12|19901229_00|19901229_12|'
                       r'19901230_00|19901230_12)(\.pp)?$')]
            )
        meanfile.set_filename('RUNIDa.pm1990dec', os.getcwd())
        self.assertEqual(mock_create.call_args[0][0].fname, meanfile.fname)
        self.assertEqual(mock_create.call_args[0][0].periodend,
                         ('1991', '01', '01', '00'))
        self.assertEqual(mock_create.call_args[0][0].component_files,
                         [os.path.join(os.getcwd(), 'monthsetDEC')])

    def test_do_meaning_offset_meanref(self):
        ''' Test call to do_meaning - meanref not 1st of the month'''
        func.logtest('Assert call to do_meaning - meanref not 1st:')
        self.atmos.suite.meanref = [1978, 12, 15]
        self.atmos.do_meaning()
        self.assertIn('Means cannot be created', func.capture('err'))

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean')
    def test_do_meaning_seasonal(self, mock_create, mock_set):
        ''' Test call to do_meaning - seasonal mean'''
        func.logtest('Assert call to do_meaning - create seasonal mean:')

        self.atmos.naml.atmospp.create_monthly_mean = True
        self.atmos.naml.atmospp.create_seasonal_mean = True
        self.atmos.naml.atmospp.create_annual_mean = False
        self.atmos.naml.atmospp.create_decadal_mean = False

        self.atmos.naml.atmospp.meanbase_stream = 'a'
        self.atmos.naml.atmospp.meanbase_period = '1m'
        self.atmos.requested_means = self.atmos._requested_means()

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing month set-end
        #   [2] .arch files in flags directory representing season set-ends
        #   [3] seasonal mean component files for Jun-Jul-Aug
        mock_set.side_effect = [[], [], ['RUNIDa.pm1990aug'], ['seasonsetJJA']]
        self.atmos.do_meaning()

        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([pm][a])\d{4}(jan|feb|mar|apr|may|jun|'
                       r'jul|aug|sep|oct|nov|dec).arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.pm\d{4}(aug|nov|feb|may).arch$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.pm(1990jun|1990jul|1990aug)(\.pp)?$')]
            )

        self.assertEqual(mock_create.call_args[0][0].fname['file'],
                         'RUNIDa.ps1990jja')
        self.assertEqual(mock_create.call_args[0][0].periodend,
                         ('1990', '09', '01'))
        self.assertEqual(mock_create.call_args[0][0].component_files,
                         [os.path.join(os.getcwd(), 'seasonsetJJA')])

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean')
    def test_do_meaning_seasonal_only(self, mock_create, mock_set):
        ''' Test call to do_meaning - seasonal only, base=1m'''
        func.logtest('Assert call to do_meaning - create seasonal mean only:')
        self.atmos.naml.atmospp.create_monthly_mean = False
        self.atmos.naml.atmospp.create_seasonal_mean = True
        self.atmos.naml.atmospp.create_annual_mean = False
        self.atmos.naml.atmospp.create_decadal_mean = False

        self.atmos.naml.atmospp.meanbase_stream = 'a'
        self.atmos.naml.atmospp.meanbase_period = '1m'
        self.atmos.requested_means = self.atmos._requested_means()

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing seasons set-ends
        #   [2] seasonal mean component files for Jun-Jul-Aug
        #   [3] seasonal mean component files for Dec-Jan-Feb
        mock_set.side_effect = [[],
                                ['RUNIDa.pa1990aug', 'RUNIDa.pa1991feb'],
                                ['seasonsetJJA'], ['seasonsetDJF']]
        self.atmos.do_meaning()

        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([pm][a])\d{4}(aug|nov|feb|may).arch$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])(1990jun|1990jul|1990aug)(\.pp)?$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])(1990dec|1991jan|1991feb)(\.pp)?$')]
            )

        self.assertEqual(mock_create.call_args[0][0].fname['file'],
                         'RUNIDa.ps1991djf')
        self.assertEqual(mock_create.call_args[0][0].periodend,
                         ('1991', '03', '01'))
        self.assertEqual(mock_create.call_args[0][0].component_files,
                         [os.path.join(os.getcwd(), 'seasonsetDJF')])

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean')
    def test_do_meaning_annual(self, mock_create, mock_set):
        ''' Test call to do_meaning - annual mean'''
        func.logtest('Assert call to do_meaning - create annual mean:')

        self.atmos.naml.atmospp.create_monthly_mean = False
        self.atmos.naml.atmospp.create_seasonal_mean = True
        self.atmos.naml.atmospp.create_annual_mean = True
        self.atmos.naml.atmospp.create_decadal_mean = False
        self.atmos.suite.meanref = [1978, 2, 1]

        self.atmos.naml.atmospp.meanbase_stream = 'a'
        self.atmos.naml.atmospp.meanbase_period = '1m'
        self.atmos.requested_means = self.atmos._requested_means()

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing seasons set-ends
        #   [2] .arch files in flags directory representing annual set-ends
        #   [3] annual mean component files for 1990
        mock_set.side_effect = [[], [], ['RUNIDa.ps1990ndj'], ['yearset']]
        self.atmos.do_meaning()

        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([pm][a])\d{4}(jan|apr|jul|oct).arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.ps\d{4}ndj.arch$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.ps(1989fma|1989mjj|1989aso|1990ndj)(\.pp)?$')]
            )

        self.assertEqual(mock_create.call_args[0][0].fname['file'],
                         'RUNIDa.py19900201')
        self.assertEqual(mock_create.call_args[0][0].periodend,
                         ('1990', '02', '01'))
        self.assertEqual(mock_create.call_args[0][0].component_files,
                         [os.path.join(os.getcwd(), 'yearset')])

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean')
    def test_do_meaning_annual_only(self, mock_create, mock_set):
        ''' Test call to do_meaning - annual only '''
        func.logtest('Assert call to do_meaning - create annual mean only:')

        self.atmos.naml.atmospp.create_monthly_mean = False
        self.atmos.naml.atmospp.create_seasonal_mean = False
        self.atmos.naml.atmospp.create_annual_mean = True
        self.atmos.naml.atmospp.create_decadal_mean = False
        self.atmos.suite.meanref = [1978, 1, 1]

        self.atmos.naml.atmospp.meanbase_stream = 'a'
        self.atmos.naml.atmospp.meanbase_period = '1m'
        self.atmos.requested_means = self.atmos._requested_means()

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing annual set-end
        #   [2] annual mean component files
        mock_set.side_effect = [[], ['RUNIDa.ps1990dec'], ['yearset']]
        self.atmos.do_meaning()

        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([pm][a])\d{4}dec.arch$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])(1990jan|1990feb|1990mar|'
                       r'1990apr|1990may|1990jun|1990jul|1990aug|1990sep|'
                       r'1990oct|1990nov|1990dec)(\.pp)?$')]
            )

        self.assertEqual(mock_create.call_args[0][0].fname['file'],
                         'RUNIDa.py19910101')
        self.assertEqual(mock_create.call_args[0][0].periodend,
                         ('1991', '01', '01'))
        self.assertEqual(mock_create.call_args[0][0].component_files,
                         [os.path.join(os.getcwd(), 'yearset')])

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean')
    def test_do_meaning_decadal(self, mock_create, mock_set):
        ''' Test call to do_meaning - decadal'''
        func.logtest('Assert call to do_meaning - create decadal mean:')

        self.atmos.naml.atmospp.create_monthly_mean = False
        self.atmos.naml.atmospp.create_seasonal_mean = False
        self.atmos.naml.atmospp.create_annual_mean = True
        self.atmos.naml.atmospp.create_decadal_mean = True
        self.atmos.suite.meanref = [1978, 12, 1]

        self.atmos.naml.atmospp.meanbase_stream = 'a'
        self.atmos.naml.atmospp.meanbase_period = '1s'
        self.atmos.requested_means = self.atmos._requested_means()

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing annual set-ends
        #   [2] .arch files in flags directory representing decadal set-ends
        #   [3] decadal mean component files for Dec-Jan-Feb
        mock_set.side_effect = [[], [], ['RUNIDa.py19981201'], ['decadeset']]
        self.atmos.do_meaning()

        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([pm][a])\d{4}son.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.py\d{3}81201.arch$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.py(19891201|19901201|19911201|19921201|'
                       r'19931201|19941201|19951201|19961201|19971201|'
                       r'19981201)(\.pp)?$')]
            )

        self.assertEqual(mock_create.call_args[0][0].fname['file'],
                         'RUNIDa.px19981201')
        self.assertEqual(mock_create.call_args[0][0].periodend,
                         ['1998', '12', '01'])
        self.assertEqual(mock_create.call_args[0][0].component_files,
                         [os.path.join(os.getcwd(), 'decadeset')])

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean')
    def test_do_meaning_decadal_only(self, mock_create, mock_set):
        ''' Test call to do_meaning - decadal only '''
        func.logtest('Assert call to do_meaning - create decadal only mean:')

        self.atmos.naml.atmospp.create_monthly_mean = False
        self.atmos.naml.atmospp.create_seasonal_mean = False
        self.atmos.naml.atmospp.create_annual_mean = False
        self.atmos.naml.atmospp.create_decadal_mean = True
        self.atmos.suite.meanref = [1978, 1, 1]

        self.atmos.naml.atmospp.meanbase_stream = 'a'
        self.atmos.naml.atmospp.meanbase_period = '1s'
        self.atmos.requested_means = self.atmos._requested_means()

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing decadal set-end
        #   [2] decadal mean component files
        mock_set.side_effect = [[], ['RUNIDa.ps1997ond'], ['decadeset']]
        self.atmos.do_meaning()

        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([pm][a])\d{3}7ond.arch$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])(1988jfm|1988amj|1988jas|'
                       '1988ond|1989jfm|1989amj|1989jas|1989ond|1990jfm|'
                       '1990amj|1990jas|1990ond|1991jfm|1991amj|1991jas|'
                       '1991ond|1992jfm|1992amj|1992jas|1992ond|1993jfm|'
                       '1993amj|1993jas|1993ond|1994jfm|1994amj|1994jas|'
                       '1994ond|1995jfm|1995amj|1995jas|1995ond|1996jfm|'
                       '1996amj|1996jas|1996ond|1997jfm|1997amj|1997jas|'
                       r'1997ond)(\.pp)?$')]
            )

        self.assertEqual(mock_create.call_args[0][0].fname['file'],
                         'RUNIDa.px19980101')
        self.assertEqual(mock_create.call_args[0][0].periodend,
                         ('1998', '01', '01'))
        self.assertEqual(mock_create.call_args[0][0].component_files,
                         [os.path.join(os.getcwd(), 'decadeset')])

    @mock.patch('atmos.utils.get_subset')
    @mock.patch('atmos.climatemean.create_mean')
    def test_do_meaning_ssn_finalcycle(self, mock_create, mock_set):
        ''' Test call to do_meaning - seasonal only, base=1m'''
        func.logtest('Assert call to do_meaning - create seasonal mean only:')
        self.atmos.naml.atmospp.create_monthly_mean = False
        self.atmos.naml.atmospp.create_seasonal_mean = True
        self.atmos.naml.atmospp.create_annual_mean = False
        self.atmos.naml.atmospp.create_decadal_mean = False

        self.atmos.naml.atmospp.meanbase_stream = 'a'
        self.atmos.naml.atmospp.meanbase_period = '1m'
        self.atmos.requested_means = self.atmos._requested_means()
        self.atmos.suite.finalcycle = True

        # Calls to mock_set - get files matching:
        #   [0] .arch file to move to flags directory
        #   [1] .arch files in flags directory representing seasons set-ends
        #   [2] seasonal mean component files for Jun-Jul-Aug
        #   [3] Setend files present in share but not yet marked for archive
        #   [4] seasonal mean component files for Dec-Jan-Feb
        mock_set.side_effect = [[],
                                ['RUNIDa.pa1990aug'], ['seasonsetJJA'],
                                ['RUNIDa.pa1991feb'], ['seasonsetDJF']]
        self.atmos.do_meaning()

        self.assertListEqual(
            mock_set.mock_calls,
            [mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])\d{4}(\d{4}|\w{3})?(_\d{2})?.arch$'),
             mock.call(self.flagdir,
                       r'^RUNIDa\.([pm][a])\d{4}(aug|nov|feb|may).arch$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])(1990jun|1990jul|1990aug)(\.pp)?$'),
             mock.call(self.atmos.share,
                       r'^RUNIDa\.([pm][a])\d{4}(aug|nov|feb|may)$'),
             mock.call(os.getcwd(),
                       r'^RUNIDa\.([pm][a])(1990dec|1991jan|1991feb)(\.pp)?$')]
            )

        self.assertEqual(mock_create.call_args[0][0].fname['file'],
                         'RUNIDa.ps1991djf')
        self.assertEqual(mock_create.call_args[0][0].periodend,
                         ('1991', '03', '01'))
        self.assertEqual(mock_create.call_args[0][0].component_files,
                         [os.path.join(os.getcwd(), 'seasonsetDJF')])


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

    def test_process_methods(self):
        '''Test return list of processing only methods'''
        func.logtest('Assert list of processing methods')
        self.atmos.suite.naml.process_toplevel = True
        self.assertListEqual(
            list(self.atmos.methods.keys()),
            ['do_ozone', 'do_meaning', 'do_transform', 'finalcycle_complete',
             'finalise_debug']
        )

    def test_archive_methods(self):
        '''Test return list of archiving only methods'''
        func.logtest('Assert list of processing methods')
        self.atmos.suite.naml.archive_toplevel = True
        self.assertListEqual(
            list(self.atmos.methods.keys()),
            ['do_archive', 'do_delete', 'finalcycle_complete', 'finalise_debug']
        )
        
    def test_dumpname(self):
        '''Test dumpname creation'''
        func.logtest('Assert return of dumpname for current cycle:')
        with mock.patch.dict('atmos.os.environ',
                             {'CYLC_TASK_CYCLE_POINT': '19900901T0600Z'}):
            self.atmos.suite = atmos.suite.SuiteEnvironment(os.getcwd())
            self.assertEqual(self.atmos.dumpname(), 'TESTPa.da19900901_06')

    def test_dumpname_specific(self):
        '''Test dumpname creation for given dumpdate'''
        func.logtest('Assert return of dumpname for final cycle:')
        self.atmos.suite.prefix = 'PREFIX'
        self.assertEqual(self.atmos.dumpname(dumpdate=[1111, 22, 33,
                                                       44, 55, 66]),
                         'PREFIXa.da11112233_44')

    def test_stream_expr_single(self):
        '''Test stream_expr calculation of regular expression - single'''
        func.logtest('Assert stream_expr calculation of regex - single:')
        self.assertEqual(self.atmos._stream_expr('a'), '([pm][a])')
        self.assertEqual(self.atmos._stream_expr('^a'),
                         '(?![pm][a])[pm][a-z1-9]')
        self.assertEqual(self.atmos._stream_expr('a', inverse=True),
                         '(?![pm][a])[pm][a-z1-9]')
        self.assertEqual(self.atmos._stream_expr('mx'), '([m][x])')

    def test_stream_expr_list(self):
        '''Test stream_expr calculation of regular expression - list'''
        func.logtest('Assert netcdf_streams calculation of regex - list:')
        self.assertEqual(self.atmos._stream_expr(['a', 'mb', 3]),
                         '([pm][a]|[m][b]|[pm][3])')
        self.assertEqual(
            self.atmos._stream_expr(['a', '1-2', 4], inverse=True),
            '(?![pm][a]|[pm][1-2]|[pm][4])[pm][a-z1-9]'
            )

    def test_stream_expr_empty(self):
        '''Test stream_expr calculation of regular expression - Empty list'''
        func.logtest('Assert stream_expr calculation of regex - Empty list:')
        self.assertEqual(self.atmos._stream_expr('', nullstring=True), '')
        self.assertEqual(self.atmos._stream_expr(''), None)
        self.assertEqual(self.atmos._stream_expr(None, nullstring=True), None)

    def test_transform_streams_default(self):
        '''Test transform streams calculation of regular expression - default'''
        func.logtest('Assert streams calculation of regex - default:')
        self.assertEqual(self.atmos.convpp_streams, '([pm][a-z]|[pm][1-9])')
        self.assertEqual(self.atmos.netcdf_streams, None)
        self.assertEqual(self.atmos.cutout_streams, None)

    def test_streams_property(self):
        '''Test the return value of the streams property'''
        func.logtest('Assert return value of the streams property:')
        self.assertEqual(self.atmos.naml.atmospp.process_streams, None)
        self.assertEqual(self.atmos.streams,
                         '([pm][1-9]|[pm][a-l]|[pm][n-r]|[pm][t-x]|[pm][z])')
        self.atmos.naml.atmospp.process_streams = ['ma', 't-z']
        self.assertEqual(self.atmos.streams, '([m][a]|[pm][t-z])')
        self.atmos.naml.atmospp.ozone_output_stream = 'o'
        self.assertEqual(self.atmos.streams, '([m][a]|[pm][t-z]|[pm][o])')
        self.atmos.naml.atmospp.process_streams = ''
        self.assertEqual(self.atmos.streams, '')

    def test_means_property(self):
        '''Test the return value of the means property'''
        func.logtest('Assert return value of the means property:')
        self.assertEqual(self.atmos.naml.atmospp.process_means, None)
        self.assertEqual(self.atmos.means, '([pm][m]|[pm][s]|[pm][y])')
        self.atmos.naml.atmospp.process_means = ['a', 'pt-z']
        self.assertEqual(self.atmos.means, '([pm][a]|[p][t-z])')

    def test_ff_match(self):
        '''Test the fieldsfile regular expression'''
        func.logtest('Assert correct return of fields file regex:')
        self.atmos.suite.prefix = 'PREFIX'
        ff_match = r'^PREFIXa\.(expr)\d{4}(\d{4}|\w{3})?' \
            r'(_\d{2})?$'
        self.assertEqual(self.atmos.ff_match('(expr)'), ff_match)

    def test_ff_match_runid(self):
        '''Test the fieldsfile regular expression - Prefix=$RUNID'''
        func.logtest('Assert correct return of fields file regex - RUNID:')
        del self.atmos.suite.prefix
        ff_pattern = r'^TESTPa\.(expr)\d{4}(\d{4}|\w{3})?' \
            r'(_\d{2})?$'
        self.assertEqual(self.atmos.ff_match('(expr)'), ff_pattern)

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

class OzoneTests(unittest.TestCase):
    '''Unit tests relating to the extraction of ozone fields to pp'''
    def setUp(self):
        self.atmos = atmos.AtmosPostProc()
        self.atmos.share = os.getcwd()
        self.atmos.work = 'WorkDir'
        self.atmos.suite = mock.Mock()
        self.atmos.suite.prefix='RUNID'
        with mock.patch('atmos.utils.os.environ',
                        return_value={'CYCLEPERIOD', 'P1M'}):
            self.atmos.suite.cyclepoint = atmos.utils.\
                                          CylcCycle('19780901T0000Z')

    def tearDown(self):
        # files = ['logfile', self.dfiles[0], self.ffiles[0],
        #          self.ffiles[0] + '.pp']
        for fname in []:
            try:
                os.remove(fname)
            except OSError:
                pass

    @mock.patch('atmos.housekeeping.get_marked_files')
    @mock.patch('atmos.utils.compare_mod_times')
    def test_do_ozone(self, mock_modtimes, mock_getfiles):
        '''Test do_ozone'''
        func.logtest('Assert running of do_ozone method:')
        self.atmos.naml.atmospp.ozone_source_stream = 's'
        self.atmos.naml.atmospp.ozone_output_stream = ''
        sfiles = ['s1a.p41976mon', 's1a.p41977mon', 's1a.p41978mon']
        mock_getfiles.side_effect = [
            # Get .arch flags
            [sfiles[-1]],
            # Get list of source files in sharedir
            [os.path.basename(f) for f in sfiles]]
        spaths = [os.path.join(os.getcwd(), f) for f in sfiles]
        mock_modtimes.side_effect = [spaths[0], spaths[1] + '.pp', spaths[2]]

        with mock.patch('atmos.transform.extract_to_pp',
                        return_value=0) as mock_extract:
            with mock.patch('atmos.transform.convert_to_pp') as mock_convert:
                with mock.patch('atmos.utils.remove_files') as mock_rm:
                    with mock.patch(OPEN_FUNC) as mock_open:
                        self.atmos.do_ozone()

        self.assertIn(mock.call([spaths[0], spaths[0] + '.pp']),
                      mock_modtimes.mock_calls)
        self.assertIn(mock.call([spaths[1], spaths[1] + '.pp']),
                      mock_modtimes.mock_calls)
        self.assertIn(mock.call([spaths[2], spaths[2] + '.pp']),
                      mock_modtimes.mock_calls)
        self.assertIn(mock.call('WorkDir',
                                r'^RUNIDa\.ps\d{4}(\d{4}|\w{3})?(_\d{2})?$',
                                '.arch'),
                      mock_getfiles.mock_calls)
        self.assertIn(mock.call(os.getcwd(),
                                r'^RUNIDa\.ps\d{4}(\d{4}|\w{3})?(_\d{2})?$',
                                ''),
                      mock_getfiles.mock_calls)

        mock_open.assert_called_once_with(
            os.path.join('WorkDir', sfiles[0] + '.arch'), 'w')
        mock_rm.assert_called_once_with(
            [sfiles[-1] + '.arch'], path=self.atmos.work
        )
        self.assertListEqual(
            sorted(mock_convert.mock_calls),
            [mock.call(spaths[0], '/projects/um1/vn10.8/xc40/utilities',
                       None, True),
             mock.call(spaths[2], '/projects/um1/vn10.8/xc40/utilities',
                       None, False)]
        )
        self.assertListEqual(sorted(mock_extract.mock_calls), [])

    @mock.patch('atmos.housekeeping.get_marked_files')
    def test_do_ozone_extract(self, mock_getfiles):
        '''Test do_ozone with extraction of fields'''
        func.logtest('Assert running of do_ozone method:')
        self.atmos.naml.atmospp.ozone_output_stream = 'z'
        mock_getfiles.side_effect = [['archflag'], ['source1', 'source2'],
                                     ['archa.po1978', 'archa.po1979']]
        with mock.patch('atmos.transform.extract_to_pp',
                        return_value=0) as mock_extract:
            self.atmos.do_ozone()
        mock_extract.assert_called_once_with(
            [os.path.join(os.getcwd(), 'source1'),
             os.path.join(os.getcwd(), 'source2')],
            [253, 30453], 'pz', data_freq='1m'
            )

        self.assertIn(mock.call('WorkDir',
                                r'^RUNIDa\.pz\d{4}(\d{4}|\w{3})?(_\d{2})?$',
                                '.arch'),
                      mock_getfiles.mock_calls)
        self.assertIn(mock.call(os.getcwd(),
                                r'^RUNIDa\.p4\d{4}(\d{4}|\w{3})?(_\d{2})?$',
                                ''),
                      mock_getfiles.mock_calls)

    @mock.patch('atmos.housekeeping.get_marked_files')
    def test_do_ozone_conflict(self, mock_getfiles):
        '''Test do_ozone with extraction to existing UM output'''
        func.logtest('Assert running of do_ozone method:')
        self.atmos.naml.atmospp.ozone_output_stream = 'z'
        mock_getfiles.side_effect = [['archa.pz1979feb.arch'],
                                     ['source1', 'source2'],
                                     ['archa.po1978', 'archa.po1979']]
        with self.assertRaises(SystemExit):
            self.atmos.do_ozone()
        self.assertIn('output stream for ozone redistribution appears to '
                      'match existing UM output',
                      func.capture('err'))

    @mock.patch('atmos.housekeeping.get_marked_files')
    def test_do_ozone_error(self, mock_getfiles):
        '''Test do_ozone with extraction to existing UM output'''
        func.logtest('Assert running of do_ozone method:')
        self.atmos.naml.atmospp.ozone_output_stream = 'z'
        mock_getfiles.side_effect = [['archa.pz1972feb.arch'],
                                     ['source1', 'source2'],
                                     []]
        with mock.patch('atmos.transform.extract_to_pp', side_effect=[1]):
            with self.assertRaises(SystemExit):
                self.atmos.do_ozone()
        self.assertIn('Failed extracting ozone fields',
                      func.capture('err'))
