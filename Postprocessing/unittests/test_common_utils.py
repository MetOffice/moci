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
import sys
import shutil
import mock

import testing_functions as func

import utils

DUMMY = ['fileone', 'filetwo', 'filethree']


class EnvironTests(unittest.TestCase):
    '''Unit tests for loading environment variables'''
    def setUp(self):
        self.loadvars = ('PWD', 'HOME')
        testname = self.shortDescription()
        self.envar = {}
        if 'Load one' in testname:
            self.envar[self.loadvars[0]] = utils.load_env(self.loadvars[0])
        else:
            for var in self.loadvars:
                self.envar[var] = utils.load_env(var)

    def test_load1(self):
        '''Test load one environment variable'''
        func.logtest('Load a single environment variable:')
        var = self.loadvars[0]
        self. assertEqual(self.envar[var], os.environ[var])

    def test_load2(self):
        '''Test load two environment variables'''
        func.logtest('Load two environment variables:')
        for var in self.loadvars:
            self.assertEqual(self.envar[var], os.environ[var])

    def test_append(self):
        '''Test load environment variables and append a further one'''
        func.logtest('Ability to append to environment variable list:')
        self.envar['DUMMYVAR'] = utils.load_env('DUMMYVAR')
        for var in self.loadvars:
            self.assertEqual(self.envar[var], os.environ[var])
        self.assertIsNone(self.envar['DUMMYVAR'])

    def test_not_found_exit(self):
        '''Attempt to load non-existent variable with a failure flag'''
        func.logtest('Failure mode of loadEnd (FAIL case):')
        with self.assertRaises(SystemExit):
            utils.load_env('DUMMYVAR', required=True)

class ExecTests(unittest.TestCase):
    '''Unit tests for exec_subproc method'''
    def setUp(self):
        self.cmd = 'echo Hello World!'

    def tearDown(self):
        try:
            os.remove('TestDir/MyFile')
        except OSError:
            pass
        try:
            os.rmdir('TestDir')
        except OSError:
            pass

    def test_success(self):
        '''Test shell out to subprocess command'''
        func.logtest('Shell out with simple echo command:')
        rcode, _ = utils.exec_subproc(self.cmd, verbose=False)
        self.assertEqual(rcode, 0)

    def test_list_success(self):
        '''test shell out with a list of commands'''
        func.logtest('Shell out with simple list as single command:')
        rcode, _ = utils.exec_subproc(self.cmd.split(), verbose=False)
        self.assertEqual(rcode, 0)

    def test_failed_exec(self):
        '''Test failure mode of exec_subproc with invalid arguments'''
        func.logtest('Attempt to shell out with invalid arguments:')
        _, output = utils.exec_subproc(self.cmd.replace('echo', 'ls'))
        # Code should catch exception: subprocess.CalledProcessError
        self.assertIn('no such file or directory', output.lower())

    def test_unknown_cmd(self):
        '''Test failure mode of exec_subproc with unknown command'''
        func.logtest('Attempt to shell out with unknown command:')
        rcode, _ = utils.exec_subproc(self.cmd.replace('echo', 'pumpkin'))
        # Code should catch exception: OSError
        self.assertEqual(rcode, 2)

    def test_multi_command(self):
        '''Test subprocess with consecutive commands'''
        func.logtest('Attempt to shell out with consecutive commands:')
        _, output = utils.exec_subproc(self.cmd.replace(' World',
                                                        '; echo World'))
        self.assertEqual(output.strip(), 'World!')

    def test_change_directory(self):
        '''Test subprocess with a change of working directory'''
        func.logtest('Attempt to shell out alternative working directory:')
        os.mkdir('TestDir')
        cmd = 'cd TestDir; echo Hello'
        _, output = utils.exec_subproc(cmd)
        # Code should catch exception: OSError
        self.assertEqual(output.strip(), 'Hello')

    def test_bad_multi_command(self):
        '''Test subprocess with consecutive commands'''
        func.logtest('Attempt to shell out with consecutive commands:')
        cmd = 'pumpkin "Hello\n"; echo "There"'
        rcode, _ = utils.exec_subproc(cmd)
        # Code should catch exception: OSError (RCode2 : No such directory)
        self.assertEqual(rcode, 2)

    def test_output(self):
        '''Test verbose output of exec_subproc'''
        func.logtest('Verbose output of subprocess command:')
        _, output = utils.exec_subproc(self.cmd)
        self.assertEqual(output.strip(), 'Hello World!')

    def test_command_path(self):
        '''Test exec_subproc functionality for running commands in
        an alternative location'''
        func.logtest('Subprocess command run in an alternative location:')
        os.mkdir('TestDir')
        open('TestDir/MyFile', 'w').close()
        rcode, output = utils.exec_subproc('ls', cwd='TestDir', verbose=False)
        self.assertEqual(rcode, 0)
        self.assertIn('MyFile', output)


class LogTests(unittest.TestCase):
    '''Unit tests for logging output messages'''
    def setUp(self):
        self.msg = 'Hello There'
        if not hasattr(sys.stdout, 'getvalue'):
            msg = 'This test requires buffered mode to run (buffer=True)'
            self.fail(msg)

    def tearDown(self):
        pass

    def test_msg(self):
        '''Test content of output message'''
        func.logtest('Verifying output message content.')
        utils.log_msg(self.msg)
        self.assertIn(self.msg, func.capture())

    def test_stdout(self):
        '''Test content of messages printed to stdout'''
        for lev in ['INFO', 'OK']:
            func.logtest('Send output to sys.stdout ({} case):'.
                         format(lev))
            utils.log_msg('', level=lev)
            self.assertIn(lev, func.capture())

    def test_stderr(self):
        '''Test content of messages printed to stderr'''
        with mock.patch('utils.get_debugmode', return_value=True):
            for lev in ['DEBUG', 'WARN', 'ERROR']:
                func.logtest('Send output to sys.stderr ({} case):'.
                             format(lev))
                utils.log_msg('', level=lev)
                self.assertIn(lev, func.capture(direct='err'))

    def test_fail(self):
        '''Test content of [FAIL] messages printed to stderr'''
        func.logtest('Send output to sys.stderr: (FAIL case):')
        for lev in ['ERROR', 'FAIL']:
            with self.assertRaises(SystemExit):
                utils.log_msg('', level=lev)
            self.assertIn(lev, func.capture(direct='err'))

    def test_key_err(self):
        '''Test KeyError exception handling for log_msg'''
        func.logtest('KeyError exception handling in output message:')
        utils.log_msg(self.msg, level='aaa')
        self.assertIn('[WARN]', func.capture(direct='err'))
        self.assertIn('Unknown', func.capture(direct='err'))


class DateCheckTests(unittest.TestCase):
    '''Unit test for date retrival'''
    def setUp(self):
        self.indate = [2004, 2, 15, 0, 0]
        self.delta = [0, 0, 20, 0, 30]

    def test_date_360(self):
        '''Test adding period to 360 day calendar date'''
        func.logtest('Cylc6 date manipulation with 360day calendar:')
        outdate = [2004, 3, 5, 0, 30]
        date = utils.add_period_to_date(self.indate, self.delta)
        self.assertListEqual(date, outdate)

    def test_date_gregorian(self):
        '''Test adding period to Gregorian date'''
        func.logtest('Cylc6 date manipulation with Gregorian calendar:')
        outdate = [2004, 3, 6, 0, 30]
        with mock.patch.dict('utils.os.environ',
                             {'CYLC_CYCLING_MODE': 'gregorian'}):
            date = utils.add_period_to_date(self.indate, self.delta)
        self.assertListEqual(date, outdate)

    def test_short_date(self):
        '''Test date input with short array'''
        func.logtest('Short array date input:')
        indate = self.indate[:2]

        outdate = [2004, 2, 21, 0, 30]
        date = utils.add_period_to_date(indate, self.delta)
        self.assertListEqual(date, outdate)

        with mock.patch.dict('utils.os.environ',
                             {'CYLC_CYCLING_MODE': 'gregorian'}):
            date = utils.add_period_to_date(indate, self.delta)
            self.assertListEqual(date, outdate)

    def test_zero_date(self):
        '''Test date input with zero date input'''
        func.logtest('All zeros date input:')
        date = utils.add_period_to_date([0]*5, self.delta)
        self.assertListEqual(date, self.delta)

    def test_negative_delta(self):
        '''Test new date with negative delta'''
        func.logtest('Assert negative delta date calculation:')
        delta = [0, -1, -20, 0, -30]
        outdate = [2003, 12, 24, 23, 30]
        date = utils.add_period_to_date(self.indate, delta)
        self.assertListEqual(date, outdate)

        delta = [0, -1, -20]
        outdate = [2003, 12, 26, 0, 0]
        with mock.patch.dict('utils.os.environ',
                             {'CYLC_CYCLING_MODE': 'gregorian'}):
            date = utils.add_period_to_date(self.indate, delta)
            self.assertListEqual(date, outdate)

    def test_bad_date(self):
        '''Test date input with bad date input'''
        func.logtest('Testing bad date input:')
        with self.assertRaises(SystemExit):
            _ = utils.add_period_to_date(['a']*5, self.delta)

    def test_string_delta(self):
        '''Test time delta in string format'''
        func.logtest('Assert calculation of delta from input string:')
        self.assertListEqual(utils.add_period_to_date([0]*5, '6HRS'),
                             [0, 0, 0, 6, 0])
        self.assertListEqual(utils.add_period_to_date([0]*5, 'day'),
                             [0, 0, 1, 0, 0])
        self.assertListEqual(utils.add_period_to_date([0]*5, '2mths'),
                             [0, 2, 0, 0, 0])
        self.assertListEqual(utils.add_period_to_date([0]*5, 'Season'),
                             [0, 3, 0, 0, 0])
        self.assertListEqual(utils.add_period_to_date([0]*5, '1y'),
                             [1, 0, 0, 0, 0])

    def test_bad_string_delta(self):
        '''Test date input with bad string delta input'''
        func.logtest('Testing bad string delta input:')
        with self.assertRaises(SystemExit):
            _ = utils.add_period_to_date(['a']*5, 'xxxx')


class PathTests(unittest.TestCase):
    '''Unit tests for path maniuplations'''
    def setUp(self):
        self.path = os.getcwd()
        self.files = ['fileone', 'filetwo', 'filethree']

    def test_add_path_single(self):
        '''Test adding $HOME path to single file'''
        func.logtest('Add $HOME path to single file:')
        outfile = utils.add_path(self.files[0], self.path)
        self.assertEqual(outfile, [self.path + '/' + self.files[0]])

    def test_add_path_multi(self):
        '''Test adding $HOME path to multiple files'''
        func.logtest('Add $HOME path to multiple files:')
        outfiles = utils.add_path(self.files, self.path)
        self.assertListEqual(outfiles,
                             [self.path + '/' + f for f in self.files])

    def test_bad_path(self):
        '''Test adding bad path to single file'''
        func.logtest('Add bad path to single file:')
        with self.assertRaises(SystemExit):
            _ = utils.add_path(self.files[0], 'Hello there')

    def test_no_path(self):
        '''Test adding "None" path to single file'''
        func.logtest('Add "None" path to single file:')
        with self.assertRaises(SystemExit):
            _ = utils.add_path(self.files[0], None)


class FileManipulationTests(unittest.TestCase):
    '''Unit tests for file manipulations'''
    def setUp(self):
        self.dir1 = 'TestFileOps1'
        os.mkdir(self.dir1)
        self.dir2 = 'TestFileOps2'
        os.mkdir(self.dir2)
        for fname in DUMMY:
            open(os.path.join(self.dir1, fname), 'w').close()

    def tearDown(self):
        for dname in [self.dir1, self.dir2]:
            try:
                shutil.rmtree(dname)
            except OSError:
                pass

    def test_move_one_file(self):
        '''Test moving one file'''
        func.logtest('Move single file:')
        utils.move_files(DUMMY[0], self.dir2, originpath=self.dir1)
        self.assertTrue(os.path.exists(os.path.join(self.dir2, DUMMY[0])))

    def test_move_multi_files(self):
        '''Test moving multiple files'''
        func.logtest('Move multiple files:')
        utils.move_files(DUMMY, self.dir2, originpath=self.dir1)
        for fname in DUMMY:
            self.assertTrue(os.path.exists(os.path.join(self.dir2, fname)))

    def test_move_non_existent(self):
        '''Test moving non-existent file'''
        func.logtest('Move non-existent files:')
        utils.move_files(DUMMY, os.getcwd(), originpath=self.dir2)
        for fname in DUMMY:
            self.assertFalse(os.path.exists(os.path.join(self.dir2, fname)))
            # Code should catch exception: IOError
            self.assertFalse(os.path.exists(os.path.join(os.getcwd(), fname)))

    def test_move_overwrite(self):
        '''Test overwriting existing file'''
        func.logtest('Overwrite existing file:')
        utils.move_files(DUMMY[0], self.dir1, originpath=self.dir1)
        # Code should catch exception: shutil.Error
        self.assertTrue(os.path.exists(os.path.join(self.dir1, DUMMY[0])))
        self.assertIn('Attempted to overwrite', func.capture('err'))

    def test_move_overwrite_fail(self):
        '''Test attempt to overwrite file with system exit'''
        func.logtest('Attempt to overwrite with system exit:')
        with self.assertRaises(SystemExit):
            utils.move_files(DUMMY[0], self.dir1, originpath=self.dir1,
                             fail_on_err=True)
        self.assertIn('Attempted to overwrite', func.capture('err'))

    def test_remove_one_file(self):
        '''Test removing single file'''
        func.logtest('Remove single file:')
        utils.remove_files(DUMMY[0], self.dir1)
        self.assertFalse(os.path.exists(os.path.join(self.dir1, DUMMY[0])))

    def test_remove_multi_files(self):
        '''Test removing multiple files'''
        func.logtest('Remove multiple files:')
        utils.remove_files(DUMMY, self.dir1)
        for fname in DUMMY:
            self.assertFalse(os.path.exists(os.path.join(self.dir1, fname)))

    def test_remove_non_existent(self):
        '''Test removing non-existent file'''
        func.logtest('Attempt to move non-existent file:')
        utils.remove_files(DUMMY[0], self.dir2)
        # Code should catch exception: OSError
        self.assertIn('does not exist', func.capture(direct='err'))
        self.assertFalse(os.path.exists(os.path.join(self.dir2, DUMMY[0])))

    def test_remove_non_existent_ignore(self):
        '''Test removing non-existent file, ingnoring failure to find'''
        func.logtest('Attempt to move non-existent file, ignoring failure:')
        utils.remove_files(DUMMY[0], self.dir2, ignoreNonExist=True)
        self.assertEqual('', func.capture(direct='err'))
        self.assertFalse(os.path.exists(os.path.join(self.dir2, DUMMY[0])))

    def test_remove_file_without_origin(self):
        '''Test removing file without specific origin ($PWD)'''
        func.logtest('Attempt to remove a file without specific origin:')
        open('testfile', 'w').close()
        self.assertTrue(os.path.exists('testfile'))
        utils.remove_files('testfile')
        self.assertFalse(os.path.exists('testfile'))

    def test_catch_failure(self):
        '''Test performance of catch_failure method'''
        func.logtest('Assert correct failure mode handling:')
        with self.assertRaises(SystemExit):
            utils.catch_failure()
        self.assertIn('Command Terminated', func.capture('err'))

    def test_catch_failure_debug(self):
        '''Test performance of catch_failure method - debug_mode'''
        func.logtest('Assert correct failure mode handling - debug:')
        with mock.patch('utils.get_debugmode', return_value=True):
            utils.catch_failure()
        self.assertIn('Ignoring failed external command',
                      func.capture('err'))
        self.assertFalse(utils.get_debugok())

    def test_create_dir(self):
        '''Test performance of create_dir method'''
        func.logtest('Assert creation of a directory:')
        self.assertFalse(os.path.isdir('./MyDir'))
        utils.create_dir('MyDir')
        self.assertTrue(os.path.isdir('./MyDir'))
        os.rmdir('./MyDir')

    def test_create_dir_existing(self):
        '''Test performance of create_dir method - pre-existing'''
        func.logtest('Assert creation of a directory - pre-existing:')
        utils.create_dir('MyDir')
        self.assertTrue(os.path.isdir('./MyDir'))
        utils.create_dir('MyDir')
        self.assertTrue(os.path.isdir('./MyDir'))
        os.rmdir('./MyDir')

    def test_create_dir_path(self):
        '''Test performance of create_dir method'''
        func.logtest('Assert creation of a directory:')
        self.assertFalse(os.path.isdir('./MyDir'))
        utils.create_dir('MyDir', path='TopLev')
        self.assertTrue(os.path.isdir('./TopLev/MyDir'))
        os.rmdir('./TopLev/MyDir')
        os.rmdir('./TopLev')

    def test_create_dir_fail(self):
        '''Test performance of create_dir method - failure'''
        func.logtest('Assert creation of a directory - failure:')
        with self.assertRaises(SystemExit):
            utils.create_dir('/MyDir')
        self.assertIn('Unable to create directory', func.capture('err'))


class GetSubsetTests(unittest.TestCase):
    '''Unit tests for the get_subset method'''
    def setUp(self):
        self.dir = os.path.join(os.getcwd(), 'TestSubset')
        self.pattern = '^file[a-z]*$'
        os.mkdir(self.dir)
        for fname in DUMMY:
            open(os.path.join(self.dir, fname), 'w').close()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_get_no_files(self):
        '''Test pattern which matches no files'''
        func.logtest('Pattern matches no files:')
        files = utils.get_subset(self.dir, 'pattern')
        self.assertListEqual(files, [])

    def test_get_one_file(self):
        '''Test pattern which matches one file'''
        func.logtest('Pattern matches one file:')
        files = utils.get_subset(self.dir,
                                 self.pattern.replace('[a-z]*', 'one'))
        self.assertListEqual(files, [DUMMY[0]])

    def test_get_multi_files(self):
        '''Test pattern which matches multiple files'''
        func.logtest('Pattern matches multiple files:')
        files = utils.get_subset(self.dir, self.pattern)
        self.assertListEqual(sorted(files), sorted(DUMMY))

    def test_bad_directory(self):
        '''Test call to get_subset with non existent directory path'''
        func.logtest('Attempt to get_subset with non-existent path:')
        with self.assertRaises(SystemExit):
            _ = utils.get_subset('NotDirectory', self.pattern)

    def test_envar_expand(self):
        '''Test variable expansion in pathnames'''
        func.logtest('Verify environment variable expansion in paths:')
        files = utils.get_subset(os.path.join(os.getcwd(), self.dir),
                                 self.pattern)
        self.assertListEqual(sorted(files), sorted(DUMMY))

    def test_none_pattern(self):
        '''Test call to get_subset with None pattern provided'''
        func.logtest('Attempt to get_subset with `None` pattern:')
        files = utils.get_subset(self.dir, None)
        # Code should catch exception: TypeError
        self.assertListEqual(files, [])


class CycletimeTests(unittest.TestCase):
    '''Unit tests for the SuiteEnvironment class'''
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_cylccycle(self):
        '''Test instantiation of a CylcCycle object'''
        func.logtest('Assert instantiation of a CylcCycle object:')
        cycle = utils.CylcCycle()
        # startcycle == $CYLC_TASK_CYCLE_POINT
        self.assertEqual(cycle.startcycle['iso'], '20000121T0000Z')
        self.assertListEqual(cycle.startcycle['strlist'],
                             ['2000', '01', '21', '00', '00'])
        self.assertListEqual(cycle.startcycle['intlist'],
                             [2000, 1, 21, 0, 0])

        self.assertEqual(cycle.endcycle['iso'], '20000221T0000Z')
        self.assertListEqual(cycle.endcycle['strlist'],
                             ['2000', '02', '21', '00', '00'])
        self.assertListEqual(cycle.endcycle['intlist'],
                             [2000, 2, 21, 0, 0])

    def test_cylccycle_specific(self):
        '''Test instantiation of a CylcCycle object - given point'''
        func.logtest('Assert instantiation of CylcCycle object - given point:')
        with mock.patch.dict('utils.os.environ',
                             {'CYCLEPERIOD': '3h1y'}):
            cycle = utils.CylcCycle(cyclepoint=[1234, 8, 17, 6])

            self.assertEqual(cycle.startcycle['iso'], '12340817T0600Z')
            self.assertListEqual(cycle.startcycle['strlist'],
                                 ['1234', '08', '17', '06', '00'])
            self.assertListEqual(cycle.startcycle['intlist'],
                                 [1234, 8, 17, 6, 0])

            self.assertEqual(cycle.endcycle['iso'], '12350817T0900Z')
            self.assertListEqual(cycle.endcycle['strlist'],
                                 ['1235', '08', '17', '09', '00'])
            self.assertListEqual(cycle.endcycle['intlist'],
                                 [1235, 8, 17, 9, 0])

    def test_failed_cylccycle(self):
        ''' Assert failure to instantiate CylcCycle object '''
        func.logtest('Assert failure to instantiate CylcCycle object:')
        with self.assertRaises(SystemExit):
            _ = utils.CylcCycle(cyclepoint='Dummy')
        self.assertIn('Unable to determine cycle point', func.capture('err'))

    def test_finalcycle_cylc(self):
        '''Test assertion of final cycle - defined by Cylc environment'''
        func.logtest('Assert final cycle time property - TRUE Cylc:')
        with mock.patch.dict('utils.os.environ',
                             {'CYLC_SUITE_FINAL_CYCLE_POINT': '20000130T2359Z',
                              'CYLC_TASK_CYCLE_POINT': '20000101T0000Z',
                              'CYCLEPERIOD': '0,1,0,0,0,0'}):
            self.assertTrue(utils.finalcycle())

    def test_finalcycle_override(self):
        '''Test assertion of final cycle - defined by Cylc override'''
        func.logtest('Assert final cycle time property - TRUE override:')
        with mock.patch.dict('utils.os.environ',
                             {'CYCLEPOINT_OVERRIDE': '19911201T0000Z',
                              'FINALCYCLE_OVERRIDE': '19911201T0000Z',
                              'CYCLEPERIOD': 'P10D'}):
            self.assertTrue(utils.finalcycle())

        with mock.patch.dict('utils.os.environ',
                             {'CYCLEPOINT_OVERRIDE': '19911201T0000Z',
                              'FINALCYCLE_OVERRIDE': '19911230T0000Z',
                              'CYCLEPERIOD': '0,1,0,0,0,0'}):
            self.assertTrue(utils.finalcycle())

    def test_final_cycle_env(self):
        '''Test assertion of final cycle in defined by ARCHIVE_FINAL'''
        func.logtest('Assert final cycle time property - TRUE archive_final:')
        with mock.patch.dict('utils.os.environ', {'ARCHIVE_FINAL': 'true'}):
            self.assertTrue(utils.finalcycle())

    def test_not_final_cycle(self):
        '''Test negative assertion of final cycle'''
        func.logtest('Assert final cycle time property - FALSE:')
        with mock.patch.dict('utils.os.environ',
                             {'CYLC_TASK_CYCLE_POINT': '19810611T0000Z',
                              'CYCLEPERIOD': '3M'}):
            self.assertFalse(utils.finalcycle())

        with mock.patch.dict('utils.os.environ',
                             {'CYCLEPOINT_OVERRIDE': '19911101T0000Z',
                              'FINALCYCLE_OVERRIDE': '19911201T0000Z',
                              'CYCLEPERIOD': '0,1,0,0,0,0'}):
            self.assertFalse(utils.finalcycle())


class SmallUtilsTests(unittest.TestCase):
    '''Unit tests for small utility methods'''
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ensure_list(self):
        ''' Assert return of a list for a given input '''
        func.logtest('Assert return of a list for a given input:')
        self.assertListEqual(utils.ensure_list(None, listnone=True), [None])
        self.assertListEqual(utils.ensure_list(None), [])

        self.assertListEqual(utils.ensure_list('', listnone=True), [''])
        self.assertListEqual(utils.ensure_list(''), [])

        self.assertListEqual(utils.ensure_list('mystring', listnone=True),
                             ['mystring'])
        self.assertListEqual(utils.ensure_list('mystring'), ['mystring'])

        self.assertListEqual(utils.ensure_list([1, 2], listnone=True), [1, 2])
        self.assertTupleEqual(utils.ensure_list((1, 2)), (1, 2))

    def test_get_frequency(self):
        ''' Assert return of int frequency and base period from delta string '''
        func.logtest('Assert return of freq and base from a delta string:')
        self.assertListEqual(utils.get_frequency('3Hrs'), [3, 'h'])
        self.assertListEqual(utils.get_frequency('10d'), [10, 'd'])
        self.assertListEqual(utils.get_frequency('3months'), [3, 'm'])
        self.assertListEqual(utils.get_frequency('2s'), [2, 's'])
        self.assertListEqual(utils.get_frequency('YEAR'), [1, 'y'])
        self.assertListEqual(utils.get_frequency('x'), [1, 'x'])

    def test_get_frequency_deltalist(self):
        ''' Assert return of a delta list from delta string '''
        func.logtest('Assert return of delta list from a delta string:')
        self.assertListEqual(utils.get_frequency('3Hrs', rtn_delta=True),
                             [0, 0, 0, 3, 0])
        self.assertListEqual(utils.get_frequency('10d', rtn_delta=True),
                             [0, 0, 10, 0, 0])
        self.assertListEqual(utils.get_frequency('3months', rtn_delta=True),
                             [0, 3, 0, 0, 0])
        self.assertListEqual(utils.get_frequency('2s', rtn_delta=True),
                             [0, 6, 0, 0, 0])
        self.assertListEqual(utils.get_frequency('YEAR', rtn_delta=True),
                             [1, 0, 0, 0, 0])
        self.assertListEqual(utils.get_frequency('x', rtn_delta=True),
                             [10, 0, 0, 0, 0])

    def test_get_frequency_delta_multi(self):
        ''' Assert get_frequency delta return value given an multiple period '''
        func.logtest('Assert get_frequency return with multiple periods:')
        self.assertListEqual(utils.get_frequency('3H-2M', rtn_delta=True),
                             [0, -2, 0, 3, 0])
        self.assertListEqual(utils.get_frequency('P5Y4M3DT2H1M',
                                                 rtn_delta=True),
                             [5, 4, 3, 2, 1])

    def test_get_frequency_fail(self):
        ''' Assert SystemExit given an invalid delta string '''
        func.logtest('Assert SystemExit given an invalid delta string:')
        with self.assertRaises(SystemExit):
            _ = utils.get_frequency('1F')
        self.assertIn('Invalid target provided: 1f', func.capture('err'))
