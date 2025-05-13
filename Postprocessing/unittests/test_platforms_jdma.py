#!/usr/bin/env python
'''
**********************************************************************
Contribution by NCAS-CMS:

**********************************************************************

NAME
    test_platforms_jdma.py

DESCRIPTION
    Unit tests for Archer2-JASMIN archiving

'''
import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock jdma_client globally to prevent import errors
sys.modules['jdma_client'] = MagicMock()
from jdma import JDMAInterface, get_user_login_name, \
                 get_gws_root_from_path, NotAGroupWorkspace

class TestJDMA(unittest.TestCase):

    @patch('jdma.pwd.getpwuid')
    @patch('jdma.os.getuid')
    def test_get_user_login_name(self, mock_getuid, mock_getpwuid):
        mock_getuid.return_value = 1000
        mock_getpwuid.return_value.pw_name = 'testuser'
        self.assertEqual(get_user_login_name(), 'testuser')

    @patch('jdma.os.path.isdir')
    def test_get_gws_root_from_path_valid(self, mock_isdir):
        mock_isdir.return_value = True
        path = '/gws/noproj/testuser'
        self.assertEqual(get_gws_root_from_path(path), '/gws/noproj/testuser')

    def test_get_gws_root_from_path_invalid(self):
        with self.assertRaises(NotAGroupWorkspace):
            get_gws_root_from_path('/invalid/path')

    @patch('jdma.get_user_login_name', return_value='testuser')
    def test_jdma_interface_init(self, mock_get_user):
        jdma = JDMAInterface(workspace='test_workspace')
        self.assertEqual(jdma.username, 'testuser')
        self.assertEqual(jdma.workspace, 'test_workspace')
        self.assertEqual(jdma.storage_type, 'elastictape')
        mock_get_user.assert_called_once_with()

    @patch('jdma.jdma_lib.upload_files')
    def test_submit_migrate(self, mock_upload_files):
        mock_upload_files.return_value.json.return_value = {
            'request_id': '1234', 'batch_id': '5678'
        }
        mock_upload_files.return_value.status_code = 200
        jdma = JDMAInterface(workspace='test_workspace')
        result = jdma.submit_migrate('/path/to/migrate')
        self.assertEqual(result, ('1234', '5678'))

    @patch('jdma.jdma_common.get_batch_stage')
    @patch('jdma.jdma_lib.get_batch')
    def test_get_batch_id_for_path(self, mock_get_batch, mock_batch_stage):
        mock_get_batch.return_value.json.return_value = {
            'migrations': [{'migration_id': 'batch123', 'stage': 'ON_STORAGE'}]
        }
        mock_get_batch.return_value.status_code = 200
        mock_batch_stage.return_value = 'ON_STORAGE'
        jdma = JDMAInterface(workspace='test_workspace')
        batch_id = jdma._get_batch_id_for_path('/path/to/migrate')
        self.assertEqual(batch_id, 'batch123')


if __name__ == '__main__':
    unittest.main()
