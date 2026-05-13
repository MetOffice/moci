#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2024-2025 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    test_common.py

DESCRIPTION
    Contains unit tests for the link_drivers.py module.
'''
import unittest
from unittest import mock
import sys
import os
import io

import importlib.util
import importlib.machinery

def import_link_drivers():
    '''
    Add the link_drivers executable file to the system modules list.
    Required due to lack of .py extension.
    '''
    # Path is $PWD if running from a suite
    lib_path = os.path.join(os.path.dirname(__file__), 'link_drivers')
    if not os.path.isfile(lib_path):
        # Path is the parent directory if running from the command line
        lib_path = os.path.join(os.path.dirname(__file__),
                                os.pardir,
                                'link_drivers')

    spec = importlib.util.spec_from_loader(
        'link_drivers',
        importlib.machinery.SourceFileLoader('link_drivers', lib_path)
        )
    if spec is None:
        raise ImportError('Could not load spec for link_drivers at:' + lib_path)

    link_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(link_module)
    sys.modules['link_drivers'] = link_module
    return link_module

link_drivers = import_link_drivers()
MODEL_FILES = ['cice_driver.py', 'jnr_driver.py', 'lfric_driver.py',
               'mct_driver.py', 'nemo_driver.py', 'um_driver.py',
               'xios_driver.py', 'xxxx_driver.py',
               'cpmip_controller.py', 'si3_controller.py', 'top_controller.py']

class TestChecks(unittest.TestCase):
    '''
    Test the private check methods.
    '''

    def test_check_drivers_single(self):
        '''
        Assert single model driver is present
        '''
        with mock.patch('link_drivers.os.path.isfile', return_value=True):
            drivers = link_drivers._check_drivers('nemo')
        self.assertListEqual(drivers, ['nemo'])

    @mock.patch('link_drivers.os.path.isfile')
    def test_check_drivers_remove_controller(self, mock_file):
        '''
        Assert controllers are removed from the models list
        '''
        models = 'nemo top um'
        files_exist = []
        for m in models.split():
            files_exist.append(m + '_driver.py' in MODEL_FILES)
            if not files_exist[-1]:
                files_exist.append(m + '_controller.py' in MODEL_FILES)
        mock_file.side_effect = files_exist

        drivers = link_drivers._check_drivers(models)
        self.assertListEqual(drivers, ['nemo', 'um'])

    @mock.patch('link_drivers.os.path.isfile')
    def test_check_drivers_sort_all(self, mock_file):
        '''
        Assert sorting of drivers alphabetically, but ending with "mct"
        '''
        models = 'cice jnr lfric mct nemo um xios xxxx'
        files_exist = []
        for m in models.split():
            files_exist.append(m + '_driver.py' in MODEL_FILES)
        mock_file.side_effect = files_exist

        drivers = link_drivers._check_drivers(models)

        self.assertListEqual(drivers, ['cice', 'jnr', 'lfric', 'nemo',
                                       'um', 'xios', 'xxxx', 'mct'])

    @mock.patch('link_drivers.os.path.isfile')
    def test_check_drivers_fail(self, mock_file):
        '''
        Assert non existent driver for named model causes SystemExit
        '''
        models = 'nemo dummy'
        files_exist = []
        for m in models.split():
            files_exist.append(m + '_driver.py' in MODEL_FILES)
            if not files_exist[-1]:
                files_exist.append(m + '_controller.py' in MODEL_FILES)
        mock_file.side_effect = files_exist

        expected_err = "Can not find driver file for model dummy"
        with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
            with self.assertRaises(SystemExit) as context:
                _ = link_drivers._check_drivers(models)

        self.assertIn(expected_err, patch_err.getvalue())
        self.assertEqual(context.exception.code,
                         link_drivers.error.MISSING_DRIVER_ERROR)
