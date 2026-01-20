#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2025 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''
import sys
import unittest
import unittest.mock as mock

import rivers_driver

COMMON_ENV = { 'CALENDAR': 'gregorian',
               'TASKSTART': '1979,09,01,00,0',
               'TASKLENGTH': '1,4,10,0,0', }
nml = rivers_driver.dr_env_lib.rivers_def.RIVERS_ENVIRONMENT_VARS_INITIAL
RIVER_ENV = { k: nml[k].get('default_val', None) for k in nml.keys()}


class TestPrivateMethods(unittest.TestCase):
    '''
    Test the private methods of the JULES river standalone driver
    '''

    @mock.patch('rivers_driver.shellout._exec_subprocess', return_value=[0, 'output'])
    def test_setup_dates(self, mock_exec):
        ''' Test the _setup_dates method '''

        start, end = rivers_driver._setup_dates(COMMON_ENV)
        self.assertIn(mock.call('isodatetime 19790901T0000Z -f "%Y-%m-%d %H:%M:%S"'),
                      mock_exec.mock_calls)
        self.assertIn(mock.call('isodatetime 19790901T0000Z -f "%Y-%m-%d %H:%M:%S" -s P1Y4M10DT0H0M --calendar gregorian'),
                      mock_exec.mock_calls)
        self.assertEqual(len(mock_exec.mock_calls), 2)

    @mock.patch('rivers_driver.common')
    @mock.patch('rivers_driver.shellout')
    @mock.patch('rivers_driver.os.path.isfile')
    @mock.patch('rivers_driver.pathlib')
    def test_update_river_nl(self, mock_lib, mock_path, mock_shellout, mock_common):
        ''' Test the _update_river_nl method '''
        mock_shellout._exec_subprocess.returnvalue = (0, 'dir="this/path/"')

        rivers_driver._update_river_nl(RIVER_ENV,
                                       '19790901T0000Z', '19810121T0000Z')

        path_calls = mock_path.mock_calls
        self.assertIn(mock.call('output.nml'), path_calls)
        self.assertIn(mock.call('timesteps.nml'), path_calls)

        nml_calls = mock_common.ModNamelist.mock_calls
        self.assertIn(mock.call('output.nml'), nml_calls)
        self.assertIn(mock.call('timesteps.nml'), nml_calls)
        self.assertIn(mock.call().var_val('output_start', '19790901T0000Z'),
                                          nml_calls)
        self.assertIn(mock.call().replace(), nml_calls)

        self.assertIn(mock.call().var_val('main_run_start', '19790901T0000Z'),
                      nml_calls)
        self.assertIn(mock.call().var_val('main_run_end', '19810121T0000Z'),
                      nml_calls)

        mock_shellout._exec_subprocess.assert_called_once_with(
            'grep output_dir output.nml'
        )
        mock_lib.Path.assert_called_once_with('this/path')
        mock_lib.Path().mkdir.assert_called_once_with(parents=True,
                                                      exist_ok=True)

    @mock.patch('rivers_driver.os.path.isfile')
    @mock.patch('rivers_driver.f90nml.read')
    def test_get_river_resol(self, mock_read, mock_path):
        '''Test the _get_river_resol function'''
        mock_read.return_value = {'jules_input_grid': {'nx': 10, 'ny': 20}}

        out_info = rivers_driver._get_river_resol('riv_nl', {})
        self.assertIn(mock.call('riv_nl'), mock_path.mock_calls)
        self.assertEqual(out_info, {'RIV_resol': [10, 20]})

    @mock.patch('rivers_driver.os.path')
    @mock.patch('rivers_driver._get_river_resol')
    @mock.patch('rivers_driver.f90nml')
    def test_sent_coupling_fields(self, mock_nml, mock_res, mock_path):
        '''Run info should pass through, and should also return None as a
        second value'''
        run_info = {'exec_list': ['toyriv'],
                    'river_nl': 'rivers_coupling.nml'}
        mock_res.return_value = run_info
        mock_nml.read.return_value = {
            'oasis_riv_send_nml': {'oasis_riv_send': 'fields'}
        }
        mock_namcpl = mock.Mock(add_to_cpl_list=mock.MagicMock())
        mock_namcpl.add_to_cpl_list.return_value = 'send_list'

        with mock.patch.dict(sys.modules, {'write_namcouple': mock_namcpl}):
            rtn = rivers_driver._sent_coupling_fields(RIVER_ENV, {})

        self.assertEqual(rtn, (run_info, 'send_list'))
        path_calls = mock_path.mock_calls
        self.assertIn(mock.call.exists('OASIS_RIV_SEND'), path_calls)
        self.assertIn(mock.call.isfile('rivers_coupling.nml'), path_calls)
        mock_res.assert_called_once_with('model_grid.nml',
                                         {'exec_list': ['toyriv']})
        mock_nml.read.assert_called_once_with('OASIS_RIV_SEND')
        mock_namcpl.add_to_cpl_list.assert_called_once_with(
            'RIV', False, 0, 'fields'
        )


class TestSetupExecutable(unittest.TestCase):
    '''
    Test the loading of environment variables and file copies
    '''
    @mock.patch('rivers_driver.dr_env_lib.env_lib')
    @mock.patch('rivers_driver.common')
    @mock.patch('rivers_driver.os.symlink')
    @mock.patch('rivers_driver._setup_dates', return_value=('start', 'end'))
    @mock.patch('rivers_driver._update_river_nl')
    def test_setup_executable(self, mock_upd, mock_date,
                              mock_link, mock_cmn, mock_env):
        '''Test the _setup_executable function'''
        rivers_envar = RIVER_ENV
        rivers_envar['RIVER_EXEC'] = 'executable'
        mock_env.load_envar_from_definition.return_value = rivers_envar

        return_rivers_envar = rivers_driver._setup_executable(COMMON_ENV)
        mock_env.LoadEnvar.assert_called_once_with()

        mock_cmn.remove_file.assert_called_once_with('river.exe')
        mock_link.assert_called_once_with('executable', 'river.exe')
        mock_date.assert_called_once_with(COMMON_ENV)
        mock_upd.assert_called_once_with(rivers_envar, 'start', 'end')
        self.assertEqual(return_rivers_envar, rivers_envar)

    def test_launcher_command(self):
        '''Test the _set_launcher_command function'''
        env = RIVER_ENV
        env['ROSE_LAUNCHER_PREOPTS_RIVER'] = 'river pre-opts'

        cmd = rivers_driver._set_launcher_command(env)
        self.assertEqual(cmd, 'river pre-opts ./river.exe')
        self.assertEqual(env['ROSE_LAUNCHER_PREOPTS_RIVER'],
                         "'river pre-opts'")


class TestFinalizeExecutable(unittest.TestCase):
    '''
    Test the finalizing of the executable
    '''
    def test_finalize_executable(self):
        '''Test the finalize. It does nothing at the moment'''
        self.assertIsNone(rivers_driver._finalize_executable())


class TestRunDriver(unittest.TestCase):
    '''
    Test the interface to run the driver
    '''
    @mock.patch('rivers_driver._setup_executable')
    @mock.patch('rivers_driver._finalize_executable')
    def test_run_driver_finalize(self, mock_finalize, mock_setup):
        '''Test finalise mode'''
        rvalue = rivers_driver.run_driver('common_env', 'finalize', 'run_info')
        self.assertEqual(rvalue, (None, None, 'run_info', None))
        mock_setup.assert_not_called()
        mock_finalize.assert_called_once_with()

    @mock.patch('rivers_driver._setup_executable')
    @mock.patch('rivers_driver._set_launcher_command')
    @mock.patch('rivers_driver._sent_coupling_fields')
    @mock.patch('rivers_driver._finalize_executable')
    def test_run_driver_l_namcouple(
            self, mock_finalize, mock_namc, mock_launcher_cmd, mock_setup
    ):
        '''Test run mode with l_namcouple set in run info'''
        run_info = {'l_namcouple': True}
        common_env = {'ROSE_LAUNCHER': 'launcher'}
        mock_setup.return_value = 'exe_envar'
        mock_launcher_cmd.return_value = 'launch_cmd'
        rvalue = rivers_driver.run_driver(common_env, 'run_driver', run_info)
        self.assertEqual(rvalue, ('exe_envar', 'launch_cmd', run_info, None))
        mock_setup.assert_called_once_with(common_env)
        mock_launcher_cmd.assert_called_once_with('exe_envar')
        mock_namc.assert_not_called()
        mock_finalize.assert_not_called()

    @mock.patch('rivers_driver._setup_executable')
    @mock.patch('rivers_driver._set_launcher_command')
    @mock.patch('rivers_driver._sent_coupling_fields')
    @mock.patch('rivers_driver._finalize_executable')
    def test_run_driver_no_l_namcouple(
            self, mock_finalize, mock_namc, mock_launcher_cmd, mock_setup
    ):
        '''Test run mode with l_namcouple set to False in run info'''
        run_info = {'l_namcouple': False}
        common_env = {'ROSE_LAUNCHER': 'launcher'}
        mock_setup.return_value = 'exe_envar'
        mock_launcher_cmd.return_value = 'launch_cmd'
        mock_namc.return_value = ('run_info', 'model_snd_list')

        rvalue = rivers_driver.run_driver(common_env, 'run_driver', run_info)

        self.assertEqual(
            rvalue, ('exe_envar', 'launch_cmd', 'run_info', 'model_snd_list'))
        mock_setup.assert_called_once_with(common_env)
        mock_launcher_cmd.assert_called_once_with('exe_envar')
        mock_namc.assert_called_once_with('exe_envar', run_info)
        mock_finalize.assert_not_called()
