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
from collections import OrderedDict
import mock

import testing_functions as func
import runtime_environment

# Import of suite requires 'RUNID' from runtime environment
runtime_environment.setup_env()
import suite


class SuiteTests(unittest.TestCase):
    '''Unit tests for the SuiteEnvironment class'''
    def setUp(self):
        self.inputnl = OrderedDict([
            ('&suitegen', None),
            ('umtask_name="atmos"', 'umtask'),
            ('prefix="RUNID"', 'prefix'),
            ('archive_command="Moose"', None),
            ('/', None),
            ('&moose_arch', None),
            ('archive_set="SUITENAME"\n/', None),
            ])
        self.myfile = 'input.nl'
        open(self.myfile, 'w').write('\n'.join(self.inputnl.keys()))
        self.mypath = 'somePath/directory'
        self.mysuite = suite.SuiteEnvironment(self.mypath, self.myfile)

    def tearDown(self):
        for fname in [self.myfile] + runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_suite_object(self):
        '''Test creation of suite object and assertion of Cylc6 environment'''
        func.logtest('Assert creation of a suite object:')
        self.assertEqual(self.mysuite.sourcedir, self.mypath)
        self.assertIn('CYLC_TASK_LOG_ROOT', self.mysuite.envars.keys())
        self.assertTrue(isinstance(self.mysuite.cyclepoint,
                                   suite.utils.CylcCycle))
        self.assertEqual(self.mysuite.cyclepoint.startcycle['iso'],
                         os.environ['CYLC_TASK_CYCLE_POINT'])
        self.assertEqual(
            '{:0>4}{:0>2}{:0>2}T{:0>2}{:0>2}Z'.format(*self.mysuite.initpoint),
            os.environ['CYLC_SUITE_INITIAL_CYCLE_POINT']
            )

    def test_suite_object_cycle_overrides(self):
        '''Test creation of suite object and assertion of Cylc6 environment'''
        func.logtest('Assert creation of a suite object with cycle overrides:')
        with mock.patch.dict('suite.os.environ',
                             {'CYCLEPOINT_OVERRIDE': '11112233T4455Z',
                              'INITCYCLE_OVERRIDE': '00060708T0910Z'}):
            mysuite = suite.SuiteEnvironment(self.mypath, self.myfile)
            self.assertEqual(mysuite.cyclepoint.startcycle['strlist'],
                             ['1111', '22', '33', '44', '55'])
        self.assertEqual(
            '{:0>4}{:0>2}{:0>2}T{:0>2}{:0>2}Z'.format(*mysuite.initpoint),
            '00060708T0910Z'
            )

    def test_suite_object_blank_file(self):
        '''Test creation of suite object with a blank namelist file'''
        func.logtest('Attempt to create suite obj with blank namelist file:')
        blank = 'blankfile.nl'
        open(blank, 'w').close()
        with self.assertRaises(SystemExit):
            suite.SuiteEnvironment(self.mypath, blank)
        os.remove(blank)

    def test_properties(self):
        '''Test access to suite properties'''
        func.logtest('Assert suite properties:')
        names = {x.split('=')[0]: [x.split('=')[1].strip('\n/').strip('"\''),
                                   self.inputnl[x]]
                 for x in self.inputnl.keys() if self.inputnl[x]}
        for key in names:
            self.assertEqual(str(getattr(self.mysuite,
                                         names[key][1])).strip('[]'),
                             names[key][0])

    def test_log(self):
        '''Test creation of and access to property "logfile"'''
        func.logtest('Create a log file:')
        logfile = os.getcwd() + '/job-archive.log'
        self.assertEqual(self.mysuite.logfile, logfile)

    def test_monthlength_360d(self):
        '''Test return of month length in days - 360d calendar'''
        func.logtest('Test the monthlength method - 360d calendar:')
        for month in range(1, 12):
            length = self.mysuite.monthlength(month)
            self.assertEqual(length, 30)

    def test_monthlength_365d(self):
        '''Test return of month length in days - 365d calendar'''
        func.logtest('Test the monthlength method - 365d calendar:')
        with mock.patch('modeltemplate.utils.calendar',
                        return_value='365day'):
            self.assertEqual(self.mysuite.monthlength('01'), 31)
            self.assertEqual(self.mysuite.monthlength('02'), 28)
            self.assertEqual(self.mysuite.monthlength('03'), 31)
            self.assertEqual(self.mysuite.monthlength('04'), 30)

    def test_monthlength_gregorian(self):
        '''Test return of month length in days - Gregorian calendar'''
        func.logtest('Test the monthlength method - Gregorian calendar:')
        # Cycle time (from runtime_environment) = 2000,1,21,0,0,0
        with mock.patch('modeltemplate.utils.calendar',
                        return_value='gregorian'):
            self.assertEqual(
                self.mysuite.cyclepoint.startcycle['intlist'][0] % 4, 0
                )
            self.assertEqual(
                self.mysuite.cyclepoint.startcycle['intlist'][0] % 100, 0
                )
            self.assertEqual(self.mysuite.monthlength('01'), 31)
            self.assertEqual(self.mysuite.monthlength('02'), 29)
            self.assertEqual(self.mysuite.monthlength('03'), 31)
            self.assertEqual(self.mysuite.monthlength('04'), 30)


class ArchiveTests(unittest.TestCase):
    '''Unit tests for the model-independent archiving method'''
    def setUp(self):
        runtime_environment.setup_env()
        self.logfile = os.environ['CYLC_TASK_LOG_ROOT'] + '-archive.log'
        self.mysuite = suite.SuiteEnvironment('somePath/directory', 'input.nl')

    def tearDown(self):
        for fname in [self.logfile] + runtime_environment.RUNTIME_FILES:
            if os.path.exists(fname):
                os.remove(fname)

    def test_archive_file(self):
        '''Test archive_file command - moo is mocked out'''
        func.logtest('File archiving - success:')
        with mock.patch('moo.archive_to_moose', return_value=0) as dummy:
            rcode = self.mysuite.archive_file('TestFile')
            self.assertEqual(rcode, 0)
            self.assertIn('TestFile ARCHIVE OK',
                          open(self.mysuite.logfile, 'r').read())
            self.assertTrue(self.mysuite.archive_ok)
            dummy.assert_called_once_with(
                'TestFile', 'TESTP', 'somePath/directory',
                self.mysuite.nl_arch, False
                )

    def test_archive_file_fail(self):
        '''Test failure mode of archive_file command - moo is mocked out'''
        func.logtest('File archiving - failure:')
        with mock.patch('moo.archive_to_moose', return_value=-1) as dummy:
            rcode = self.mysuite.archive_file('TestFile')
            self.assertNotEqual(rcode, 0)
            self.assertIn('TestFile ARCHIVE FAILED',
                          open(self.mysuite.logfile, 'r').read())
            self.assertFalse(self.mysuite.archive_ok)

    def test_archive_empty_file_moo(self):
        '''Test attempt to archive an empty file - moo is mocked out'''
        func.logtest('File archiving - Empty file:')
        with mock.patch('moo.archive_to_moose', return_value=11) as dummy:
            rcode = self.mysuite.archive_file('TestFile')
            self.assertEqual(rcode, 0)
            self.assertIn('TestFile FILE NOT ARCHIVED',
                          open(self.mysuite.logfile, 'r').read())
            self.assertTrue(self.mysuite.archive_ok)

    def test_archive_file_debug(self):
        '''Test debug mode of archive_file command with no file handle'''
        func.logtest('File archiving - debug:')
        with mock.patch('suite.utils.get_debugmode', return_value=True):
            rcode = self.mysuite.archive_file('TestFile')
        self.assertEqual(rcode, 0)
        log = open(self.mysuite.logfile, 'r').read()
        self.assertIn('TestFile WOULD BE ARCHIVED', log)

    def test_archive_debug_open_log(self):
        '''Test debug mode of archive_file command with open file handle'''
        func.logtest('File archiving - log using open file:')
        logfile = 'OpenLog'
        with mock.patch('suite.utils.get_debugmode', return_value=True):
            with open(logfile, 'w') as fname:
                rcode = self.mysuite.archive_file('TestFile', logfile=fname)
        self.assertEqual(rcode, 0)
        self.assertIn('TestFile WOULD BE ARCHIVED', open(logfile, 'r').read())
        self.assertFalse(os.path.exists(self.logfile))
        os.remove(logfile)

    def test_no_archive_command(self):
        '''Test attempt to archive to alternative system'''
        func.logtest('Attempt to access alternative archiving system:')
        self.mysuite.naml.archive_command = 'Dummy'
        with self.assertRaises(SystemExit):
            self.mysuite.archive_file('TestFile')


class PreProcessTests(unittest.TestCase):
    '''Unit tests for the model-independent pre-processing methods'''
    def setUp(self):
        runtime_environment.setup_env()
        self.mysuite = suite.SuiteEnvironment('somePath/directory', 'input.nl')

    def tearDown(self):
        pass

    def test_preprocess_file_nccopy(self):
        '''Test preprocess_file command'''
        func.logtest('File pre-processing - select nccopy:')
        with mock.patch('suite.SuiteEnvironment.preproc_nccopy') as mock_cmd:
            self.mysuite.preprocess_file('nccopy', 'File',
                                         arg1='ARG1', arg2='ARG2')
            mock_cmd.assert_called_with('File', arg1='ARG1', arg2='ARG2')

    def test_preproc_file_select_fail(self):
        '''Test preprocess_file command failure mode'''
        func.logtest('File pre-processing - selection failure:')
        with self.assertRaises(SystemExit):
            self.mysuite.preprocess_file('utility', 'File', arg1='ARG1')

    def test_nccopy(self):
        '''Test file compression with nccopy'''
        func.logtest('Assert function of file compression with nccopy:')
        infile = 'TestDir/myMean'
        cmd = ' '.join(['nccopy -d 5 -c a/1,b/2,c/3',
                        infile, infile + '.tmp'])
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            with mock.patch('suite.os.rename') as mock_mv:
                mock_exec.return_value = (0, '')
                self.mysuite.preproc_nccopy(infile, compression=5,
                                            chunking=['a/1', 'b/2', 'c/3'])
                mock_mv.assert_called_with(infile + '.tmp', infile)
            mock_exec.assert_called_with(cmd)

    def test_nccopy_complete_path(self):
        '''Test file compression with nccopy (complete path given)'''
        func.logtest('Assert function of nccopy method given full path:')
        infile = 'TestDir/myMean'
        cmd = ' '.join(['PATH/nccopy -d 5 -c a/1,b/2,c/3',
                        infile, infile + '.tmp'])
        self.mysuite.naml.nccopy_path = 'PATH/nccopy'
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            with mock.patch('suite.os.rename') as mock_mv:
                mock_exec.return_value = (0, '')
                self.mysuite.preproc_nccopy(infile, compression=5,
                                            chunking=['a/1', 'b/2', 'c/3'])
                mock_mv.assert_called_with(infile + '.tmp', infile)
            mock_exec.assert_called_with(cmd)

    def test_nccopy_fail(self):
        '''Test file compression with nccopy'''
        func.logtest('Assert function of file compression with nccopy:')
        infile = 'TestDir/myMean'
        cmd = ' '.join(['nccopy -d 5 -c a/1,b/2,c/3',
                        infile, infile + '.tmp'])
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, '')
            with self.assertRaises(SystemExit):
                _ = self.mysuite.preproc_nccopy(infile, compression=5,
                                                chunking=['a/1', 'b/2', 'c/3'])
            mock_exec.assert_called_with(cmd)
        self.assertIn('Compression failed', func.capture('err'))

    def test_nccopy_rename_fail(self):
        '''Test file compression with nccopy - fail rename'''
        func.logtest('Assert file compression with nccopy - failure to rename:')
        infile = 'TestDir/myMean'
        cmd = ' '.join(['nccopy -d 5 -c a/1,b/2,c/3',
                        infile, infile + '.tmp'])
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            with self.assertRaises(SystemExit):
                _ = self.mysuite.preproc_nccopy(infile, compression=5,
                                                chunking=['a/1', 'b/2', 'c/3'])
            mock_exec.assert_called_with(cmd)
        self.assertIn('Failed to rename', func.capture('err'))

    @mock.patch('suite.os.rename')
    def test_nccopy_fail_debug(self, mock_rename):
        '''Test file compression with nccopy - debug failure'''
        func.logtest('Assert file compression with nccopy - debug failure:')
        infile = 'TestDir/myMean'
        cmd = ' '.join(['nccopy -d 5 -c a/1,b/2,c/3',
                        infile, infile + '.tmp'])
        with mock.patch('suite.utils.get_debugmode', return_value=True):
            with mock.patch('suite.utils.exec_subproc') as mock_exec:
                mock_exec.return_value = (1, '')
                rtn = self.mysuite.preproc_nccopy(
                    infile, compression=5, chunking=['a/1', 'b/2', 'c/3']
                    )
                mock_exec.assert_called_with(cmd)
        self.assertListEqual(mock_rename.mock_calls, [])
        self.assertIn('Compression failed', func.capture('err'))
        self.assertEqual(rtn, 1)

    def test_nccopy_rename_fail_debug(self):
        '''Test file compression with nccopy - rename failure debug'''
        func.logtest('Assert file compression with nccopy - rename fail debug:')
        infile = 'TestDir/myMean'
        cmd = ' '.join(['nccopy -d 5 -c a/1,b/2,c/3',
                        infile, infile + '.tmp'])
        with mock.patch('suite.utils.get_debugmode', return_value=True):
            with mock.patch('suite.utils.exec_subproc') as mock_exec:
                mock_exec.return_value = (0, '')
                rtn = self.mysuite.preproc_nccopy(
                    infile, compression=5, chunking=['a/1', 'b/2', 'c/3']
                    )
                mock_exec.assert_called_with(cmd)
        self.assertIn('Failed to rename', func.capture('err'))
        self.assertEqual(rtn, 99)

    def test_ncdump(self):
        '''Test call to ncdump utility'''
        func.logtest('Assert call to ncdump file utility:')
        infile = 'TestDir/myFile'
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, 'NCDUMP output')
            rtn = self.mysuite.preproc_ncdump(infile, h='')
            mock_exec.assert_called_with('ncdump -h  TestDir/myFile')
        self.assertEqual('NCDUMP output', rtn)

    def test_ncdump_path(self):
        '''Test call to ncdump utility with util path provided'''
        func.logtest('Assert call to ncdump file utility - path provided:')
        infile = 'TestDir/myFile'
        self.mysuite.naml.ncdump_path = 'path/to/ncutils'
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            self.mysuite.preproc_ncdump(infile)
            cmdstring = 'path/to/ncutils/ncdump TestDir/myFile'
            mock_exec.assert_called_with(cmdstring)

    def test_ncdump_fail(self):
        '''Test call to ncdump utility - failure'''
        func.logtest('Assert failure in call to ncdump file utility:')
        infile = 'TestDir/myFile'
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, 'I failed')
            with self.assertRaises(SystemExit):
                self.mysuite.preproc_ncdump(infile, h='')
            mock_exec.assert_called_with('ncdump -h  TestDir/myFile')
        self.assertIn('I failed', func.capture('err'))

    def test_ncrcat(self):
        '''Test call to ncrcat utility'''
        func.logtest('Assert call to ncrcat file utility:')
        infiles = ['INfile1', 'INfile2']
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            self.mysuite.preproc_ncrcat(infiles, outfile='OUTfile')
            mock_exec.assert_called_with('ncrcat INfile1 INfile2 OUTfile')
        self.assertIn('ncrcat: Command successful', func.capture())

    def test_ncrcat_args(self):
        '''Test call to ncrcat utility - additional arguments'''
        func.logtest('Assert call to ncrcat file utility - added args:')
        infiles = ['INfile1', 'INfile2']
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            self.mysuite.preproc_ncrcat(infiles, k='val', outfile='OUTfile')
            mock_exec.assert_called_with(
                'ncrcat -k val INfile1 INfile2 OUTfile'
                )
        self.assertIn('ncrcat: Command successful', func.capture())

    def test_ncrcat_path(self):
        '''Test call to ncrcat utility with util path provided'''
        func.logtest('Assert call to ncrcat file utility - path provided:')
        infiles = ['INfile1', 'INfile2']
        self.mysuite.naml.ncrcat_path = 'path/to/ncutils'
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            self.mysuite.preproc_ncrcat(infiles, outfile='OUTfile')
            cmdstring = 'path/to/ncutils/ncrcat INfile1 INfile2 OUTfile'
            mock_exec.assert_called_with(cmdstring)

    def test_ncrcat_cmd_failure(self):
        '''Test call to ncrcat utility - command failure'''
        func.logtest('Assert failure in call to ncrcat file utility:')
        infiles = ['INfile1', 'INfile2']
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, 'I failed')
            with self.assertRaises(SystemExit):
                self.mysuite.preproc_ncrcat(infiles, outfile='OUTfile')
            mock_exec.assert_called_with('ncrcat INfile1 INfile2 OUTfile')
        self.assertIn('I failed', func.capture('err'))

    def test_ncrcat_no_outfile(self):
        '''Test call to ncrcat utility - no outfile'''
        func.logtest('Assert call to ncrcat file utility - no outfile:')
        infiles = ['INfile1', 'INfile2']
        with self.assertRaises(SystemExit):
            self.mysuite.preproc_ncrcat(infiles, kwarg='KWARG')
        self.assertIn('ncrcat: Cannot continue', func.capture('err'))

    def test_ncks(self):
        '''Test file manipulation with ncks'''
        func.logtest('Assert function of file manipulation with ncks:')
        infile = 'TestDir/myFile'
        cmd = ' '.join(['ncks -O  -a  -d x,1,2 -d y,1,2',
                        infile, infile + '.tmp'])
        self.mysuite.naml.ncks_path = ''
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            with mock.patch('suite.os.rename') as mock_mv:
                mock_exec.return_value = (0, '')
                self.mysuite.preproc_ncks(infile, O='', a='',
                                          d_1='x,1,2', d_2='y,1,2')
                mock_mv.assert_called_with(infile + '.tmp', infile)
            mock_exec.assert_called_with(cmd)

    def test_ncks_complete_path(self):
        '''Test file manipulation with ncks (complete path given)'''
        func.logtest('Assert function of ncks method given full path:')
        infile = 'TestDir/myFile'
        cmd = ' '.join(['PATH/ncks -O  -a  -d x,1,2 -d y,1,2',
                        infile, infile + '.tmp'])
        self.mysuite.naml.ncks_path = 'PATH/ncks'
        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            with mock.patch('suite.os.rename') as mock_mv:
                mock_exec.return_value = (0, '')
                self.mysuite.preproc_ncks(infile, O='', a='',
                                          d_1='x,1,2', d_2='y,1,2')
                mock_mv.assert_called_with(infile + '.tmp', infile)
            mock_exec.assert_called_with(cmd)

    def test_ncks_fail(self):
        '''Test file manipulation with ncks'''
        func.logtest('Assert function of file manipulation with ncks:')
        infile = 'TestDir/myFile'
        cmd = ' '.join(['ncks -O  -a  -d x,1,2 -d y,1,2',
                        infile, infile + '.tmp'])
        self.mysuite.naml.ncks_path = ''

        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, '')
            with self.assertRaises(SystemExit):
                _ = self.mysuite.preproc_ncks(infile, O='', a='',
                                              d_1='x,1,2', d_2='y,1,2')
            mock_exec.assert_called_with(cmd)
        self.assertIn('ncks: Command failed:', func.capture('err'))

    def test_ncks_rename_fail(self):
        '''Test file manipulation with ncks - fail rename'''
        func.logtest('Assert file manipulation with ncks - failure to rename:')
        infile = 'TestDir/myFile'
        cmd = ' '.join(['ncks -O  -a  -d x,1,2 -d y,1,2',
                        infile, infile + '.tmp'])
        self.mysuite.naml.ncks_path = ''

        with mock.patch('suite.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            with self.assertRaises(SystemExit):
                _ = self.mysuite.preproc_ncks(infile, O='', a='',
                                              d_1='x,1,2', d_2='y,1,2')
            mock_exec.assert_called_with(cmd)
        self.assertIn('Failed to rename', func.capture('err'))

    @mock.patch('suite.os.rename')
    def test_ncks_fail_debug(self, mock_rename):
        '''Test file manipulation with ncks - debug failure'''
        func.logtest('Assert file manipulation with ncks - debug failure:')
        infile = 'TestDir/myFile'
        cmd = ' '.join(['ncks -d x,1,2 -d y,1,2', infile, infile + '.tmp'])
        self.mysuite.naml.ncks_path = ''

        with mock.patch('suite.utils.get_debugmode', return_value=True):
            with mock.patch('suite.utils.exec_subproc') as mock_exec:
                mock_exec.return_value = (1, '')
                rtn = self.mysuite.preproc_ncks(infile,
                                                d_1='x,1,2', d_2='y,1,2')
                mock_exec.assert_called_with(cmd)
        self.assertListEqual(mock_rename.mock_calls, [])
        self.assertIn('Command failed:', func.capture('err'))
        self.assertTupleEqual(rtn, (1, ''))

    def test_ncks_rename_fail_debug(self):
        '''Test file manipulation with ncks - rename failure debug'''
        func.logtest('Assert file manipulation with ncks - rename fail debug:')
        infile = 'TestDir/myFile'
        cmd = ' '.join(['ncks -d x,1,2 -d y,1,2', infile, infile + '.tmp'])
        self.mysuite.naml.ncks_path = ''

        with mock.patch('suite.utils.get_debugmode', return_value=True):
            with mock.patch('suite.utils.exec_subproc') as mock_exec:
                mock_exec.return_value = (0, '')
                rtn = self.mysuite.preproc_ncks(infile,
                                                d_1='x,1,2', d_2='y,1,2')
                mock_exec.assert_called_with(cmd)
        self.assertIn('Failed to rename', func.capture('err'))
        self.assertTupleEqual(rtn, (99, ''))
