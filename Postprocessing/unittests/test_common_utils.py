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
import sys
import shutil

import testing_functions as func
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'common'))
import utils

DUMMY = ['fileone', 'filetwo', 'filethree']


class EnvironTests(unittest.TestCase):
    '''Unit tests for loading environment variables'''
    def setUp(self):
        self.loadvars = ('PWD', 'HOME')
        testname = self.shortDescription()
        if 'Load one' in testname:
            self.envar = utils.loadEnv(self.loadvars[0])
        else:
            self.envar = utils.loadEnv(*self.loadvars)

    def test_object(self):
        '''test object Instantiation'''
        func.logtest('Variables() instantiation:')
        self.assertIsInstance(self.envar, utils.Variables)

    def test_load1(self):
        '''Test load one environment variable'''
        func.logtest('Load a single environment variable:')
        var = self.loadvars[0]
        self. assertEqual(getattr(self.envar, var), os.environ[var])

    def test_load2(self):
        '''Test load two environment variables'''
        func.logtest('Load two environment variables:')
        for var in self.loadvars:
            self.assertEqual(getattr(self.envar, var), os.environ[var])

    def test_append(self):
        '''Test load one environment variable and append a second'''
        func.logtest('Ability to append to environment variable list:')
        envar = utils.loadEnv(self.loadvars[1], append=self.envar)
        for var in self.loadvars:
            self.assertEqual(getattr(envar, var), os.environ[var])

    def test_not_found_warn(self):
        '''Attempt to load non-existent variable with warning flag'''
        func.logtest('Failure mode of loadEnv (WARN case):')
        envar = utils.loadEnv('ARCHIVE_FINAL')
        try:
            self.fail(envar.ARCHIVE_FINAL)
        except AttributeError:
            pass

    def test_not_found_exit(self):
        '''Attempt to load non-existent variable with a failure flag'''
        func.logtest('Failure mode of loadEnd (FAIL case):')
        with self.assertRaises(SystemExit):
            _ = utils.loadEnv('DUMMYVAR')


class ExecTests(unittest.TestCase):
    '''Unit tests for exec_subproc method'''
    def setUp(self):
        self.cmd = 'echo Hello World!'

    def tearDown(self):
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
        cwd = os.path.dirname(os.path.abspath(
            os.path.dirname(__file__)))+'/common'
        rcode, output = utils.exec_subproc('ls', cwd=cwd, verbose=False)
        self.assertEqual(rcode, 0)
        self.assertIn('utils.py', output)


class LogTests(unittest.TestCase):
    '''Unit tests for logging output messages'''
    def setUp(self):
        self.msg = 'Hello There'
        self.tag = {0: 'DEBUG', 1: 'INFO', 2: ' OK ',
                    3: 'WARN', 4: 'ERROR', 5: 'FAIL'}
        if not hasattr(sys.stdout, 'getvalue'):
            msg = 'This test requires buffered mode to run (buffer=True)'
            self.fail(msg)

    def test_msg(self):
        '''Test content of output message'''
        func.logtest('Verifying output message content.')
        utils.log_msg(self.msg)
        self.assertIn(self.msg, func.capture())

    def test_stdout(self):
        '''Test content of messages printed to stdout'''
        for i in [0, 1, 2]:
            func.logtest('Send output to sys.stdout ({} case):'.
                         format(self.tag[i]))
            utils.log_msg('', i)
            self.assertIn(self.tag[i], func.capture())

    def test_stderr(self):
        '''Test content of messages printed to stderr'''
        for i in [3, 4]:
            func.logtest('Send output to sys.stderr ({} case):'.
                         format(self.tag[i]))
            utils.log_msg('', i)
            self.assertIn(self.tag[i], func.capture(direct='err'))

    def test_fail(self):
        '''Test content of [FAIL] messages printed to stderr'''
        func.logtest('Send output to sys.stderr: (FAIL case):')
        with self.assertRaises(SystemExit):
            utils.log_msg('', 5)
            self.assertIn(self.tag[5], func.capture(direct='err'))

    def test_key_err(self):
        '''Test KeyError exception handling for log_msg'''
        func.logtest('KeyError exception handling in output message:')
        utils.log_msg(self.msg, 10)
        self.assertIn('[WARN]', func.capture(direct='err'))
        self.assertIn('Unknown', func.capture(direct='err'))


class DateCheckTests(unittest.TestCase):
    '''Unit test for date retrival'''
    def setUp(self):
        self.indate = [2004, 2, 15, 0, 0]
        self.delta = [0, 0, 20, 0, 30]
        os.environ['CYLC_CYCLING_MODE'] = '360day'
        try:
            del os.environ['ROSE_HOME']
        except KeyError:
            pass

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
        os.environ['CYLC_CYCLING_MODE'] = 'gregorian'
        date = utils.add_period_to_date(self.indate, self.delta)
        self.assertListEqual(date, outdate)

    def test_short_date(self):
        '''Test date input with short array'''
        func.logtest('Short array date input:')
        indate = self.indate[:2]
        outdate = [2004, 2, 20, 0, 30]
        date = utils.add_period_to_date(indate, self.delta)
        self.assertListEqual(date, outdate)

    def test_zero_date(self):
        '''Test date input with zero date input'''
        func.logtest('All zeros date input:')
        date = utils.add_period_to_date([0]*5, self.delta)
        self.assertListEqual(date, self.delta)

    def test_bad_date(self):
        '''Test date input with bad date input'''
        func.logtest('Testing bad date input:')
        with self.assertRaises(SystemExit):
            _ = utils.add_period_to_date(['a']*5, self.delta)

    def test_pre_c6_cal_360(self):
        '''Test pre-Cylc6 360day calendar date manipulation'''
        func.logtest('Pre-Cylc6 date manipulation with 360day calendar:')
        del os.environ['CYLC_CYCLING_MODE']
        outdate = [2004, 3, 5, 0, 30]
        date = utils.add_period_to_date(self.indate, self.delta)
        self.assertListEqual(date, outdate)

    @unittest.skip('Pre-Cylc 6 is no longer installed')
    def test_pre_c6_gregorian(self):
        '''Test pre-Cylc6 Gregorian calendar date manipulation'''
        func.logtest('Pre-Cylc6 date manipulation with Gregorian calendar:')
        del os.environ['CYLC_CYCLING_MODE']
        os.environ['ROSE_HOME'] = '/home/h03/fcm/rose-2013-12'
        outdate = [2004, 3, 6, 0, 0]
        date = utils.add_period_to_date(self.indate, self.delta, False)
        self.assertListEqual(date, outdate)


class PathTests(unittest.TestCase):
    '''Unit tests for path maniuplations'''
    def setUp(self):
        self.path = os.environ['PWD']
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
        utils.move_files(DUMMY[0], self.dir2, self.dir1)
        self.assertTrue(os.path.exists(os.path.join(self.dir2, DUMMY[0])))

    def test_move_multi_files(self):
        '''Test moving multiple files'''
        func.logtest('Move multiple files:')
        utils.move_files(DUMMY, self.dir2, self.dir1)
        for fname in DUMMY:
            self.assertTrue(os.path.exists(os.path.join(self.dir2, fname)))

    def test_move_non_existent(self):
        '''Test moving non-existent file'''
        func.logtest('Move non-existent files:')
        utils.move_files(DUMMY, os.environ['PWD'], self.dir2)
        for fname in DUMMY:
            self.assertFalse(os.path.exists(os.path.join(self.dir2, fname)))
            # Code should catch exception: IOError
            self.assertFalse(os.path.exists(os.path.join(os.environ['PWD'],
                                                         fname)))

    def test_move_overwrite(self):
        '''Test overwriting existing file'''
        func.logtest('Overwrite existing file:')
        utils.move_files(DUMMY[0], self.dir1, self.dir1)
        # Code should catch exception: shutil.Error
        self.assertTrue(os.path.exists(os.path.join(self.dir1, DUMMY[0])))

    def test_move_without_origin(self):
        '''Test moving file without origin'''
        func.logtest('Move file without origin:')
        utils.move_files(DUMMY[0], self.dir2)
        # Code should catch exception: IOError
        self.assertFalse(os.path.exists(DUMMY[0]))
        self.assertFalse(os.path.exists(os.path.join(self.dir2, DUMMY[0])))

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


class GetSubsetTests(unittest.TestCase):
    '''Unit tests for the get_subset method'''
    def setUp(self):
        self.dir = os.path.join(os.environ['PWD'], 'TestSubset')
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
        files = utils.get_subset(os.path.join(os.environ['PWD'], self.dir),
                                 self.pattern)
        self.assertListEqual(sorted(files), sorted(DUMMY))

    def test_none_pattern(self):
        '''Test call to get_subset with None pattern provided'''
        func.logtest('Attempt to get_subset with `None` pattern:')
        files = utils.get_subset(self.dir, None)
        # Code should catch exception: TypeError
        self.assertListEqual(files, [])


def main():
    '''Main function'''
    unittest.main(buffer=True)


if __name__ == '__main__':
    main()
