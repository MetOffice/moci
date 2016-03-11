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
import mock
from collections import OrderedDict
import sys

import runtimeEnvironment
import testing_functions as func
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'common'))
import suite


class SuiteTests(unittest.TestCase):
    '''Unit tests for the SuiteEnvironment class'''
    def setUp(self):
        if 'pre_cylc6' in self.id():
            os.environ['CYLC_TASK_CYCLE_TIME'] = '1980090100'
        else:
            os.environ['CYLC_TASK_CYCLE_POINT'] = '19800901T0000Z'
        self.inputnl = OrderedDict([
            ('&suitegen', None),
            ('archive_set="SUITENAME"', 'suitename'),
            ('umtask_name="atmos"', 'umtask'),
            ('prefix="RUNID"', 'prefix'),
            ('cycleperiod=0, 1, 10, 0, 0', 'cycleperiod'),
            ('tasks_per_cycle=2', 'tasks_per_cycle'),
            ('archive_command="Moose"', None),
            ('/', None),
            ])
        self.myfile = 'input.nl'
        open(self.myfile, 'w').write('\n'.join(self.inputnl.keys()))
        self.mypath = 'somePath/directory'
        self.mysuite = suite.SuiteEnvironment(self.mypath, self.myfile)

    def tearDown(self):
        for fname in ['atmospp.nl', self.myfile]:
            try:
                os.remove(fname)
            except OSError:
                pass
        for var in ['CYLC_TASK_CYCLE_POINT', 'CYLC_TASK_CYCLE_TIME',
                    'ARCHIVE_FINAL']:
            try:
                del os.environ[var]
            except KeyError:
                pass

    def test_suite_object(self):
        '''Test creation of suite object and assertion of Cylc6 environment'''
        func.logtest('Assert creation of a suite object:')
        self.assertEqual(self.mysuite.sourcedir, self.mypath)
        self.assertTrue(hasattr(self.mysuite.envars, 'CYLC_TASK_LOG_ROOT'))
        self.assertTrue(self.mysuite.cylc6)

    def test_pre_cylc6_suite(self):
        '''Test assertion of pre-Cylc6 environment'''
        func.logtest('Assert pre-Cylc6 suite creation:')
        self.assertFalse(self.mysuite.cylc6)
        self.assertTrue(hasattr(self.mysuite.envars, 'CYLC_TASK_CYCLE_TIME'))

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
        names = {x.split('=')[0]: [x.split('=')[1].strip('"\''),
                                   self.inputnl[x]]
                 for x in self.inputnl.keys() if self.inputnl[x]}
        for key in names:
            self.assertEqual(str(getattr(self.mysuite,
                                         names[key][1])).strip('[]'),
                             names[key][0])

    def test_cyclestring(self):
        '''Test calculation of property "cyclestring in a Cylc6 environment"'''
        func.logtest('Assert cycletime as string array property:')
        self.assertTupleEqual(self.mysuite.cyclestring,
                              ('1980', '09', '01', '00', '00'))

    def test_pre_cylc6_cyclestring(self):
        '''Test calculation of property "cyclestring; pre-Cylc6 environment"'''
        func.logtest('Assert pre-Cylc6 cycletime as string array property:')
        self.assertTupleEqual(self.mysuite.cyclestring,
                              ('1980', '09', '01', '00'))

    def test_cycledt(self):
        '''Test access to property "cycledt"'''
        func.logtest('Assert cycletime as integer array property:')
        self.assertListEqual(self.mysuite.cycledt, [1980, 9, 1, 0, 0])

    def test_bad_cycletime(self):
        '''Test failure mode with incorrect format for
        task cycle time environment variable'''
        func.logtest('Failure mode of cycletime property:')
        self.mysuite.envars.CYLC_TASK_CYCLE_POINT = 'Dummy'
        with self.assertRaises(SystemExit):
            print self.mysuite.cyclestring

    def test_existing_cyclestring(self):
        '''Test access to previously calculated property "cyclestring"'''
        func.logtest('Retrieval existing cycle time string array:')
        mycycle = ('1981', '09', '01', '00', '00')
        self.mysuite._cyclestring = mycycle
        self.assertTupleEqual(self.mysuite.cyclestring, mycycle)

    def test_final_cycle(self):
        '''Test assertion of final cycle in Cylc6 environment'''
        func.logtest('Assert final cycle time property - TRUE:')
        os.environ['ARCHIVE_FINAL'] = 'true'
        self.assertTrue(self.mysuite.finalcycle)

    def test_not_final_cycle(self):
        '''Test negative assertion of final cycle in Cylc6 environment'''
        func.logtest('Assert final cycle time property - FALSE:')
        self.assertFalse(self.mysuite.finalcycle)

    def test_pre_cylc6_final_cycle(self):
        '''Test assertion of final cycle in pre-Cylc6 environment'''
        func.logtest('Assert pre-Cylc6 final cycle time property - TRUE:')
        os.environ['END_CYCLE_TIME'] = '1985090100'
        self.mysuite._cyclestring = ('1985', '09', '01', '00')
        self.assertTrue(self.mysuite.finalcycle)

    def test_pre_cylc6_not_final_cycle(self):
        '''Test negative assertion of final cycle in pre-Cylc6 environment'''
        func.logtest('Assert pre-Cylc6 final cycle time property - FALSE:')
        os.environ['END_CYCLE_TIME'] = '1985090100'
        self.assertFalse(self.mysuite.finalcycle)

    def test_existing_final_cycle(self):
        '''Test previously asserted final cycle'''
        func.logtest('Retrieval of existing final cycle time logical:')
        mycycle = ('2000', '09', '01', '00', '00')
        self.mysuite._finalcycle = mycycle
        self.assertTupleEqual(self.mysuite.finalcycle, mycycle)

    def test_log(self):
        '''Test creation of and access to property "logfile"'''
        func.logtest('Create a log file:')
        logfile = os.path.join(os.environ['PWD'], 'job-archive.log')
        self.assertEqual(self.mysuite.logfile, logfile)


class ArchiveTests(unittest.TestCase):
    '''Unit tests for the model-independent archiving method'''
    def setUp(self):
        os.environ['CYLC_TASK_LOG_ROOT'] = os.environ['PWD'] + '/job'
        self.logfile = os.environ['CYLC_TASK_LOG_ROOT'] + '-archive.log'
        os.environ['CYLC_TASK_CYCLE_POINT'] = '19800901T0000Z'
        self.mysuite = suite.SuiteEnvironment('somePath/directory', 'input.nl')

    def tearDown(self):
        for fname in ['input.nl', self.logfile]:
            if os.path.exists(fname):
                os.remove(fname)

    def test_archive_file(self):
        '''Test archive_file command - moo is mocked out'''
        func.logtest('File archiving - success:')
        with mock.patch('moo.CommandExec') as dummy:
            moose_arch_inst = dummy.return_value
            moose_arch_inst.execute.return_value = {'TestFile': 0}
            rcode = self.mysuite.archive_file('TestFile')
            self.assertEqual(rcode, 0)
            self.assertIn('TestFile ARCHIVE OK',
                          open(self.mysuite.logfile, 'r').read())
            self.assertTrue(self.mysuite.archiveOK)

    def test_archive_file_fail(self):
        '''Test failure mode of archive_file command - moo is mocked out'''
        func.logtest('File archiving - failure:')
        with mock.patch('moo.CommandExec') as dummy:
            moose_arch_inst = dummy.return_value
            moose_arch_inst.execute.return_value = {'TestFile': -1}
            rcode = self.mysuite.archive_file('TestFile')
            self.assertNotEqual(rcode, 0)
            self.assertIn('TestFile ARCHIVE FAILED',
                          open(self.mysuite.logfile, 'r').read())
            self.assertFalse(self.mysuite.archiveOK)

    def test_archive_empty_file(self):
        '''Test attempt to archive an empty file - moo is mocked out'''
        func.logtest('File archiving - Empty file:')
        with mock.patch('moo.CommandExec') as dummy:
            moose_arch_inst = dummy.return_value
            moose_arch_inst.execute.return_value = {'TestFile': 11}
            rcode = self.mysuite.archive_file('TestFile')
            self.assertEqual(rcode, 11)
            self.assertIn('TestFile FILE NOT ARCHIVED',
                          open(self.mysuite.logfile, 'r').read())
            self.assertTrue(self.mysuite.archiveOK)

    def test_archive_file_debug(self):
        '''Test debug mode of archive_file command with no file handle'''
        func.logtest('File archiving - debug:')
        rcode = self.mysuite.archive_file('TestFile', debug=True)
        self.assertEqual(rcode, 0)
        log = open(self.mysuite.logfile, 'r').read()
        self.assertIn('TestFile WOULD BE ARCHIVED', log)

    def test_archive_debug_open_log(self):
        '''Test debug mode of archive_file command with open file handle'''
        func.logtest('File archiving - log using open file:')
        logfile = 'OpenLog'
        with open(logfile, 'w') as fname:
            rcode = self.mysuite.archive_file('TestFile', fname, True)
        self.assertEqual(rcode, 0)
        self.assertIn('TestFile WOULD BE ARCHIVED', open(logfile, 'r').read())
        self.assertFalse(os.path.exists(self.logfile))
        os.remove(logfile)

    def test_no_archive_command(self):
        '''Test attempt to archive to alternative system'''
        func.logtest('Attempt to access alternative archiving system:')
        self.mysuite.nl.archive_command = 'Dummy'
        with self.assertRaises(SystemExit):
            self.mysuite.archive_file('TestFile')


class PreProcessTests(unittest.TestCase):
    '''Unit tests for the model-independent pre-processing methods'''
    def setUp(self):
        os.environ['CYLC_TASK_LOG_ROOT'] = os.environ['PWD'] + '/job'
        os.environ['CYLC_TASK_CYCLE_POINT'] = '19800901T0000Z'
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
        with mock.patch('utils.exec_subproc') as mock_exec:
            with mock.patch('os.rename') as mock_mv:
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
        self.mysuite.nl.nccopy_path = 'PATH/nccopy'
        with mock.patch('utils.exec_subproc') as mock_exec:
            with mock.patch('os.rename') as mock_mv:
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
        with mock.patch('utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, '')
            with self.assertRaises(SystemExit):
                self.mysuite.preproc_nccopy(infile, compression=5,
                                            chunking=['a/1', 'b/2', 'c/3'])
            mock_exec.assert_called_with(cmd)

    def test_nccopy_rename_fail(self):
        '''Test file compression with nccopy'''
        func.logtest('Assert function of file compression with nccopy:')
        infile = 'TestDir/myMean'
        cmd = ' '.join(['nccopy -d 5 -c a/1,b/2,c/3',
                        infile, infile + '.tmp'])
        with mock.patch('utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            with self.assertRaises(SystemExit):
                self.mysuite.preproc_nccopy(infile, compression=5,
                                            chunking=['a/1', 'b/2', 'c/3'])
            mock_exec.assert_called_with(cmd)

    def test_ncdump(self):
        '''Test call to ncdump utility'''
        func.logtest('Assert call to ncdump file utility:')
        infile = 'TestDir/myFile'
        with mock.patch('utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, 'NCDUMP output')
            rtn = self.mysuite.preproc_ncdump(infile, h='')
            mock_exec.assert_called_with('ncdump -h  TestDir/myFile')
        self.assertEqual('NCDUMP output', rtn)

    def test_ncdump_path(self):
        '''Test call to ncdump utility with util path provided'''
        func.logtest('Assert call to ncdump file utility - path provided:')
        infile = 'TestDir/myFile'
        self.mysuite.nl.ncdump_path = 'path/to/ncutils'
        with mock.patch('utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (0, '')
            self.mysuite.preproc_ncdump(infile)
            cmdstring = 'path/to/ncutils/ncdump TestDir/myFile'
            mock_exec.assert_called_with(cmdstring)

    def test_ncdump_fail(self):
        '''Test call to ncdump utility - failure'''
        func.logtest('Assert failure in call to ncdump file utility:')
        infile = 'TestDir/myFile'
        with mock.patch('utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, 'I failed')
            with self.assertRaises(SystemExit):
                self.mysuite.preproc_ncdump(infile, h='')
            mock_exec.assert_called_with('ncdump -h  TestDir/myFile')
        self.assertIn('I failed', func.capture('err'))


def main():
    '''Main function'''
    unittest.main(buffer=True)


if __name__ == '__main__':
    main()
