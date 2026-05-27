#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    test_nemo_driver_misc.py

DESCRIPTION
    Test miscellaneous functions in the Nemo Driver
'''

import unittest
import unittest.mock as mock

import os

import error
import nemo_driver


class TestNemoDriverAssertions(unittest.TestCase):
    '''
    Test the assertions for the NEMO drivers, and that when they fail
    an assertion error is raised
    '''
    def test_success_nemo_36(self):
        '''If the nemo version is 3.6 and NEMO is in parallel mode, we run
        correctly'''
        nemo_envar = {'NEMO_VERSION': 306,
                      'NEMO_NPROC': 10}
        self.assertIsNone(nemo_driver._nemo_driver_assertions(nemo_envar))

    def test_success_nemo_40(self):
        '''If the nemo version is 4.0 and NEMO is in parallel mode, we run
        correctly'''
        nemo_envar = {'NEMO_VERSION': 400,
                      'NEMO_NPROC': 2}
        self.assertIsNone(nemo_driver._nemo_driver_assertions(nemo_envar))

    def test_failure_nemo_serial(self):
        '''If nemo is attempting to run in serial mode, assertion will fail'''
        nemo_envar = {'NEMO_VERSION': 400,
                      'NEMO_NPROC': 1}
        with self.assertRaises(AssertionError) as context:
            nemo_driver._nemo_driver_assertions(nemo_envar)
        self.assertEqual('[FAIL] Nemo driver does not support the running'
                         ' of NEMO in serial mode\n',
                         str(context.exception))

    def test_failure_nemo_34(self):
        '''If nemo version is lower than 3.6 (ie 3.4) assertion will fail'''
        nemo_envar = {'NEMO_VERSION': 304,
                      'NEMO_NPROC': 2}
        with self.assertRaises(AssertionError) as context:
            nemo_driver._nemo_driver_assertions(nemo_envar)
        self.assertEqual('[FAIL] The python drivers are only valid for NEMO'
                         ' versions 3.6 and later.\n',
                         str(context.exception))

class TestRunSubmodelCustom(unittest.TestCase):
    '''
    Test the running of code that is custom to the submodels
    '''
    @mock.patch('nemo_driver.update_nemo_nl.update_top_nl')
    @mock.patch('nemo_driver.update_nemo_nl.update_si3_nl')
    def test_run_submodel_custom_si3_only(
            self, mock_update_si3_nl, mock_update_top_nl):
        common_env = {'models': 'si3'}
        self.assertIsNone(nemo_driver._run_submodel_custom(
            common_env, 'nemo_envar', 'ln_restart', 'restart_ctl'))
        mock_update_si3_nl.assert_called_once_with('nemo_envar')
        mock_update_top_nl.assert_not_called()

    @mock.patch('nemo_driver.update_nemo_nl.update_top_nl')
    @mock.patch('nemo_driver.update_nemo_nl.update_si3_nl')
    def test_run_submodel_custom_top_lnrestart_true(
            self, mock_update_si3_nl, mock_update_top_nl):
        '''Test the correct running when ln_restart is .true. and no si3'''
        common_env = {'models': 'top'}
        ln_restart = '.true.'
        self.assertIsNone(nemo_driver._run_submodel_custom(
            common_env, 'nemo_envar', ln_restart, 'restart_ctl'))
        mock_update_top_nl.assert_called_once_with(
            'nemo_envar', '.true.', 'restart_ctl', '.false.')
        mock_update_si3_nl.assert_not_called()

    @mock.patch('nemo_driver.update_nemo_nl.update_top_nl')
    @mock.patch('nemo_driver.update_nemo_nl.update_si3_nl')
    def test_run_submodel_custom_top_lnrestart_false_and_si3(
            self, mock_update_si3_nl, mock_update_top_nl):
        '''Test the correct running when ln_restart is .false. and si3'''
        common_env = {'models': 'top si3'}
        ln_restart = '.false.'
        self.assertIsNone(nemo_driver._run_submodel_custom(
            common_env, 'nemo_envar', ln_restart, 'restart_ctl'))
        mock_update_top_nl.assert_called_once_with(
            'nemo_envar', '.false.', 'restart_ctl', '.true.')
        mock_update_si3_nl.assert_called_once_with('nemo_envar')

    @mock.patch('nemo_driver.sys.stderr.write')
    def test_run_submodel_custom_top_lnrestart_invalid(self, mock_stderr):
        '''Test that we exit with an error message if ln_restart has invalid
        value'''
        common_env = {'models': 'top'}
        ln_restart = 'invalid'
        with self.assertRaises(SystemExit) as context:
            nemo_driver._run_submodel_custom(common_env, None, ln_restart, None)
        self.assertEqual(context.exception.code,
                         error.INVALID_LOCAL_ERROR)
        mock_stderr.assert_called_once_with(
            '[FAIL] TOP: invalid ln_restart value: invalid\n')



class TestProcessorRestartFiles(unittest.TestCase):
    '''
    Test the call to set up the various restart files
    '''
    @mock.patch('nemo_driver.ocn_lib.setup_restart')
    def test_processor_restart_files_crun(self, mock_setup_rst):
        '''Check the correct calls to setup_restart for CRUN'''
        nemo_driver._processor_restart_files_crun(
            'nemo_init_dir', 'rst_link_dir', 'nemo_nproc',
            'nemo_dump_time', 'runid')
        mock_setup_rst.assert_has_calls(
            [mock.call('nemo_init_dir', 'rst_link_dir',
                       'runido_nemo_dump_time_restart',
                       'restart', 'nemo_nproc', 'NEMO'),
             mock.call('nemo_init_dir', 'rst_link_dir',
                       'runido_nemo_dump_time_restart_ice',
                       'restart_ice', 'nemo_nproc', 'SI3'),
             mock.call('nemo_init_dir', 'rst_link_dir',
                       'runido_icebergs_nemo_dump_time_restart',
                       'restart_icebergs', 'nemo_nproc', 'Icebergs')])

    @mock.patch('nemo_driver.ocn_lib.setup_nrun')
    def test_processor_restart_files_nrun_nemo_only(self, mock_setup_nrun):
        '''Check the correct calls to setup_restart for NRUN with no Ice or
        TOP'''
        mock_setup_nrun.side_effect = ['ln_restart', None]
        nemo_envar = {'NEMO_START': 'nemo_startdump',
                      'NEMO_ICEBERGS_START': 'icebergs_startdump',
                      'RST_LINK_DIR': 'rst_link_dir'}
        common_env = {'models': 'nemo xios'}
        self.assertEqual('ln_restart',
                         nemo_driver._processor_restart_files_nrun(
                             nemo_envar, common_env, 'nemo_init_dir'))
        mock_setup_nrun.assert_has_calls(
            [mock.call('nemo_startdump', 'rst_link_dir',
                       'restart', 'nemo_init_dir',
                       'NEMO_START not set\nNEMO will use climatology\n'),
             mock.call(
                 'icebergs_startdump', 'rst_link_dir',
                 'restart_icebergs', 'nemo_init_dir',
                 'NEMO_ICEBERGS_START not set or file(s)' \
                 ' not found. Icebergs (if switched on) will start' \
                 ' from a state of zero icebergs\n')])

    @mock.patch('nemo_driver.ocn_lib.setup_nrun')
    def test_processor_restart_files_nrun_with_si3(self, mock_setup_nrun):
        '''Check the correct calls to setup_restart for NRUN with Ice but no
        TOP'''
        mock_setup_nrun.side_effect = ['ln_restart', None, None]
        nemo_envar = {'NEMO_START': 'nemo_startdump',
                      'NEMO_ICEBERGS_START': 'icebergs_startdump',
                      'SI3_START': 'si3_startdump',
                      'RST_LINK_DIR': 'rst_link_dir'}
        common_env = {'models': 'nemo xios si3'}
        self.assertEqual('ln_restart',
                         nemo_driver._processor_restart_files_nrun(
                             nemo_envar, common_env, 'nemo_init_dir'))
        mock_setup_nrun.assert_has_calls(
            [mock.call('nemo_startdump', 'rst_link_dir',
                       'restart', 'nemo_init_dir',
                       'NEMO_START not set\nNEMO will use climatology\n'),
             mock.call(
                 'icebergs_startdump', 'rst_link_dir', 'restart_icebergs',
                 'nemo_init_dir',
                 'NEMO_ICEBERGS_START not set or file(s)' \
                 ' not found. Icebergs (if switched on) will start' \
                 ' from a state of zero icebergs\n'),
             mock.call(
                 'si3_startdump', 'rst_link_dir', 'restart_ice',
                 'nemo_init_dir', 'New SI3 run\n')])

    @mock.patch('nemo_driver.ocn_lib.setup_nrun')
    def test_processor_restart_files_nrun_with_top(self, mock_setup_nrun):
        '''Check the correct calls to setup_restart for NRUN with TOP but no
        ice'''
        mock_setup_nrun.side_effect = ['ln_restart', None, None]
        nemo_envar = {'NEMO_START': 'nemo_startdump',
                      'NEMO_ICEBERGS_START': 'icebergs_startdump',
                      'TOP_START': 'top_startdump',
                      'RST_LINK_DIR': 'rst_link_dir'}
        common_env = {'models': 'nemo xios top'}
        self.assertEqual('ln_restart',
                         nemo_driver._processor_restart_files_nrun(
                             nemo_envar, common_env, 'nemo_init_dir'))
        mock_setup_nrun.assert_has_calls(
            [mock.call('nemo_startdump', 'rst_link_dir',
                       'restart', 'nemo_init_dir',
                       'NEMO_START not set\nNEMO will use climatology\n'),
             mock.call(
                 'icebergs_startdump', 'rst_link_dir',
                 'restart_icebergs', 'nemo_init_dir',
                 'NEMO_ICEBERGS_START not set or file(s)' \
                 ' not found. Icebergs (if switched on) will start' \
                 ' from a state of zero icebergs\n'),
             mock.call(
                 'top_startdump', 'rst_link_dir', 'restart_trc',
                 'nemo_init_dir', 'New TOP run\n')])


class TestCrunTimesteps(unittest.TestCase):
    '''
    Test the setting up of timesteps for a CRUN
    '''
    @mock.patch('nemo_driver.sys.stdout.write')
    def test_integer_cycle_msg_continue_from_fail(self, mock_stdout):
        '''Test an integer cycling when used with CONTINUE_FROM_FAIL true'''
        common_env = {'CONTINUE_FROM_FAIL': 'true'}
        expected_out = ('.true.', 2, 145)
        rvalue = nemo_driver._crun_timesteps(
            False, '144', 1200, None, common_env)
        self.assertEqual(rvalue, expected_out)
        mock_stdout.assert_called_once_with(
            '[INFO] Nemo has previously completed 2 days\n')

    @mock.patch('nemo_driver.sys.stdout.write')
    def test_date_cycle(self, mock_stdout):
        '''Test an date cycling when used with CONTINUE_FROM_FAIL false'''
        common_env = {'CONTINUE_FROM_FAIL': 'false'}
        expected_out = ('.true.', 2, 73)
        rvalue = nemo_driver._crun_timesteps(
            True, None, None, 72, common_env)
        self.assertEqual(rvalue, expected_out)
        mock_stdout.assert_not_called()

class TestNrunTimesteps(unittest.TestCase):
    '''
    Test setting up of timesteps for an NRUN
    '''
    def test_nrun_timesteps(self):
        nemo_first_step = 72
        expected_return = (0, nemo_first_step, nemo_first_step - 1)
        self.assertEqual(
            expected_return, nemo_driver._nrun_timesteps(nemo_first_step))


class TestWriteOutputFileToStdOut(unittest.TestCase):
    '''
    Test the writing of an ocean output file to standard out
    '''
    def setUp(self):
        '''Create an output, one with unicode, one with errors to read'''
        self.unicode_fn = 'unicode_output'
        self.error_fn = 'error_output'
        self.unicode_contents = '''A first line in the ascii range
A second line in the ascii range
A third line containing a unicode division in brackets (\u00F7)
A fourth line in the ascii range'''
        self.error_contents = '''A first line with no error
A second line with E R R O R
A a third line with no error
A fourth line with E R R O R in the middle
A fifth line'''
        with open(self.unicode_fn, 'w', encoding='utf8') as unicode_fh:
            unicode_fh.write(self.unicode_contents)
        with open(self.error_fn, 'w') as error_fh:
            error_fh.write(self.error_contents)

    def tearDown(self):
        '''Remove the test files'''
        for test_f in [self.unicode_fn, self.error_fn]:
            try:
                os.remove(test_f)
            except FileNotFoundError:
                pass

    @mock.patch('nemo_driver.sys.stdout.write')
    def test_write_output_file_to_stdout_error_zero(self, mock_stdout):
        '''Test errors get written and we count two of them with no
        error count provided'''
        self.assertEqual(
            2, nemo_driver._write_output_file_to_stdout(self.error_fn))
        mock_stdout.assert_has_calls(
            [mock.call(
                '[INFO] Ocean output from file %s\n' % self.error_fn),
             mock.call('A first line with no error\n'),
             mock.call('A second line with E R R O R\n'),
             mock.call('A a third line with no error\n'),
             mock.call('A fourth line with E R R O R in the middle\n'),
             mock.call('A fifth line')])

    @mock.patch('nemo_driver.sys.stdout.write')
    def test_write_output_file_to_stdout_error_non_zero(self, mock_stdout):
        '''Test errors get written and we count four of them when input
        error count is 2'''
        self.assertEqual(
            4, nemo_driver._write_output_file_to_stdout(self.error_fn, 2))

    @mock.patch('nemo_driver.sys.stdout.write')
    def test_write_output_file_to_stdout_unicode_error_passed_in(
            self, mock_stdout):
        '''Test that the unicode string is written successfully without the
        unicode character, and that with 2 errors passed in, 2 are passed out
        as there are no E R R O Rs in this test'''
        self.assertEqual(
            2, nemo_driver._write_output_file_to_stdout(self.unicode_fn, 2))
        mock_stdout.assert_has_calls(
            [mock.call(
                '[INFO] Ocean output from file %s\n' % self.unicode_fn),
             mock.call('A first line in the ascii range\n'),
             mock.call('A second line in the ascii range\n'),
             mock.call('A third line containing a unicode division in'
                       ' brackets ()\n'),
             mock.call('A fourth line in the ascii range')])

class TestWriteOceanToStdout(unittest.TestCase):
    '''
    Test the listing through of output files and calling the function to write
    them to standard out
    '''
    @mock.patch('nemo_driver.os.path.isfile')
    @mock.patch('nemo_driver._write_output_file_to_stdout')
    @mock.patch('nemo_driver.sys.stdout.write')
    def test_write_ocean_out_to_stdout_succeed(
            self, mock_stdout, mock_write_file, mock_isfile):
        '''Test for all potential restart files exisiting'''
        mock_isfile.side_effect = [True, True, True, True]
        mock_write_file.side_effect = ['error1', 'error2', 'error3', 'error4']
        self.assertEqual('error4', nemo_driver._write_ocean_out_to_stdout())
        mock_isfile.assert_has_calls([mock.call('ocean.output'),
                                      mock.call('solver.stat'),
                                      mock.call('run.stat'),
                                      mock.call('icebergs.stat')])
        mock_write_file.assert_has_calls(
            [mock.call('ocean.output', 0),
             mock.call('solver.stat', 'error1'),
             mock.call('run.stat', 'error2'),
             mock.call('icebergs.stat', 'error3')])
        mock_stdout.assert_not_called()

    @mock.patch('nemo_driver.os.path.isfile')
    @mock.patch('nemo_driver._write_output_file_to_stdout')
    @mock.patch('nemo_driver.sys.stdout.write')
    def test_write_ocean_out_to_stdout_failed(
            self, mock_stdout, mock_write_file, mock_isfile):
        '''Test for all potential restart files missing'''
        no_file_line = '[INFO] Nemo output file %s not avaliable\n'
        mock_isfile.side_effect = [False, False, False, False]
        self.assertEqual(0, nemo_driver._write_ocean_out_to_stdout())
        mock_isfile.assert_has_calls([mock.call('ocean.output'),
                                      mock.call('solver.stat'),
                                      mock.call('run.stat'),
                                      mock.call('icebergs.stat')])
        mock_write_file.assert_not_called()
        mock_stdout.assert_has_calls(
            [mock.call(no_file_line % 'ocean.output'),
             mock.call(no_file_line % 'solver.stat'),
             mock.call(no_file_line % 'run.stat'),
             mock.call(no_file_line % 'icebergs.stat')])

    @mock.patch('nemo_driver.os.path.isfile')
    @mock.patch('nemo_driver._write_output_file_to_stdout')
    @mock.patch('nemo_driver.sys.stdout.write')
    def test_write_ocean_out_to_stdout_nemo4_combo(
            self, mock_stdout, mock_write_file, mock_isfile):
        '''Test the file combination for NEMO4 (no solver.stat)'''
        no_file_line = '[INFO] Nemo output file %s not avaliable\n'
        mock_isfile.side_effect = [True, False, True, True]
        mock_write_file.side_effect = ['error1', 'error2', 'error3']
        self.assertEqual('error3', nemo_driver._write_ocean_out_to_stdout())
        mock_isfile.assert_has_calls([mock.call('ocean.output'),
                                      mock.call('solver.stat'),
                                      mock.call('run.stat'),
                                      mock.call('icebergs.stat')])
        mock_write_file.assert_has_calls(
            [mock.call('ocean.output', 0),
             mock.call('run.stat', 'error1'),
             mock.call('icebergs.stat', 'error2')])
        mock_stdout.assert_called_once_with(no_file_line % 'solver.stat')


class TestMoveNLEndOfRun(unittest.TestCase):
    '''
    Test the copying of the namelist files at the end of the run
    '''
    def setUp(self):
        '''Set up the environment variable object'''
        self.nemo_envar_fin = {'NEMO_NL': 'nemo_namelist',
                               'TOP_NL': 'top_namelist'}

    @mock.patch('nemo_driver.os.path.isdir')
    @mock.patch('nemo_driver.shutil.copy')
    def test_nemo_only(self, mock_copy, mock_isdir):
        '''Test copying of namelist NEMO only'''
        mock_isdir.return_value = True
        nemo_driver._copy_nl_end_of_run(self.nemo_envar_fin, 'nemo_rst', None)
        mock_isdir.assert_called_once_with('nemo_rst')
        mock_copy.assert_called_once_with('nemo_namelist', 'nemo_rst')

    @mock.patch('nemo_driver.os.path.isdir')
    @mock.patch('nemo_driver.shutil.copy')
    def test_nemo_top(self, mock_copy, mock_isdir):
        '''Test copying of namelist NEMO and TOP'''
        mock_isdir.side_effect = [True, True]
        nemo_driver._copy_nl_end_of_run(
            self.nemo_envar_fin, 'nemo_rst', 'top_rst')
        mock_isdir.assert_has_calls([mock.call('nemo_rst'),
                                     mock.call('top_rst')])
        mock_copy.assert_has_calls([mock.call('nemo_namelist', 'nemo_rst'),
                                    mock.call('top_namelist', 'top_rst')])




class TestFinaliseExecutable(unittest.TestCase):
    '''
    Test the finalise executable function
    '''
    @mock.patch('nemo_driver.sys.stdout.write')
    @mock.patch('nemo_driver.os.getcwd')
    @mock.patch('nemo_driver._write_ocean_out_to_stdout')
    @mock.patch('nemo_driver.sys.stderr.write')
    def test_finalize_executable_error_count(
            self, mock_stderr, mock_write, mock_cwd, mock_stdout):
        '''Test we exit if the error count is one'''
        mock_write.return_value = 1
        mock_cwd.return_value = 'current_wd'
        with self.assertRaises(SystemExit) as context:
            nemo_driver._finalize_executable(None)
        mock_stdout.assert_has_calls(
            [mock.call('[INFO] finalizing NEMO\n'),
             mock.call('[INFO] running finalize in current_wd\n')])
        mock_cwd.assert_called_once_with()
        self.assertEqual(context.exception.code,
                         error.COMPONENT_MODEL_ERROR)
        mock_stderr.assert_called_once_with(
            '[FAIL] An error has been found with the NEMO run.'
            ' Please investigate the ocean.output file for more'
            ' details\n')

    @mock.patch('nemo_driver.sys.stdout.write')
    @mock.patch('nemo_driver.os.getcwd')
    @mock.patch('nemo_driver._write_ocean_out_to_stdout')
    @mock.patch('nemo_driver.nemo_lib.load_environment_variables')
    @mock.patch('nemo_driver.nemo_lib.read_current_cycle_nl')
    @mock.patch('nemo_driver._copy_nl_end_of_run')
    def test_finalize_executable_nemo_rst_top_rist(
            self, mock_copy_nl_end_of_run, mock_read_nl,
            mock_load_env, mock_write, mock_cwd, mock_stdout):
        '''Test finalise when the nemo and top restarts are avaliable to move'''
        common_env = {'models': 'model list'}
        mock_write.return_value = 0
        mock_cwd.return_value = ''
        mock_load_env.return_value = ({'NEMO_NL': 'nemo_namelist'},
                                      'model list updated')
        mock_read_nl.return_value = ('nemo_rst', None, None, 'top_rst')
        nemo_driver._finalize_executable(common_env)
        mock_stdout.assert_has_calls(
            [mock.call('[INFO] finalizing NEMO\n'),
             mock.call('[INFO] running finalize in \n')])
        mock_load_env.assert_called_once_with('final', 'model list')
        mock_read_nl.assert_called_once_with(common_env,
                                             {'NEMO_NL': 'nemo_namelist'})
        mock_copy_nl_end_of_run.assert_called_once_with(
            {'NEMO_NL': 'nemo_namelist'}, 'nemo_rst', 'top_rst')

    @mock.patch('nemo_driver.sys.stdout.write')
    @mock.patch('nemo_driver.os.getcwd')
    @mock.patch('nemo_driver._write_ocean_out_to_stdout')
    @mock.patch('nemo_driver.nemo_lib.load_environment_variables')
    @mock.patch('nemo_driver.nemo_lib.read_current_cycle_nl')
    @mock.patch('nemo_driver.os.path.isdir')
    @mock.patch('nemo_driver.shutil.copy')
    def test_finalize_executable_nemo_rst_no_nemo_rst(
            self, mock_copy, mock_isdir, mock_read_nl,
            mock_load_env, mock_write, mock_cwd, mock_stdout):
        '''Test finalise when there is no nemo_rst directory'''
        mock_write.return_value = 0
        mock_cwd.return_value = ''
        mock_load_env.return_value = ({'NEMO_NL': 'nemo_namelist'},
                                      'model list updated')
        mock_read_nl.return_value = ('nemo_rst',  None, None, None)
        mock_isdir.return_value = False
        nemo_driver._finalize_executable({'models': 'model list updated'})
        mock_copy.assert_not_called()

class TestRunDriver(unittest.TestCase):
    '''
    Test the interface to run the driver
    '''
    @mock.patch('nemo_driver._setup_executable')
    @mock.patch('nemo_driver._finalize_executable')
    @mock.patch('nemo_driver._write_ocean_out_to_stdout')
    def test_run_driver_finalize(self, mock_write, mock_finalize, mock_setup):
        '''Test finalise mode'''
        rvalue = nemo_driver.run_driver('common_env', 'finalize', 'run_info')
        self.assertEqual(rvalue, (None, None, 'run_info', None))
        mock_setup.assert_not_called()
        mock_write.assert_not_called()
        mock_finalize.assert_called_once_with('common_env')

    @mock.patch('nemo_driver._setup_executable')
    @mock.patch('nemo_driver._finalize_executable')
    @mock.patch('nemo_driver._write_ocean_out_to_stdout')
    def test_run_driver_failure(self, mock_write, mock_finalize, mock_setup):
        '''Test finalise mode'''
        rvalue = nemo_driver.run_driver('common_env', 'failure', 'run_info')
        self.assertEqual(rvalue, (None, None, 'run_info', None))
        mock_setup.assert_not_called()
        mock_finalize.assert_not_called()
        mock_write.assert_called_once_with()

    @mock.patch('nemo_driver._setup_executable')
    @mock.patch('nemo_driver._set_launcher_command')
    @mock.patch('nemo_driver.nemo_runtime_namcouple.sent_coupling_fields')
    @mock.patch('nemo_driver._finalize_executable')
    @mock.patch('nemo_driver._write_ocean_out_to_stdout')
    def test_run_driver_l_namcouple(self, mock_write, mock_finalize, mock_namc,
                                    mock_launcher_cmd, mock_setup):
        '''Test run mode with l_namcouple set in run info'''
        run_info = {'l_namcouple': True}
        common_env = {'ROSE_LAUNCHER': 'launcher'}
        mock_setup.return_value = 'exe_envar'
        mock_launcher_cmd.return_value = 'launch_cmd'
        rvalue = nemo_driver.run_driver(common_env, 'run_driver', run_info)
        self.assertEqual(rvalue, ('exe_envar', 'launch_cmd', run_info, None))
        mock_setup.assert_called_once_with(common_env)
        mock_launcher_cmd.assert_called_once_with('launcher', 'exe_envar')
        mock_namc.assert_not_called()
        mock_finalize.assert_not_called()
        mock_write.assert_not_called()

    @mock.patch('nemo_driver._setup_executable')
    @mock.patch('nemo_driver._set_launcher_command')
    @mock.patch('nemo_driver.nemo_runtime_namcouple.sent_coupling_fields')
    @mock.patch('nemo_driver._finalize_executable')
    @mock.patch('nemo_driver._write_ocean_out_to_stdout')
    def test_run_driver_no_l_namcouple(
            self, mock_write, mock_finalize, mock_namc, mock_launcher_cmd,
            mock_setup):
        '''Test run mode with l_namcouple set to false in run info'''
        run_info = {'l_namcouple': False}
        common_env = {'ROSE_LAUNCHER': 'launcher'}
        mock_setup.return_value = 'exe_envar'
        mock_launcher_cmd.return_value = 'launch_cmd'
        mock_namc.return_value = ('run_info', 'model_snd_list')
        rvalue = nemo_driver.run_driver(common_env, 'run_driver', run_info)
        self.assertEqual(
            rvalue, ('exe_envar', 'launch_cmd', 'run_info', 'model_snd_list'))
        mock_setup.assert_called_once_with(common_env)
        mock_launcher_cmd.assert_called_once_with('launcher', 'exe_envar')
        mock_namc.assert_called_once_with('exe_envar', run_info)
        mock_finalize.assert_not_called()
        mock_write.assert_not_called()

class TestVerifyRestart(unittest.TestCase):
    '''
    Test the verification of NEMO restart files
    '''
    @mock.patch('nemo_driver.nemo_restart_lib.verify_fix_rst')
    def test_verify_restart_no_validation(self, mock_verify_fix):
        '''Test for DRIVERS_VERIFY_RST false, nothing is done'''
        common_env = {'DRIVERS_VERIFY_RST': 'False'}
        self.assertEqual(
            'nemo_dump_time', nemo_driver._verify_restart(
                common_env, None, 'nemo_dump_time', None))
        mock_verify_fix.assert_not_called()

    @mock.patch('nemo_driver.nemo_restart_lib.verify_fix_rst')
    def test_verify_restart(self, mock_verify_fix):
        '''Test for DRIVERS_VERIFY_RST True, validation performed'''
        common_env = {'DRIVERS_VERIFY_RST': 'True',
                      'CYLC_TASK_CYCLE_POINT': 'cycle_point'}
        nemo_env = {'NEMO_NPROC': '25'}
        mock_verify_fix.return_value = 'nemo_dump_time_rtn'
        self.assertEqual(
            'nemo_dump_time_rtn', nemo_driver._verify_restart(
                common_env, nemo_env, 'nemo_dump_time', 'nemo_rst'))
        mock_verify_fix.assert_called_once_with(
            'nemo_dump_time', 'cycle_point', 'nemo_rst')

