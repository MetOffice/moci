#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2017 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    test_platforms_transfer.py

DESCRIPTION
    Transfer archived data to remote machine (e.g. JASMIN)

'''

import unittest
import os
from collections import OrderedDict
import mock

import testing_functions as func

import transfer

class TransferTest(unittest.TestCase):
    '''Unit tests relating to transfer of archived data to JASMIN'''
    @mock.patch('transfer.Transfer.tidy_up')
    def setUp(self, mock_tidyup):
        self.inputnl = OrderedDict([
            ('&pptransfer', None),
            ('verify_chksums=false', None),
            ('gridftp="False"', None),
            ('transfer_type="Push"', None),
            ('remote_host=RHOST', None),
            ('transfer_dir="/XDIR"', None),
            ('/', None),
            ('&archer_arch', None),
            ('archive_root_path=/ArchiveDir', None),
            ('archive_name="NAME"\n/', None),
            ])

        self.myfile = 'input.nl'
        open(self.myfile, 'w').write('\n'.join(self.inputnl.keys()))
        self.inst = transfer.Transfer(self.myfile)

    def tearDown(self):
        for fname in [self.myfile, 'checksums']:
            try:
                os.remove(fname)
            except OSError:
                pass

# Tidy up tests
    @mock.patch('transfer.Transfer._clean_up_push')
    @mock.patch('transfer.os.path.exists', return_value=True)
    def test_tidy_up_push(self, mock_osexists, mock_cleanup):
        '''Test tidy up'''
        func.logtest('test tidy_up')
        self.inst.tidy_up()
        self.assertEqual(mock_cleanup.call_count, 1)

    @mock.patch('transfer.os.path.exists', return_value=False)
    def test_tidy_up_push_fail(self, mock_osexists):
        '''Test tidy up'''
        func.logtest('test tidy_up')
        with self.assertRaises(SystemExit):
            self.inst.tidy_up()
        self.assertIn('doesn\'t exist', func.capture('err'))

    @mock.patch('transfer.Transfer._clean_up_pull')
    @mock.patch('transfer.utils.exec_subproc', return_value=[0, ''])
    def test_tidy_up_pull(self, mock_exec, mock_cleanup):
        '''Test tidy up - Pull'''
        func.logtest('test tidy_up')
        self.inst._transfer_type = "pull"
        self.inst.tidy_up()
        self.assertEqual(mock_cleanup.call_count, 1)

    @mock.patch('transfer.utils.exec_subproc', return_value=[2, ''])
    def test_tidy_up_pull_fail(self, mock_exec):
        '''Test tidy up - Pull'''
        func.logtest('test tidy_up')
        self.inst._transfer_type = "pull"
        with self.assertRaises(SystemExit):
            self.inst.tidy_up()
        self.assertIn('doesn\'t exist', func.capture('err'))

# Clean up tests
    @mock.patch('transfer.os.remove', return_value=[0, ''])
    def test_clean_up_push(self, mock_osremove):
        '''Test clean up before running a push transfer'''
        func.logtest('test _clean_up_push with verify checksums')
        self.inst._clean_up_push()
        self.assertIn('Deleting old checksum file', func.capture())

    @mock.patch('transfer.utils.exec_subproc')
    def test_clean_up_pull(self, mock_exec):
        '''Test clean up before running a pull transfer'''
        func.logtest('test _clean_up_pull with verify checksums')
        mock_exec.side_effect = [[0, ''], [0, '']]
        _ = self.inst._clean_up_pull()
        self.assertEqual(mock_exec.call_count, 2)

    @mock.patch('transfer.utils.exec_subproc', return_value=[3, ''])
    def test_clean_up_pull_fail_ls(self, mock_exec):
        '''Test clean up before running a pull transfer'''
        func.logtest('test _clean_up_pull with verify checksums')
        _ = self.inst._clean_up_pull()
        self.assertEqual(mock_exec.call_count, 1)
        self.assertIn('Problem checking existence', func.capture('err'))

    @mock.patch('transfer.utils.exec_subproc')
    def test_clean_up_pull_remote_rm(self, mock_exec):
        '''Test clean up before running a pull transfer'''
        func.logtest('test _clean_up_pull with verify checksums')
        mock_exec.side_effect = [[0, ''], [1, '']]
        _ = self.inst._clean_up_pull()
        self.assertEqual(mock_exec.call_count, 2)
        self.assertIn('Problem removing', func.capture('err'))

# Generate Checksum Tests
    @mock.patch('transfer.utils.exec_subproc', return_value=[0, ''])
    def test_gen_checksums_pull(self, mock_exec):
        '''Test generation of checksums'''
        func.logtest('test _generate_checksums - pull')
        self.inst._transfer_type = 'pull'
        rtn = self.inst._generate_checksums()
        self.assertEqual(rtn, True)

    @mock.patch('transfer.utils.exec_subproc', return_value=[1, ''])
    def test_gen_checksums_pull_fail(self, mock_exec):
        '''Test generation of checksums'''
        func.logtest('test _generate_checksums - pull')
        self.inst._transfer_type = 'pull'
        rtn = self.inst._generate_checksums()
        self.assertEqual(rtn, False)
        self.assertIn('Failed to generate checksums', func.capture('err'))

    @mock.patch('transfer.utils.exec_subproc')
    @mock.patch('transfer.glob.glob')
    def test_gen_checksums_push(self, mock_glob, mock_exec):
        '''Test generation of checksums'''
        func.logtest('test _generate_checksums - push')
        mock_glob.return_value = ['/path/to/file1', '/path/to/file2']
        mock_exec.return_value = [0, 'checksum1 file1\nchecksum2 file2\n']
        self.inst._archive_dir = ''
        rtn = self.inst._generate_checksums()
        self.assertEqual(rtn, True)
        self.assertTrue(os.path.exists('checksums'))
        mock_exec.assert_called_once_with(['md5sum', 'file1', 'file2'],
                                          verbose=False, cwd='')
        with open('checksums', 'r') as cfh:
            text = cfh.read()
        self.assertEqual(text, 'checksum1 file1\nchecksum2 file2\n')

    @mock.patch('transfer.utils.exec_subproc')
    @mock.patch('transfer.glob.glob')
    def test_gen_checksums_push_fail(self, mock_glob, mock_exec):
        '''Test generation of checksums'''
        func.logtest('test _generate_checksums - push')
        mock_glob.return_value = ['/path/to/file1', '/path/to/file2']
        mock_exec.return_value = [1, '']
        self.inst._archive_dir = ''
        rtn = self.inst._generate_checksums()
        self.assertEqual(rtn, False)
        self.assertIn('Failed to generate checksums', func.capture('err'))

# Verify Checksum Tests
    @mock.patch('transfer.utils.exec_subproc', return_value=[0, ''])
    def test_verify_checksums_pull(self, mock_exec):
        '''Test verification of checksums - Pull'''
        func.logtest('test _do_verify_checksums')
        self.inst._transfer_type = "Pull"
        rtn = self.inst._do_verify_checksums()
        self.assertIn('Checksum verification succeeded', func.capture())
        self.assertEqual(rtn, True)

    @mock.patch('transfer.utils.exec_subproc', return_value=[1, ''])
    def test_verify_chksums_pull_fail(self, mock_exec):
        '''Test verification of checksums - Pull'''
        func.logtest('test _do_verify_checksums')
        self.inst._transfer_type = "Pull"
        with self.assertRaises(SystemExit):
            rtn = self.inst._do_verify_checksums()
            self.assertEqual(rtn, False)
        self.assertIn('Checksum verification failed', func.capture('err'))

    @mock.patch('transfer.utils.exec_subproc', return_value=[0, ''])
    def test_do_verify_checksums_push(self, mock_exec):
        '''Test verification of checksums - Push'''
        func.logtest('test _do_verify_checksums')
        rtn = self.inst._do_verify_checksums()
        self.assertIn('Checksum verification succeeded', func.capture())
        self.assertEqual(rtn, True)

    @mock.patch('transfer.utils.exec_subproc', return_value=[1, ''])
    def test_verify_chksums_push_fail(self, mock_exec):
        '''Test verification of checksums - Push'''
        func.logtest('test _do_verify_checksums')
        with self.assertRaises(SystemExit):
            rtn = self.inst._do_verify_checksums()
            self.assertEqual(rtn, False)
        self.assertIn('Checksum verification failed', func.capture('err'))

# Transfer Tests
    @mock.patch('transfer.utils.exec_subproc', return_value=[0, ''])
    def test_do_transfer_no_files(self, mock_exec):
        '''Test transfer of archived files'''
        func.logtest('test do_transfer')
        self.inst.do_transfer()
        self.assertIn('Nothing to transfer', func.capture())

    @mock.patch('transfer.utils.exec_subproc', return_value=[255, ''])
    def test_do_transfer_ssh_failed(self, mock_exec):
        '''Test transfer of archived files'''
        func.logtest('test do_transfer')
        with self.assertRaises(SystemExit):
            self.inst.do_transfer()
        self.assertIn('Failed: ssh failed', func.capture('err'))

    @mock.patch('transfer.utils.exec_subproc', return_value=[10, ''])
    def test_xfer_error_checking_files(self, mock_exec):
        '''Test transfer of archived files'''
        func.logtest('test do_transfer')
        with self.assertRaises(SystemExit):
            self.inst.do_transfer()
        self.assertIn('Error checking files', func.capture('err'))

    @mock.patch('transfer.Transfer._do_verify_checksums', retrun_value=True)
    @mock.patch('transfer.Transfer._generate_checksums', return_value=True)
    @mock.patch('transfer.utils.exec_subproc')
    def test_xfer_push_rsync_verify_ok(self, mock_exec,
                                       mock_gen, mock_verify):
        '''Test do_transfer using rsync and checksum verification -push'''
        func.logtest('test do_transfer')
        mock_exec.side_effect = [[0, 'file'], [0, '']]
        self.inst._verify_chksums = True
        rtn = self.inst.do_transfer()
        self.assertIn('Checksums generated successfully', func.capture())
        self.assertIn('using rsync', func.capture())
        transfer_cmd = 'rsync -av --stats --rsync-path="mkdir -p ' \
            '/XDIR/NAME/20000121T0000Z && rsync" ' \
            '/ArchiveDir/NAME/20000121T0000Z/ ' \
            'RHOST:/XDIR/NAME/20000121T0000Z'
        mock_exec.assert_any_call(transfer_cmd)
        self.assertIn('Transfer command succeeded', func.capture())
        self.assertIn('Checksums verified', func.capture())
        self.assertIn('Transfer OK', func.capture())
        self.assertEqual(rtn, 0)

    @mock.patch('transfer.utils.create_dir')
    @mock.patch('transfer.os.path.exists', return_value=False)
    @mock.patch('transfer.utils.exec_subproc')
    def test_do_transfer_pull_rsync_ok(self, mock_exec, mock_exists, mock_cdir):
        '''Test do_transfer using rsync - pull'''
        func.logtest('test do_transfer')
        mock_exec.side_effect = [[0, 'file'], [0, '']]
        self.inst._transfer_type = 'pull'
        rtn = self.inst.do_transfer()
        self.assertIn('using rsync', func.capture())
        self.assertIn('Creating transfer directory', func.capture())
        transfer_cmd = 'rsync -av --stats ' \
            'RHOST:/ArchiveDir/NAME/20000121T0000Z/ ' \
            '/XDIR/NAME/20000121T0000Z'
        mock_exec.assert_any_call(transfer_cmd)
        self.assertIn('Transfer command succeeded', func.capture())
        self.assertIn('Transfer OK', func.capture())
        self.assertEqual(rtn, 0)

    @mock.patch('transfer.Transfer._do_verify_checksums', retrun_value=True)
    @mock.patch('transfer.Transfer._generate_checksums', return_value=True)
    @mock.patch('transfer.utils.exec_subproc')
    def test_xfer_push_gftp_verify_ok(self, mock_exec,
                                      mock_gen, mock_verify):
        '''Test do_transfer using gridftp and checksum verification - push'''
        func.logtest('test do_transfer')
        mock_exec.side_effect = [[0, 'file'], [0, '']]
        self.inst._verify_chksums = True
        self.inst._gridftp = True
        rtn = self.inst.do_transfer()
        self.assertIn('Checksums generated successfully', func.capture())
        self.assertIn('using gridFTP', func.capture())
        transfer_cmd = 'globus-url-copy -vb -cd -p 4 -cc 4 -sync ' \
            'file:///ArchiveDir/NAME/20000121T0000Z/ '\
            'sshftp://RHOST/XDIR/NAME/20000121T0000Z/'
        mock_exec.assert_any_call(transfer_cmd)
        self.assertIn('Transfer command succeeded', func.capture())
        self.assertIn('Checksums verified', func.capture())
        self.assertIn('Transfer OK', func.capture())
        self.assertEqual(rtn, 0)

    @mock.patch('transfer.utils.exec_subproc')
    def test_transfer_pull_gridftp_ok(self, mock_exec):
        '''Test do_transfer using gridftp - pull'''
        func.logtest('test do_transfer')
        mock_exec.side_effect = [[0, 'file'], [0, '']]
        self.inst._gridftp = True
        self.inst._transfer_type = 'pull'
        rtn = self.inst.do_transfer()
        self.assertIn('using gridFTP', func.capture())
        transfer_cmd = 'globus-url-copy -vb -cd -p 4 -cc 4 -sync ' \
            'sshftp://RHOST/ArchiveDir/NAME/20000121T0000Z/ ' \
            'file:///XDIR/NAME/20000121T0000Z/'
        mock_exec.assert_any_call(transfer_cmd)
        self.assertIn('Transfer command succeeded', func.capture())
        self.assertIn('Transfer OK', func.capture())
        self.assertEqual(rtn, 0)

    @mock.patch('transfer.Transfer._generate_checksums', return_value=False)
    @mock.patch('transfer.utils.exec_subproc', return_value=[0, 'file'])
    def test_transfer_checksum_gen_fail(self, mock_exec, mock_gen):
        '''Test do_transfer with checksum generation fail'''
        func.logtest('test do_transfer checksum gen fail')
        self.inst._verify_chksums = True
        with self.assertRaises(SystemExit):
            rtn = self.inst.do_transfer()
            self.assertEqual(rtn, 3)
        self.assertIn('Checksum generation failed', func.capture('err'))

    @mock.patch('transfer.Transfer._do_verify_checksums', return_value=False)
    @mock.patch('transfer.Transfer._generate_checksums', return_value=True)
    @mock.patch('transfer.utils.exec_subproc')
    def test_xfer_checksum_verify_fail(self, mock_exec, mock_gen,
                                       mock_verify):
        '''Test do_transfer with checksum verification fail'''
        func.logtest('test do_transfer checksum verify fail')
        self.inst._verify_chksums = True
        mock_exec.side_effect = [[0, 'file'], [0, '']]
        with self.assertRaises(SystemExit):
            rtn = self.inst.do_transfer()
            self.assertEqual(rtn, 4)
        self.assertIn('Problem with checksum verification', func.capture('err'))

    @mock.patch('transfer.utils.exec_subproc')
    def test_do_transfer__fail(self, mock_exec):
        '''Test do_transfer with failure'''
        func.logtest('test do_transfer checksum verify fail')
        mock_exec.side_effect = [[0, 'file'], [5, '']]
        with self.assertRaises(SystemExit):
            _ = self.inst.do_transfer()
        self.assertIn('Transfer command failed:', func.capture('err'))
        self.assertIn('transfer.py: Unknown', func.capture('err'))
