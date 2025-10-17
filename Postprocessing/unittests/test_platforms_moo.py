#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2025 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''
import unittest
import os
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
    import mock

import testing_functions as func
import runtime_environment

# Import of moo requires 'CYLC_SUITE_NAME' from runtime environment
runtime_environment.setup_env()
import moo

MOO_NLIST = moo.MooseArch()
MOO_NLIST.archive_set='mysuite'
MOO_NLIST.dataclass='myclass'
MOO_CMD = {
    'CURRENT_RQST_ACTION': 'ARCHIVE',
    'CURRENT_RQST_NAME':   'full/path/to/TESTPa.daTestFile',
    'FILENAME_PREFIX':     'TESTP',
    'DATAM':               'TestDir',
    'SETNAME':             MOO_NLIST.archive_set,
    'NON_DUPLEXED':        MOO_NLIST.non_duplexed_set,
    'CATEGORY':            'UNCATEGORISED',
    'DATACLASS':           MOO_NLIST.dataclass,
    'ENSEMBLEID':          MOO_NLIST.ensembleid,
    'MOOPATH':             MOO_NLIST.moopath,
    'PROJECT':             MOO_NLIST.mooproject,
    'CONVERTPP':           True,
    'ACT_AS':              MOO_NLIST.act_as
    }

class CommandTests(unittest.TestCase):
    '''Unit tests relating to the moo.CommandExec() method'''

    def setUp(self):
         self.inst = moo.CommandExec()

    def tearDown(self):
        pass

    def test_instance_command_exec(self):
        '''Test creation of moose archiving object'''
        func.logtest('Check creation of moose object instance')
        self.assertIsInstance(self.inst, moo.CommandExec)

    @mock.patch('moo._Moose.put_data')
    @mock.patch('moo.utils.exec_subproc')
    def test_archive(self, mock_subproc, mock_putdata):
        '''Test archive request'''
        func.logtest('Test archive request:')
        mock_subproc.return_value = (0, '')
        mock_putdata.return_value = 'A'
        self.assertEqual(self.inst.execute(MOO_CMD),
                         {MOO_CMD['CURRENT_RQST_NAME']:
                          mock_putdata.return_value})

    @mock.patch('moo.os')
    def test_delete(self, mock_os):
        '''Test delete request'''
        func.logtest('Test delete request:')
        moocmd = MOO_CMD.copy()
        moocmd['CURRENT_RQST_ACTION'] = 'DELETE'
        fname = MOO_CMD['CURRENT_RQST_NAME']
        mock_os.path.exists.return_value = False
        retcode = self.inst.execute(moocmd)
        mock_os.path.exists.assert_called_with(fname)
        mock_os.remove.assert_called_with(fname)
        self.assertIn('Deleting', func.capture())
        self.assertEqual(retcode, {'DELETE': 0})

    @mock.patch('moo.os')
    def test_delete_archived(self, mock_os):
        '''Test delete request for archived file'''
        func.logtest('Test delete request for successfully archived file:')
        fname = MOO_CMD['CURRENT_RQST_NAME']
        mock_os.path.exists.return_value = False
        retcode = self.inst.delete(fname, 0)
        mock_os.path.exists.assert_called_with(fname)
        mock_os.remove.assert_called_with(fname)
        self.assertIn('Deleting', func.capture())
        self.assertEqual(retcode, 0)

    @mock.patch('moo.os')
    def test_delete_not_archived(self, mock_os):
        '''Test delete request for un-archived file'''
        func.logtest('Test delete request for failed archive file:')
        fname = MOO_CMD['CURRENT_RQST_NAME']
        retcode = self.inst.delete(fname, 20)
        mock_os.path.exists.assert_called_with(fname)
        self.assertFalse(mock_os.remove.called)
        self.assertIn('Not deleting', func.capture(direct='err'))
        self.assertEqual(retcode, 1)

    def test_execute_no_action(self):
        '''Test execute "NO ACTION" request'''
        func.logtest('Test execute "NO ACTION" request:')
        moocmd = MOO_CMD.copy()
        moocmd['CURRENT_RQST_ACTION'] = 'NA'
        self.assertEqual(self.inst.execute(moocmd), {'NO ACTION': 0})
        self.assertIn('Neither', func.capture(direct='err'))


class MooseTests(unittest.TestCase):
    '''Unit tests relating to Moose archiving functionality'''

    def setUp(self):
        cmd = MOO_CMD.copy()
        if 'iceberg' in self.id():
            cmd['CURRENT_RQST_NAME'] = \
                'nemo_testpo_icebergs_YYYYMMDD_restart.nc'
        elif '_tracer_' in self.id():
            cmd['CURRENT_RQST_NAME'] = 'TESTPo_YYYYMMDD_restart_trc.nc'
        elif '_SI3_' in self.id():
            cmd['CURRENT_RQST_NAME'] = 'TESTPo_YYYYMMDD_restart_ice.nc'
        elif '_ocean_' in self.id():
            cmd['FILENAME_PREFIX'] = 'u-TESTP'
            cmd['CURRENT_RQST_NAME'] = 'u-TESTPo_YYYYMMDD_restart.nc'
        elif '_seaice_' in self.id():
            cmd['FILENAME_PREFIX'] = 'u_TESTP'
            cmd['CURRENT_RQST_NAME'] = 'u_TESTPi.restart.YYYY-MM-DD-00000.nc'
        elif '_oi_fail' in self.id():
            cmd['CURRENT_RQST_NAME'] = 'TESTPo.YYYY-MM-DD-00000.nc'
        with mock.patch('moo.utils.exec_subproc', return_value=(0, '')):
            with mock.patch.dict('moo.os.environ', {'PREFIX': 'PATH/'}):
                self.inst = moo._Moose(cmd)

    def tearDown(self):
        pass

    @mock.patch('moo.utils.exec_subproc')
    def test_instance_moose(self, mock_subproc):
        '''Test creation of a Moose archiving object'''
        func.logtest('test creation of a Moose archiving object:')
        mock_subproc.return_value = (0, 'true')
        self.assertEqual(self.inst._model_id, 'a')
        self.assertEqual(self.inst._file_id, 'daTestFile')
        self.assertTrue(self.inst.chkset())

    def test_model_id(self):
        '''Test model_id of a Moose archiving object'''
        func.logtest('assert correct model_id for Moose arch object:')
        cmd = MOO_CMD.copy()

        func.logtest('Testing raw output filename - fileprefix="medus"...')
        cmd['CURRENT_RQST_NAME'] = 'full/path/to/medusa.daYYYYMMDD'
        cmd['FILENAME_PREFIX'] = 'medus'
        with mock.patch('moo._Moose.chkset', return_value=True):
            inst = moo._Moose(cmd)
            self.assertEqual(inst._model_id, 'a')
            self.assertEqual(inst._file_id, 'daYYYYMMDD')

        func.logtest('Testing raw output filename - fileprefix="nem"...')
        cmd['CURRENT_RQST_NAME'] = 'full/path/to/nemo_YYYYMMDD_restart.nc'
        cmd['FILENAME_PREFIX'] = 'nem'
        with mock.patch('moo._Moose.chkset', return_value=True):
            inst = moo._Moose(cmd)
            self.assertEqual(inst._model_id, 'o')
            self.assertEqual(inst._file_id, 'YYYYMMDD_restart.nc')

        func.logtest('Testing raw output filename - fileprefix="nemo"...')
        cmd['CURRENT_RQST_NAME'] = 'full/path/to/nemoo_YYYYMMDD_restart.nc'
        cmd['FILENAME_PREFIX'] = 'nemo'
        with mock.patch('moo._Moose.chkset', return_value=True):
            inst = moo._Moose(cmd)
            self.assertEqual(inst._model_id, 'o')
            self.assertEqual(inst._file_id, 'YYYYMMDD_restart.nc')

        func.logtest('Testing netCDF output filename - fileprefix="nem"...')
        cmd['CURRENT_RQST_NAME'] = 'full/path/to/nemo_nemo_YYYYMMDD...nc'
        cmd['FILENAME_PREFIX'] = 'nem'
        with mock.patch('moo._Moose.chkset', return_value=True):
            inst = moo._Moose(cmd)
            self.assertEqual(inst._model_id, 'o')
            self.assertEqual(inst._file_id, 'YYYYMMDD...nc')

        func.logtest('Testing netCDF output filename - prefix="FN-PREFIX"...')
        cmd['CURRENT_RQST_NAME'] = 'full/path/to/cice_fn-prefixi_YYYYMMDD...nc'
        cmd['FILENAME_PREFIX'] = 'FN-PREFIX'
        with mock.patch('moo._Moose.chkset', return_value=True):
            inst = moo._Moose(cmd)
            self.assertEqual(inst._model_id, 'i')
            self.assertEqual(inst._file_id, 'YYYYMMDD...nc')

    def test_create_set(self):
        '''Test creation of a Moose data set'''
        func.logtest('test creation of a Moose set:')
        self.assertFalse(self.inst.chkset())

    @mock.patch('moo.utils.exec_subproc', return_value=(0, 'true'))
    def test_chkset_act_as(self, mock_subproc):
        '''Test chkset function with act_as'''
        func.logtest('test chkset function, with act_as:')
        cmd_dict = MOO_CMD.copy()
        cmd_dict['ACT_AS'] = 'user.name'

        with mock.patch('moo._Moose.chkset', return_value=True):
            inst = moo._Moose(cmd_dict)
        inst.chkset()
        cmd = 'moo test -sw --act-as user.name ' + inst.dataset
        mock_subproc.assert_called_with(cmd, verbose=False)

    @mock.patch('moo.utils.exec_subproc')
    def test_mkset_project(self, mock_subproc):
        '''Test mkset function with project'''
        func.logtest('test mkset function, with project:')
        mock_subproc.return_value = (0, '')
        project = 'UKESM'
        self.inst.mkset('UNCATEGORISED', project, False)
        cmd = 'moo mkset -v -p ' + project + ' ' + self.inst.dataset
        mock_subproc.assert_called_with(cmd, verbose=False)
        self.assertIn('created set', func.capture())

    @mock.patch('moo.utils.exec_subproc')
    def test_mkset_nonduplex(self, mock_subproc):
        '''Test mkset function with non-duplex option'''
        func.logtest('test mkset function, with non-duplex option:')
        mock_subproc.return_value = (0, '')
        self.inst.mkset('UNCATEGORISED', '', True)
        cmd = 'moo mkset -v --single-copy ' + self.inst.dataset
        mock_subproc.assert_called_with(cmd, verbose=False)
        self.assertIn('created set', func.capture())

    @mock.patch('moo.utils.exec_subproc')
    def test_mkset_act_as(self, mock_subproc):
        '''Test mkset function with act_as option'''
        func.logtest('test mkset function, with act_as option:')
        mock_subproc.return_value = (0, '')
        self.inst._act_as = 'user.name'
        self.inst.mkset('UNCATEGORISED', '', False)
        cmd = 'moo mkset -v --act-as user.name ' + self.inst.dataset
        mock_subproc.assert_called_with(cmd, verbose=False)
        self.assertIn('created set', func.capture())

    @mock.patch('moo.utils.exec_subproc')
    def test_mkset_category_fail(self, mock_subproc):
        '''Test mkset function with category - Failed operation'''
        func.logtest('test mkset with category - Failed operation:')
        mock_subproc.return_value = (-1, '')
        cat = 'GLOBAL'
        self.inst.mkset(cat, '', False)
        cmd = 'moo mkset -v -c ' + cat + ' ' + self.inst.dataset
        mock_subproc.assert_called_with(cmd, verbose=False)
        self.assertIn('Unable to create', func.capture(direct='err'))

    @mock.patch('moo.utils.exec_subproc')
    def test_mkset_pre_existing(self, mock_subproc):
        '''Test mkset function with pre-existing set'''
        func.logtest('test mkset function, with pre-existing set:')
        mock_subproc.return_value = (10, '')
        self.inst.mkset('UNCATEGORISED', '', False)
        mock_subproc.assert_called_with('moo mkset -v ' + self.inst.dataset,
                                        verbose=False)
        self.assertIn('already exists', func.capture())

    def test_collection_atmos_dump(self):
        '''Test formation of collection name - atmosphere dump'''
        func.logtest('test formation of collection name with atmos dump:')
        collection = self.inst._collection()
        self.assertEqual(collection, 'ada.file')
        self.assertFalse(self.inst.fl_pp)

    def test_collection_atmos_pp(self):
        '''Test formation of collection name - atmosphere pp'''
        func.logtest('test formation of collection name with atmos pp:')
        self.inst._model_id = 'a'
        self.inst._file_id = 'pmYYYYMMDD'
        collection = self.inst._collection()
        self.assertEqual(collection, 'apm.pp')
        self.assertTrue(self.inst.fl_pp)

    def test_collection_atmos_ff(self):
        '''Test formation of collection name - atmosphere fieldsfile'''
        func.logtest('test formation of collection name with atmos ffile:')
        self.inst._model_id = 'a'
        self.inst._file_id = 'pm'
        self.inst.convertpp = False
        collection = self.inst._collection()
        self.assertEqual(collection, 'apm.file')
        self.assertFalse(self.inst.fl_pp)

    def test_collection_atmos_netcdf(self):
        '''Test formation of collection name - atmosphere netCDF'''
        func.logtest('test formation of collection name with atmos netCDF:')
        self.inst._model_id = 'a'
        self.inst._file_id = '1d_YYYYMMDD-YYYYMMDD_pm-TAG.nc'
        collection = self.inst._collection()
        self.assertEqual(collection, 'anm.nc.file')
        self.assertFalse(self.inst.fl_pp)

    def test_collection_atmos_netcdf_noid(self):
        '''Test formation of collection name - atmosphere netCDF with no ID'''
        func.logtest('test formation of coll. name with atmos netCDF (no ID):')
        self.inst._model_id = 'a'
        self.inst._file_id = '1d_YYYYMMDD-YYYYMMDD_genericTAG.nc'
        collection = self.inst._collection()
        self.assertEqual(collection, 'and.nc.file')
        self.assertFalse(self.inst.fl_pp)

    def test_collection_ocean_restart(self):
        '''Test formation of collection name - NEMO restart'''
        func.logtest('test formation of collection name with NEMO restart:')
        collection = self.inst._collection()
        self.assertEqual(collection, 'oda.file')
        self.assertFalse(self.inst.fl_pp)

    def test_collection_iceberg_restart(self):
        '''Test formation of collection name - iceberg restart'''
        func.logtest('test formation of collection name with iceberg restart:')
        collection = self.inst._collection()
        self.assertEqual(collection, 'oda.file')
        self.assertFalse(self.inst.fl_pp)

    def test_collection_ocean_tracer_restart(self):
        '''Test formation of collection name - NEMO passive tracer restart'''
        func.logtest('test formation of collection name with tracer restart:')
        collection = self.inst._collection()
        self.assertEqual(collection, 'oda.file')
        self.assertFalse(self.inst.fl_pp)

    def test_collection_ocean_SI3_restart(self):
        '''Test formation of collection name - NEMO SI3 restart'''
        func.logtest('test formation of collection name with SI3 restart:')
        collection = self.inst._collection()
        self.assertEqual(collection, 'ida.file')
        self.assertFalse(self.inst.fl_pp)

    def test_collection_seaice_restart(self):
        '''Test formation of collection name - CICE restart'''
        func.logtest('test formation of collection name with CICE restart:')
        collection = self.inst._collection()
        self.assertEqual(collection, 'ida.file')
        self.assertFalse(self.inst.fl_pp)

    def test_collection_oi_fail(self):
        '''Test formation of collection name - invalid ocean/ice file type'''
        func.logtest('test formation of collection name with invalid type:')
        with self.assertRaises(SystemExit):
            _ = self.inst._collection()
        self.assertIn('file type not recognised', func.capture('err'))

    def test_collection_ocn_period_file(self):
        '''Test formation of collection name - NEMO period files'''
        func.logtest('test formation of collection name: NEMO period file:')
        self.inst._model_id = 'o'
        self.inst._file_id = '12h'
        collection = self.inst._collection()
        self.assertEqual(collection, 'onh.nc.file')
        self.assertFalse(self.inst.fl_pp)

        self.inst._file_id = '10d'
        collection = self.inst._collection()
        self.assertEqual(collection, 'ond.nc.file')
        self.assertFalse(self.inst.fl_pp)

        self.inst._file_id = '1m'
        collection = self.inst._collection()
        self.assertEqual(collection, 'onm.nc.file')
        self.assertFalse(self.inst.fl_pp)

        self.inst._file_id = '1s'
        collection = self.inst._collection()
        self.assertEqual(collection, 'ons.nc.file')
        self.assertFalse(self.inst.fl_pp)

        self.inst._file_id = '1y'
        collection = self.inst._collection()
        self.assertEqual(collection, 'ony.nc.file')
        self.assertFalse(self.inst.fl_pp)

        self.inst._file_id = '1x'
        collection = self.inst._collection()
        self.assertEqual(collection, 'onx.nc.file')
        self.assertFalse(self.inst.fl_pp)

    def test_collection_ice_season_mean(self):
        '''Test formation of collection name - CICE seasonal mean'''
        func.logtest('test formation of collection name: CICE seasonal mean:')
        self.inst._model_id = 'i'
        self.inst._file_id = '1s'
        collection = self.inst._collection()
        self.assertEqual(collection, 'ins.nc.file')
        self.assertFalse(self.inst.fl_pp)

    @mock.patch('moo.utils.exec_subproc')
    @mock.patch('moo.os.path.exists')
    def test_putdata_prefix(self, mock_exist, mock_subproc):
        '''Test put_data function with $PREFIX$RUNID crn'''
        func.logtest('test put_data function with $PREFIX$RUNID crn:')
        self.inst._rqst_name = '$PREFIX$RUNID.daTestfile'
        mock_subproc.return_value = (0, '')
        mock_exist.return_value = True
        self.inst.put_data()
        src = os.path.expandvars('TestDir/$PREFIX$RUNID.daTestfile')
        dest = os.path.expandvars('moose:myclass/mysuite/$RUNID.daTestfile')
        mock_subproc.assert_called_with('moo put -f -vv ' + src + ' ' + dest)

    @mock.patch('moo.utils.exec_subproc')
    def test_putdata_pp(self, mock_subproc):
        '''Test put_data function with fieldsfile'''
        func.logtest('test put_data function with fieldsfile:')
        self.inst._rqst_name = 'TESTPa.pmTestfile'
        self.inst._model_id = 'a'
        self.inst._file_id = 'pm'
        mock_subproc.return_value = (0, '')
        with mock.patch('moo.os.path.exists', return_value=True):
            self.inst.put_data()
        cmd = 'moo put -f -vv -c=umpp '
        src = 'TestDir/TESTPa.pmTestfile'
        dest = 'moose:myclass/mysuite/apm.pp/TESTPa.pmTestfile.pp'
        mock_subproc.assert_called_with(cmd + os.path.expandvars(
            src + ' ' + dest))

    @mock.patch('moo.utils.exec_subproc')
    def test_putdata_pp_no_convert(self, mock_subproc):
        '''Test put_data function with converted fieldsfile'''
        func.logtest('test put_data function with converted fieldsfile:')
        self.inst._rqst_name = 'TESTPa.pmTestfile.pp'
        self.inst.fl_pp = True
        mock_subproc.return_value = (0, '')
        with mock.patch('moo._Moose._collection', return_value='apm.pp'):
            with mock.patch('moo.os.path.exists', return_value=True):
                self.inst.put_data()
        cmd = 'moo put -f -vv TestDir/TESTPa.pmTestfile.pp ' \
            'moose:myclass/mysuite/apm.pp'
        mock_subproc.assert_called_with(cmd)

    @mock.patch('moo.utils.exec_subproc')
    def test_putdata_ff_no_convert(self, mock_subproc):
        '''Test put_data function with unconverted fieldsfile'''
        func.logtest('test put_data function with unconverted fieldsfile:')
        self.inst._rqst_name = 'TESTPa.pmTestfile'
        self.inst.fl_pp = False
        mock_subproc.return_value = (0, '')
        with mock.patch('moo._Moose._collection', return_value='apm.file'):
            with mock.patch('moo.os.path.exists', return_value=True):
                self.inst.put_data()
        cmd = 'moo put -f -vv TestDir/TESTPa.pmTestfile ' \
            'moose:myclass/mysuite/apm.file'
        mock_subproc.assert_called_with(cmd)

    @mock.patch('moo.utils.exec_subproc')
    def test_putdata_non_existent(self, mock_subproc):
        '''Test put_data with non-existent file'''
        func.logtest('test put_data function with non-existent file:')
        rtn = self.inst.put_data()
        mock_subproc.assert_not_called()
        self.assertIn('does not exist', func.capture(direct='err'))
        self.assertEqual(rtn, 99)

    @mock.patch('moo.os.path.exists')
    def test_putdata_jobtemp(self, mock_exist):
        '''Test put_data function with JOBTEMP'''
        func.logtest('test put_data function with JOBTEMP:')
        mock_exist.return_value = True
        with mock.patch.dict('moo.os.environ', {'JOBTEMP': 'jobtemp'}):
            self.inst.put_data()
            self.assertEqual(os.environ['UM_TMPDIR'], 'jobtemp')

    @mock.patch('moo.os.path.exists')
    def test_putdata_jobtemp_empty(self, mock_exist):
        '''Test put_data function with empty JOBTEMP'''
        func.logtest('test put_data function with empty JOBTEMP:')
        mock_exist.return_value = True
        with mock.patch.dict('moo.os.environ', {'JOBTEMP': ''}):
            self.inst.put_data()
        self.assertIn('likely to fail', func.capture(direct='err'))


class PutCommandTests(unittest.TestCase):
    '''Unit tests relating to the creation of the `moo put` command'''

    def setUp(self):
        self.moocmd = 'moo put -f -vv '
        self.testfile = os.path.join(MOO_CMD['DATAM'],
                                     MOO_CMD['CURRENT_RQST_NAME'])
        self.archdest = os.path.join(MOO_CMD['DATACLASS'],
                                     MOO_CMD['SETNAME'],
                                     'ada.file')
        with mock.patch.dict('moo.os.environ', {'PREFIX': 'PATH/'}):
            with mock.patch('moo._Moose.chkset', return_value=True):
                self.inst = moo._Moose(MOO_CMD)

    def tearDown(self):
        pass

    @mock.patch('moo.utils.exec_subproc')
    @mock.patch('moo.os.path.exists')
    def test_put_no_options(self, mock_exist, mock_subproc):
        '''Test put_data with standard options'''
        func.logtest('test moo command with standard options:')
        mock_exist.return_value = True
        mock_subproc.return_value = (0, 'true')
        self.inst.put_data()
        outcmd = self.moocmd + self.testfile + ' moose:' + self.archdest
        self.assertIn(outcmd, func.capture())

    @mock.patch('moo.utils.exec_subproc')
    @mock.patch('moo.os.path.exists')
    def test_put_moopath_option(self, mock_exist, mock_subproc):
        '''Test put_data with project option'''
        func.logtest('test moo command with project option:')
        mock_exist.return_value = True
        mock_subproc.return_value = (0, 'true')
        self.inst._moopath = 'MyMooPath'
        self.inst.put_data()
        outcmd = 'MyMooPath/{}{} moose:{}'.format(self.moocmd, self.testfile,
                                                  self.archdest)
        self.assertIn(outcmd, func.capture())

    @mock.patch('moo.utils.exec_subproc')
    @mock.patch('moo.os.path.exists')
    def test_put_ensemble_option(self, mock_exist, mock_subproc):
        '''Test put_data with ensemble ID option'''
        func.logtest('test moo command with ensemble ID option:')
        mock_exist.return_value = True
        mock_subproc.return_value = (0, 'true')
        self.inst._ens_id = 'MyEnsemble'
        self.inst.put_data()
        archdest = self.archdest.replace('mysuite/', 'mysuite/MyEnsemble/')
        outcmd = '{}{} moose:{}'.format(self.moocmd, self.testfile, archdest)
        self.assertIn(outcmd, func.capture())

    @mock.patch('moo.utils.exec_subproc', return_value=(0, 'true'))
    @mock.patch('moo.os.path.exists', return_value=True)
    def test_put_act_as_option(self, mock_exist, mock_subproc):
        '''Test put_data with act_as option'''
        func.logtest('test moo command with act_as option:')
        act_as = 'user.name'
        self.inst._act_as = act_as
        self.inst.put_data()
        moocmd = '{}--act-as {} '.format(self.moocmd, act_as)
        outcmd = '{}{} moose:{}'.format(moocmd, self.testfile, self.archdest)
        self.assertIn(outcmd, func.capture())


class Utilitytests(unittest.TestCase):
    '''Tests relating to the moo utility methods'''

    def setUp(self):
        self.cmd = MOO_CMD.copy()
        self.cmd['CURRENT_RQST_NAME'] = 'FILE'
        self.cmd['FILENAME_PREFIX'] = 'FN-PREFIX'
        self.cmd['DATAM'] = 'SOURCEDIR'
    def tearDown(self):
        pass

    @mock.patch('moo.CommandExec.execute')
    def test_archive_to_moose(self, mock_exec):
        '''Test call to archive a file to the Moose system'''
        func.logtest('Assert call to archive file to Moose')
        self.cmd['CONVERTPP'] = False
        moo.archive_to_moose('FILE', 'FN-PREFIX', 'SOURCEDIR',
                             MOO_NLIST, False)
        mock_exec.assert_called_with(self.cmd)

    @mock.patch('moo.CommandExec.execute')
    def test_archive_to_moose_convertpp(self, mock_exec):
        '''Test call to archive a file to the Moose system'''
        func.logtest('Assert call to archive file to Moose')
        self.cmd['CONVERTPP'] = True
        moo.archive_to_moose('FILE', 'FN-PREFIX', 'SOURCEDIR',
                             MOO_NLIST, True)
        mock_exec.assert_called_with(self.cmd)
