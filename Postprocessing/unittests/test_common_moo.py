#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''
import unittest
import mock
import os
import sys

import runtimeEnvironment
import testing_functions as func
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'common'))
import moo


class CommandTests(unittest.TestCase):
    '''Unit tests relating to the moo.CommandExec() method'''
    def setUp(self):
        self.cmd = {
            'CURRENT_RQST_ACTION': 'ARCHIVE',
            'CURRENT_RQST_NAME':   'RUNIDa.daTestFile',
            'DATAM':               'TestDir',
            'RUNID':               'runid',
            'CATEGORY':            'UNCATEGORISED',
            'DATACLASS':           'myclass',
            'MOOPATH':             '',
            'PROJECT':             ''
        }
        self.inst = moo.CommandExec()

    def tearDown(self):
        pass

    def test_instance_command_exec(self):
        '''Test creation of moose archiving object'''
        func.logtest('Check creation of moose object instance')
        self.assertIsInstance(self.inst, moo.CommandExec)

    @mock.patch('moo._Moose.putData')
    @mock.patch('utils.exec_subproc')
    def test_archive(self, mock_subproc, mock_putdata):
        '''Test archive request'''
        func.logtest('Test archive request:')
        mock_subproc.return_value = (0, '')
        mock_putdata.return_value = 'A'
        self.assertEqual(self.inst.execute(self.cmd),
                         {self.cmd['CURRENT_RQST_NAME']:
                          mock_putdata.return_value})

    @mock.patch('moo.os')
    def test_delete(self, mock_os):
        '''Test delete request'''
        func.logtest('Test delete request:')
        self.cmd['CURRENT_RQST_ACTION'] = 'DELETE'
        fname = self.cmd['CURRENT_RQST_NAME']
        mock_os.path.exist.return_value = False
        retcode = self.inst.execute(self.cmd)
        mock_os.path.exist.assert_called_with(fname)
        mock_os.remove.assert_called_with(fname)
        self.assertIn('Deleting', func.capture())
        self.assertEqual(retcode, {'DELETE': 0})

    @mock.patch('moo.os')
    def test_delete_archived(self, mock_os):
        '''Test delete request for archived file'''
        func.logtest('Test delete request for successfully archived file:')
        fname = self.cmd['CURRENT_RQST_NAME']
        mock_os.path.exist.return_value = False
        retcode = self.inst.delete(fname, 0)
        mock_os.path.exist.assert_called_with(fname)
        mock_os.remove.assert_called_with(fname)
        self.assertIn('Deleting', func.capture())
        self.assertEqual(retcode, 0)

    @mock.patch('moo.os')
    def test_delete_not_archived(self, mock_os):
        '''Test delete request for un-archived file'''
        func.logtest('Test delete request for failed archive file:')
        fname = self.cmd['CURRENT_RQST_NAME']
        retcode = self.inst.delete(fname, 20)
        mock_os.path.exist.assert_called_with(fname)
        self.assertFalse(mock_os.remove.called)
        self.assertIn('Not deleting', func.capture(direct='err'))
        self.assertEqual(retcode, 1)

    def test_execute_no_action(self):
        '''Test execute "NO ACTION" request'''
        func.logtest('Test execute "NO ACTION" request:')
        self.cmd['CURRENT_RQST_ACTION'] = 'NA'
        self.assertEqual(self.inst.execute(self.cmd), {'NO ACTION': 0})
        self.assertIn('Neither', func.capture(direct='err'))


class MooseTests(unittest.TestCase):
    '''Unit tests relating to Moose archiving functionality'''
    @mock.patch('utils.exec_subproc')
    def setUp(self, mock_subproc):
        mock_subproc.return_value = (0, '')
        cmd = {
            'CURRENT_RQST_ACTION': 'ARCHIVE',
            'CURRENT_RQST_NAME':   'full/path/to/RUNIDa.daTestFile',
            'DATAM':               'TestDir',
            'RUNID':               'runid',
            'CATEGORY':            'UNCATEGORISED',
            'DATACLASS':           'myclass',
            'MOOPATH':             '',
            'PROJECT':             ''
        }
        if 'iceberg' in self.id():
            cmd['CURRENT_RQST_NAME'] = \
                'RUNIDo_icebergs_YYYYMMDD_restart.nc'
        elif 'ocean' in self.id():
            cmd['CURRENT_RQST_NAME'] = \
                'RUNIDo_19951130_restart.nc'
        os.environ['PREFIX'] = 'PATH/'
        self.inst = moo._Moose(cmd)

    def tearDown(self):
        pass

    @mock.patch('utils.exec_subproc')
    def test_instance_moose(self, mock_subproc):
        '''Test creation of a Moose archiving object'''
        func.logtest('test creation of a Moose archiving object:')
        mock_subproc.return_value = (0, 'true')
        self.assertEqual(self.inst._modelID, 'a')
        self.assertEqual(self.inst._fileID, 'da')
        self.assertTrue(self.inst.chkset())

    @mock.patch('utils.exec_subproc')
    def test_create_set(self, mock_subproc):
        '''Test creation of a Moose data set'''
        func.logtest('test creation of a Moose set:')
        mock_subproc.return_value = (0, 'false')
        self.assertFalse(self.inst.chkset())
        self.assertIn('mkset:', func.capture())

    @mock.patch('utils.exec_subproc')
    def test_mkset_project(self, mock_subproc):
        '''Test mkset function with project'''
        func.logtest('test mkset function, with project:')
        mock_subproc.return_value = (0, '')
        self.inst._project = 'UKESM'
        self.inst.mkset()
        cmd = 'moo mkset -v -p ' + self.inst._project + ' ' + self.inst.dataset
        mock_subproc.assert_called_with(cmd, verbose=False)
        self.assertIn('created set', func.capture())

    @mock.patch('utils.exec_subproc')
    def test_mkset_category_fail(self, mock_subproc):
        '''Test mkset function with category - Failed operation'''
        func.logtest('test mkset with category - Failed operation:')
        mock_subproc.return_value = (-1, '')
        self.inst._cat = 'GLOBAL'
        self.inst.mkset()
        cmd = 'moo mkset -v -c ' + self.inst._cat + ' ' + self.inst.dataset
        mock_subproc.assert_called_with(cmd, verbose=False)
        self.assertIn('Unable to create', func.capture(direct='err'))

    @mock.patch('utils.exec_subproc')
    def test_mkset_pre_existing(self, mock_subproc):
        '''Test mkset function with pre-existing set'''
        func.logtest('test mkset function, with pre-existing set:')
        mock_subproc.return_value = (10, '')
        self.inst.mkset()
        mock_subproc.assert_called_with('moo mkset -v ' + self.inst.dataset,
                                        verbose=False)
        self.assertIn('already exists', func.capture())

    def test_collection_atmos_dump(self):
        '''Test formation of collection name - atmosphere dump'''
        func.logtest('test formation of collection name with atmos dump:')
        collection = self.inst._collection()
        self.assertEqual(collection, 'ada.file')
        self.assertFalse(self.inst._fl_pp)

    def test_collection_atmos_pp(self):
        '''Test formation of collection name - atmosphere mean'''
        func.logtest('test formation of collection name with atmos mean:')
        self.inst._modelID = 'a'
        self.inst._fileID = 'pm'
        collection = self.inst._collection()
        self.assertEqual(collection, 'apm.pp')
        self.assertTrue(self.inst._fl_pp)

    def test_collection_ocean_restart(self):
        '''Test formation of collection name - NEMO restart'''
        func.logtest('test formation of collection name with NEMO restart:')
        collection = self.inst._collection()
        self.assertEqual(collection, 'oda.file')
        self.assertFalse(self.inst._fl_pp)

    def test_collection_iceberg_restart(self):
        '''Test formation of collection name - iceberg restart'''
        func.logtest('test formation of collection name with iceberg restart:')
        collection = self.inst._collection()
        self.assertEqual(collection, 'oda.file')
        self.assertFalse(self.inst._fl_pp)

    def test_collection_ice_mean(self):
        '''Test formation of collection name - CICE mean'''
        func.logtest('test formation of collection name with CICE mean:')
        self.inst._modelID = 'i'
        self.inst._fileID = '1s'
        collection = self.inst._collection()
        self.assertEqual(collection, 'ins.nc.file')
        self.assertFalse(self.inst._fl_pp)

    @mock.patch('utils.exec_subproc')
    @mock.patch('os.path.exists')
    def test_putdata_prefix(self, mock_exist, mock_subproc):
        '''Test putData function with $PREFIX$RUNID crn'''
        func.logtest('test putData function with $PREFIX$RUNID crn:')
        self.inst._rqst_name = '$PREFIX$RUNID.daTestfile'
        mock_subproc.return_value = (0, '')
        mock_exist.return_value = True
        self.inst.putData()
        src = os.path.expandvars('TestDir/$PREFIX$RUNID.daTestfile')
        dest = os.path.expandvars('moose:myclass/runid/$RUNID.daTestfile')
        mock_subproc.assert_called_with('moo put -f -vv ' + src + ' ' + dest)

    @mock.patch('utils.exec_subproc')
    def test_putdata_pp(self, mock_subproc):
        '''Test putData function with fieldsfile'''
        func.logtest('test putData function with fieldsfile:')
        self.inst._rqst_name = 'RUNIDa.pmTestfile'
        self.inst._modelID = 'a'
        self.inst._fileID = 'pm'
        mock_subproc.return_value = (0, '')
        with mock.patch('os.path.exists', return_value=True):
            self.inst.putData()
        self.inst.putData()
        cmd = 'moo put -f -vv -c=umpp '
        src = 'TestDir/RUNIDa.pmTestfile'
        dest = 'moose:myclass/runid/apm.pp/RUNIDa.pmTestfile.pp'
        mock_subproc.assert_called_with(cmd + os.path.expandvars(
            src + ' ' + dest))

    @mock.patch('utils.exec_subproc')
    def test_putdata_pp_no_convert(self, mock_subproc):
        '''Test putData function with fieldsfile'''
        func.logtest('test putData function with fieldsfile:')
        self.inst._rqst_name = 'RUNIDa.pmTestfile.pp'
        self.inst._fl_pp = True
        mock_subproc.return_value = (0, '')
        with mock.patch('moo._Moose._collection', return_value='apm.pp'):
            with mock.patch('os.path.exists', return_value=True):
                self.inst.putData()
        cmd = 'moo put -f -vv TestDir/RUNIDa.pmTestfile.pp ' \
            'moose:myclass/runid/apm.pp'
        mock_subproc.assert_called_with(cmd)

    @mock.patch('utils.exec_subproc')
    def testPutDataNonExistant(self, mock_subproc):
        '''Test putData with non-existant file'''
        func.logtest('test putData function with non-existant file:')
        rtn = self.inst.putData()
        mock_subproc.assert_not_called()
        self.assertIn('does not exist', func.capture(direct='err'))
        self.assertEqual(rtn, 99)

    @mock.patch('os.path.exists')
    def test_putdata_jobtemp(self, mock_exist):
        '''Test putData function with JOBTEMP'''
        func.logtest('test putData function with JOBTEMP:')
        os.environ['JOBTEMP'] = 'jobtemp'
        mock_exist.return_value = True
        self.inst.putData()
        self.assertEqual(os.environ['UM_TMPDIR'], 'jobtemp')

    @mock.patch('os.path.exists')
    def test_putdata_jobtemp_empty(self, mock_exist):
        '''Test putData function with empty JOBTEMP'''
        func.logtest('test putData function with empty JOBTEMP:')
        os.environ['JOBTEMP'] = ''
        mock_exist.return_value = True
        self.inst.putData()
        self.assertIn('likely to fail', func.capture(direct='err'))


def main():
    '''Main function'''
    unittest.main(buffer=True)


if __name__ == '__main__':
    main()
