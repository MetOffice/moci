#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021-2026 Met Office. All rights reserved.

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

import generate_nam_s1

class TestGlobal(unittest.TestCase):
    '''
    Test any global variables in the module
    '''
    def test_error(self):
        '''An error code must be between 1 and 127 inclusive'''
        self.assertTrue(1 <= generate_nam_s1.GENERATE_SECTION1_ERROR <= 127)

class TestNlogprtVal1(unittest.TestCase):
    '''
    Test the validation of the values for nlogprt value 1
    '''
    @mock.patch('generate_nam_s1.sys.stdout.write')
    def test_check_nlogprt_val1_correct_values(self, mock_stdout):
        '''Test the passing in of correct values to nlogprt gives the
        correct values out again'''
        correct_vals = [0, 1, 2, 5, 10, 12, 15, 20, 30]
        output_vals = []
        for val in correct_vals:
            output_vals.append(generate_nam_s1.check_nlogprt_val1(val))
        self.assertEqual(output_vals, correct_vals)
        mock_stdout.assert_not_called()

    @mock.patch('generate_nam_s1.sys.stdout.write')
    def test_check_nlogprt_val1_negative_value(self, mock_stdout):
        '''Test the passing in of a negative value to check it gives zero'''
        self.assertEqual(generate_nam_s1.check_nlogprt_val1(-1), 0)
        mock_stdout.assert_called_once()

    @mock.patch('generate_nam_s1.sys.stdout.write')
    def test_check_nlogprt_val1_high_value(self, mock_stdout):
        '''Test the passing in of a value over 30 to check it gives 30'''
        self.assertEqual(generate_nam_s1.check_nlogprt_val1(32), 30)
        mock_stdout.assert_called_once()

    @mock.patch('generate_nam_s1.sys.stdout.write')
    def test_check_nlogprt_val1_wrong_values(self, mock_stdout):
        '''Test the passing in of values between 0 and 30 to check the
        rounding'''
        expected_values = [0, 1, 2,
                           5, 5, 5,
                           10, 10, 10, 10, 10,
                           12, 12,
                           15, 15, 15,
                           20, 20, 20, 20, 20,
                           30, 30, 30, 30, 30, 30, 30, 30, 30, 30]
        input_values = list(range(0, 31))
        for in_val in input_values:
            self.assertEqual(generate_nam_s1.check_nlogprt_val1(in_val),
                             expected_values[in_val])
        self.assertEqual(mock_stdout.call_count, 22)

    @mock.patch('generate_nam_s1.sys.stdout.write')
    def test_check_nlogprt_val1_info_message(self, mock_stdout):
        '''Test the info message when we do some rounding'''
        expected_msg = '[INFO] The user chosen value for nlogprt is 23,' \
                       ' which is an invalid value. It has been reset to' \
                       ' the next highest valid value, 30\n'
        _ = generate_nam_s1.check_nlogprt_val1(23)
        mock_stdout.assert_called_once_with(expected_msg)


class TestNlogprtVal2(unittest.TestCase):
    '''
    Test the validation of the values for nlogprt value 2
    '''
    @mock.patch('generate_nam_s1.sys.stderr.write')
    def test_correct_values(self, mock_stderr):
        '''Test that with correct values we return nothing, and stderror is
        not called'''
        for val in [-1, 0, 1, 2, 3]:
            assert generate_nam_s1.check_nlogprt_val2(val) == None
        mock_stderr.assert_not_called()

    @mock.patch('generate_nam_s1.sys.stderr.write')
    def test_too_small_value(self, mock_stderr):
        '''Test that if the value is too small we exit, and the error message
        is correct'''
        test_val = -2
        expected_error = '[FAIL] The user chosen value for the second value' \
                         ' for nlogprt is {}. It must be -1, 0, 1, 2, 3\n'. \
                         format(test_val)
        with self.assertRaises(SystemExit) as context:
            generate_nam_s1.check_nlogprt_val2(test_val)
        self.assertEqual(context.exception.code,
                         generate_nam_s1.GENERATE_SECTION1_ERROR)
        mock_stderr.assert_called_once_with(expected_error)

    @mock.patch('generate_nam_s1.sys.stderr.write')
    def test_too_large_value(self, mock_stderr):
        '''Test that if the value is too large we exit, and the error message
        is correct'''
        test_val = 4
        expected_error = '[FAIL] The user chosen value for the second value' \
                         ' for nlogprt is {}. It must be -1, 0, 1, 2, 3\n'. \
                         format(test_val)
        with self.assertRaises(SystemExit) as context:
            generate_nam_s1.check_nlogprt_val2(test_val)
        self.assertEqual(context.exception.code,
                         generate_nam_s1.GENERATE_SECTION1_ERROR)
        mock_stderr.assert_called_once_with(expected_error)


class TestCheckNfields(unittest.TestCase):
    '''
    Test the validation and automatic setting of the value for nfields
    '''
    @mock.patch('generate_nam_s1.sys.stdout.write')
    def test_nfields_gt_n_field_def(self, mock_stdout):
        '''If the value for nfields is greater than that for n_field_def then
        we can run'''
        nfields = 10
        n_field_def = 5
        self.assertEqual(nfields, generate_nam_s1.check_nfields(nfields,
                                                                n_field_def))
        mock_stdout.assert_not_called()

    @mock.patch('generate_nam_s1.sys.stdout.write')
    def test_nfields_eq_n_field_def(self, mock_stdout):
        '''If the value for nfields is equal to that for n_field_def then
        we can run'''
        nfields = 10
        self.assertEqual(nfields, generate_nam_s1.check_nfields(nfields,
                                                                nfields))
        mock_stdout.assert_not_called()

    @mock.patch('generate_nam_s1.sys.stdout.write')
    def test_nfields_lt_n_field_def(self, mock_stdout):
        '''If the value for nfields is less than that for n_field_def then
        we need to set nfields to n_field_def and inform the user'''
        nfields = 5
        n_field_def = 10
        expected_out = '[INFO] The value for nfields in the namelist ({0}) is' \
                       ' smaller than the number of fields required for' \
                       ' coupling ({1}). Automatically redefinining nfields' \
                       ' to {1}\n'.format(nfields, n_field_def)

        self.assertEqual(n_field_def,
                         generate_nam_s1.check_nfields(nfields, n_field_def))
        mock_stdout.assert_called_once_with(expected_out)


class TestBuildItem(unittest.TestCase):
    '''
    Test the building of an item in the namcouple file
    '''
    def test_lowercase_name_no_end_string(self):
        '''Test that a lower case name becomes uppercase with sring value'''
        expected_out = '$NAME\n 2 toyatm junior 99 99\n'
        self.assertEqual(generate_nam_s1.build_item('name',
                                                    '2 toyatm junior 99 99'),
                         expected_out)

    def test_uppercase_name_no_end_integer(self):
        '''Test that an uppercase name stays uppercase with integer value'''
        expected_out = '$NAME\n 99\n'
        self.assertEqual(generate_nam_s1.build_item('NAME', 99), expected_out)

    def test_lower_case_name_end_float(self):
        '''Test that a float value and the optional include_end flag work
        correctly'''
        expected_out = '$NAME\n 99.9\n$END\n'
        self.assertEqual(generate_nam_s1.build_item('NAME', 99.9,
                                                    include_end=True),
                         expected_out)


class TestConstructSectionOne(unittest.TestCase):
    '''
    Test the construction of namcouple section one
    '''
    def setUp(self):
        '''Create the header dictionary'''
        self.header = {'nfields': 'nfields_dict_value',
                       'runtime': 'runtime_value',
                       'nlogprt': ['nlogprt_dict_1', 'nlogprt_dict_2']}

    @mock.patch('generate_nam_s1.check_nfields')
    @mock.patch('generate_nam_s1.check_nlogprt_val1')
    @mock.patch('generate_nam_s1.check_nlogprt_val2')
    @mock.patch('generate_nam_s1.build_item')
    def test_construct_section_one(self, mock_build, mock_v2, mock_v1,
                                   mock_nfields):
        '''Test the function, we return a string containing all the items'''
        mock_nfields.return_value = 'checked_nfields'
        mock_v1.return_value = 'nlogprt_checked_1'
        mock_build.side_effect = ['line1', 'line2', 'line3']

        self.assertEqual(generate_nam_s1.construct_section_one(
            self.header, 'size_fields_dict'), 'line1line2line3')

        mock_nfields.assert_called_once_with('nfields_dict_value',
                                             'size_fields_dict')
        mock_v1.assert_called_once_with('nlogprt_dict_1')
        mock_v2.assert_called_once_with('nlogprt_dict_2')
        build_item_calls = [mock.call('NFIELDS', 'checked_nfields',
                                      include_end=True),
                            mock.call('RUNTIME', 'runtime_value',
                                      include_end=True),
                            mock.call('NLOGPRT',
                                      'nlogprt_checked_1 nlogprt_dict_2',
                                      include_end=True)]
        mock_build.assert_has_calls(build_item_calls)
