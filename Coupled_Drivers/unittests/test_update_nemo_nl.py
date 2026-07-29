#!/usr/bin/env python
# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------
'''
NAME
    test_update_nemo_nl.py

DESCRIPTION
    Contains unit tests for updating the nemo namelist
'''
import os
import unittest
import unittest.mock as mock

import update_nemo_nl

class TestUpdateSI3NL(unittest.TestCase):
    '''
    Test the update SI3 NL file
    '''
    def setUp(self):
        '''Set up the unit test'''
        # The internal variables dictionary
        self.variables = {'cn_icerst_indir': "'ocean_link_directory'"}
        self.nemo_envar = {'SI3_NL': 'si3_namelist',
                           'RST_LINK_DIR': 'ocean_link_directory'}

    @mock.patch('update_nemo_nl.do_update_nl_files')
    @mock.patch('update_nemo_nl.shutil.move')
    def test_update_si3(self, mock_move, mock_update):
        '''Test the correct behaviour for updating SI3 namelist'''
        mock_update.return_value = 'my_nl_file.tmp'
        update_nemo_nl.update_si3_nl(self.nemo_envar)
        mock_update.assert_called_once_with('si3_namelist', self.variables)
        mock_move.assert_called_once_with('my_nl_file.tmp', 'si3_namelist')

class TestUpdateTopNL(unittest.TestCase):
    '''
    Test the update Top NL file
    '''
    def setUp(self):
        '''Set up the variables dictionary'''
        # The internal variables dictionary
        self.variables = {'ln_rsttr': 'my_ln_restart',
                          'nn_rsttr': 'my_restart_ctl',
                          'ln_trcdta': 'my_ln_trcdta',
                          'cn_trcrst_indir': "'ocean_link_directory'"}
        self.nemo_envar = {'TOP_NL': 'top_namelist',
                           'RST_LINK_DIR': 'ocean_link_directory'}

    @mock.patch('update_nemo_nl.do_update_nl_files')
    @mock.patch('update_nemo_nl.shutil.move')
    def test_update_top(self, mock_move, mock_update):
        '''Test the correct behaviour for updating top namelist'''
        mock_update.return_value = 'my_nl_file.tmp'
        update_nemo_nl.update_top_nl(self.nemo_envar, 'my_ln_restart',
                                     'my_restart_ctl', 'my_ln_trcdta')
        mock_update.assert_called_once_with('top_namelist', self.variables)
        mock_move.assert_called_once_with('my_nl_file.tmp', 'top_namelist')


class TestUpdateNemoNL(unittest.TestCase):
    '''
    Test the update nemo nl file, with NEMO3.6 and NEMO4 behaviour
    '''
    def setUp(self):
        '''Set up the variables dictionary'''
        # The internal variable dictionaries
        self.variables_4 = {'cn_exp': "'my_runido'",
                            'ln_rstart': 'my_restart',
                            'nn_rstctl': 'my_ctl',
                            'nn_it000': 'my_next_step',
                            'nn_itend': 'my_final_step',
                            'nn_date0': 'my_ndate0',
                            'nn_leapy': 'my_leapy',
                            'jpni': 'my_iproc',
                            'jpnj': 'my_jproc',
                            'nn_cpl_river': 'my_cpl_river',
                            'cn_ocerst_indir': "'ocean_link_directory'"}
        self.variables_36 = {**self.variables_4, **{'jpnij': 'my_jpnij'}}

        # Common envar to be passed in
        self.common_envar = {'RUNID': 'my_runid',
                             'CPL_RIVER_COUNT': 'my_cpl_river'}

        # Nemo environment variables to be passed in
        self.nemo_envar_4 = {'NEMO_VERSION': 400,
                             'NEMO_IPROC': 'my_iproc',
                             'NEMO_JPROC': 'my_jproc',
                             'NEMO_NL': 'my_nl_file',
                             'RST_LINK_DIR': 'ocean_link_directory'}
        # Sort out for nemo 3.6
        self.nemo_envar_36 = {**self.nemo_envar_4, **{'NEMO_NPROC': 'my_jpnij'}}
        self.nemo_envar_36['NEMO_VERSION'] = 360

    @mock.patch('update_nemo_nl.do_update_nl_files')
    @mock.patch('update_nemo_nl.shutil.move')
    def test_update_nl_nemo_4(self, mock_move, mock_update):
        '''Test the correct behaviour for NEMO4'''
        mock_update.return_value = 'my_nl_file.tmp'
        update_nemo_nl.update_nl(self.common_envar, self.nemo_envar_4,
                                 'my_restart', 'my_ctl', 'my_next_step',
                                 'my_final_step', 'my_ndate0', 'my_leapy')
        mock_update.assert_called_with('my_nl_file', self.variables_4)
        mock_move.assert_called_with('my_nl_file.tmp', 'my_nl_file')

    @mock.patch('update_nemo_nl.do_update_nl_files')
    @mock.patch('update_nemo_nl.shutil.move')
    def test_update_nl_nemo_36(self, mock_move, mock_update):
        '''Test the correct behaviour for NEMO3.6'''
        mock_update.return_value = 'my_nl_file.tmp'
        update_nemo_nl.update_nl(self.common_envar, self.nemo_envar_36,
                                 'my_restart', 'my_ctl', 'my_next_step',
                                 'my_final_step', 'my_ndate0', 'my_leapy')
        mock_update.assert_called_with('my_nl_file', self.variables_36)
        mock_move.assert_called_with('my_nl_file.tmp', 'my_nl_file')


class TestDoUpdateNLFiles(unittest.TestCase):
    '''
    Test the updating of namelist files
    '''
    def setUp(self):
        '''Create a dummy namelist file to update'''
        self.nl_name = 'dummy_nl_cfg'
        self.nl_swap_name = 'dummy_nl_cfg.tmp'
        # Create our input file
        file_contents = '''&namrun
swap1=original_value1,
ln_mskland=.true.,
/
&namzgr
swap2='original_value2',
swap3=original_value3,
swap4=original_value4,
ln_zps=.true.,
/
'''
        with open(self.nl_name, 'w') as fh:
            fh.write(file_contents)

        # Expected contents after swap
        self.expected_out = '''&namrun
swap1=new_value1,
ln_mskland=.true.,
/
&namzgr
swap2=.true.,
swap3=.false.,
swap4=4.5,
ln_zps=.true.,
/
'''

    def tearDown(self):
        '''Remove any files created in the unit test'''
        for filename in [self.nl_name, self.nl_swap_name]:
            try:
                os.remove(filename)
            except FileNotFoundError:
                pass

    def test_update_nl_files(self):
        '''Test the updating function'''
        variables = {'swap1': 'new_value1',
                     'swap2': '.true.',
                     'swap3': '.false.',
                     'swap4': 4.5}
        rvalue = update_nemo_nl.do_update_nl_files(self.nl_name, variables)
        self.assertEqual(rvalue, self.nl_swap_name)
        with open(self.nl_swap_name, 'r') as fh:
            for line, expected_line in zip(fh.readlines(),
                                           self.expected_out.split('\n')):
                self.assertEqual(line.rstrip(), expected_line)

