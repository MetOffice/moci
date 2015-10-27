#!/usr/bin/env python2.7

import unittest
import mock
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(
                                os.path.dirname(__file__)))+'/common')
import moo
import testing_functions as func


class commandTests(unittest.TestCase):
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

    def testInstanceCommandExec(self):
        '''Test creation of moose archiving object'''
        func.logtest('Check creation of moose object instance')
        self.assertIsInstance(self.inst, moo.CommandExec)

    @mock.patch('moo._Moose.putData')
    @mock.patch('utils.exec_subproc')
    def testArchive(self, mock_subproc, mock_putData):
        '''Test archive request'''
        func.logtest('Test archive request:')
        mock_subproc.return_value = (0, '')
        mock_putData.return_value = 'A'
        self.assertEqual(self.inst.execute(self.cmd),
                         {self.cmd['CURRENT_RQST_NAME']:
                          mock_putData.return_value})

    @mock.patch('moo.os')
    def testDelete(self, mock_os):
        '''Test delete request'''
        func.logtest('Test delete request:')
        self.cmd['CURRENT_RQST_ACTION'] = 'DELETE'
        fn = self.cmd['CURRENT_RQST_NAME']
        mock_os.path.exist.return_value = False
        rc = self.inst.execute(self.cmd)
        mock_os.path.exist.assert_called_with(fn)
        mock_os.remove.assert_called_with(fn)
        self.assertIn('Deleting', func.capture())
        self.assertEqual(rc, {'DELETE': 0})

    @mock.patch('moo.os')
    def testDeleteArchived(self, mock_os):
        '''Test delete request for archived file'''
        func.logtest('Test delete request for successfully archived file:')
        fn = self.cmd['CURRENT_RQST_NAME']
        mock_os.path.exist.return_value = False
        rc = self.inst.delete(fn, 0)
        mock_os.path.exist.assert_called_with(fn)
        mock_os.remove.assert_called_with(fn)
        self.assertIn('Deleting', func.capture())
        self.assertEqual(rc, 0)

    @mock.patch('moo.os')
    def testDeleteNotArchived(self, mock_os):
        '''Test delete request for un-archived file'''
        func.logtest('Test delete request for failed archive file:')
        fn = self.cmd['CURRENT_RQST_NAME']
        rc = self.inst.delete(fn, 20)
        mock_os.path.exist.assert_called_with(fn)
        self.assertFalse(mock_os.remove.called)
        self.assertIn('Not deleting', func.capture(direct='err'))
        self.assertEqual(rc, 1)

    def testExecuteNoAction(self):
        '''Test execute "NO ACTION" request'''
        func.logtest('Test execute "NO ACTION" request:')
        self.cmd['CURRENT_RQST_ACTION'] = 'NA'
        self.assertEqual(self.inst.execute(self.cmd), {'NO ACTION': 0})
        self.assertIn('Neither', func.capture(direct='err'))


class mooseTests(unittest.TestCase):
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
        os.environ['RUNID'] = 'ATMOS'
        os.environ['PREFIX'] = 'PATH/'
        self.inst = moo._Moose(cmd)

    def tearDown(self):
        pass

    @mock.patch('utils.exec_subproc')
    def testInstanceMoose(self, mock_subproc):
        '''Test creation of a Moose archiving object'''
        func.logtest('test creation of a Moose archiving object:')
        mock_subproc.return_value = (0, 'true')
        self.assertEqual(self.inst._modelID, 'a')
        self.assertEqual(self.inst._fileID, 'da')
        self.assertTrue(self.inst.chkset())

    @mock.patch('utils.exec_subproc')
    def testCreateSet(self, mock_subproc):
        '''Test creation of a Moose data set'''
        func.logtest('test creation of a Moose set:')
        mock_subproc.return_value = (0, 'false')
        self.assertFalse(self.inst.chkset())
        self.assertIn('mkset:', func.capture())

    @mock.patch('utils.exec_subproc')
    def testMksetProject(self, mock_subproc):
        '''Test mkset function with project'''
        func.logtest('test mkset function, with project:')
        mock_subproc.return_value = (0, '')
        self.inst._project = 'UKESM'
        self.inst.mkset()
        cmd = 'moo mkset -v -p ' + self.inst._project + ' ' + self.inst.dataset
        mock_subproc.assert_called_with(cmd, verbose=False)
        self.assertIn('created set', func.capture())

    @mock.patch('utils.exec_subproc')
    def testMksetCategoryFail(self, mock_subproc):
        '''Test mkset function with category - Failed operation'''
        func.logtest('test mkset with category - Failed operation:')
        mock_subproc.return_value = (-1, '')
        self.inst._cat = 'GLOBAL'
        self.inst.mkset()
        cmd = 'moo mkset -v -c ' + self.inst._cat + ' ' + self.inst.dataset
        mock_subproc.assert_called_with(cmd, verbose=False)
        self.assertIn('Unable to create', func.capture(direct='err'))

    @mock.patch('utils.exec_subproc')
    def testMksetPreExisting(self, mock_subproc):
        '''Test mkset function with pre-existing set'''
        func.logtest('test mkset function, with pre-existing set:')
        mock_subproc.return_value = (10, '')
        self.inst.mkset()
        mock_subproc.assert_called_with('moo mkset -v ' + self.inst.dataset,
                                        verbose=False)
        self.assertIn('already exists', func.capture())

    def testCollectionAtmosDump(self):
        '''Test formation of collection name - atmosphere dump'''
        func.logtest('test foramtion of collection name with atmos dump:')
        collection = self.inst._collection()
        self.assertEqual(collection, 'ada.file')
        self.assertFalse(self.inst._fl_pp)

    def testCollectionAtmosPP(self):
        '''Test formation of collection name - atmosphere mean'''
        func.logtest('test foramtion of collection name with atmos mean:')
        self.inst._modelID = 'a'
        self.inst._fileID = 'pm'
        collection = self.inst._collection()
        self.assertEqual(collection, 'apm.pp')
        self.assertTrue(self.inst._fl_pp)

    def testCollectionOceanRestart(self):
        '''Test formation of collection name - NEMO restart'''
        func.logtest('test foramtion of collection name with NEMO restart:')
        self.inst._modelID = 'o'
        self.inst._fileID = 're'
        collection = self.inst._collection()
        self.assertEqual(collection, 'oda.file')
        self.assertFalse(self.inst._fl_pp)

    def testCollectionIceMean(self):
        '''Test formation of collection name - CICE mean'''
        func.logtest('test foramtion of collection name with CICE mean:')
        self.inst._modelID = 'i'
        self.inst._fileID = '1s'
        collection = self.inst._collection()
        self.assertEqual(collection, 'ins.nc.file')
        self.assertFalse(self.inst._fl_pp)

    @mock.patch('utils.exec_subproc')
    @mock.patch('os.path.exists')
    def testPutDataPrefix(self, mock_exist, mock_subproc):
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
    @mock.patch('os.path.exists')
    def testPutDataPP(self, mock_exist, mock_subproc):
        '''Test putData function with fieldsfile'''
        func.logtest('test putData function with fieldsfile:')
        self.inst._rqst_name = 'RUNIDa.pmTestfile'
        mock_subproc.return_value = (0, '')
        mock_exist.return_value = True
        self.inst._modelID = 'a'
        self.inst._fileID = 'pm'
        self.inst.putData()
        cmd = 'moo put -f -vv -c=umpp '
        src = 'TestDir/RUNIDa.pmTestfile'
        dest = 'moose:myclass/runid/apm.pp/RUNIDa.pmTestfile.pp'
        mock_subproc.assert_called_with(cmd + os.path.expandvars(
            src + ' ' + dest))

    @mock.patch('utils.exec_subproc')
    def testPutDataNonExistant(self, mock_subproc):
        '''Test putData with non-existant file'''
        func.logtest('test putData function with non-existant file:')
        rtn = self.inst.putData()
        mock_subproc.assert_not_called()
        self.assertIn('does not exist', func.capture(direct='err'))
        self.assertEqual(rtn, 99)

    @mock.patch('os.path.exists')
    def testPutDataJOBTEMP(self, mock_exist):
        '''Test putData function with JOBTEMP'''
        func.logtest('test putData function with JOBTEMP:')
        os.environ['JOBTEMP'] = 'jobtemp'
        mock_exist.return_value = True
        self.inst.putData()
        self.assertEqual(os.environ['UM_TMPDIR'], 'jobtemp')

    @mock.patch('os.path.exists')
    def testPutDataJOBTEMPempty(self, mock_exist):
        '''Test putData function with empty JOBTEMP'''
        func.logtest('test putData function with empty JOBTEMP:')
        os.environ['JOBTEMP'] = ''
        mock_exist.return_value = True
        self.inst.putData()
        self.assertIn('likely to fail', func.capture(direct='err'))


def main():
    unittest.main(buffer=True)


if __name__ == '__main__':
    main()
