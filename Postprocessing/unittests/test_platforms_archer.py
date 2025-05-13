#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2017-2018 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    test_platforms_archer.py

DESCRIPTION
    Archer archiving

'''

import shutil
import unittest
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
    import mock

import testing_functions as func

import archer

class ArcherTests(unittest.TestCase):
    '''Unit tests relating to the archiving from Archer'''
    def setUp(self):
        cmd = {
            'CURRENT_RQST_NAME':   'atmos_testpa.daTestFile',
            'DATAM':               'TestDir',
            'RUNID':               'RUNID',
            'ARCHIVE_ROOT':        'ArchiveDir',
        }
        with mock.patch.dict('archer.os.environ',
                             {'ROSE_DATAC': ''}):
            self.nlist = archer.ArcherArch()
            self.inst = archer._Archer(cmd)

    def tearDown(self):
        for dirname in ['ArchiveDir', 'suiteID']:
            try:
                shutil.rmtree(dirname)
            except OSError:
                pass

    @mock.patch('archer.os.path')
    @mock.patch('archer._Archer.put_data')
    def test_archive(self, mock_putdata, mock_ospath):
        ''' Test archive_to_rdf '''
        func.logtest('Assert call to put_data:')
        mock_ospath.exists.return_value = True
        with mock.patch.dict('archer.os.environ',
                             {'ROSE_DATAC': ''}):
            _ = archer.archive_to_rdf('RUNIDa.pa1234jan', 'SourceDir',
                                      self.nlist)
        mock_putdata.assert_called_once_with()

    @mock.patch('archer.utils.exec_subproc')
    @mock.patch('archer.os.path')
    def test_putdata(self, mock_ospath, mock_exec):
        '''Test creation of Archer archiving object'''
        func.logtest('Check creation of Archer object instance')
        mock_ospath.exists.return_value = True
        mock_exec.return_value = [0, '']
        rtn = self.inst.put_data()
        self.assertEqual(rtn, 0)
        self.assertIn('copied to staging area ArchiveDir/RUNID', func.capture())
        exec_cmd = mock_exec.mock_calls[0]
        self.assertTrue(exec_cmd.startswith('mv '))
        self.assertTrue(exec_cmd.endswith('ArchiveDir/RUNID/20000121T0000Z.'))

    @mock.patch('archer.utils.exec_subproc')
    @mock.patch('archer.os.path')
    def test_putdata_copy_error(self, mock_ospath, mock_exec):
        '''Test creation of Archer archiving object'''
        func.logtest('Check creation of Archer object instance')
        mock_ospath.exists.return_value = True
        mock_exec.return_value = [1, 'Error']
        rtn = self.inst.put_data()
        self.assertEqual(rtn, 13)
        self.assertIn('Move failed', func.capture('err'))

    @mock.patch('archer.os.path')
    def test_putdata_no_such_path(self, mock_ospath):
        '''Test creation of Archer archiving object'''
        func.logtest('Check creation of Archer object instance')
        mock_ospath.exists.return_value = False
        with self.assertRaises(SystemExit):
            rtn = self.inst.put_data()
            self.assertEqual(rtn, 99)
        self.assertIn('No archiving done', func.capture('err'))
        self.assertNotIn('Unknown Error', func.capture('err'))

    @mock.patch('archer.os.path')
    def test_putdata_no_such_path_debug(self, mock_ospath):
        '''Test creation of Archer archiving object'''
        func.logtest('Check creation of Archer object instance')
        mock_ospath.exists.return_value = False
        with mock.patch('archer.utils.get_debugmode', return_value=True):
            rtn = self.inst.put_data()
            self.assertEqual(rtn, 99)
        self.assertIn('No archiving done', func.capture('err'))
        self.assertIn('Unknown Error', func.capture('err'))