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
    test_nemo_lib_nl.py

DESCRIPTION
    Test the 'namelist' functions in the NEMO library
'''

import unittest
import unittest.mock as mock

import dr_env_lib.nemo_def
import dr_env_lib.ocn_cont_def

import error
import nemo_lib


class TestReadCurrentCycleNLPublic(unittest.TestCase):
    '''
    Test the public interface function to read the current namelist cycles
    '''
    def setUp(self):
        '''Set up the nemo environment variable object'''
        self.nemo_envar = {'NEMO_NL': 'nemo_namelist',
                           'SI3_NL': 'ice_namelist',
                           'TOP_NL': 'top_namelist'}

    @mock.patch('nemo_lib._read_current_cycle_nl_nemo')
    @mock.patch('nemo_lib._read_current_cycle_nl_si3')
    @mock.patch('nemo_lib._read_current_cycle_nl_top')
    def test_no_models(self, mock_top, mock_si3, mock_nemo):
        '''Test that if no models are present we just return nones'''
        common_env = {'models': 'no recognised models'}
        self.assertEqual(
            (None, None, None, None),
            nemo_lib.read_current_cycle_nl(common_env, self.nemo_envar))
        mock_nemo.assert_not_called()
        mock_top.assert_not_called()
        mock_si3.assert_not_called()

    @mock.patch('nemo_lib._read_current_cycle_nl_nemo')
    @mock.patch('nemo_lib._read_current_cycle_nl_si3')
    @mock.patch('nemo_lib._read_current_cycle_nl_top')
    def test_nemo_only(self, mock_top, mock_si3, mock_nemo):
        '''Test for nemo only'''
        common_env = {'models': 'nemo xios'}
        mock_nemo.return_value = ('nemo_rst', 'ln_icebergs')
        self.assertEqual(
            ('nemo_rst', 'ln_icebergs', None, None),
            nemo_lib.read_current_cycle_nl(common_env, self.nemo_envar))
        mock_nemo.assert_called_once_with('nemo_namelist')
        mock_top.assert_not_called()
        mock_si3.assert_not_called()

    @mock.patch('nemo_lib._read_current_cycle_nl_nemo')
    @mock.patch('nemo_lib._read_current_cycle_nl_si3')
    @mock.patch('nemo_lib._read_current_cycle_nl_top')
    def test_nemo_top(self, mock_top, mock_si3, mock_nemo):
        '''Test for nemo and top'''
        common_env = {'models': 'nemo top xios'}
        mock_nemo.return_value = ('nemo_rst', 'ln_icebergs')
        mock_top.return_value = ('top_rst')
        self.assertEqual(
            ('nemo_rst', 'ln_icebergs', None, 'top_rst'),
            nemo_lib.read_current_cycle_nl(common_env, self.nemo_envar))
        mock_nemo.assert_called_once_with('nemo_namelist')
        mock_top.assert_called_once_with('top_namelist')
        mock_si3.assert_not_called()

    @mock.patch('nemo_lib._read_current_cycle_nl_nemo')
    @mock.patch('nemo_lib._read_current_cycle_nl_si3')
    @mock.patch('nemo_lib._read_current_cycle_nl_top')
    def test_nemo_si3(self, mock_top, mock_si3, mock_nemo):
        '''Test for nemo and si3'''
        common_env = {'models': 'nemo si3 xios'}
        mock_nemo.return_value = ('nemo_rst', 'ln_icebergs')
        mock_si3.return_value = ('si3_rst')
        self.assertEqual(
            ('nemo_rst', 'ln_icebergs', 'si3_rst', None),
            nemo_lib.read_current_cycle_nl(common_env, self.nemo_envar))
        mock_nemo.assert_called_once_with('nemo_namelist')
        mock_si3.assert_called_once_with('ice_namelist')
        mock_top.assert_not_called()

    @mock.patch('nemo_lib._read_current_cycle_nl_nemo')
    @mock.patch('nemo_lib._read_current_cycle_nl_si3')
    @mock.patch('nemo_lib._read_current_cycle_nl_top')
    def test_nemo_si3_top(self, mock_top, mock_si3, mock_nemo):
        '''Test for nemo si3 and top'''
        common_env = {'models': 'nemo top si3 xios'}
        mock_nemo.return_value = ('nemo_rst', 'ln_icebergs')
        mock_si3.return_value = ('si3_rst')
        mock_top.return_value = ('top_rst')
        self.assertEqual(
            ('nemo_rst', 'ln_icebergs', 'si3_rst', 'top_rst'),
            nemo_lib.read_current_cycle_nl(common_env, self.nemo_envar))
        mock_nemo.assert_called_once_with('nemo_namelist')
        mock_si3.assert_called_once_with('ice_namelist')
        mock_top.assert_called_once_with('top_namelist')


class TestCheckNemoNL(unittest.TestCase):
    '''
    Test the existance of the Nemo namelist file
    '''
    @mock.patch('nemo_lib.os.path.isfile')
    def test_check_nemonl(self, mock_isfile):
        '''Check return zero if the namelist file is present'''
        nemo_envar = {'NEMO_NL': 'namelist_cfg'}
        mock_isfile.return_value = True
        self.assertIsNone(nemo_lib._check_nemonl(nemo_envar))
        mock_isfile.assert_called_once_with(nemo_envar['NEMO_NL'])

    @mock.patch('nemo_lib.os.path.isfile')
    @mock.patch('nemo_lib.sys.stderr.write')
    def test_check_nemonl_missing(self, mock_stderr, mock_isfile):
        '''Check correct behaviour if the namelist file is missing'''
        nemo_envar = {'NEMO_NL': 'namelist_cfg'}
        mock_isfile.return_value = False
        with self.assertRaises(SystemExit) as cm:
            nemo_lib._check_nemonl(nemo_envar)
        self.assertEqual(cm.exception.code, error.MISSING_DRIVER_FILE_ERROR)
        mock_stderr.assert_called_once_with(
            '[FAIL] Can not find the nemo namelist file %s\n' %
            nemo_envar['NEMO_NL'])
        mock_isfile.assert_called_once_with(nemo_envar['NEMO_NL'])


class TestCheckSI3NL(unittest.TestCase):
    '''
    Test the existance of the SI3 namelist file
    '''
    @mock.patch('nemo_lib.os.path.isfile')
    def test_check_nemonl(self, mock_isfile):
        '''Check return zero if the namelist file is present'''
        envar = {'SI3_NL': 'ice_namelist_cfg'}
        mock_isfile.return_value = True
        self.assertIsNone(nemo_lib._check_si3nl(envar))
        mock_isfile.assert_called_once_with(envar['SI3_NL'])

    @mock.patch('nemo_lib.os.path.isfile')
    @mock.patch('nemo_lib.sys.stderr.write')
    def test_check_nemonl_missing(self, mock_stderr, mock_isfile):
        '''Check correct behaviour if the namelist file is missing'''
        envar = {'SI3_NL': 'ice_namelist_cfg'}
        mock_isfile.return_value = False
        with self.assertRaises(SystemExit) as cm:
            nemo_lib._check_si3nl(envar)
        self.assertEqual(cm.exception.code, error.MISSING_DRIVER_FILE_ERROR)
        mock_stderr.assert_called_once_with(
            '[FAIL] Can not find the SI3 namelist file %s\n' %
            envar['SI3_NL'])
        mock_isfile.assert_called_once_with(envar['SI3_NL'])

class TestCheckTopNL(unittest.TestCase):
    '''
    Test the existance of the Top namelist file
    '''
    @mock.patch('nemo_lib.os.path.isfile')
    def test_check_nemonl(self, mock_isfile):
        '''Check return zero if the namelist file is present'''
        envar = {'TOP_NL': 'top_namelist_cfg'}
        mock_isfile.return_value = True
        self.assertIsNone(nemo_lib._check_topnl(envar))
        mock_isfile.assert_called_once_with(envar['TOP_NL'])

    @mock.patch('nemo_lib.os.path.isfile')
    @mock.patch('nemo_lib.sys.stderr.write')
    def test_check_topnl_missing(self, mock_stderr, mock_isfile):
        '''Check correct behaviour if the namelist file is missing'''
        envar = {'TOP_NL': 'top_namelist_cfg'}
        mock_isfile.return_value = False
        with self.assertRaises(SystemExit) as cm:
            nemo_lib._check_topnl(envar)
        self.assertEqual(cm.exception.code, error.MISSING_DRIVER_FILE_ERROR)
        mock_stderr.assert_called_once_with(
            '[FAIL] Can not find the TOP namelist file %s\n' %
            envar['TOP_NL'])
        mock_isfile.assert_called_once_with(envar['TOP_NL'])

class TestReadCurrentCycleNLPrivate(unittest.TestCase):
    '''
    Test we correctly read from the current cycle namelist. These are the
    private functions that carry this out
    '''
    def setUp(self):
        '''Set up the unit test'''
        class DummyReadOcnNL:
            '''Dummy for ocn_lib.ReadOcnNamelist'''
            def __init__(self, *vars_to_set_to_none):
                '''Constructor containing any variables to set to none'''
                self.vars_to_set_to_none = vars_to_set_to_none
            def read_variables(self, *variables):
                '''Check we pass through the correct variables in order,
                setting desired ones to None'''
                vars_to_return = []
                for var in variables:
                    vars_to_return.append(
                        None if var in self.vars_to_set_to_none else var)
                return tuple(vars_to_return)
        self.DummyNL = DummyReadOcnNL

    @mock.patch('nemo_lib.ocn_lib.ReadOcnNamelist')
    @mock.patch('nemo_lib.common.remove_trailing_slash')
    @mock.patch('nemo_lib.string_to_boolean')
    def test_read_current_cycle_nl_nemo(
            self, mock_str_to_bool, mock_rmslash, mock_readnl):
        '''Test the correct behaviour for reading NEMO restart'''
        mock_readnl.return_value = self.DummyNL()
        mock_rmslash.return_value = 'nemo_rst_rmslash'
        mock_str_to_bool.return_value = 'bool_icebergs'
        self.assertEqual(
            ('nemo_rst_rmslash', 'bool_icebergs'),
            nemo_lib._read_current_cycle_nl_nemo('namelist_path'))
        mock_rmslash.assert_called_once_with('nemo_rst')
        mock_str_to_bool.assert_called_once_with('ln_icebergs')

    @mock.patch('nemo_lib.ocn_lib.ReadOcnNamelist')
    @mock.patch('nemo_lib.common.remove_trailing_slash')
    def test_read_current_cycle_nl_si3(self, mock_rmslash, mock_readnl):
        '''Test the correct behaviour for reading SI3 restart'''
        mock_readnl.return_value = self.DummyNL()
        mock_rmslash.return_value = 'ice_rst_rmslash'
        self.assertEqual(
            'ice_rst_rmslash',
            nemo_lib._read_current_cycle_nl_si3('namelist_path'))
        mock_rmslash.assert_called_once_with(('ice_rst',))

    @mock.patch('nemo_lib.ocn_lib.ReadOcnNamelist')
    @mock.patch('nemo_lib.common.remove_trailing_slash')
    def test_read_current_cycle_nl_top(self, mock_rmslash, mock_readnl):
        '''Test the correct behaviour for reading TOP restart'''
        mock_readnl.return_value = self.DummyNL()
        mock_rmslash.return_value = 'top_rst_rmslash'
        self.assertEqual(
            'top_rst_rmslash',
            nemo_lib._read_current_cycle_nl_top('namelist_path'))
        mock_rmslash.assert_called_once_with(('top_rst',))



class TestReadHistoryNl(unittest.TestCase):
    '''
    Test the reading of History namelist for nemo
    '''
    def setUp(self):
        '''Test class for reading of history nl'''
        class DummyReadNL:
            '''Dummy ocn_lib.ReadOcnNamelist to test interface'''
            def __init__(self, nlfilename):
                '''Dummy constructor'''
                pass
            def read_variables(self, *testvar):
                '''Verify called with, and return some information'''
                assert testvar == ('nemo_first_step', 'nemo_last_step',
                                   'nemo_step_int', 'nemo_rst_date')
                return '1', 'nemo_last_step', '1200', 'nemo_rst_date'
        self.namelist = DummyReadNL('namelist_file')

    def test_check_nemo_laststep_digit(self):
        '''If nemo last step is a digit, return an integer'''
        self.assertEqual(2000, nemo_lib._check_nemo_last_step('2000'))

    def test_check_nemo_laststep_notdigit(self):
        '''If nemo last step is not a digit, return 0'''
        self.assertEqual(0, nemo_lib._check_nemo_last_step('set_by_system'))

    def test_string_to_boolean_true(self):
        '''If the rst_date string is true, return boolean True'''
        self.assertTrue(nemo_lib.string_to_boolean('.true.'))

    def test_string_to_boolean_upper_true(self):
        '''If the rst_date string is TRUE, return boolean True'''
        self.assertTrue(nemo_lib.string_to_boolean('.TRUE.'))

    def test_string_to_boolean_false(self):
        '''If the rst_date string is false, return boolean False'''
        self.assertFalse(nemo_lib.string_to_boolean('.false.'))

    @mock.patch('nemo_lib.ocn_lib.ReadOcnNamelist')
    @mock.patch('nemo_lib.string_to_boolean')
    @mock.patch('nemo_lib._check_nemo_last_step')
    def test_read_history_nl(self, mock_last_step, mock_str_to_bool,
                             mock_read_nl):
        '''Test the reading of history namelist, and conversions'''
        expected_rvalue = (1, 'checked_last', 1200, 'converted_rst')
        mock_read_nl.return_value = self.namelist
        mock_last_step.return_value = 'checked_last'
        mock_str_to_bool.return_value = 'converted_rst'
        self.assertEqual(
            expected_rvalue, nemo_lib.read_history_nl('namelist_file'))
        mock_last_step.assert_called_once_with('nemo_last_step')
        mock_str_to_bool.assert_called_once_with('nemo_rst_date')


class TestLoadEnvironmentVariables(unittest.TestCase):
    '''
    Test the correct reading of environment variables for various submodels
    '''
    @mock.patch('nemo_lib.dr_env_lib.env_lib.LoadEnvar')
    @mock.patch('nemo_lib._check_nemonl')
    @mock.patch('dr_env_lib.env_lib.load_envar_from_definition')
    def test_setup_nemo_only(self, mock_load_def, mock_check_nemo, mock_load):
        '''Test the correct loading of nemo setup'''
        mock_load.return_value = 'nemo_envar'
        mock_load_def.return_value = {'L_OCN_PASS_TRC': 'False'}
        self.assertEqual(
            ({'L_OCN_PASS_TRC': 'False'}, 'nemo xios'),
            nemo_lib.load_environment_variables('setup', 'nemo xios'))
        mock_load_def.assert_called_once_with(
            'nemo_envar', dr_env_lib.nemo_def.NEMO_ENVIRONMENT_VARS_INITIAL)
        mock_check_nemo.assert_called_once_with({'L_OCN_PASS_TRC': 'False'})

    @mock.patch('nemo_lib.dr_env_lib.env_lib.LoadEnvar')
    @mock.patch('nemo_lib._check_nemonl')
    @mock.patch('dr_env_lib.env_lib.load_envar_from_definition')
    def test_final_nemo_only(self, mock_load_def, mock_check_nemo, mock_load):
        '''Test the correct loading of nemo final'''
        mock_load.return_value = 'nemo_envar'
        mock_load_def.return_value = {'L_OCN_PASS_TRC': 'False'}
        self.assertEqual(
            ({'L_OCN_PASS_TRC': 'False'}, 'nemo xios'),
            nemo_lib.load_environment_variables('final', 'nemo xios'))
        mock_load_def.assert_called_once_with(
            'nemo_envar', dr_env_lib.nemo_def.NEMO_ENVIRONMENT_VARS_FINAL)
        mock_check_nemo.assert_called_once_with({'L_OCN_PASS_TRC': 'False'})

    @mock.patch('nemo_lib.dr_env_lib.env_lib.LoadEnvar')
    @mock.patch('nemo_lib._check_nemonl')
    @mock.patch('nemo_lib._check_si3nl')
    @mock.patch('nemo_lib._check_topnl')
    @mock.patch('dr_env_lib.env_lib.load_envar_from_definition')
    def test_setup_nemo_top_si3(
            self, mock_load_def, mock_check_top, mock_check_si3,
            mock_check_nemo, mock_load):
        '''Test the correct loading of setup for all 3 models'''
        mock_load.return_value = 'nemo_envar'
        nemo_load_dict = {'L_OCN_PASS_TRC': 'True'}
        si3_load_dict = {'L_OCN_PASS_TRC': 'True',
                         'SI3_LOADED': 'yes'}
        top_load_dict = {'L_OCN_PASS_TRC': 'True',
                         'SI3_LOADED': 'yes',
                         'TOP_LOADED': 'yes'}
        mock_load_def.side_effect = [nemo_load_dict, si3_load_dict,
                                     top_load_dict]
        self.assertEqual(
            (top_load_dict, 'nemo xios si3 top'),
            nemo_lib.load_environment_variables('setup', 'nemo xios si3'))
        mock_load_def.assert_has_calls(
            [mock.call('nemo_envar',
                       dr_env_lib.nemo_def.NEMO_ENVIRONMENT_VARS_INITIAL),
             mock.call(nemo_load_dict,
                      dr_env_lib.ocn_cont_def.SI3_ENVIRONMENT_VARS_INITIAL),
             mock.call(si3_load_dict,
                       dr_env_lib.ocn_cont_def.TOP_ENVIRONMENT_VARS_INITIAL)])
        mock_check_nemo.assert_called_once_with(nemo_load_dict)
        mock_check_si3.assert_called_once_with(si3_load_dict)
        mock_check_top.assert_called_once_with(top_load_dict)

    @mock.patch('nemo_lib.dr_env_lib.env_lib.LoadEnvar')
    @mock.patch('nemo_lib._check_nemonl')
    @mock.patch('nemo_lib._check_si3nl')
    @mock.patch('nemo_lib._check_topnl')
    @mock.patch('dr_env_lib.env_lib.load_envar_from_definition')
    def test_final_nemo_top_si3(
            self, mock_load_def, mock_check_top, mock_check_si3,
            mock_check_nemo, mock_load):
        '''Test the correct loading of final for all 3 models - Note that
        si3 doesnt have any final environment variables'''
        mock_load.return_value = 'nemo_envar'
        nemo_load_dict = {'L_OCN_PASS_TRC': 'True'}
        si3_load_dict = {'L_OCN_PASS_TRC': 'True',
                         'SI3_LOADED': 'yes'}
        top_load_dict = {'L_OCN_PASS_TRC': 'True',
                         'SI3_LOADED': 'yes',
                         'TOP_LOADED': 'yes'}
        mock_load_def.side_effect = [nemo_load_dict, si3_load_dict,
                                     top_load_dict]
        self.assertEqual(
            (top_load_dict, 'nemo xios si3 top'),
            nemo_lib.load_environment_variables('final', 'nemo xios si3'))
        mock_load_def.assert_has_calls(
            [mock.call('nemo_envar',
                       dr_env_lib.nemo_def.NEMO_ENVIRONMENT_VARS_FINAL),
             mock.call(nemo_load_dict,
                       dr_env_lib.ocn_cont_def.SI3_ENVIRONMENT_VARS_FINAL),
             mock.call(si3_load_dict,
                       dr_env_lib.ocn_cont_def.TOP_ENVIRONMENT_VARS_FINAL)])
        mock_check_nemo.assert_called_once_with(nemo_load_dict)
        mock_check_si3.assert_called_once_with(si3_load_dict)
        mock_check_top.assert_called_once_with(top_load_dict)
