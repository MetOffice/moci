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
'''

import unittest
import unittest.mock as mock

import nemo_driver

class TestRunSubmodelControllers(unittest.TestCase):
    '''
    Test the code that runs the sub model controllers from the nemo drivers
    '''
    def setUp(self):
        '''Set up a mock controller object to test the run controller'''
        class MockController:
            '''A mock controller to test the calls to run controller'''
            def __init__(self, submodel):
                '''Inititalise with a string containing the submodel name'''
                self.name = submodel
                self.expected_arguments = ()
            def run_controller(self, *arguments):
                '''A function to test the running of the controller'''
                assert arguments == self.expected_arguments
            def clear(self):
                '''Clear expected_arguments'''
                self.expected_arguments = ()
        self.top_controller = MockController('TOP')
        self.si3_controller = MockController('SI3')

    @mock.patch('nemo_driver.sys.stdout.write')
    @mock.patch('nemo_driver.importlib.import_module')
    def test_no_controllers(self, mock_import, mock_stdout):
        '''Test the code runs correctly if no controllers are used'''
        nemo_envar = {'L_OCN_PASS_TRC': 'False'}
        common_envar = {'models': 'um nemo'}
        nemo_driver._run_submodel_controllers(nemo_envar, common_envar,
                                              None, None, None)
        mock_stdout.assert_called_once_with(
            '[INFO] nemo_driver: Passive tracer code not active.\n')
        mock_import.assert_not_called()

    @mock.patch('nemo_driver.sys.stdout.write')
    @mock.patch('nemo_driver.importlib.import_module')
    def test_top_only(self, mock_import, mock_stdout):
        '''Test that a top only call works, with upper case T'''
        nemo_envar = {'L_OCN_PASS_TRC': 'True',
                      'NEMO_NPROC': '10'}
        common_envar = {'models': 'um nemo',
                        'RUNID': 'runid',
                        'DRIVERS_VERIFY_RST': 'verify_rst'}
        #expected_arguments_to_controller
        expected_args = (common_envar, 'restart_ctl', 10, 'runid',
                         'verify_rst', 'nemo_dump_time', 'mode')
        self.top_controller.expected_arguments = expected_args
        mock_import.return_value = self.top_controller
        nemo_driver._run_submodel_controllers(nemo_envar, common_envar,
                                              'restart_ctl', 'nemo_dump_time',
                                              'mode')
        mock_stdout.assert_has_calls(
            [mock.call('[INFO] nemo_driver: Passive tracer code is active.\n'),
             mock.call('[INFO] Calling top_controller in mode mode\n')])
        mock_import.assert_called_once_with('top_controller')
        self.top_controller.clear()
