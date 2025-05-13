#!/usr/bin/env python
'''
**********************************************************************
Contribution by NCAS-CMS

**********************************************************************

NAME
    test_platforms_transfer.py

DESCRIPTION
    Unit tests for transfer archived data to remote machine (e.g. JASMIN)

'''

import unittest
import os
from collections import OrderedDict
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
    import mock

import testing_functions as func

import transfer

class TransferTest(unittest.TestCase):
    '''Unit tests relating to transfer of archived data to JASMIN'''
    def setUp(self):
        self.inputnl = OrderedDict([
            ('&pptransfer', None),
            ('verify_chksums=false', None),
            ('transfer_type="Push"', None),
            ('remote_host=RHOST', None),
            ('transfer_dir="/XDIR"', None),
            ('globus_cli=false', None),
            ('globus_default_colls=true', None),
            ('globus_notify="off"', None),
            ('/', None),
            ('&archer_arch', None),
            ('archive_root_path=/ArchiveDir', None),
            ('archive_name="NAME"\n/', None),
            ])

        self.myfile = 'input.nl'
        open(self.myfile, 'w').write('\n'.join(self.inputnl.keys()))
        with mock.patch.dict('transfer.os.environ',
                             {'ROSE_DATAC': ''}):
            with mock.patch('transfer.Transfer.tidy_up'):
                self.inst = transfer.Transfer(input_nl=self.myfile)

        self.inst._globus_src_coll = '3e90d018-0d05-461a-bbaf-aab605283d21' # ARCHER2 
        self.inst._globus_dst_coll = 'a2f53b7f-1b4e-4dce-9b7c-349ae760fee0' # JASMIN

    def tearDown(self):
        for fname in [self.myfile, 'checksums']:
            try:
                os.remove(fname)
            except OSError:
                pass

# Tidy up tests
    @mock.patch('transfer.Transfer._clean_up_push')
    def test_tidy_up_push(self, mock_cleanup):
        '''Test tidy up'''
        func.logtest('test tidy_up')
        with mock.patch('transfer.os.path.exists', return_value=True):
            self.inst.tidy_up()
        self.assertEqual(mock_cleanup.call_count, 1)

    def test_tidy_up_push_fail(self):
        '''Test tidy up'''
        func.logtest('test tidy_up')
        with mock.patch('transfer.os.path.exists', return_value=False):
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
        mock_exec.assert_called_once_with(
            'ssh RHOST -n ls /ArchiveDir/NAME/20000121T0000Z', verbose=False
            )

    @mock.patch('transfer.utils.exec_subproc', return_value=[2, ''])
    def test_tidy_up_pull_fail(self, mock_exec):
        '''Test tidy up - Pull'''
        func.logtest('test tidy_up')
        self.inst._transfer_type = "pull"
        with self.assertRaises(SystemExit):
            self.inst.tidy_up()
        self.assertIn('doesn\'t exist', func.capture('err'))
        mock_exec.assert_called_once_with(
            'ssh RHOST -n ls /ArchiveDir/NAME/20000121T0000Z', verbose=False
            )

# Clean up tests
    @mock.patch('transfer.os.remove', return_value=[0, ''])
    def test_clean_up_push(self, mock_osremove):
        '''Test clean up before running a push transfer'''
        func.logtest('test _clean_up_push with verify checksums')
        self.inst._clean_up_push()
        self.assertIn('Deleting old checksum file', func.capture())
        mock_osremove.assert_called_once_with(
            '/ArchiveDir/NAME/20000121T0000Z/checksums'
            )

    @mock.patch('transfer.utils.exec_subproc')
    def test_clean_up_pull(self, mock_exec):
        '''Test clean up before running a pull transfer'''
        func.logtest('test _clean_up_pull with verify checksums')
        mock_exec.side_effect = [[0, ''], [0, '']]
        _ = self.inst._clean_up_pull()
        self.assertEqual(mock_exec.call_count, 2)
        mock_exec.assert_called_with(
            'ssh RHOST -n rm /ArchiveDir/NAME/20000121T0000Z/checksums',
            verbose=False
            )

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
        mock_exec.assert_called_once_with(
            ['ssh', '-oBatchMode=yes', 'RHOST', '-n', 'cd',
             '/ArchiveDir/NAME/20000121T0000Z', ';', 'md5sum',
             '*', '>', 'checksums'],
            cwd=os.getcwd(), verbose=False
            )

    def test_gen_checksums_pull_fail(self):
        '''Test generation of checksums'''
        func.logtest('test _generate_checksums - pull')
        self.inst._transfer_type = 'pull'
        with mock.patch('transfer.utils.exec_subproc', return_value=[1, '']):
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
        mock_exec.assert_called_once_with('md5sum -c checksums',
                                          cwd='/XDIR/NAME/20000121T0000Z')

    def test_verify_chksums_pull_fail(self):
        '''Test verification of checksums - Pull'''
        func.logtest('test _do_verify_checksums')
        self.inst._transfer_type = "Pull"
        with mock.patch('transfer.utils.exec_subproc', return_value=[1, '']):
            with self.assertRaises(SystemExit):
                rtn = self.inst._do_verify_checksums()
                self.assertEqual(rtn, False)
        self.assertIn('Checksum verification failed', func.capture('err'))

    def test_do_verify_checksums_push(self):
        '''Test verification of checksums - Push'''
        func.logtest('test _do_verify_checksums')
        with mock.patch('transfer.utils.exec_subproc', return_value=[0, '']):
            rtn = self.inst._do_verify_checksums()
            self.assertEqual(rtn, True)
        self.assertIn('Checksum verification succeeded', func.capture())

    def test_verify_chksums_push_fail(self):
        '''Test verification of checksums - Push'''
        func.logtest('test _do_verify_checksums')
        with mock.patch('transfer.utils.exec_subproc', return_value=[1, '']):
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
        mock_exec.assert_called_once_with(
            'ls -A /ArchiveDir/NAME/20000121T0000Z', verbose=False
            )

    def test_do_transfer_ssh_failed(self):
        '''Test transfer of archived files'''
        func.logtest('test do_transfer')
        with mock.patch('transfer.utils.exec_subproc', return_value=[255, '']):
            with self.assertRaises(SystemExit):
                self.inst.do_transfer()
        self.assertIn('Failed: ssh failed', func.capture('err'))

    def test_xfer_error_checking_files(self):
        '''Test transfer of archived files'''
        func.logtest('test do_transfer')
        with mock.patch('transfer.utils.exec_subproc', return_value=[10, '']):
            with self.assertRaises(SystemExit):
                self.inst.do_transfer()
        self.assertIn('Error checking files', func.capture('err'))

    @mock.patch('transfer.Transfer._do_verify_checksums', return_value=True)
    @mock.patch('transfer.Transfer._generate_checksums', return_value=True)
    @mock.patch('transfer.utils.exec_subproc')
    def test_xfer_push_rsync_verify_ok(self, mock_exec,
                                       mock_gen, mock_verify):
        '''Test do_transfer using rsync and checksum verification -push'''
        func.logtest('test do_transfer')
        mock_exec.side_effect = [[0, 'file'], [0, '']]
        self.inst._verify_chksums = True
        with mock.patch('transfer.Transfer._get_data_size', return_value=100):
           rtn = self.inst.do_transfer()
        self.assertIn('Checksums generated successfully', func.capture())
        self.assertIn('using rsync', func.capture())
        transfer_cmd = 'rsync -av --stats --rsync-path="mkdir -p ' \
            '/XDIR/NAME/20000121T0000Z && rsync" ' \
            '/ArchiveDir/NAME/20000121T0000Z/ ' \
            'RHOST:/XDIR/NAME/20000121T0000Z'
        mock_exec.assert_any_call(transfer_cmd)
        mock_verify.assert_called_once_with()
        mock_gen.assert_called_once_with()
        self.assertIn('Transfer command succeeded', func.capture())
        self.assertIn('Checksums verified', func.capture())
        self.assertIn('Transfer OK', func.capture())
        self.assertEqual(rtn, 0)

    @mock.patch('transfer.utils.create_dir')
    @mock.patch('transfer.utils.exec_subproc')
    def test_do_transfer_pull_rsync_ok(self, mock_exec, mock_cdir):
        '''Test do_transfer using rsync - pull'''
        func.logtest('test do_transfer')
        mock_exec.side_effect = [[0, 'file'], [0, '']]
        self.inst._transfer_type = 'pull'
        with mock.patch('transfer.Transfer._get_data_size', return_value=100):
            with mock.patch('transfer.os.path.exists', return_value=False):
                rtn = self.inst.do_transfer()
        self.assertIn('using rsync', func.capture())
        self.assertIn('Creating transfer directory', func.capture())
        mock_cdir.assert_called_once_with('/XDIR/NAME/20000121T0000Z')
        transfer_cmd = 'rsync -av --stats ' \
            'RHOST:/ArchiveDir/NAME/20000121T0000Z/ ' \
            '/XDIR/NAME/20000121T0000Z'
        mock_exec.assert_any_call(transfer_cmd)
        self.assertIn('Transfer command succeeded', func.capture())
        self.assertIn('Transfer OK', func.capture())
        self.assertEqual(rtn, 0)

    @mock.patch('transfer.utils.exec_subproc')
    def test_do_transfer_push_globus_ok(self, mock_exec):
        '''Test do_transfer using globus - push'''
        func.logtest('test do_transfer')
        mock_exec.side_effect = [[0, 'file'], [0, 'TASKID'], [0,'']]
        self.inst._globus_cli = True
        self.inst._globus_notify = 'off'
        self.inst._globus_default_colls = True
        with mock.patch('transfer.Transfer._get_data_size', return_value=100):
            with mock.patch('transfer.os.path.exists', return_value=False):
                rtn = self.inst.do_transfer()
        self.assertIn('using Globus CLI', func.capture())
        globus_cmd = 'globus transfer --format unix --jmespath \'task_id\' --recursive' \
                '--fail-on-quota-errors --sync-level checksum --label NAME/20000121T0000Z' \
                '--verify-checksum --notify=\'off\'' 
        globus_cmd = 'globus transfer --format unix --jmespath \'task_id\' --recursive ' \
                '--fail-on-quota-errors --sync-level checksum --label NAME/20000121T0000Z ' \
                '--verify-checksum --notify off ' \
                '3e90d018-0d05-461a-bbaf-aab605283d21:/ArchiveDir/NAME/20000121T0000Z ' \
                'a2f53b7f-1b4e-4dce-9b7c-349ae760fee0:/XDIR/NAME/20000121T0000Z'
        mock_exec.assert_any_call(globus_cmd)
        globus_wait_cmd = 'globus task wait -H TASKID'
        mock_exec.assert_any_call(globus_wait_cmd)
        self.assertIn('Transfer command succeeded', func.capture())
        self.assertEqual(rtn, 0)

    @mock.patch('transfer.utils.exec_subproc')
    def test_do_transfer_push_globus_fail(self, mock_exec):
        '''Test do_transfer using globus - Fail'''
        func.logtest('test do_transfer with globus fail')
        mock_exec.side_effect = [[0, 'file'], [1, '']]
        self.inst._globus_cli = True
        self.inst._globus_notify = 'off'
        self.inst._globus_default_colls = True
        with mock.patch('transfer.Transfer._get_data_size', return_value=100):
            with mock.patch('transfer.os.path.exists', return_value=False):
                with self.assertRaises(SystemExit):
                    rtn = self.inst.do_transfer()
                    self.assertEqual(rtn, 1)
        self.assertIn('using Globus CLI', func.capture())
        self.assertIn('Transfer command failed:', func.capture('err'))
        self.assertIn('transfer.py: Globus Error: Network', func.capture('err'))

    @mock.patch('transfer.utils.exec_subproc')
    def test_do_transfer_pull_globus_fail(self, mock_exec):
        '''Test do_transfer using globus pull - Fail'''
        func.logtest('test do_transfer with globus pull')
        mock_exec.side_effect = [[0, 'file']]
        self.inst._globus_cli = True
        self.inst._globus_notify = 'off'
        self.inst._globus_default_colls = True
        self.inst._transfer_type = 'pull'
        with mock.patch('transfer.Transfer._get_data_size', return_value=100):
            with mock.patch('transfer.os.path.exists', return_value=False):
                with self.assertRaises(SystemExit):
                    rtn = self.inst.do_transfer()
                    self.assertEqual(rtn, 5)
        self.assertIn('Using Globus CLI to pull files to JASMIN', func.capture('err'))

    @mock.patch('transfer.utils.exec_subproc', return_value=[0, 'file'])
    def test_transfer_checksum_gen_fail(self, mock_exec):
        '''Test do_transfer with checksum generation fail'''
        func.logtest('test do_transfer checksum gen fail')
        self.inst._verify_chksums = True
        with mock.patch('transfer.Transfer._generate_checksums',
                        return_value=False):
            with self.assertRaises(SystemExit):
                rtn = self.inst.do_transfer()
                self.assertEqual(rtn, 3)
        mock_exec.assert_called_once_with(
            'ls -A /ArchiveDir/NAME/20000121T0000Z', verbose=False
            )
        self.assertIn('Checksum generation failed', func.capture('err'))

    @mock.patch('transfer.utils.exec_subproc')
    def test_xfer_checksum_verify_fail(self, mock_exec):
        '''Test do_transfer with checksum verification fail'''
        func.logtest('test do_transfer checksum verify fail')
        self.inst._verify_chksums = True
        mock_exec.side_effect = [[0, 'file'], [0, '']]
        with mock.patch('transfer.Transfer._get_data_size', return_value=100):
            with mock.patch('transfer.Transfer._do_verify_checksums',
                            return_value=False):
                with mock.patch('transfer.Transfer._generate_checksums'):
                    with self.assertRaises(SystemExit):
                        rtn = self.inst.do_transfer()
                        self.assertEqual(rtn, 4)
        self.assertIn('Problem with checksum verification', func.capture('err'))

    @mock.patch('transfer.utils.exec_subproc')
    def test_do_transfer__fail(self, mock_exec):
        '''Test do_transfer with failure'''
        func.logtest('test do_transfer checksum verify fail')
        mock_exec.side_effect = [[0, 'file'], [5, '']]
        with mock.patch('transfer.Transfer._get_data_size',
                        return_value=100):
            with self.assertRaises(SystemExit):
                _ = self.inst.do_transfer()
        self.assertIn('Transfer command failed:', func.capture('err'))
        self.assertIn('transfer.py: Unknown', func.capture('err'))
