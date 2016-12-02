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
import re
import mock

import testing_functions as func
import runtime_environment

import atmosNamelist
import validation
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

    def tearDown(self):
        files = ['logfile', self.dfiles[0], self.ffiles[0],
                 self.ffiles[0] + '.pp']
        for fname in runtime_environment.RUNTIME_FILES + files:
            try:
                os.remove(fname)
            except OSError:
                pass

    @mock.patch('atmos.AtmosPostProc.pp_to_archive',
                return_value=['path/a.pa2000', 'path/a.pb2000.pp',
                              'path/FF_noconv'])
    @mock.patch('atmos.AtmosPostProc.dumps_to_archive',
                return_value=['DumpFile'])
    def test_do_archive(self, mock_dump, mock_pp):
        '''Test do_archive functionality'''
        func.logtest('Assert call to archive_file')
        self.atmos.do_archive()
        self.assertListEqual(
            sorted(self.atmos.suite.archive_file.mock_calls),
            sorted([mock.call('path/a.pa2000', preproc=True),
                    mock.call('path/a.pb2000.pp', preproc=True),
                    mock.call('path/FF_noconv', preproc=False),
                    mock.call('DumpFile', preproc=False)])
            )
        mock_dump.assert_called_once_with(mock.ANY)
        mock_pp.assert_called_once_with(mock.ANY, False)

    @mock.patch('atmos.AtmosPostProc.pp_to_archive',
                return_value=['path/a.pa2000', 'path/a.pb2000.pp'])
    @mock.patch('atmos.AtmosPostProc.dumps_to_archive', return_value=[])
    def test_do_archive_unconverted(self, mock_dump, mock_pp):
        '''Test do_archive functionality - unconverted fieldsfiles'''
        func.logtest('Assert call to archive_file, with unconverted ffiles')
        self.atmos.naml.archiving.convert_pp = False
        self.atmos.do_archive()
        self.assertListEqual(
            sorted(self.atmos.suite.archive_file.mock_calls),
            sorted([mock.call('path/a.pa2000', preproc=False),
                    mock.call('path/a.pb2000.pp', preproc=False)])
            )
        mock_dump.assert_called_once_with(mock.ANY)
        mock_pp.assert_called_once_with(mock.ANY, False)

    @mock.patch('atmos.AtmosPostProc.pp_to_archive',
                return_value=['path/a.pa2000', 'path/a.pb2000.pp'])
    @mock.patch('atmos.AtmosPostProc.dumps_to_archive',
                return_value=['DumpFile'])
    @mock.patch('utils.remove_files')
    def test_do_archive_finalcycle(self, mock_rm, mock_dump, mock_pp):
        '''Test do_archive functionality - final cycle'''
        func.logtest('Assert call to archive_file - final cycle')
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
        mock_pp.assert_called_once_with(mock.ANY, True)

    @mock.patch('atmos.AtmosPostProc.pp_to_archive',
                return_value=['path/a.pa2000', 'path/a.pb2000.pp'])
    @mock.patch('atmos.AtmosPostProc.dumps_to_archive',
                return_value=['DumpFile'])
    @mock.patch('os.remove')
    def test_do_archive_final_debug(self, mock_rm, mock_dump, mock_pp):
        '''Test do_archive functionality - final cycle, debug'''
        func.logtest('Assert call to archive_file - final cycle debug')
        self.atmos.suite.archive_file.return_value = 0
        self.atmos.suite._debug_mode(True)
        self.atmos.do_archive(finalcycle=True)
        arch_calls = [mock.call('path/a.pa2000', preproc=True),
                      mock.call('path/a.pb2000.pp', preproc=True)]
        self.assertListEqual(sorted(self.atmos.suite.archive_file.mock_calls),
                             sorted(arch_calls))
        self.assertListEqual(mock_dump.mock_calls, [])
        mock_pp.assert_called_once_with(mock.ANY, True)
        mock_rm.assert_called_once_with('path/a.pb2000.pp')

    def test_do_archive_nothing(self):
        '''Test do_archive functionality - nothing to archive'''
        func.logtest('Assert do_archive behaviour with nothing to archive:')
        self.atmos.do_archive()
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
        with mock.patch('validation.make_dump_name',
                        return_value=self.dfiles):
            with mock.patch('validation.verify_header', return_value=True):
                with open(self.atmos.suite.logfile, 'w') as log:
                    dumps = self.atmos.dumps_to_archive(log)
                validation.verify_header.assert_called_once_with(
                    mock.ANY, os.path.join(os.getcwd(), self.dfiles[0]),
                    mock.ANY, mock.ANY
                    )
            validation.make_dump_name.assert_called_once_with(self.atmos)
        self.assertListEqual(dumps, [self.dfiles[0]])

    def test_archive_dump_non_existent(self):
        '''Test do_archive - dump files list - file non-existent'''
        func.logtest('Assert dumpfiles for do_archive - file non existent:')
        self.atmos.naml.archiving.archive_dumps = True
        with mock.patch('validation.make_dump_name',
                        return_value=self.dfiles):
            with open(self.atmos.suite.logfile, 'w') as log:
                dumps = self.atmos.dumps_to_archive(log)
            validation.make_dump_name.assert_called_once_with(self.atmos)
        self.assertListEqual(dumps, [])

    @mock.patch('housekeeping.get_marked_files')
    @mock.patch('housekeeping.convert_to_pp')
    def test_archive_pp(self, mock_convpp, mock_getfiles):
        '''Test do_archive - pp files list - pre-conversion to pp OFF'''
        func.logtest('Assert pp files list created for do_archive:')
        self.atmos.naml.archiving.archive_pp = True
        self.atmos.naml.archiving.convert_pp = False
        mock_getfiles.return_value = self.ffiles[1:]

        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('validation.verify_header', return_value=True):
                with open(self.atmos.suite.logfile, 'w') as log:
                    ppfiles = self.atmos.pp_to_archive(log, False)

        self.assertListEqual(ppfiles, [os.path.join(os.getcwd(), fn) for
                                       fn in self.ffiles[1:]])
        mock_getfiles.assert_called_once_with('WorkDir', mock.ANY, '.arch')
        self.assertListEqual(mock_convpp.mock_calls, [])

    @mock.patch('housekeeping.get_marked_files')
    def test_do_archive_tidy_pp(self, mock_getfiles):
        '''Test do_archive functionality - tidy up ppfiles left on disk'''
        func.logtest('Assert do_archive method - tidy left over ppfile:')
        self.atmos.naml.archiving.archive_pp = True
        fnfull = os.path.join(os.getcwd(), self.ffiles[0])
        open(self.ffiles[0] + '.pp', 'w').close()
        mock_getfiles.return_value = [self.ffiles[0]]

        with open(self.atmos.suite.logfile, 'w') as log:
            ppfiles = self.atmos.pp_to_archive(log, False)
        mock_getfiles.assert_called_once_with('WorkDir', mock.ANY, '.arch')
        self.assertListEqual(ppfiles, [fnfull + '.pp'])

    @mock.patch('housekeeping.get_marked_files')
    def test_archive_pp_non_existent(self, mock_getfiles):
        '''Test do_archive - pp files list - file non-existent'''
        func.logtest('Assert pp files list for do_archive - file non existent:')
        self.atmos.naml.archiving.archive_pp = True
        mock_getfiles.return_value = ['FileNotHere']

        with open(self.atmos.suite.logfile, 'w') as log:
            ppfiles = self.atmos.pp_to_archive(log, False)

        self.assertListEqual(ppfiles, [])
        self.assertIn('{}/FileNotHere does not exist'.format(os.getcwd()),
                      func.capture('err'))

    @mock.patch('housekeeping.get_marked_files')
    @mock.patch('housekeeping.convert_to_pp')
    def test_archive_pp_finalcycle(self, mock_convpp, mock_getfiles):
        '''Test do_archive - pp files list on final cycle, pre-conversion ON'''
        func.logtest('Assert final cycle pp files list created for do_archive:')
        self.atmos.naml.archiving.archive_pp = True
        mock_getfiles.return_value = self.ffiles[1:]
        mock_convpp.side_effect = [fn + '.pp' for fn in self.ffiles[1:]]

        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('validation.verify_header', return_value=True):
                with open(self.atmos.suite.logfile, 'w') as log:
                    ppfiles = self.atmos.pp_to_archive(log, True)

        self.assertListEqual(ppfiles, [fn + '.pp' for fn in self.ffiles[1:]])
        mock_getfiles.assert_called_once_with(os.getcwd(), mock.ANY, '')
        for fname in self.ffiles[1:]:
            fnfull = os.path.join(os.getcwd(), fname)
            self.assertIn(mock.call(fnfull, mock.ANY, True),
                          mock_convpp.mock_calls)

    @mock.patch('housekeeping.get_marked_files')
    def test_archive_pp_off(self, mock_getfiles):
        '''Test do_archive - pp files list, namelist switch = False'''
        func.logtest('Assert final pp files for do_archive - switch=False:')
        self.atmos.naml.archiving.archive_pp = False
        with open(self.atmos.suite.logfile, 'w') as log:
            ppfiles = self.atmos.pp_to_archive(log, False)
        self.assertListEqual(ppfiles, [])
        self.assertListEqual(mock_getfiles.mock_calls, [])

    @mock.patch('housekeeping.get_marked_files')
    @mock.patch('housekeeping.convert_to_pp')
    def test_archive_pp_convert_sel(self, mock_convpp, mock_getfiles):
        '''Test do_archive - pp files list - selected pre-conversion to pp'''
        func.logtest('Assert pp files list for do_archive - some pre-convert:')
        self.atmos.naml.archiving.archive_pp = True

        self.atmos.convpp_streams = '^d-f^1'
        mock_getfiles.return_value = self.ffiles[1:]
        mock_convpp.side_effect = [fn + '.pp' for fn in self.ffiles[1:]]

        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('validation.verify_header', return_value=True):
                with open(self.atmos.suite.logfile, 'w') as log:
                    _ = self.atmos.pp_to_archive(log, False)

        mock_getfiles.assert_called_once_with('WorkDir', mock.ANY, '.arch')
        for fname in self.ffiles[1:]:
            fnfull = os.path.join(os.getcwd(), fname)
            func.logtest('Testing filename: ' + fnfull)
            if fname == self.ffiles[-1]:
                self.assertNotIn(mock.call(fnfull, mock.ANY, False),
                                 mock_convpp.mock_calls)
            else:
                self.assertIn(mock.call(fnfull, mock.ANY, False),
                              mock_convpp.mock_calls)

    @mock.patch('housekeeping.get_marked_files')
    @mock.patch('housekeeping.convert_to_pp')
    def test_archive_pp_convert_none(self, mock_convpp, mock_getfiles):
        '''Test do_archive - pp files list - no conversion to pp'''
        func.logtest('Assert pp files list for do_archive - ppconvert:')
        self.atmos.naml.archiving.archive_pp = True
        self.atmos.convpp_streams = '^a-z'
        mock_getfiles.return_value = self.ffiles[1:]

        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('validation.verify_header', return_value=True):
                with open(self.atmos.suite.logfile, 'w') as log:
                    ppfiles = self.atmos.pp_to_archive(log, False)

        self.assertListEqual(ppfiles, [os.path.join(os.getcwd(), fn) for
                                       fn in self.ffiles[1:]])
        mock_getfiles.assert_called_once_with('WorkDir', mock.ANY, '.arch')
        self.assertListEqual(mock_convpp.mock_calls, [])


class PropertyTests(unittest.TestCase):
    '''Unit tests relating to the atmosphere property methods'''
    def setUp(self):
        self.atmos = atmos.AtmosPostProc()
        self.atmos.suite = mock.Mock()
        self.atmos.naml.archiving = atmosNamelist.Archiving()

    def tearDown(self):
        for fname in ['atmospp.nl']:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_convpp_single(self):
        '''Test _convpp_streams calculation of regular expression - single'''
        func.logtest('Assert _convpp_streams calculation of regex - single:')
        self.atmos.naml.archiving.archive_as_fieldsfiles = 'a'
        self.assertEqual(self.atmos._convpp_streams, '^a')

    def test_convpp_list(self):
        '''Test _convpp_streams calculation of regular expression - single'''
        func.logtest('Assert _convpp_streams calculation of regex - single:')
        self.atmos.naml.archiving.archive_as_fieldsfiles = ['a', '1-2']
        self.assertEqual(self.atmos._convpp_streams, '^a^1-2')

    def test_convpp_all(self):
        '''Test _convpp_streams calculation of regular expression - single'''
        func.logtest('Assert _convpp_streams calculation of regex - single:')
        for value in [None, '']:
            self.atmos.naml.archiving.archive_as_fieldsfiles = value
            self.assertEqual(self.atmos._convpp_streams, 'a-z1-9')

    def test_streams_property(self):
        '''Test the return value of the streams property'''
        func.logtest('Assert return value of the streams property:')
        self.assertEqual(self.atmos.naml.archiving.process_streams, None)
        self.assertEqual(self.atmos.streams, '1-9a-lp-rt-xz')
        self.atmos.naml.archiving.process_streams = 'at-z'
        self.assertEqual(self.atmos.streams, 'at-z')

    def test_means_property(self):
        '''Test the return value of the means property'''
        func.logtest('Assert return value of the means property:')
        self.assertEqual(self.atmos.naml.archiving.process_means, None)
        self.assertEqual(self.atmos.means, 'msy')
        self.atmos.naml.archiving.process_means = 'at-z'
        self.assertEqual(self.atmos.means, 'at-z')

    @mock.patch('atmos.suite.SuiteEnvironment')
    def test_ff_pattern(self, mock_suite):
        '''Test the fieldsfile regular expression'''
        func.logtest('Assert correct return of fields file regex:')

        atmos.utils.loadEnv = mock.Mock()
        mock_suite().finalcycle = False
        mock_suite().prefix = 'RUNID'
        atmos.AtmosPostProc._directory = mock.Mock(return_value='ModelDir')
        with mock.patch('atmos.AtmosPostProc.runpp',
                        new_callable=mock.PropertyMock,
                        return_value=True):
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
