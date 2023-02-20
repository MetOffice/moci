#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2023 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''

import unittest
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
    import mock

import cpmip_controller
import dr_env_lib.env_lib

class TestGlobals(unittest.TestCase):
    '''
    The module sets a global variable, check that it is still there or not
    changed
    '''
    def test_globals(self):
        '''
        Test the controller global variables
        '''
        self.assertEqual(cpmip_controller.CORES_PER_NODE,
                         {'broadwell': 36, 'haswell': 32, 'exz': 128})

class TestAllocatedCpus(unittest.TestCase):
    '''
    Test the retrieval of the allocated CPUS from the preopts
    '''
    def test_no_preopts(self):
        '''
        Test what happens if there are no preopt environment variables
        '''
        cpmip_envar = dr_env_lib.env_lib.LoadEnvar()
        self.assertEqual(cpmip_controller.get_allocated_cpus(cpmip_envar),
                         ({'JNR': 0, 'NEMO': 0, 'UM': 0, 'XIOS': 0},
                          {'JNR': 0, 'NEMO': 0, 'UM': 0, 'XIOS': 0}))

    def test_no_nproc(self):
        '''
        Check that an error is raided if the preopts do not contain -n
        '''
        cpmip_envar = dr_env_lib.env_lib.LoadEnvar()
        cpmip_envar['ROSE_LAUNCHER_PREOPTS_UM'] = ''
        with self.assertRaises(ValueError):
            cpmip_controller.get_allocated_cpus(cpmip_envar)


    def test_no_thread_no_hyper(self):
        '''
        Check that everything works correctly without the -d -j options
        '''
        cpmip_envar = dr_env_lib.env_lib.LoadEnvar()
        cpmip_envar['ROSE_LAUNCHER_PREOPTS_UM'] = '-n 64'
        cpmip_envar['ROSE_LAUNCHER_PREOPTS_JNR'] = '-n 32'
        cpmip_envar['ROSE_LAUNCHER_PREOPTS_NEMO'] = '-n 32'
        cpmip_envar['ROSE_LAUNCHER_PREOPTS_XIOS'] = '-n 6'
        self.assertEqual(cpmip_controller.get_allocated_cpus(cpmip_envar),
                         ({'JNR': 32, 'NEMO': 32, 'UM': 64, 'XIOS': 6},
                          {'JNR': 32, 'NEMO': 32, 'UM': 64, 'XIOS': 6}))

    def test_threads_and_hyper(self):
        '''
        Check that picking up threads and hyperthreads works correctly,
        and we igrnore any enviroment variables passed
        '''
        cpmip_envar = dr_env_lib.env_lib.LoadEnvar()
        cpmip_envar['ROSE_LAUNCHER_PREOPTS_UM'] = '-n 64 -d 2'
        cpmip_envar['ROSE_LAUNCHER_PREOPTS_JNR'] = '-n 32 -d 2 -j 2'
        cpmip_envar['ROSE_LAUNCHER_PREOPTS_NEMO'] = '-n 32 --env ENV=3'
        cpmip_envar['ROSE_LAUNCHER_PREOPTS_XIOS'] = '-n 6 -j 2'
        self.assertEqual(cpmip_controller.get_allocated_cpus(cpmip_envar),
                         ({'JNR': 32, 'NEMO': 32, 'UM': 128, 'XIOS': 3},
                          {'JNR': 32, 'NEMO': 32, 'UM': 64, 'XIOS': 6}))


class TestUpdateNamelist(unittest.TestCase):
    '''
    Test the calling of update functions to ensure that the timers are set
    to be running
    '''
    @mock.patch('cpmip_controller.cpmip_um.update_input_for_metrics_um')
    @mock.patch('cpmip_controller.cpmip_nemo.update_namelists_for_timing_nemo')
    def test__update_namelists_for_metrics(self, mock_nl_nemo, mock_nl_um):
        '''
        Test the calling of the updating funcions for UM and NEMO namelists
        '''
        common_envar = {'models': ['um', 'jnr', 'nemo']}
        cpmip_envar = 'CPMIP_envar'
        mock_nl_um.side_effect = ['um_nn_timing_val', 'jnr_nn_timing_val']
        cpmip_controller._update_namelists_for_metrics(common_envar,
                                                       cpmip_envar)
        mock_nl_um.assert_has_calls([mock.call(cpmip_envar, 'SHARED',
                                               'IOSCNTL'),
                                     mock.call(cpmip_envar, 'SHARED_JNR',
                                               'IOSCNTL_JNR')])
        mock_nl_nemo.assert_called_with(cpmip_envar, 'um_nn_timing_val')

    def test__update_namelists_for_metrics_no_um(self):
        '''
        If the function is called in a configuration that runs NEMO but not
        the UM, this should fail with an assertion error
        '''
        common_envar = {'models': ['nemo']}
        assertion_msg = 'To determine metrics for NEMO, we must be' \
                        ' running in a configuration that also includes' \
                        ' the UM'
        with self.assertRaises(AssertionError) as context:
            cpmip_controller._update_namelists_for_metrics(common_envar, None)
        self.assertEqual(str(context.exception), assertion_msg)


class LaunchCommand(unittest.TestCase):
    '''
    Test the generation of launch command
    '''
    def test__set_launch_command(self):
        '''
        No launch command set by a controller
        '''
        self.assertEqual(cpmip_controller._set_launcher_command(None), '')

class RunningController(unittest.TestCase):
    '''
    Test the controller run command
    '''
    @mock.patch('cpmip_controller._setup_cpmip_controller')
    @mock.patch('cpmip_controller._set_launcher_command')
    @mock.patch('cpmip_controller._finalize_cpmip_controller')
    def test_run_controller_run(
            self, mock_finalize, mock_launcher_cmd, mock_setup):
        '''
        Test in run controller mode
        '''
        mock_setup.return_value = 'exe_envar'
        mock_launcher_cmd.return_value = 'launch_cmd'
        self.assertEqual(cpmip_controller.run_controller('run_controller',
                                                         'common_envar'),
                         ('exe_envar', 'launch_cmd'))
        mock_setup.assert_called_once_with('common_envar')
        mock_launcher_cmd.assert_called_once_with('exe_envar')
        mock_finalize.assert_not_called()

    @mock.patch('cpmip_controller._setup_cpmip_controller')
    @mock.patch('cpmip_controller._set_launcher_command')
    @mock.patch('cpmip_controller._finalize_cpmip_controller')
    def test_run_controller_finalize(
            self, mock_finalize, mock_launcher_cmd, mock_setup):
        '''
        Test in finalize mode
        '''
        self.assertEqual(cpmip_controller.run_controller('finalize',
                                                         'common_envar'),
                         (None, None))
        mock_finalize.assert_called_once_with('common_envar')
        mock_setup.assert_not_called()
        mock_launcher_cmd.assert_not_called()
