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

from collections import namedtuple
import io
import os
import error
import ocn_lib

class TestReadOcnNamelist(unittest.TestCase):
    '''
    Test the reading of wet model namelists
    '''
    def setUp(self):
        '''Set up a dummy namelist file'''
        self.nl_name = 'test_nl_file'
        file_contents = '''
&TESTNL
nn_it000=1,
nn_itend=2232,
ln_rstdate=.true.,
rn_rdt=1200,
dummy=32,
/
        '''
        with open(self.nl_name, 'w') as f_h:
            f_h.write(file_contents)

    def tearDown(self):
        '''Delete the dummy NL file at the end of thes test'''
        try:
            os.remove(self.nl_name)
        except FileNotFoundError:
            pass

    def test_variables_database(self):
        '''Test the dictionary containing variables and regular expressions
        remains unchaged'''
        read_ocn_namelist_object = ocn_lib.ReadOcnNamelist(self.nl_name)
        NamelistVal = namedtuple('NamelistVal', 'regex value')
        expected_variables \
            = {'nemo_first_step': NamelistVal(r'nn_it000=(.+),', None),
               'nemo_last_step': NamelistVal(r'nn_itend=(.+),', None),
               'nemo_step_int': NamelistVal(r'rn_rdt=(\d*)', None),
               'nemo_rst_date': NamelistVal(r'ln_rstdate=(.+),', None),
               'nemo_rst': NamelistVal(
                   r'cn_ocerst_outdir=[\"\'](.*?)[\"\']', None),
               'ice_rst': NamelistVal(
                   r'cn_icerst_outdir=[\"\'](.*?)[\"\']', None),
               'ln_icebergs': NamelistVal(r'ln_icebergs=(.+),', None),
               'top_rst': NamelistVal(
                   r'cn_trcrst_outdir=[\"\'](.*?)[\"\']', None)}
        self.assertEqual(expected_variables,
                         read_ocn_namelist_object._variables)
        del read_ocn_namelist_object

    def test_read_variables_multiple(self):
        '''Test reading in of the variables from the namelist'''
        read_ocn_namelist_object = ocn_lib.ReadOcnNamelist(self.nl_name)
        expected_out = ('1', '2232', '.true.', '1200')
        self.assertEqual(
            expected_out, read_ocn_namelist_object.read_variables(
                'nemo_first_step', 'nemo_last_step', 'nemo_rst_date',
                'nemo_step_int'))
        del read_ocn_namelist_object

    def test_read_variables_single(self):
        '''Test that reading a single variable returns that variable and not
        a tuple'''
        read_ocn_namelist_object = ocn_lib.ReadOcnNamelist(self.nl_name)
        expected_out = '1'
        self.assertEqual(expected_out,
                         read_ocn_namelist_object.read_variables(
                             'nemo_first_step'))
        del read_ocn_namelist_object

    @mock.patch('ocn_lib.sys.stderr.write')
    def test_read_variables_fail(self, mock_stderr):
        read_ocn_namelist_object = ocn_lib.ReadOcnNamelist(self.nl_name)
        with self.assertRaises(SystemExit) as context:
            read_ocn_namelist_object.read_variables('invalid_var')
        self.assertEqual(context.exception.code,
                         error.MISSING_FILE_CONTENTS_ERROR)
        mock_stderr.assert_called_once_with(
            '[FAIL] Unable to determine how to read the variable invalid_var'
            ' from file %s\n' % (self.nl_name))
        del read_ocn_namelist_object




class TestGetNemoNprocStr(unittest.TestCase):
    '''
    Unit tests for determining the number of zeros in the unrebuilt NEMO
    restart files
    '''
    @mock.patch('ocn_lib.glob.glob')
    def test_index_error_exception(self, mock_glob):
        '''Test that if the index error is thrown, we have a returned length
        of zero'''
        mock_glob.side_effect = IndexError
        self.assertEqual(ocn_lib._get_nemo_nproc_str(), 0)

    @mock.patch('ocn_lib.glob.glob')
    def test_default_restart_directory(self, mock_glob):
        '''Test correct behaviour with default dictionary'''
        mock_glob.return_value = ['oce_2021_restart_000.nc']
        self.assertEqual(ocn_lib._get_nemo_nproc_str(), 3)
        mock_glob.assert_called_with('./*_[0-9]*_restart_*0.nc')

    @mock.patch('ocn_lib.glob.glob')
    def test_non_default_restart_directory(self, mock_glob):
        '''Test correct behaviour with non default directory'''
        mock_glob.return_value = ['oce_2021_restart_0.nc']
        self.assertEqual(ocn_lib._get_nemo_nproc_str('custom_dir'), 1)
        mock_glob.assert_called_with('custom_dir/*_[0-9]*_restart_*0.nc')


class TestSetupMultipleRestart(unittest.TestCase):
    '''
    Unit tests for setting up of multiple restart files
    '''
    @mock.patch('ocn_lib.common.remove_file')
    @mock.patch('ocn_lib.os.path.isfile')
    @mock.patch('ocn_lib.os.symlink')
    def test_two_restarts(self, mock_slink, mock_isfile, mock_rmfile):
        '''Test the correct linking of two restart files. Two nemo processors
        but a nproc string length of 4'''
        mock_isfile.side_effect = [True, True]
        ocn_lib._setup_multiple_restart(
            'init_dir', 'rst_link_dir', 'fname', 'lnname', 2, 4)
        mock_rmfile.assert_has_calls([mock.call('rst_link_dir/lnname_0000.nc'),
                                      mock.call('rst_link_dir/lnname_0001.nc')])
        mock_isfile.assert_has_calls([mock.call('init_dir/fname_0000.nc'),
                                      mock.call('init_dir/fname_0001.nc')])
        mock_slink.assert_has_calls([mock.call('init_dir/fname_0000.nc',
                                               'rst_link_dir/lnname_0000.nc'),
                                     mock.call('init_dir/fname_0001.nc',
                                               'rst_link_dir/lnname_0001.nc')])

    @mock.patch('ocn_lib.common.remove_file')
    @mock.patch('ocn_lib.os.path.isfile')
    @mock.patch('ocn_lib.os.symlink')
    def test_no_file(self, mock_slink, mock_isfile, mock_rmfile):
        '''Test that if a file isn't found it isn't linked'''
        mock_isfile.return_value = False
        ocn_lib._setup_multiple_restart(
            'init_dir', 'rst_link_dir', 'fname', 'lnname', 1, 4)
        mock_rmfile.assert_called_once_with('rst_link_dir/lnname_0000.nc')
        mock_isfile.assert_called_once_with('init_dir/fname_0000.nc')
        mock_slink.assert_not_called()


class TestSetupSingleRestart(unittest.TestCase):
    '''
    Unit tests for setting up a single restart file
    '''
    @mock.patch('ocn_lib.sys.stdout.write')
    @mock.patch('ocn_lib.common.remove_file')
    @mock.patch('ocn_lib.os.path.isfile')
    @mock.patch('ocn_lib.os.symlink')
    def test_single_rst(self, mock_slink, mock_isfile, mock_rmfile,
                        mock_stdout):
        '''Test the correct linking of a single restart file'''
        mock_isfile.return_value = True
        ocn_lib._setup_single_restart(
            'init_dir', 'rst_link_dir', 'fname', 'lnname', 'MODEL')
        mock_rmfile.assert_called_once_with('rst_link_dir/lnname.nc')
        mock_isfile.assert_called_once_with('init_dir/fname.nc')
        mock_slink.assert_called_once_with('init_dir/fname.nc',
                                           'rst_link_dir/lnname.nc')
        mock_stdout.assert_has_calls(
            [mock.call('[INFO] No MODEL sub-PE restarts found\n'),
             mock.call('[INFO] Using rebuilt MODEL restart file'
                       ' init_dir/fname.nc\n')])

    @mock.patch('ocn_lib.sys.stdout.write')
    @mock.patch('ocn_lib.common.remove_file')
    @mock.patch('ocn_lib.os.path.isfile')
    @mock.patch('ocn_lib.os.symlink')
    def test_single_rst_no_file(self, mock_slink, mock_isfile, mock_rmfile,
                                mock_stdout):
        '''Test that if the file is not found, no link attempted'''
        mock_isfile.return_value = False
        ocn_lib._setup_single_restart(
            'init_dir', 'rst_link_dir', 'fname', 'lnname', 'MODEL')
        mock_rmfile.assert_called_once_with('rst_link_dir/lnname.nc')
        mock_isfile.assert_called_once_with('init_dir/fname.nc')
        mock_slink.assert_not_called()
        mock_stdout.assert_called_once_with(
            '[INFO] No MODEL sub-PE restarts found\n')

class TestSetupRestart(unittest.TestCase):
    '''
    Test the top level of the setup restart functionality
    '''
    @mock.patch('ocn_lib._create_restart_link_dir')
    @mock.patch('ocn_lib._get_nemo_nproc_str')
    @mock.patch('ocn_lib._setup_multiple_restart')
    @mock.patch('ocn_lib._setup_single_restart')
    def test_setup_restart_multiple(self, mock_single, mock_multiple,
                                    mock_nproc, mock_linkdir):
        '''Setup the restart for multiple restart files'''
        mock_nproc.return_value = 2
        ocn_lib.setup_restart(
            'init_dir', 'rst_link_dir', 'fname', 'lnname', 'nemo_nproc',
            'MODEL')
        mock_linkdir.assert_called_once_with('rst_link_dir')
        mock_multiple.assert_called_once_with(
            'init_dir', 'rst_link_dir', 'fname', 'lnname', 'nemo_nproc', 2)
        mock_single.assert_not_called()

    @mock.patch('ocn_lib._create_restart_link_dir')
    @mock.patch('ocn_lib._get_nemo_nproc_str')
    @mock.patch('ocn_lib._setup_multiple_restart')
    @mock.patch('ocn_lib._setup_single_restart')
    def test_setup_restart_single(self, mock_single, mock_multiple,
                                  mock_nproc, mock_linkdir):
        '''Setup the restart for single restart files'''
        mock_nproc.return_value = 0
        ocn_lib.setup_restart(
            'init_dir', 'rst_link_dir', 'fname', 'lnname', 'nemo_nproc',
            'MODEL')
        mock_linkdir.assert_called_once_with('rst_link_dir')
        mock_single.assert_called_once_with(
            'init_dir', 'rst_link_dir', 'fname', 'lnname', 'MODEL')
        mock_multiple.assert_not_called()

class TestSetupNRUN(unittest.TestCase):
    '''
    Test setting up of restart files for an NRUN
    '''
    @mock.patch('ocn_lib._create_restart_link_dir')
    @mock.patch('ocn_lib.sys.stdout.write')
    def test_setup_nrun_unset_start_envar(self, mock_stdout, mock_linkdir):
        '''Test a value for the START environment variable which evaluates to
        false'''
        self.assertEqual(ocn_lib.setup_nrun(
            False, 'rst_link_dir', None, None, 'my_warning'), '.false.')
        mock_linkdir.assert_called_once_with('rst_link_dir')
        mock_stdout.assert_called_once_with('[WARN] my_warning\n')

    @mock.patch('ocn_lib._create_restart_link_dir')
    @mock.patch('ocn_lib._get_nemo_nproc_str')
    @mock.patch('ocn_lib.os.path.isfile')
    @mock.patch('ocn_lib.sys.stderr.write')
    def test_setup_nrun_no_restart(
            self, mock_stderr, mock_isfile, mock_nproc, mock_linkdir):
        '''Check we exit correctly if the restart file is not found'''
        mock_nproc.return_value = 0
        mock_isfile.side_effect = [False, False]
        with self.assertRaises(SystemExit) as context:
            ocn_lib.setup_nrun('start', 'rst_link_dir', None, None, None)
        self.assertEqual(context.exception.code,
                         error.MISSING_MODEL_FILE_ERROR)
        mock_linkdir.assert_called_once_with('rst_link_dir')
        mock_stderr.assert_called_once_with('[FAIL] file start not found\n')

    @mock.patch('ocn_lib._create_restart_link_dir')
    @mock.patch('ocn_lib._get_nemo_nproc_str')
    @mock.patch('ocn_lib.os.path.isfile')
    @mock.patch('ocn_lib.os.symlink')
    def test_setup_nrun_single_file(
            self, mock_slink, mock_isfile, mock_nproc, mock_linkdir):
        '''Check the linking of a single restart file for NRUN'''
        mock_nproc.return_value = 0
        mock_isfile.return_value = True
        self.assertEqual(ocn_lib.setup_nrun(
            'start', 'rst_link_dir', 'restart', 'init', None), '.true.')
        mock_linkdir.assert_called_once_with('rst_link_dir')
        mock_nproc.assert_called_once_with('init')
        mock_slink.assert_called_once_with('start', 'rst_link_dir/restart.nc')

    @mock.patch('ocn_lib._create_restart_link_dir')
    @mock.patch('ocn_lib._get_nemo_nproc_str')
    @mock.patch('ocn_lib.os.path.isfile')
    @mock.patch('ocn_lib.glob.glob')
    @mock.patch('ocn_lib.common.remove_file')
    @mock.patch('ocn_lib.os.symlink')
    def test_setup_nrun_multiple_file(self, mock_slink, mock_rmfile, mock_glob,
                                      mock_isfile, mock_nproc, mock_linkdir):
        '''Check the linking of multiple restart files for NRUN'''
        mock_nproc.return_value = 4
        mock_isfile.side_effect = [False, True]
        mock_glob.return_value = ['start_0000.nc', 'start_0001.nc']
        self.assertEqual(ocn_lib.setup_nrun(
            'start', 'rst_link_dir', 'restart', 'init', None), '.true.')
        mock_linkdir.assert_called_once_with('rst_link_dir')
        mock_nproc.assert_called_once_with('init')
        mock_isfile.assert_has_calls([mock.call('start'),
                                      mock.call('start_0000.nc')])
        mock_glob.assert_called_once_with('start_????.nc')
        mock_rmfile.assert_has_calls(
            [mock.call('rst_link_dir/restart_0000.nc'),
             mock.call('rst_link_dir/restart_0001.nc')])
        mock_slink.assert_has_calls(
            [mock.call('start_0000.nc', 'rst_link_dir/restart_0000.nc'),
             mock.call('start_0001.nc', 'rst_link_dir/restart_0001.nc')])

class TestCreateRestartLinkDir(unittest.TestCase):
    '''
    Test the functionaility of creating restart directory
    '''
    @mock.patch('ocn_lib.os.mkdir')
    def test_create_linkdir_wd(self, mock_mkdir):
        '''Test that nothing happens if the restart dir is the current
        working dir '.' '''
        self.assertIsNone(ocn_lib._create_restart_link_dir('.'))
        mock_mkdir.assert_not_called()

    @mock.patch('ocn_lib.os.mkdir')
    def test_create_linkdir(self, mock_mkdir):
        '''Test that we call os.mkdir when the directory doesnt exist'''
        self.assertIsNone(ocn_lib._create_restart_link_dir('restart_dir'))
        mock_mkdir.assert_called_once_with('restart_dir')

    @mock.patch('ocn_lib.os.mkdir')
    @mock.patch('ocn_lib.sys.stdout.write')
    def test_create_linkdir_existing_folder(self, mock_stdout, mock_mkdir):
        '''Test that a FileExistsError is captured if dictionary can't be
        created'''
        mock_mkdir.side_effect = FileExistsError
        self.assertIsNone(ocn_lib._create_restart_link_dir('restart_dir'))
        mock_stdout.assert_called_once_with(
            '[INFO] Restart link subdirectory restart_dir exists\n')
