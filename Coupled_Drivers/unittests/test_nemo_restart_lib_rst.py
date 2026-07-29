#!/usr/bin/env python
# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------
'''
NAME
    test_nemo_restart_lib_rst.py

DESCRIPTION
    Test the 'restart' functions in the NEMO restart library
'''
import unittest
import unittest.mock as mock

import error
import nemo_restart_lib

class TestVerifyFixRst(unittest.TestCase):
    '''
    Test the verification that the nemo start dump date is consistent with the
    start of the cycle
    '''
    @mock.patch('nemo_restart_lib.sys.stdout.write')
    def test_verify_fix_rst_does_match(self, mock_stdout):
        '''Test a matching cycle point'''
        restart_date = '20210423'
        cyclepoint = '20210423T1150Z'
        self.assertEqual(
            restart_date, nemo_restart_lib.verify_fix_rst(
                restart_date, cyclepoint, None))
        mock_stdout.assert_called_once_with(
            '[INFO] Validated NEMO restart date\n')

    @mock.patch('nemo_restart_lib.sys.stdout.write')
    @mock.patch('nemo_restart_lib.sys.stderr.write')
    @mock.patch('nemo_restart_lib.os.listdir')
    @mock.patch('nemo_restart_lib.re.findall')
    @mock.patch('nemo_restart_lib.common.remove_file')
    @mock.patch('nemo_restart_lib.os.path.join')
    def test_verify_fix_rst_perform_fix(
            self, mock_pathjoin, mock_rmfile, mock_findall, mock_lsdir,
            mock_stderr, mock_stdout):
        '''Test the removal of later restart files'''
        expected_msg = '[WARN] The NEMO restart data does not match the ' \
                       ' current cycle time\n.' \
                       '   Cycle time is 20210423\n' \
                       '   NEMO restart time is 20210424\n' \
                       '[WARN] Automatically removing NEMO dumps ahead of ' \
                       'the current cycletime, and pick up the dump at ' \
                       'this time\n'
        restart_date = '20210424'
        cyclepoint = '20210423T1150Z'
        restart_regex = r'(icebergs)?.*restart(_trc)?(_\d+)?\.nc'
        date_regex = r'\d{8}'
        mock_findall.side_effect = [True, False, True, True,
                                    ['20210423'], ['20210422'], ['20210425']]
        mock_lsdir.return_value = ['file1', 'file4', 'file2', 'file3']
        mock_pathjoin.return_value = 'joined_rst_path'
        self.assertEqual(
            '20210423', nemo_restart_lib.verify_fix_rst(
                restart_date, cyclepoint, 'nemo_rst'))
        mock_findall.assert_has_calls(
            [mock.call(restart_regex, 'file1'),
             mock.call(restart_regex, 'file4'),
             mock.call(restart_regex, 'file2'),
             mock.call(restart_regex, 'file3'),
             mock.call(date_regex, 'file1'),
             mock.call(date_regex, 'file2'),
             mock.call(date_regex, 'file3')])
        mock_pathjoin.assert_called_once_with('nemo_rst', 'file3')
        mock_rmfile.assert_called_once_with('joined_rst_path')
        mock_stdout.assert_called_once_with(expected_msg)
        mock_stderr.assert_called_once_with(expected_msg)


class TestCompileNemoRestartFiles(unittest.TestCase):
    '''
    Test the determination of NEMO restart files
    '''
    @mock.patch('nemo_restart_lib.os.listdir')
    @mock.patch('nemo_restart_lib.re.findall')
    @mock.patch('nemo_restart_lib.os.path.join')
    @mock.patch('nemo_restart_lib.common.remove_file')
    @mock.patch('nemo_restart_lib.os.path.isfile')
    def test_restart_files_latest_dump(
            self, mock_isfile, mock_rmfile, mock_pathjoin,
            mock_re_findall, mock_listdir):
        '''Test behaviour when there are restart files and dump'''
        restart_regex = r'.+_\d{8}_restart(_\d+)?\.nc'
        # reverse order so they can later be sorted
        mock_listdir.return_value = ['file3', 'file2', 'file1']
        mock_re_findall.side_effect = [True, False, True]
        mock_pathjoin.return_value = 'latest_nemo_dump'
        mock_isfile.return_value = True
        self.assertEqual((['file1', 'file3'], 'latest_nemo_dump', 'nemo_rst'),
                         nemo_restart_lib.compile_nemo_restart_files(
                             'nemo_rst'))
        mock_listdir.assert_called_once_with('nemo_rst')
        mock_re_findall.assert_has_calls([mock.call(restart_regex, 'file3'),
                                          mock.call(restart_regex, 'file2'),
                                          mock.call(restart_regex, 'file1')])
        mock_pathjoin.assert_called_once_with('nemo_rst', 'file3')
        mock_rmfile.assert_has_calls([mock.call('restart.nc'),
                                      mock.call('restart_icebergs.nc'),
                                      mock.call('restart_trc.nc')])
        mock_isfile.assert_called_once_with('latest_nemo_dump')


    @mock.patch('nemo_restart_lib.os.listdir')
    @mock.patch('nemo_restart_lib.re.findall')
    @mock.patch('nemo_restart_lib.os.path.join')
    @mock.patch('nemo_restart_lib.common.remove_file')
    @mock.patch('nemo_restart_lib.os.path.isfile')
    def test_no_restart_no_dump(
            self, mock_isfile, mock_rmfile, mock_pathjoin,
            mock_re_findall, mock_listdir):
        '''Test behaviour when there are no restart files and no dumps'''
        restart_regex = r'.+_\d{8}_restart(_\d+)?\.nc'
        # reverse order so they can later be sorted
        mock_listdir.return_value = ['file3', 'file2', 'file1']
        mock_re_findall.side_effect = [False, False, False]
        mock_isfile.return_value = False
        self.assertEqual(([], 'unset', '.'),
                         nemo_restart_lib.compile_nemo_restart_files(
                             'nemo_rst'))
        mock_listdir.assert_called_once_with('nemo_rst')
        mock_re_findall.assert_has_calls([mock.call(restart_regex, 'file3'),
                                          mock.call(restart_regex, 'file2'),
                                          mock.call(restart_regex, 'file1')])
        mock_pathjoin.assert_not_called()
        mock_rmfile.assert_has_calls([mock.call('restart.nc'),
                                      mock.call('restart_icebergs.nc'),
                                    mock.call('restart_trc.nc')])
        mock_isfile.assert_called_once_with('unset')

class TestCreateRestartDirecs(unittest.TestCase):
    '''
    Test the archiving and creation of NEMO restart directories
    '''
    @mock.patch('nemo_restart_lib.os.rename')
    @mock.patch('nemo_restart_lib.os.makedirs')
    def test_crun(self, mock_mkdir, mock_rename):
        '''For a CRUN we dont rename or make directories'''
        common_env = {'CONTINUE': 'true'}
        nemo_restart_lib.create_restart_direcs(None, common_env)
        mock_mkdir.assert_not_called()
        mock_rename.assert_not_called()

    @mock.patch('nemo_restart_lib.os.path.isdir')
    @mock.patch('nemo_restart_lib.os.rename')
    @mock.patch('nemo_restart_lib.os.makedirs')
    @mock.patch('nemo_restart_lib.sys.stdout.write')
    def test_false_options(self, mock_stdout, mock_mkdir, mock_rename,
                           mock_isdir):
        '''Test the option for directly creating a restart dir, continue
        is false, and the directory doesnt exist'''
        common_env = {'CONTINUE': 'false'}
        restart_direcs = ['NEMORESTART']
        mock_isdir.return_value = False
        nemo_restart_lib.create_restart_direcs(restart_direcs, common_env)
        mock_isdir.assert_called_once_with('NEMORESTART')
        mock_mkdir.assert_called_once_with('NEMORESTART')
        mock_rename.assert_not_called()
        mock_stdout.assert_called_once_with(
            '[INFO] Creating NEMO restart directory:\n  NEMORESTART\n')

    @mock.patch('nemo_restart_lib.os.path.isdir')
    @mock.patch('nemo_restart_lib.os.rename')
    @mock.patch('nemo_restart_lib.os.makedirs')
    @mock.patch('nemo_restart_lib.sys.stdout.write')
    def test_cwd(self, mock_stdout, mock_mkdir, mock_rename, mock_isdir):
        '''Test that if the directories are either . or ./ we dont do
        anything'''
        common_env = {'CONTINUE': 'false'}
        restart_direcs = ['./', '.']
        mock_isdir.side_effect = [True, True]
        nemo_restart_lib.create_restart_direcs(restart_direcs, common_env)
        mock_isdir.assert_has_calls([mock.call('./'), mock.call('.')])
        mock_mkdir.assert_not_called()
        mock_stdout.assert_not_called()
        mock_rename.assert_not_called()

    @mock.patch('nemo_restart_lib.time.strftime')
    @mock.patch('nemo_restart_lib.os.path.isdir')
    @mock.patch('nemo_restart_lib.os.rename')
    @mock.patch('nemo_restart_lib.os.makedirs')
    @mock.patch('nemo_restart_lib.sys.stdout.write')
    def test_multi(self, mock_stdout, mock_mkdir, mock_rename, mock_isdir,
                   mock_time):
        '''Test if two restart directorys exist, and one doesnt, that the
        two that exist get archived and new ones are created in their place'''
        common_env = {'CONTINUE': 'false'}
        restart_direcs = ['EXIST_1', 'EXIST_2', 'DONT_EXIST', '.']
        mock_isdir.side_effect = [True, True, False, True]
        mock_time.return_value = '202104161924'
        nemo_restart_lib.create_restart_direcs(restart_direcs, common_env)
        mock_time.assert_called_once_with("%Y%m%d%H%M")
        mock_rename.assert_has_calls([
            mock.call('EXIST_1', 'EXIST_1.202104161924'),
            mock.call('EXIST_2', 'EXIST_2.202104161924')])
        mock_mkdir.assert_has_calls([mock.call('EXIST_1'),
                                     mock.call('EXIST_2')])
        mock_stdout.assert_has_calls([
            mock.call('[INFO] directory is EXIST_1\n'),
            mock.call('[INFO] This is a New Run. Renaming old NEMO'
                      ' history directory\n'),
            mock.call('[INFO] directory is EXIST_2\n'),
            mock.call('[INFO] This is a New Run. Renaming old NEMO'
                      ' history directory\n')])
