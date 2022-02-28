#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2022 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    test_update_namcouple.py

DESCRIPTION
    Tests the updating of the namcouple file
'''

import unittest
import unittest.mock as mock

import filecmp
import inspect
import io
import os

import error
import update_namcouple

class TestUpdateComponents(unittest.TestCase):
    '''
    Test the update components class
    '''
    def _create_test_class(self):
        '''Create the test class'''
        self.updatecomponents \
            = update_namcouple._UpdateComponents('common_envs')

    def _destroy_test_class(self):
        '''Destroy the test class'''
        del self.updatecomponents

    def test_failed_update(self):
        '''Test we return an error message for incorrect component'''
        self._create_test_class()
        expected_err = '[FAIL] update_namcouple can not update the' \
                       ' nomodel component'
        with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
            with self.assertRaises(SystemExit) as context:
                self.updatecomponents.update('nomodel')
        self.assertEqual(patch_err.getvalue(), expected_err)
        self.assertEqual(
            context.exception.code, error.INVALID_DRIVER_ARG_ERROR)
        self._destroy_test_class()

    def test_update(self):
        '''
        Test the update calls the correct functions
        '''
        self._create_test_class()
        mock_um = mock.MagicMock()
        mock_nemo = mock.MagicMock()
        mock_mct = mock.MagicMock()
        self.updatecomponents.models_to_update = {'um': mock_um,
                                                  'nemo': mock_nemo,
                                                  'mct': mock_mct}
        self.updatecomponents.update('um mct nemo')
        mock_um.assert_called_once_with()
        mock_nemo.assert_called_once_with()
        mock_mct.assert_called_once_with()

        self._destroy_test_class()

    def test_check_methods_exist(self):
        '''
        Check that update details methods exist for NEMO, UM and MCT
        even if they do nothing
        '''
        self._create_test_class()
        self.assertTrue(inspect.ismethod(self.updatecomponents.add_um_details))
        self.assertTrue(inspect.ismethod(
            self.updatecomponents.add_nemo_details))
        self.assertTrue(inspect.ismethod(self.updatecomponents.add_mct_details))
        self._destroy_test_class()

    @mock.patch('update_namcouple.common.setup_runtime')
    def test_add_mct_details(self, mock_setup_runtime):
        '''
        Test the updating of the MCT details in the namcouple file
        '''
        def clearup_test():
            '''Remove our two dummy namcouple files'''
            files_to_remove = ('namcouple', 'expected_namcouple')
            for file_to_remove in files_to_remove:
                try:
                    os.remove(file_to_remove)
                except FileNotFoundError:
                    pass

        def create_test_namcouple():
            '''Create our dummy namcouple'''
            contents = """#Leading comment
 $NFIELDS
          74
 $END

 $RUNTIME
     
         45
         56
 $END
        
 $NBMODEL
   3 toyatm toyoce xios.x 99 99 99
 $END"""
            with open('namcouple', 'w') as namcouple_fh:
                namcouple_fh.write(contents)

        def create_expected_namcouple():
            '''Create a namcouple file containing expected output'''
            contents = """#Leading comment
 $NFIELDS
          74
 $END
#
 $RUNTIME
#
# Runtime setting automated via suite run length settings
  100
 $END
#
 $NBMODEL
   3 toyatm toyoce xios.x 99 99 99
 $END"""
            with open('expected_namcouple', 'w') as namcouple_fh:
                namcouple_fh.write(contents)

        create_test_namcouple()
        create_expected_namcouple()
        self._create_test_class()
        mock_setup_runtime.return_value=100
        self.updatecomponents.update('mct')
        # check the files are identical - the False indicates that this is a
        # non shallow comparison and the file contents will be compared
        self.assertTrue(filecmp.cmp('namcouple', 'expected_namcouple', False))
        self._destroy_test_class()
        clearup_test()


class TestStartEditNamcouple(unittest.TestCase):
    '''
    Test the function _start_edit_namcouple
    '''
    @mock.patch('update_namcouple.common.open_text_file')
    def test__start_edit_namcouple_default_name(self, mock_open_text_file):
        '''Test the function with default filename namcouple'''
        mock_open_text_file.side_effect = ['namcfilein', 'namcfileout']
        rvalue = update_namcouple._start_edit_namcouple()
        mock_open_text_file.assert_has_calls(
            [mock.call('namcouple', 'r'),
             mock.call('namcouple.out', 'w')])
        self.assertEqual(rvalue, ('namcfilein', 'namcfileout'))

    @mock.patch('update_namcouple.common.open_text_file')
    def test__start_edit_namcouple_custom_name(self, mock_open_text_file):
        '''Test the function with custom filename custom'''
        mock_open_text_file.side_effect = ['namcfilein', 'namcfileout']
        rvalue = update_namcouple._start_edit_namcouple('custom')
        mock_open_text_file.assert_has_calls(
            [mock.call('custom', 'r'),
             mock.call('custom.out', 'w')])
        self.assertEqual(rvalue, ('namcfilein', 'namcfileout'))


class TestEndEditNamcouple(unittest.TestCase):
    '''
    Test the function _end_edit_namcouple
    '''
    @mock.patch('update_namcouple.os.rename')
    def test__end_edit_namcouple(self, mock_rename):
        '''Test the ending fuction using magic mocks for the filehandles'''
        mock_file_in = mock.MagicMock()
        mock_file_out = mock.MagicMock()
        mock_file_in.name = 'inname'
        mock_file_out.name = 'outname'
        update_namcouple._end_edit_namcouple(mock_file_in, mock_file_out)
        mock_rename.assert_called_once_with('outname', 'inname')
        mock_file_in.close.assert_called_with()
        mock_file_out.close.assert_called_with()

class TestUpdate(unittest.TestCase):
    '''
    Test the interface function update
    '''
    @mock.patch('update_namcouple._UpdateComponents')
    def test_update(self, mock_update):
        '''Test the update function'''
        mock_update.return_value = mock.MagicMock()
        update_namcouple.update('models', 'common_envs')
        mock_update.assert_called_once_with('common_envs')
        mock_update.return_value.update.assert_called_with('models')
