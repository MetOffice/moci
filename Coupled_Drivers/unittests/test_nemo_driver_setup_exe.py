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
    test_nemo_driver_setup_exe.py

DESCRIPTION
    Test the setup executable function in NEMO driver. This has been separated
    out, the function is essentially a list of calls to other functions but
    it requires a large degree of mocking.
'''

import unittest
import unittest.mock as mock

import nemo_driver


class TestSetupExecutable(unittest.TestCase):
    '''
    Test the setup_executable function
    '''
    def setUp(self):
        '''Commonalities required for setup executable'''
        self.nemo_envar = {'OCEAN_LINK': 'ocean_link',
                           'OCEAN_EXEC': 'ocean_exec',
                           'NEMO_NL': 'nemo_namelist',
                           'NEMO_NPROC': '25',
                           'RST_LINK_DIR': 'rst_link_dir'}
        self.nemo_envar_si3 = {**self.nemo_envar,
                               **{'SI3_NL': 'ice_namelist'}}
        self.common_env = {'RUNID': 'runid',
                           'models': 'nemo xios'}
        self.common_env_si3 = {'RUNID': 'runid',
                               'models': 'nemo si3 xios'}

    @mock.patch('nemo_driver.nemo_lib.load_environment_variables')
    @mock.patch('nemo_driver.common.remove_file')
    @mock.patch('nemo_driver.os.symlink')
    @mock.patch('nemo_driver.nemo_lib.setup_dates')
    @mock.patch('nemo_driver._nemo_driver_assertions')
    @mock.patch('nemo_driver.nemo_lib.read_current_cycle_nl')
    @mock.patch('nemo_driver.nemo_restart_lib.create_restart_direcs')
    @mock.patch('nemo_driver.nemo_restart_lib.compile_nemo_restart_files')
    @mock.patch('nemo_driver.nemo_restart_lib.setup_previous_restart_nl')
    @mock.patch('nemo_driver.os.path.join')
    @mock.patch('nemo_driver.nemo_lib.read_history_nl')
    # Beginning of IF os.path.isfile
    @mock.patch('nemo_driver.os.path.isfile')
    @mock.patch('nemo_driver._processor_restart_files_nrun')
    @mock.patch('nemo_driver._nrun_timesteps')
    # End if
    @mock.patch('nemo_driver.nemo_lib.setup_nemo_runlen')
    @mock.patch('nemo_driver.update_nemo_nl.update_nl')
    # Not called
    @mock.patch('nemo_driver._verify_restart')
    @mock.patch('nemo_driver._processor_restart_files_crun')
    @mock.patch('nemo_driver._crun_timesteps')
    def test_setup_executable_nrun_no_si3(self,
                                          mock_crun_timesteps,
                                          mock_proc_files_crun,
                                          mock_verify_rst,
                                          # Not called
                                          mock_update_nl,
                                          mock_setup_runlen,
                                          # End if
                                          mock_nrun_timesteps,
                                          mock_proc_files_nrun,
                                          mock_path_isfile,
                                          # Beginning of IF os.path.isfile
                                          mock_read_history_nl,
                                          mock_path_join,
                                          mock_setup_previous_nl,
                                          mock_compile_restarts,
                                          mock_create_restart_direcs,
                                          mock_read_current_nl,
                                          mock_assertions,
                                          mock_setup_dates,
                                          mock_symlink,
                                          mock_remove_file,
                                          mock_load_envar):
        '''Test setting up of executable for an NRUN with no SI3'''
        mock_load_envar.return_value = (self.nemo_envar, \
                                        self.common_env['models'])
        # The list is model basis
        mock_setup_dates.return_value = (
            'nleapy', [2020, 12, 1, 0, 0, 0], 'run_start', 'run_length',
            'run_days')
        mock_read_current_nl.return_value = ('nemo_rst', None, None, None)
        mock_compile_restarts.return_value = (
            'nemo_restart_files', 'latest_nemo_dump', 'nemo_init_dir')
        mock_setup_previous_nl.return_value = 'restart_nl_path'
        mock_path_join.return_value = 'history_nemo_nl'
        mock_read_history_nl.return_value = (
            'nemo_first_step', 'nemo_last_step', 'nemo_step_int',
            'nemo_rst_date_bool')
        # Beginning of IF os.path.isfile
        mock_path_isfile.return_value = False
        mock_proc_files_nrun.return_value = 'ln_restart'
        mock_nrun_timesteps.return_value = (
            'restart_ctl', 'nemo_next_step', 'nemo_last_step')
        # End if
        mock_setup_runlen.return_value = 'nemo_final_step'

        self.assertEqual(
            self.nemo_envar, nemo_driver._setup_executable(self.common_env))

        mock_load_envar.assert_called_once_with('setup', 'nemo xios')
        mock_remove_file.assert_called_once_with('ocean_link')
        mock_symlink.assert_called_once_with('ocean_exec', 'ocean_link')
        mock_read_current_nl.assert_called_once_with(self.common_env,
                                                     self.nemo_envar)
        mock_create_restart_direcs.assert_called_once_with(
            ['nemo_rst'], self.common_env)
        mock_compile_restarts.assert_called_once_with('nemo_rst')
        mock_setup_previous_nl.assert_called_once_with(
            self.common_env, 'nemo_rst', None, None, 'latest_nemo_dump')
        mock_path_join.assert_called_once_with('restart_nl_path',
                                               'nemo_namelist')
        mock_read_history_nl.assert_called_once_with('history_nemo_nl')
        # Beginning of IF os.path.isfile
        mock_path_isfile.assert_called_once_with('latest_nemo_dump')
        mock_proc_files_nrun.assert_called_once_with(self.nemo_envar,
                                                     self.common_env,
                                                     'nemo_init_dir')
        mock_nrun_timesteps.assert_called_once_with('nemo_first_step')
        # End if
        mock_setup_runlen.assert_called_once_with(
            self.common_env, 'run_start', [2020, 12, 1, 0, 0, 0],
            'nemo_step_int', 'run_days', 'run_length', 'nemo_next_step',
            'nemo_last_step')
        mock_update_nl.assert_called_once_with(
            self.common_env, self.nemo_envar, 'ln_restart', 'restart_ctl',
            'nemo_next_step', 'nemo_final_step', '20201201', 'nleapy')

        # Not called
        mock_verify_rst.assert_not_called()
        mock_proc_files_crun.assert_not_called()
        mock_crun_timesteps.assert_not_called()


    @mock.patch('nemo_driver.nemo_lib.load_environment_variables')
    @mock.patch('nemo_driver.common.remove_file')
    @mock.patch('nemo_driver.os.symlink')
    @mock.patch('nemo_driver.nemo_lib.setup_dates')
    @mock.patch('nemo_driver._nemo_driver_assertions')
    @mock.patch('nemo_driver.nemo_lib.read_current_cycle_nl')
    @mock.patch('nemo_driver.nemo_restart_lib.create_restart_direcs')
    @mock.patch('nemo_driver.nemo_restart_lib.compile_nemo_restart_files')
    @mock.patch('nemo_driver.nemo_restart_lib.setup_previous_restart_nl')
    @mock.patch('nemo_driver.os.path.join')
    @mock.patch('nemo_driver.nemo_lib.read_history_nl')
    # Beginning of IF os.path.isfile
    @mock.patch('nemo_driver.os.path.isfile')
    @mock.patch('nemo_driver.re.findall')
    @mock.patch('nemo_driver._verify_restart')
    @mock.patch('nemo_driver._processor_restart_files_crun')
    @mock.patch('nemo_driver._crun_timesteps')
    # End if
    @mock.patch('nemo_driver.nemo_lib.setup_nemo_runlen')
    @mock.patch('nemo_driver.update_nemo_nl.update_nl')
    # Not called
    @mock.patch('nemo_driver._processor_restart_files_nrun')
    @mock.patch('nemo_driver._nrun_timesteps')
    @mock.patch('nemo_driver._run_submodel_custom')
    def test_setup_executable_crun_si3(self,
                                       mock_run_submodel_cust,
                                       mock_nrun_timesteps,
                                       mock_proc_files_nrun,
                                       # Not called
                                       mock_update_nl,
                                       mock_setup_runlen,
                                       # End if
                                       mock_crun_timesteps,
                                       mock_proc_files_crun,
                                       mock_verify_rst,
                                       mock_re_findall,
                                       mock_path_isfile,
                                       # Beginning of IF os.path.isfile
                                       mock_read_history_nl,
                                       mock_path_join,
                                       mock_setup_previous_nl,
                                       mock_compile_restarts,
                                       mock_create_restart_direcs,
                                       mock_read_current_nl,
                                       mock_assertions,
                                       mock_setup_dates,
                                       mock_symlink,
                                       mock_remove_file,
                                       mock_load_envar):
        '''Test setting up of executable for a CRUN with si3'''
        mock_load_envar.return_value = (self.nemo_envar_si3,
                                        self.common_env_si3['models'])
        # The list is model basis
        mock_setup_dates.return_value = (
            'nleapy', [2020, 12, 1, 0, 0, 0], 'run_start', 'run_length',
            'run_days')
        mock_read_current_nl.return_value = (
            'nemo_rst', None, 'ice_rst', None)
        mock_compile_restarts.return_value = (
            'nemo_restart_files', 'latest_nemo_dump', 'nemo_init_dir')
        mock_setup_previous_nl.return_value = 'restart_nl_path'
        mock_path_join.return_value = 'history_nemo_nl'
        mock_read_history_nl.return_value = (
            'nemo_first_step', 'nemo_last_step', 'nemo_step_int',
            'nemo_rst_date_bool')
        # Beginning of IF os.path.isfile
        mock_path_isfile.return_value = True
        mock_re_findall.return_value = ['nemo_dump_time_re']
        mock_verify_rst.return_value = 'nemo_dump_time_verify'
        mock_crun_timesteps.return_value = (
            'ln_restart', 'restart_ctl', 'nemo_next_step')
        # End if
        mock_setup_runlen.return_value = 'nemo_final_step'

        self.assertEqual(
            self.nemo_envar_si3,
            nemo_driver._setup_executable(self.common_env_si3))

        mock_load_envar.assert_called_once_with('setup', 'nemo si3 xios')
        mock_remove_file.assert_has_calls([mock.call('ocean_link'),
                                           mock.call('restart.nc'),
                                           mock.call('restart_ice.nc')])
        mock_symlink.assert_called_once_with('ocean_exec', 'ocean_link')
        mock_read_current_nl.assert_called_once_with(self.common_env_si3,
                                                     self.nemo_envar_si3)
        mock_create_restart_direcs.assert_called_once_with(
            ['nemo_rst', 'ice_rst'], self.common_env_si3)
        mock_compile_restarts.assert_called_once_with('nemo_rst')
        mock_setup_previous_nl.assert_called_once_with(
            self.common_env_si3, 'nemo_rst', 'ice_rst',
            None, 'latest_nemo_dump')
        mock_path_join.assert_called_once_with('restart_nl_path',
                                               'nemo_namelist')
        mock_read_history_nl.assert_called_once_with('history_nemo_nl')
        # Beginning of IF os.path.isfile
        mock_path_isfile.assert_called_once_with('latest_nemo_dump')
        mock_re_findall.assert_called_once_with(
            r'_(\d*)_restart', 'latest_nemo_dump')
        mock_verify_rst.assert_called_once_with(
            self.common_env_si3, self.nemo_envar_si3, 'nemo_dump_time_re',
            'nemo_rst')
        mock_proc_files_crun.assert_called_once_with(
            'nemo_init_dir', 'rst_link_dir', 25, 'nemo_dump_time_verify',
            'runid')
        mock_crun_timesteps.assert_called_once_with(
            'nemo_rst_date_bool', 'nemo_dump_time_verify', 'nemo_step_int',
            'nemo_last_step', self.common_env_si3)
        # End if
        mock_setup_runlen.assert_called_once_with(
            self.common_env_si3, 'run_start', [2020, 12, 1, 0, 0, 0],
            'nemo_step_int', 'run_days', 'run_length', 'nemo_next_step',
            'nemo_last_step')
        mock_update_nl.assert_called_once_with(
            self.common_env_si3, self.nemo_envar_si3, 'ln_restart',
            'restart_ctl', 'nemo_next_step', 'nemo_final_step', '20201201',
            'nleapy')
        mock_run_submodel_cust.assert_called_once_with(
            self.common_env_si3, self.nemo_envar_si3, 'ln_restart',
            'restart_ctl')

        # Not called
        mock_proc_files_nrun.assert_not_called()
        mock_nrun_timesteps.assert_not_called()
