#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------
'''
NAME
    test_nemo_driver.py

DESCRIPTION
    Contains unit tests for the si3_controller.py module.
'''
import unittest
import unittest.mock as mock
import io

import si3_controller

nml = si3_controller.dr_env_lib.ocn_cont_def.SI3_ENVIRONMENT_VARS_INITIAL
SI3_ENV = { k: nml[k].get('default_val', None) for k in nml.keys()}

class TesSetupController(unittest.TestCase):
    '''
    Tests for the setup of the SI3 model prior to running
    '''
    @mock.patch('si3_controller.os.path.isfile', return_value=True)
    def test_naml_isfile(self, mock_path):
        rval = si3_controller._check_si3nl_envar(SI3_ENV)
        self.assertEqual(rval, 0)
        mock_path.assert_called_once_with('namelist_ice_cfg')

    def test_naml_missing(self):
        expected_err = '[FAIL] si3_controller: ' \
            'Can not find the SI3 namelist file namelist_ice_cfg'

        with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
            with self.assertRaises(SystemExit) as context:
                rval = si3_controller._check_si3nl_envar(SI3_ENV)
        self.assertIn(expected_err, patch_err.getvalue())
        self.assertEqual(context.exception.code,
                         si3_controller.error.MISSING_CONTROLLER_FILE_ERROR)

    @mock.patch('si3_controller.common.exec_subproc')
    def test_si3rst(self, mock_exec):
        mock_exec.return_value = (0, "cn_icerst_outdir='Ice/Rst/Dir',")
        rval = si3_controller._get_si3rst('namelist.nl')
        self.assertEqual(rval, 'Ice/Rst/Dir')
        mock_exec.assert_called_once_with(
            ['grep', 'cn_icerst_outdir', 'namelist.nl']
        )

    @mock.patch('si3_controller.common.exec_subproc')
    def test_si3rst_fail(self, mock_exec):
        mock_exec.return_value = (1, '')
        rval = si3_controller._get_si3rst('namelist.nl')
        self.assertEqual(rval, None)
        mock_exec.assert_called_once_with(
            ['grep', 'cn_icerst_outdir', 'namelist.nl']
        )

    @mock.patch('si3_controller.re.findall')
    def test_verify_si3_rst_one(self, mock_find):
        cyclept = 'YYYYMMDD'
        rst_files = ['rstfile.nc']
        si3_controller._verify_si3_rst(cyclept, 3, rst_files)
        mock_find.assert_called_once_with(
            r'YYYYMMDD_restart_ice(_\d+)?\.nc', 'rstfile.nc'
    )

    @mock.patch('si3_controller.re.findall')
    def test_verify_si3_rst_nproc(self, mock_find):
        cyclept = 'YYYYMMDD'
        rst_files = ['rst1.nc', 'rst2.nc', 'rst3.nc']
        si3_controller._verify_si3_rst(cyclept, 3, rst_files)
        expected_find = [
            mock.call(r'YYYYMMDD_restart_ice(_\d+)?\.nc', 'rst1.nc'),
            mock.call(r'YYYYMMDD_restart_ice(_\d+)?\.nc', 'rst2.nc'),
            mock.call(r'YYYYMMDD_restart_ice(_\d+)?\.nc', 'rst3.nc')
        ]

        for call in expected_find:
            self.assertIn(call, mock_find.mock_calls)

    @mock.patch('si3_controller.re.findall')
    def test_verify_si3_rst_nprocplus(self, mock_find):
        cyclept = 'YYYYMMDD'
        rst_files = ['rst1.nc', 'rst2.nc', 'rst3.nc']
        si3_controller._verify_si3_rst(cyclept, 2, rst_files)
        expected_find = [
            mock.call(r'YYYYMMDD_restart_ice(_\d+)?\.nc', 'rst1.nc'),
            mock.call(r'YYYYMMDD_restart_ice(_\d+)?\.nc', 'rst2.nc'),
            mock.call(r'YYYYMMDD_restart_ice(_\d+)?\.nc', 'rst3.nc')
        ]

        for call in expected_find:
            self.assertIn(call, mock_find.mock_calls)

    @mock.patch('si3_controller.re.findall', return_value=[])
    def test_verify_si3_rst_fail(self, mock_find):
        cyclept = 'YYYYMMDD'
        rst_files = ['rst1.nc', 'rst2.nc', 'rst3.nc']
        with self.assertRaises(SystemExit) as context:
            si3_controller._verify_si3_rst(cyclept, 2, rst_files)
        self.assertEqual(context.exception.code,
                         si3_controller.error.MISSING_MODEL_FILE_ERROR)

    def test_load_envar(self):
        si3_envars = si3_controller.dr_env_lib.env_lib.LoadEnvar()
        rval = si3_controller._load_environment_variables(si3_envars)

        # Environment variables should take default values
        self.assertEqual(rval['SI3_NL'], 'namelist_ice_cfg')
        self.assertEqual(rval['SI3_START'], '')


class RunningController(unittest.TestCase):
    '''
    Test the controller run command
    '''
    def setUp(self):
        if 'climatology' not in self.id():
            si3_controller.os.environ['SI3_START'] = 'startfile'

    def tearDown(self):
        try:
            del si3_controller.os.environ['SI3_START']
        except KeyError:
            pass

    @mock.patch('si3_controller._setup_si3_controller')
    @mock.patch('si3_controller._finalize_si3_controller')
    def test_run_controller_runmode(self, mock_finalize, mock_setup):
        mock_setup.return_value = 'exe_envar'
        self.assertEqual(si3_controller.run_controller('common_envar',
                                                       'restart_ctl',
                                                       'nemo_nproc',
                                                       'RUNID',
                                                       'verify_restart',
                                                       'nemo_dump_time',
                                                       'run_controller'),
                         ('exe_envar', ''))
        mock_setup.assert_called_once_with('common_envar', 'restart_ctl',
                                           'nemo_nproc', 'RUNID',
                                           'verify_restart', 'nemo_dump_time')
        mock_finalize.assert_not_called()

    @mock.patch('si3_controller._setup_si3_controller')
    @mock.patch('si3_controller._set_launcher_command')
    @mock.patch('si3_controller._finalize_si3_controller')
    def test_run_controller_finalize(
        self, mock_finalize, mock_launcher_cmd, mock_setup):

        self.assertEqual(si3_controller.run_controller('common_envar',
                                                       'restart_ctl',
                                                       'nemo_nproc',
                                                       'RUNID',
                                                       'verify_restart',
                                                       'nemo_dump_time',
                                                       'finalize'),
                         (None, None))
        mock_finalize.assert_called_once_with()
        mock_setup.assert_not_called()
        mock_launcher_cmd.assert_not_called()

    @mock.patch('si3_controller._check_si3nl_envar', return_value=0)
    @mock.patch('si3_controller._get_si3rst', return_value='startfiledir')
    @mock.patch('si3_controller.os.listdir', return_value=[])
    @mock.patch('si3_controller.common.remove_file')
    @mock.patch('si3_controller.os.path.isfile', return_value=True)
    @mock.patch('si3_controller.os.symlink')
    def test_setup_nrun(self, mock_link, mock_isfile, mock_rm, mock_lsdir,
                        mock_getrst, mock_checkenv):
        common_env = { 'CONTINUE': 'false' }
        expected_info = ['si3_controller: New SI3 run',
                         'Removing old SI3 restart data']

        with mock.patch('sys.stdout', new=io.StringIO()) as patch_out:
            rval = si3_controller._setup_si3_controller(
                common_env, 'restart_ctl', 3, 'RUNID', 'verify_rst', 'YYYYMMDD'
            )

        mock_checkenv.assert_called_once()
        self.assertTrue(isinstance(mock_checkenv.call_args[0][0],
                                   si3_controller.dr_env_lib.env_lib.LoadEnvar))
        mock_getrst.assert_called_once_with('namelist_ice_cfg')
        mock_lsdir.assert_called_once_with('startfiledir')
        mock_rm.assert_called_once_with('restart_ice.nc')
        mock_isfile.mock_calls = [mock.call('startfile'), mock.call('startfile')]
        mock_link.assert_called_once_with('startfile', 'restart_ice.nc')
        self.assertEqual(rval.env_vars, {'SI3_START': 'startfile',
                                         'SI3_NL': 'namelist_ice_cfg'})
        for infostr in expected_info:
            self.assertIn(infostr, patch_out.getvalue())

    @mock.patch('si3_controller._check_si3nl_envar', return_value=0)
    @mock.patch('si3_controller._get_si3rst', return_value='startfiledir')
    @mock.patch('si3_controller.os.listdir', return_value=[])
    @mock.patch('si3_controller.common.remove_file')
    def test_setup_nrun_climatology(self, mock_rm, mock_lsdir,
                                    mock_getrst, mock_checkenv):
        common_env = { 'CONTINUE': 'false' }
        expected_info = ['si3_controller: New SI3 run',
                         'SI3 is starting from climatology']

        with mock.patch('sys.stdout', new=io.StringIO()) as patch_out:
            rval = si3_controller._setup_si3_controller(
                common_env, 'restart_ctl', 3, 'RUNID', 'verify_rst', 'YYYYMMDD'
                )

        mock_checkenv.assert_called_once()
        self.assertTrue(isinstance(mock_checkenv.call_args[0][0],
                                   si3_controller.dr_env_lib.env_lib.LoadEnvar))
        mock_getrst.assert_called_once_with('namelist_ice_cfg')
        mock_lsdir.assert_called_once_with('startfiledir')
        mock_rm.assert_called_once_with('restart_ice.nc')
        self.assertEqual(rval.env_vars, {'SI3_START': '',
                                         'SI3_NL': 'namelist_ice_cfg'})
        for infostr in expected_info:
            self.assertIn(infostr, patch_out.getvalue())

    @mock.patch('si3_controller._check_si3nl_envar', return_value=0)
    @mock.patch('si3_controller._get_si3rst', return_value='startfiledir')
    @mock.patch('si3_controller.os.listdir', return_value=[])
    @mock.patch('si3_controller.common.remove_file')
    def test_setup_nrun_missing_start(self, mock_rm, mock_lsdir,
                                      mock_getrst, mock_checkenv):
        common_env = { 'CONTINUE': 'false' }
        expected_err = 'file startfile not found'

        with self.assertRaises(SystemExit) as context:
            with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
                rval = si3_controller._setup_si3_controller(
                    common_env, 'restart_ctl', 3, 'RUNID', 'verify_rst', 'YYYYMMDD'
                )

        self.assertEqual(context.exception.code,
                         si3_controller.error.MISSING_MODEL_FILE_ERROR)
        self.assertIn(expected_err, patch_err.getvalue())

    @mock.patch('si3_controller._check_si3nl_envar', return_value=0)
    @mock.patch('si3_controller._get_si3rst', return_value='startfiledir')
    @mock.patch('si3_controller.os.listdir')
    @mock.patch('si3_controller.common.remove_file')
    @mock.patch('si3_controller.os.path.isfile', return_value=True)
    @mock.patch('si3_controller.os.symlink')
    def test_setup_crun_nproc(self, mock_link, mock_isfile, mock_rm, mock_lsdir,
                        mock_getrst, mock_checkenv):
        common_env = { 'CONTINUE': 'true' }
        expected_info = ['si3_controller: New SI3 run',
                         'SI3 is starting from climatology']
        mock_lsdir.return_value = ['runid_11112233_restart_ice',
                                   'runid_22223344_restart_ice']

        with mock.patch('sys.stdout', new=io.StringIO()) as patch_out:
            rval = si3_controller._setup_si3_controller(
                common_env, 'restart_ctl', 3, 'RUNID', 'True1', '22223344'
            )

        mock_checkenv.assert_called_once()
        self.assertTrue(isinstance(mock_checkenv.call_args[0][0],
                                   si3_controller.dr_env_lib.env_lib.LoadEnvar))
        mock_getrst.assert_called_once_with('namelist_ice_cfg')
        mock_lsdir.assert_called_once_with('startfiledir')
        rm_calls = [mock.call('restart_ice.nc')]
        link_calls = []
        for proc in range(3):
            rm_calls.append(mock.call(f'restart_ice_000{proc}.nc'))
            link_calls.append(mock.call(
                f'startfiledir/RUNIDo_22223344_restart_ice_000{proc}.nc',
                f'restart_ice_000{proc}.nc'
            ))
        self.assertListEqual(mock_rm.mock_calls, rm_calls)
        self.assertListEqual(mock_link.mock_calls, link_calls)
        self.assertEqual(rval.env_vars, {'SI3_START': 'startfile',
                                         'SI3_NL': 'namelist_ice_cfg'})
        for infostr in expected_info:
            self.assertIn(infostr, patch_out.getvalue())

    @mock.patch('si3_controller._check_si3nl_envar', return_value=0)
    @mock.patch('si3_controller._get_si3rst', return_value='startfiledir')
    @mock.patch('si3_controller.os.listdir')
    @mock.patch('si3_controller.common.remove_file')
    @mock.patch('si3_controller.os.path.isfile', return_value=True)
    @mock.patch('si3_controller.os.symlink')
    def test_setup_crun_nproc(self, mock_link, mock_isfile, mock_rm, mock_lsdir,
                        mock_getrst, mock_checkenv):
        common_env = { 'CONTINUE': 'true' }
        expected_info = ['si3_controller: Restart data available',
                         'Restarting from previous task output']
        mock_lsdir.return_value = ['runid_11112233_restart_ice',
                                   'runid_22223344_restart_ice']

        with mock.patch('sys.stdout', new=io.StringIO()) as patch_out:
            rval = si3_controller._setup_si3_controller(
                common_env, 'restart_ctl', 3, 'RUNID', 'True1', '22223344'
            )

        mock_checkenv.assert_called_once()
        self.assertTrue(isinstance(mock_checkenv.call_args[0][0],
                                   si3_controller.dr_env_lib.env_lib.LoadEnvar))
        mock_getrst.assert_called_once_with('namelist_ice_cfg')
        mock_lsdir.assert_called_once_with('startfiledir')
        rm_calls = [mock.call('restart_ice.nc')]
        link_calls = []
        for proc in range(3):
            rm_calls.append(mock.call(f'restart_ice_000{proc}.nc'))
            link_calls.append(mock.call(
                f'startfiledir/RUNIDo_22223344_restart_ice_000{proc}.nc',
                f'restart_ice_000{proc}.nc'
            ))
        self.assertListEqual(mock_rm.mock_calls, rm_calls)
        self.assertListEqual(mock_link.mock_calls, link_calls)
        self.assertEqual(rval.env_vars, {'SI3_START': 'startfile',
                                         'SI3_NL': 'namelist_ice_cfg'})
        for infostr in expected_info:
            self.assertIn(infostr, patch_out.getvalue())

    @mock.patch('si3_controller._check_si3nl_envar', return_value=0)
    @mock.patch('si3_controller._get_si3rst', return_value='startfiledir')
    @mock.patch('si3_controller.os.listdir')
    @mock.patch('si3_controller.common.remove_file')
    @mock.patch('si3_controller.os.path.isfile')
    @mock.patch('si3_controller.os.symlink')
    def test_setup_crun_single(self, mock_link, mock_isfile, mock_rm, mock_lsdir,
                        mock_getrst, mock_checkenv):
        common_env = { 'CONTINUE': 'true' }
        expected_info = ['si3_controller: Restart data available',
                         'Restarting from previous task output',
                         'No SI3 sub-PE restarts found']
        mock_lsdir.return_value = ['runid_11112233_restart_ice',
                                   'runid_22223344_restart_ice']
        mock_isfile.side_effect=[True,                # Latest dump file
                                 False, False, False, # Sub-PE files
                                 True]                # Full domain file
        with mock.patch('sys.stdout', new=io.StringIO()) as patch_out:
            rval = si3_controller._setup_si3_controller(
                common_env, 'restart_ctl', 3, 'RUNID', 'True1', '22223344'
            )

        mock_checkenv.assert_called_once()
        self.assertTrue(isinstance(mock_checkenv.call_args[0][0],
                                   si3_controller.dr_env_lib.env_lib.LoadEnvar))
        mock_getrst.assert_called_once_with('namelist_ice_cfg')
        mock_lsdir.assert_called_once_with('startfiledir')

        rm_calls = [mock.call('restart_ice.nc')]
        for proc in range(3):
            rm_calls.append(mock.call(f'restart_ice_000{proc}.nc'))
        rm_calls.append(mock.call('restart_ice.nc'))
        self.assertListEqual(mock_rm.mock_calls, rm_calls)

        link_calls = [mock.call('startfiledir/RUNIDo_22223344_restart_ice.nc',
                                'restart_ice.nc')]
        self.assertListEqual(mock_link.mock_calls, link_calls)

        self.assertEqual(rval.env_vars, {'SI3_START': 'startfile',
                                         'SI3_NL': 'namelist_ice_cfg'})
        for infostr in expected_info:
            self.assertIn(infostr, patch_out.getvalue())

    @mock.patch('si3_controller._check_si3nl_envar', return_value=0)
    @mock.patch('si3_controller._get_si3rst', return_value='startfiledir')
    @mock.patch('si3_controller.os.listdir')
    @mock.patch('si3_controller.common.remove_file')
    @mock.patch('si3_controller.os.path.isfile')
    @mock.patch('si3_controller.os.symlink')
    def test_setup_crun_fail(self, mock_link, mock_isfile, mock_rm, mock_lsdir,
                        mock_getrst, mock_checkenv):
        common_env = { 'CONTINUE': 'true' }
        expected_info = ['si3_controller: No restart data available']
        mock_lsdir.return_value = ['runid_11112233_restart_ice',
                                   'runid_22223344_restart_ice']
        mock_isfile.side_effect=[False] # Latest dump file
        with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
            with self.assertRaises(SystemExit) as context:
                rval = si3_controller._setup_si3_controller(
                    common_env, 'restart_ctl', 3, 'RUNID', 'True1', '22223344'
                )
        self.assertEqual(context.exception.code,
                         si3_controller.error.MISSING_MODEL_FILE_ERROR)

        mock_checkenv.assert_called_once()
        self.assertTrue(isinstance(mock_checkenv.call_args[0][0],
                                   si3_controller.dr_env_lib.env_lib.LoadEnvar))
        mock_getrst.assert_called_once_with('namelist_ice_cfg')
        mock_lsdir.assert_called_once_with('startfiledir')

        rm_calls = [mock.call('restart_ice.nc')]
        self.assertListEqual(mock_rm.mock_calls, rm_calls)
        self.assertListEqual(mock_link.mock_calls, [])

        for infostr in expected_info:
            self.assertIn(infostr, patch_err.getvalue())
