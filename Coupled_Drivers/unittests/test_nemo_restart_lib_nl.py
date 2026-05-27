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
    test_nemo_restart_lib_nl.py

DESCRIPTION
    Test the 'namelist' functions in the NEMO restart library
'''

import unittest
import unittest.mock as mock

import error
import nemo_restart_lib

class TestSetupPreviousRestart(unittest.TestCase):
    '''
    Test the sourcing from previous work directories in NEMO library
    '''
    @mock.patch('nemo_restart_lib.sys.stdout.write')
    @mock.patch('nemo_restart_lib._setup_previous_restart_nl_nrun')
    @mock.patch('nemo_restart_lib._setup_previous_restart_nl_crun')
    @mock.patch('nemo_restart_lib.os.path.isfile')
    def test_setup_previous_restart_nl_new_run(
            self, mock_isfile, mock_setup_crun, mock_setup_nrun, mock_stdout):
        '''Test correct calls for NRUN'''
        common_env = {'CONTINUE': 'false'}
        rvalue = nemo_restart_lib.setup_previous_restart_nl(
            common_env, 'nemo_rst', 'ice_rst', 'top_rst', None)
        self.assertEqual(rvalue, '.')
        mock_stdout.assert_called_once_with('[INFO] New nemo run\n')
        mock_setup_nrun.assert_called_once_with(
            'nemo_rst', 'ice_rst', 'top_rst')
        mock_setup_crun.assert_not_called()
        mock_isfile.assert_not_called()

    @mock.patch('nemo_restart_lib.sys.stdout.write')
    @mock.patch('nemo_restart_lib._setup_previous_restart_nl_nrun')
    @mock.patch('nemo_restart_lib._setup_previous_restart_nl_crun')
    @mock.patch('nemo_restart_lib.os.path.isfile')
    def test_setup_previous_restart_nl_cont_run(
            self, mock_isfile, mock_setup_crun, mock_setup_nrun, mock_stdout):
        '''Test correct calls for CRUN'''
        common_env = {'CONTINUE': 'true'}
        mock_isfile.return_value = True
        mock_setup_crun.return_value = 'setup_crun'
        rvalue = nemo_restart_lib.setup_previous_restart_nl(
            common_env, 'nemo_rst', 'ice_rst', 'top_rst', 'nemo_dump')
        self.assertEqual(rvalue, 'setup_crun')
        mock_stdout.assert_called_once_with(
            '[INFO] Restart data available in NEMO restart '
            'directory nemo_rst. Restarting from previous task output\n'
            '[INFO] Sourcing namelist file from the work '
            'directory of the previous cycle\n')
        mock_setup_nrun.assert_not_called()
        mock_setup_crun.assert_called_once()
        mock_isfile.assert_called_once_with('nemo_dump')

    @mock.patch('nemo_restart_lib.sys.stderr.write')
    @mock.patch('nemo_restart_lib._setup_previous_restart_nl_nrun')
    @mock.patch('nemo_restart_lib._setup_previous_restart_nl_crun')
    @mock.patch('nemo_restart_lib.os.path.isfile')
    def test_setup_previous_restart_nl_fail(self, mock_isfile, mock_setup_crun,
                                            mock_setup_nrun, mock_stderr):
        '''Test the failure mode'''
        common_env = {'CONTINUE': 'true'}
        mock_isfile.return_value = False
        with self.assertRaises(SystemExit) as context:
            nemo_restart_lib.setup_previous_restart_nl(
                common_env, 'nemo_rst', 'ice_rst', 'top_rst', 'nemo_dump')
        self.assertEqual(context.exception.code, error.MISSING_MODEL_FILE_ERROR)
        mock_setup_nrun.assert_not_called()
        mock_setup_crun.assert_not_called()
        mock_isfile.assert_called_once_with('nemo_dump')
        mock_stderr.assert_called_once_with(
            '[FAIL] No restart data available in NEMO restart '
            'directory:\n  nemo_rst\n')

    @mock.patch('nemo_restart_lib.glob.glob')
    @mock.patch('nemo_restart_lib.common.remove_file')
    def test_setup_previous_restart_nl_nrun(self, mock_rmfile, mock_glob):
        '''Test the removal for restarts for NRUNS so we dont acidentally
        pick them up'''
        mock_glob.side_effect = [['path1'], ['path2'], ['path3'], ['path4']]
        nemo_restart_lib._setup_previous_restart_nl_nrun(
            'nemo_rst', 'ice_rst', 'top_rst')
        mock_glob.assert_has_calls([mock.call('nemo_rst/*restart*'),
                                    mock.call('nemo_rst/*trajectory*'),
                                    mock.call('ice_rst/*restart*'),
                                    mock.call('top_rst/*restart*')])
        mock_rmfile.assert_has_calls([mock.call('path1'),
                                      mock.call('path2'),
                                      mock.call('path3'),
                                      mock.call('path4')])

    @mock.patch('nemo_restart_lib.glob.glob')
    @mock.patch('nemo_restart_lib.common.remove_file')
    def test_setup_previous_restart_nl_nrun_no_ice(
            self, mock_rmfile, mock_glob):
        '''Test the removal for restarts for NRUNS so we dont acidentally
        pick them up. In this case there is no ice restart set'''
        mock_glob.side_effect = [['path1', 'path2'], ['path3']]
        nemo_restart_lib._setup_previous_restart_nl_nrun(
            'nemo_rst', None, None)
        mock_glob.assert_has_calls([mock.call('nemo_rst/*restart*'),
                                    mock.call('nemo_rst/*trajectory*')])
        mock_rmfile.assert_has_calls([mock.call('path1'),
                                      mock.call('path2'),
                                      mock.call('path3')])

    def test_setup_previous_restart_nl_crun_cont_from_fail(self):
        '''If continue from fail, we run from the current work directory
        and so the path returned will be a blank string'''
        common_env = {'CONTINUE_FROM_FAIL': 'true'}
        self.assertEqual(
            '', nemo_restart_lib._setup_previous_restart_nl_crun(common_env))

    @mock.patch('common.find_previous_workdir')
    def test_setup_previous_restart_nl_crun_sub_cycle(self, mock_workdir):
        '''Test the Coupled NWP sub cycling mode'''
        common_env = {'CONTINUE_FROM_FAIL': 'false',
                      'CNWP_SUB_CYCLING': 'True',
                      'CYLC_TASK_CYCLE_POINT': 'cycle_point',
                      'CYLC_TASK_WORK_DIR': 'work_dir',
                      'CYLC_TASK_NAME': 'task_name',
                      'CYLC_TASK_PARAM_run': 'param_run'}
        mock_workdir.return_value = 'prev_workdir'
        self.assertEqual('prev_workdir',
                         nemo_restart_lib._setup_previous_restart_nl_crun(
                             common_env))
        mock_workdir.assert_called_once_with(
            'cycle_point', 'work_dir', 'task_name', 'param_run')

    @mock.patch('common.find_previous_workdir')
    def test_setup_previous_restart_nl_crun_climate(self, mock_workdir):
        '''Test the climate cycling mode'''
        common_env = {'CONTINUE_FROM_FAIL': 'false',
                      'CNWP_SUB_CYCLING': 'false',
                      'CYLC_TASK_CYCLE_POINT': 'cycle_point',
                      'CYLC_TASK_WORK_DIR': 'work_dir',
                      'CYLC_TASK_NAME': 'task_name'}
        mock_workdir.return_value = 'prev_workdir'
        self.assertEqual('prev_workdir',
                         nemo_restart_lib._setup_previous_restart_nl_crun(
                             common_env))
        mock_workdir.assert_called_once_with('cycle_point', 'work_dir',
                                             'task_name')
