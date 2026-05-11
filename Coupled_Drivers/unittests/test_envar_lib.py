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

import io
import os
import dr_env_lib.env_lib

class VerifyErrorCode(unittest.TestCase):
    '''Check the error code is set'''
    def test_error_code(self):
        '''
        A linux error code needs to be between 1 and 127 inclusive
        '''
        self.assertTrue(dr_env_lib.env_lib.ENV_LIB_ERROR in range(1, 128))

class LoadEnvarTests(unittest.TestCase):
    '''
    Unit tests for the Loading Environment class
    '''
    def setUp(self):
        self.load_envar = dr_env_lib.env_lib.LoadEnvar()
        os.environ['TEST_ENVVAR_SET'] = 'iamset'
        os.environ['TEST_ENVAR_LOAD'] = 'test_envar_load'
        os.environ['TEST_LOAD_AND_CHECK'] = 'test_envar_landc'

    def tearDown(self):
        del os.environ['TEST_ENVVAR_SET']
        del os.environ['TEST_ENVAR_LOAD']

    def test_init_load_envar(self):
        '''
        Test instantiation of LoadEnvar object
        '''
        self.assertIsInstance(self.load_envar, dr_env_lib.env_lib.LoadEnvar)
        self.assertEqual(self.load_envar.env_vars, {})

    def test_contains_empty(self):
        '''
        Test for an unset variable dictionary
        '''
        self.assertFalse(self.load_envar.contains('IDONTEXIST'))

    def test_load(self):
        '''
        Test we can load an environemnt variable that exists
        '''
        self.assertEqual(self.load_envar.load_envar('TEST_ENVAR_LOAD'), 0)
        self.assertEqual(self.load_envar.env_vars,
                         {'TEST_ENVAR_LOAD': 'test_envar_load'})

    def test_load_and_check(self):
        '''
        Test we can load an environemnt variable that exists and check its
        value using the getter method
        '''
        self.assertEqual(self.load_envar.load_envar('TEST_LOAD_AND_CHECK'), 0)
        self.assertEqual(self.load_envar['TEST_LOAD_AND_CHECK'],
                         'test_envar_landc')

    def test_load_nonexist(self):
        '''
        Test loading an non existing environment variable
        '''
        self.assertEqual(self.load_envar.load_envar('IDONTEXIST'), 1)

    def test_load_default(self):
        '''
        Test loading a default environment variable
        '''
        expected_output = '[INFO] environment variable DEFAULT doesn\'t exist' \
                          ', setting to default value default\n'
        with mock.patch('sys.stdout', new=io.StringIO()) as patch_output:
            self.assertEqual(self.load_envar.load_envar('DEFAULT', 'default'),
                             0)
            self.assertEqual(patch_output.getvalue(), expected_output)

    def test_is_set_set(self):
        '''
        Test if environemnt variable is set
        '''
        self.assertTrue(self.load_envar.is_set('TEST_ENVVAR_SET'))

    def test_is_set_unset(self):
        '''
        Test if environemnt variable is unset
        '''
        self.assertFalse(self.load_envar.is_set('TEST_ENVVAR_UNSET'))

    def test_get_nonexistent(self):
        '''
        Test getter for non existant variable
        '''
        expected_output = '[FAIL] Attempt to access environment variable' \
                          ' IDONTEXIST. This has not been loaded\n'
        with mock.patch('sys.stderr', new=io.StringIO()) as patch_output:
            with self.assertRaises(SystemExit) as context:
                self.load_envar['IDONTEXIST']
        self.assertEqual(patch_output.getvalue(), expected_output)
        self.assertEqual(context.exception.code,
                         dr_env_lib.env_lib.ENV_LIB_ERROR)


class TestLoadEnvarApplyTriggers(unittest.TestCase):
    '''
    Test the application of applying triggers to the environment variable
    definitions
    '''
    def setUp(self):
        '''
        Set up a dummy environment variable container
        '''
        class DummyEnvarContainer:
            ''' A test environment variable container'''
            def __init__(self):
                '''Constructor'''
                self.reset()
            def reset(self):
                '''reset for next test'''
                self.loaded_variables = {}
            def __getitem__(self, varname):
                '''getter'''
                return self.loaded_variables[varname]
            def load_envar(self, varname, default=None):
                '''dummy load of environment variables'''
                if default:
                    self.loaded_variables[varname] = default
                else:
                    self.loaded_variables[varname] = 'loaded from environment'
                return 0

        self.dummy_envars = DummyEnvarContainer()

    def reset(self):
        '''
        Reset the dummy envar
        '''
        self.dummy_envars.reset()

    @mock.patch('dr_env_lib.env_lib.LoadEnvar')
    def test_null(self, mock_loadenvar):
        '''
        A dictionary with no triggers should pass straight through
        '''
        envar_def = {'EVAR1': {'has_default': False},
                     'EVAR2': {'has_default': True, 'default_val': 3}}
        self.assertEqual(dr_env_lib.env_lib.load_envar_apply_triggers(
            envar_def),
                         envar_def)

    @mock.patch('dr_env_lib.env_lib.LoadEnvar')
    def test_trigger_false(self, mock_loadenvar):
        '''
        With a false trigger we dont do anything, measure a default value
        '''
        self.reset()
        envar_def = {'TRIG': {'has_default': True,
                              'default_val': '0',
                              'triggers': [[lambda my_val: my_val == '0',
                                            ['TEST1']]]},
                     'TEST1': {'has_default': True, 'default_val': 3}}
        envar_expected = {'TRIG': {'has_default': True,
                                   'default_val': '0',
                                   'triggers': None},
                          'TEST1': {'has_default': True, 'default_val': 3}}
        mock_loadenvar.return_value = self.dummy_envars
        returned_envar = dr_env_lib.env_lib.load_envar_apply_triggers(
            envar_def)
        #mangle the returned envar to deal with the deep copy in the function
        #under test
        returned_envar['TRIG']['triggers'] = None
        self.assertEqual(returned_envar, envar_expected)

    @mock.patch('dr_env_lib.env_lib.LoadEnvar')
    def test_trigger_true_default(self, mock_loadenvar):
        '''
        With a true trigger we remove TEST_RM and keep TEST_KP,
        measure a default value
        '''
        self.reset()
        envar_def = {'TRIG': {'has_default': True,
                              'default_val': '0',
                              'triggers': [[lambda my_val: my_val != '0',
                                            ['TEST_RM']]]},
                     'TEST_RM': {'has_default': True, 'default_val': 2},
                     'TEST_KP': {'has_default': True, 'default_val': 3}}

        envar_expected = {'TRIG': {'has_default': True,
                                   'default_val': '0',
                                   'triggers': None},
                          'TEST_KP': {'has_default': True, 'default_val': 3}}
        mock_loadenvar.return_value = self.dummy_envars
        returned_envar = dr_env_lib.env_lib.load_envar_apply_triggers(
            envar_def)
        #mangle the returned envar to deal with the deep copy in the function
        #under test
        returned_envar['TRIG']['triggers'] = None
        self.assertEqual(returned_envar, envar_expected)

    @mock.patch('dr_env_lib.env_lib.LoadEnvar')
    def test_trigger_true_env_two_vars(self, mock_loadenvar):
        '''
        With a true trigger we remove two test functions and measure
        value from environment
        '''
        self.reset()
        envar_def = {'TRIG': {'has_default': False,
                              'triggers': [[lambda my_val: my_val == '0',
                                            ['TEST_RM1', 'TEST_RM2']]]},
                     'TEST_RM1': {'has_default': True, 'default_val': 2},
                     'TEST_RM2': {'has_default': True, 'default_val': 3}}

        envar_expected = {'TRIG': {'has_default': False,
                                   'triggers': None}}
        mock_loadenvar.return_value = self.dummy_envars
        returned_envar = dr_env_lib.env_lib.load_envar_apply_triggers(
            envar_def)
        #mangle the returned envar to deal with the deep copy in the function
        #under test
        returned_envar['TRIG']['triggers'] = None
        self.assertEqual(returned_envar, envar_expected)

    @mock.patch('dr_env_lib.env_lib.LoadEnvar')
    def test_trigger_true_env_two_triggers(self, mock_loadenvar):
        '''
        With a two true triggers we remove two test functions and measure
        value from environment
        '''
        self.reset()
        envar_def = {'TRIG': {'has_default': False,
                              'triggers': [[lambda my_val: my_val == '0',
                                            ['TEST_RM1']],
                                           [lambda my_val: my_val == '1',
                                            ['TEST_RM2']]]},
                     'TEST_RM1': {'has_default': True, 'default_val': 2},
                     'TEST_RM2': {'has_default': True, 'default_val': 3}}

        envar_expected = {'TRIG': {'has_default': False,
                                   'triggers': None}}
        mock_loadenvar.return_value = self.dummy_envars
        returned_envar = dr_env_lib.env_lib.load_envar_apply_triggers(
            envar_def)
        #mangle the returned envar to deal with the deep copy in the function
        #under test
        returned_envar['TRIG']['triggers'] = None
        self.assertEqual(returned_envar, envar_expected)


    @mock.patch('dr_env_lib.env_lib.LoadEnvar')
    def test_trigger_nested_triggers(self, mock_loadenvar):
        '''
        We dont cater for nested triggers, check it works cleanly
        '''
        self.reset()
        envar_def = {'TRIG': {'has_default': False,
                              'triggers': [[lambda my_val: my_val == '0',
                                            ['TEST_RM1']]]},
                     'TEST_RM1': {'has_default': False,
                                  'triggers': [[lambda my_val: my_val == '0',
                                                ['TEST_RM2']]]},
                     'TEST_RM2': {'has_default': False,
                                  'triggers': [[lambda my_val: my_val == '0',
                                                ['TEST_RM3']]]},
                     'TEST_RM3': {'has_default': False}}

        mock_loadenvar.return_value = self.dummy_envars
        expected_err = 'Triggers cant be nested, look at variable TEST_RM1\n' \
                       'Triggers cant be nested, look at variable TEST_RM2\n'
        with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
            with self.assertRaises(SystemExit) as context:
                dr_env_lib.env_lib.load_envar_apply_triggers(envar_def)
        self.assertEqual(patch_err.getvalue(), expected_err)
        self.assertEqual(
            context.exception.code, dr_env_lib.env_lib.ENV_LIB_ERROR)



class TestLoadEnvarCheckDict(unittest.TestCase):
    '''
    Test the checking of the environment variable definitions
    '''
    def setUp(self):
        '''
        Common error messages and definitions
        '''
        self.correct1 = {'default_val': '3'}
        self.correct2 = {'default_val': False}
        self.empty = {}
        self.bad_default = {'default_val': 3}
        self.bad_default_err = '[FAIL] default_val must be of type string or' \
                         ' boolean. For variable FAIL_BAD_DEFAULT it is %s\n' \
                         % (type(self.bad_default['default_val']))

    def test_no_default_val(self):
        '''
        Check that if default_val is not present we return a zero
        '''
        definition = {'EMPTY': self.empty}
        expected_return = 0
        self.assertEqual(
            dr_env_lib.env_lib.load_envar_check_dict(definition),
            expected_return)

    def test_default_not_string(self):
        '''
        Test a failure when the default value is not a string or boolean
        '''
        definition = {'FAIL_BAD_DEFAULT': self.bad_default}
        expected_err = self.bad_default_err
        with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
            with self.assertRaises(SystemExit) as context:
                dr_env_lib.env_lib.load_envar_check_dict(definition)
        self.assertEqual(patch_err.getvalue(), expected_err)
        self.assertEqual(
            context.exception.code, dr_env_lib.env_lib.ENV_LIB_ERROR)

    def test_correct_string(self):
        '''
        Test a correct string default
        '''
        definition = {'CORRECT1': self.correct1}
        self.assertEqual(
            0, dr_env_lib.env_lib.load_envar_check_dict(definition))

    def test_correct_bool(self):
        '''
        Test a correct boolean default
        '''
        definition = {'CORRECT2': self.correct2}
        self.assertEqual(
            0, dr_env_lib.env_lib.load_envar_check_dict(definition))

    def test_compound(self):
        '''
        Test a dictionary with several correct and several failed. Remember
        for the error messages we cant guaruntee the iteration through the
        dictionary will be in any given order
        '''
        definition = {'CORRECT1': self.correct1,
                      'CORRECT2': self.correct2,
                      'FAIL_BAD_DEFAULT': self.bad_default,
                      'EMPTY': self.empty}
        with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
            with self.assertRaises(SystemExit) as context:
                dr_env_lib.env_lib.load_envar_check_dict(definition)
        returned_error = patch_err.getvalue()
        self.assertTrue(self.bad_default_err in returned_error)
        self.assertEqual(context.exception.code,
                         dr_env_lib.env_lib.ENV_LIB_ERROR)

class TestLoadEnvarFromDefinition(unittest.TestCase):
    '''
    Test the loading of a unit test from a definition
    '''
    @mock.patch('dr_env_lib.env_lib.load_envar_apply_triggers')
    @mock.patch('dr_env_lib.env_lib.load_envar_check_dict', return_value=0)
    def test_null(self, mock_check_dict, mock_triggers):
        '''
        If the definition is empty then return the same value we passed in for
        the envar container
        '''
        definition = {}
        envar_container = 'placeholder_container'
        mock_triggers.return_value = {}
        self.assertEqual(
            envar_container,
            dr_env_lib.env_lib.load_envar_from_definition(envar_container,
                                                              definition))

    @mock.patch('dr_env_lib.env_lib.load_envar_apply_triggers')
    @mock.patch('dr_env_lib.env_lib.load_envar_check_dict', return_value=0)
    def test_fail_default_error(self, mock_check_dict, mock_triggers):
        '''
        Test the production of the default error message
        '''
        mock_container = mock.Mock()
        mock_container.load_envar = mock.Mock(return_value=1)
        definition = {'NOT_A_VARIABLE': {}}
        mock_triggers.return_value = definition
        with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
            with self.assertRaises(SystemExit) as context:
                dr_env_lib.env_lib.load_envar_from_definition(
                    mock_container, definition)
        mock_container.load_envar.assert_called_with('NOT_A_VARIABLE')
        mock_triggers.assert_called_with(definition)
        self.assertEqual(context.exception.code,
                         dr_env_lib.env_lib.ENV_LIB_ERROR)
        self.assertEqual(patch_err.getvalue(),
                         '[FAIL] Environment variable NOT_A_VARIABLE not set\n')

    @mock.patch('dr_env_lib.env_lib.load_envar_apply_triggers')
    @mock.patch('dr_env_lib.env_lib.load_envar_check_dict', return_value=0)
    def test_fail_two_errors(self, mock_check_dict, mock_triggers):
        '''
        Test we can stack missing environment variables
        '''
        mock_container = mock.Mock()
        mock_container.load_envar = mock.Mock(return_value=1)
        definition = {'NOT_A_VAR_ONE': {},
                      'NOT_A_VAR_TWO': {}}
        mock_triggers.return_value = definition
        with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
            with self.assertRaises(SystemExit) as context:
                dr_env_lib.env_lib.load_envar_from_definition(
                    mock_container, definition)
        self.assertEqual(context.exception.code,
                         dr_env_lib.env_lib.ENV_LIB_ERROR)
        err_msg = patch_err.getvalue()
        self.assertTrue(
            '[FAIL] Environment variable NOT_A_VAR_ONE not set\n' in err_msg)
        self.assertTrue(
            '[FAIL] Environment variable NOT_A_VAR_TWO not set\n' in err_msg)

    @mock.patch('dr_env_lib.env_lib.load_envar_apply_triggers')
    @mock.patch('dr_env_lib.env_lib.load_envar_check_dict', return_value=0)
    def test_fail_custom_error(self, mock_check_dict, mock_triggers):
        '''
        Test the production of a custom error message
        '''
        mock_container = mock.Mock()
        mock_container.load_envar = mock.Mock(return_value=1)
        definition = {'NOT_A_VARIABLE': {'desc': 'Missing Variable'}}
        mock_triggers.return_value = definition
        with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
            with self.assertRaises(SystemExit) as context:
                dr_env_lib.env_lib.load_envar_from_definition(
                    mock_container, definition)
        mock_container.load_envar.assert_called_with('NOT_A_VARIABLE')
        mock_triggers.assert_called_with(definition)
        self.assertEqual(context.exception.code,
                         dr_env_lib.env_lib.ENV_LIB_ERROR)
        self.assertEqual(patch_err.getvalue(),
                         '[FAIL] Environment variable NOT_A_VARIABLE' \
                         ' containing Missing Variable not set\n')

    @mock.patch('dr_env_lib.env_lib.load_envar_apply_triggers')
    @mock.patch('dr_env_lib.env_lib.load_envar_check_dict', return_value=0)
    def test_default_value(self, mock_check_dict, mock_triggers):
        '''
        Test loading with an evironment variable with default value
        '''
        mock_container = mock.Mock()
        mock_container.load_envar = mock.Mock(return_value=0)
        definition = {'VARIABLE': {'default_val': 'value'}}
        mock_triggers.return_value = definition
        dr_env_lib.env_lib.load_envar_from_definition(mock_container,
                                                          definition)
        mock_container.load_envar.assert_called_with('VARIABLE', 'value')
        mock_triggers.assert_called_with(definition)

    @mock.patch('dr_env_lib.env_lib.load_envar_apply_triggers')
    @mock.patch('dr_env_lib.env_lib.load_envar_check_dict', return_value=0)
    def test_two_successes_and_returns(self, mock_check_dict, mock_triggers):
        '''
        Test two successful loads and the return of the correct object
        '''
        class DummyEnvarContainer:
            ''' A test environment variable container'''
            def __init__(self):
                '''Constructor'''
                self.loaded_variables = {}
            def load_envar(self, varname, default=None):
                '''Dummy load of environment variables'''
                if default:
                    self.loaded_variables[varname] = default
                else:
                    self.loaded_variables[varname] = 'loaded from environment'
                return 0

        envar_container = DummyEnvarContainer()
        definition = {'VAR_FROM_ENV': {},
                      'VAR_DEFAULT': {'default_val': 'default_val'}}
        mock_triggers.return_value = definition
        returned_container = dr_env_lib.env_lib.load_envar_from_definition(
            envar_container, definition)
        mock_triggers.assert_called_with(definition)
        self.assertEqual(returned_container.loaded_variables['VAR_FROM_ENV'],
                         'loaded from environment')
        self.assertEqual(returned_container.loaded_variables['VAR_DEFAULT'],
                         'default_val')

    def test_check_dict_before_triggers(self):
        '''
        Check that the check dictionary function is called before applying
        the triggers
        '''
        source_mock = mock.MagicMock()
        with mock.patch('dr_env_lib.env_lib.load_envar_check_dict',
                        source_mock.load_envar_check_dict), \
            mock.patch('dr_env_lib.env_lib.load_envar_apply_triggers',
                       source_mock.load_envar_apply_triggers):
            source_mock.envar_definition.return_value = 0
            source_mock.load_envar_apply_triggers.return_value = {}
            expected_order = [
                mock.call.load_envar_check_dict({}),
                mock.call.load_envar_apply_triggers({})]
            _ = dr_env_lib.env_lib.load_envar_from_definition('', {})
            self.assertEqual(source_mock.mock_calls, expected_order)


class TestSetContinueFromFail(unittest.TestCase):
    '''
    Test the correct setting of continue and continue from fail for climate
    and NWP style CRUNS
    '''
    def test_fail_fail(self):
        '''Test that when the t isn't present, both variables are set to
        lower case fail'''
        test_envars = {'CONTINUE': 'a',
                       'CONTINUE_FROM_FAIL': 'b'}
        expected_output = {'CONTINUE': 'false',
                           'CONTINUE_FROM_FAIL': 'false'}
        rvalue = dr_env_lib.env_lib.set_continue_cont_from_fail(test_envars)
        self.assertEqual(rvalue, expected_output)

    def test_continue_capital_t(self):
        '''Test that if a capital T comes into continue, then we correctly
        set to lower case true'''
        test_envars = {'CONTINUE': 'True',
                       'CONTINUE_FROM_FAIL': 'b'}
        expected_output = {'CONTINUE': 'true',
                           'CONTINUE_FROM_FAIL': 'false'}
        rvalue = dr_env_lib.env_lib.set_continue_cont_from_fail(test_envars)
        self.assertEqual(rvalue, expected_output)

    def test_continue_lowercase_t(self):
        '''Test that if a lowercase t comes into continue, then we correctly
        set to lower case true'''
        test_envars = {'CONTINUE': 't',
                       'CONTINUE_FROM_FAIL': 'b'}
        expected_output = {'CONTINUE': 'true',
                           'CONTINUE_FROM_FAIL': 'false'}
        rvalue = dr_env_lib.env_lib.set_continue_cont_from_fail(test_envars)
        self.assertEqual(rvalue, expected_output)

    def test_from_fail_capital_t(self):
        '''Test that if a capital T comes into continue_from_fail, we
        correctly set both variables to lowercase true'''
        test_envars = {'CONTINUE': 'a',
                       'CONTINUE_FROM_FAIL': 'True'}
        expected_output = {'CONTINUE': 'true',
                           'CONTINUE_FROM_FAIL': 'true'}
        rvalue = dr_env_lib.env_lib.set_continue_cont_from_fail(test_envars)
        self.assertEqual(rvalue, expected_output)

    def test_from_fail_lower_t(self):
        '''Test that if a lower case t comes into contine_from_fail, we
        correctly set both variables to lowercase true'''
        test_envars = {'CONTINUE': 'a',
                       'CONTINUE_FROM_FAIL': 't'}
        expected_output = {'CONTINUE': 'true',
                           'CONTINUE_FROM_FAIL': 'true'}
        rvalue = dr_env_lib.env_lib.set_continue_cont_from_fail(test_envars)
        self.assertEqual(rvalue, expected_output)

    def test_blank_continue(self):
        '''Older suites have a blank string set for CONTINUE. Check that this
        translates correctly to lower case false'''
        test_envars = {'CONTINUE': '',
                       'CONTINUE_FROM_FAIL': 'false'}
        expected_output = {'CONTINUE': 'false',
                           'CONTINUE_FROM_FAIL': 'false'}
        rvalue = dr_env_lib.env_lib.set_continue_cont_from_fail(test_envars)
        self.assertEqual(rvalue, expected_output)


class TestStringForExport(unittest.TestCase):
    '''
    Test the exporting of the environment variables using a bash command
    '''
    def setUp(self):
        class DummyEnvarInst:
            '''Test Environment Variable container'''
            def __init__(self, envar_dict):
                '''Constructor'''
                self.env_vars = envar_dict

        self.dummy_envar = DummyEnvarInst

    def test_correct(self):
        '''Test correct behaviour for two instances, each with two variables
        with no duplicates'''
        env_inst = {'model1': self.dummy_envar({'model1_var1': '1',
                                                'model1_var2': 'a'}),
                    'model2': self.dummy_envar({'model2_var1': '2',
                                                'model2_var2': 'b'})}
        expected_output = 'export model1_var1=1; export model1_var2=a;' \
                          ' export model2_var1=2; export model2_var2=b;'
        self.assertEqual(
            dr_env_lib.env_lib.string_for_export(env_inst),
            expected_output)

    def test_correct_space(self):
        '''Test correct behaviour for two variables containing spaces, one
        with quotes, and one without'''
        env_inst = {'model': self.dummy_envar(
            {'model1_var1': "'space with quotes'",
             'model1_var2': 'space no quotes'})}
        expected_output = 'export model1_var1=\'space with quotes\';' \
                          ' export model1_var2=\'space no quotes\';'
        self.assertEqual(
            dr_env_lib.env_lib.string_for_export(env_inst),
            expected_output)

    def test_duplicates(self):
        '''Test correct behaviour for three instances, sharing both duplicates
        and unique values. Each duplicate should appear only once in the
        error message'''
        env_inst = {'model1': self.dummy_envar({'dup123': 'a',
                                                'dup12': 'b',
                                                'unique1': 'c'}),
                    'model2': self.dummy_envar({'dup123': 'a',
                                                'dup12': 'b',
                                                'unique2': 'c'}),
                    'model3': self.dummy_envar({'dup123': 'b',
                                                'unique3a': 'b',
                                                'unique3b': 'd'})}
        # There are two potential expected errors, as the set we are using
        # to hold our duplicates is unordered
        expected_err = '\n[FAIL] The following environment variables have' \
                       ' been set in more than one driver, please ensure this' \
                       ' is not the case:\n%s\n'
        expected_errs = (expected_err % ['dup12', 'dup123'],
                         expected_err % ['dup123', 'dup12'])
        with mock.patch('sys.stderr', new=io.StringIO()) as patch_err:
            with self.assertRaises(SystemExit) as context:
                dr_env_lib.env_lib.string_for_export(env_inst)
        self.assertEqual(context.exception.code,
                         dr_env_lib.env_lib.ENV_LIB_ERROR)
        self.assertTrue(patch_err.getvalue(), expected_errs)
