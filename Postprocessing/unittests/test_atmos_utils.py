#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2017 Met Office. All rights reserved.

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
import re
import mock

import testing_functions as func
import runtime_environment

import atmosNamelist
import validation
import housekeeping

# Import of atmos requires RUNID from runtime_environment
runtime_environment.setup_env()
import atmos


try:
    IRIS_AVAIL = True
    try:
        IRIS_DATA = os.path.isfile(housekeeping.iris_transform.
                                   iris.sample_data_path('air_temp.pp'))
    except ValueError:
        # Requires the "iris_sample_data" package to be installed
        IRIS_DATA = False
except AttributeError:
    IRIS_DATA = IRIS_AVAIL = False


class HousekeepTests(unittest.TestCase):
    '''Unit tests relating to the atmosphere housekeeping utilities'''
    def setUp(self):
        self.umutils = 'UMDIR/../utilities'
        self.atmos = atmos.AtmosPostProc()
        self.atmos.work = 'WorkDir'
        self.atmos.share = 'ShareDir'
        self.atmos.suite = mock.Mock()
        self.atmos.suite.prefix = 'RUNID'

        self.del_inst_pp = [('INST1', True), ('INST2', False), ('INST3', True)]
        self.del_mean_pp = [('MEAN1', True), ('MEAN2', False), ('MEAN3', True)]
        self.del_ncfiles = [('NCFILE1', False), ('NCFILE2', True)]
        self.arch_dumps = [('DUMP1', True), ('DUMP2', False), ('DUMP3', True)]
        self.del_dumps = ['DUMP1', 'DUMP1a', 'DUMP2', 'DUMP2a',
                          'DUMP3', 'DUMP3a']

    def tearDown(self):
        for fname in runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass

    @mock.patch('housekeeping.utils.remove_files')
    def test_delete_inst_pp_archived(self, mock_rm):
        '''Test delete_ppfiles functionality - archived instantaneous files'''
        func.logtest('Assert successful deletion of archived inst. ppfiles:')
        self.atmos.naml.delete_sc.gpdel = True
        housekeeping.delete_ppfiles(self.atmos, self.del_inst_pp,
                                    self.del_mean_pp, self.del_ncfiles, True)
        self.assertEqual(
            mock_rm.mock_calls,
            [mock.call(['INST1', 'INST3'], path='ShareDir'),
             mock.call(['INST1.arch', 'INST3.arch'], path='WorkDir',
                       ignoreNonExist=True)]
            )

    @mock.patch('housekeeping.utils.remove_files')
    def test_delete_mean_pp_archived(self, mock_rm):
        '''Test delete_ppfiles functionality - archived mean ppfiles'''
        func.logtest('Assert successful deletion of archived mean ppfiles:')
        self.atmos.naml.delete_sc.gcmdel = True
        housekeeping.delete_ppfiles(self.atmos, self.del_inst_pp,
                                    self.del_mean_pp, self.del_ncfiles, True)
        self.assertEqual(
            mock_rm.mock_calls,
            [mock.call(['MEAN1', 'MEAN3'], path='ShareDir'),
             mock.call(['MEAN1.arch', 'MEAN3.arch'], path='WorkDir',
                       ignoreNonExist=True)]
            )

    @mock.patch('utils.remove_files')
    def test_delete_ncfiles_archived(self, mock_rm):
        '''Test delete_ppfiles functionality - archived mean ppfiles'''
        func.logtest('Assert successful deletion of archived mean ppfiles:')
        self.atmos.naml.delete_sc.ncdel = True
        housekeeping.delete_ppfiles(self.atmos, self.del_inst_pp,
                                    self.del_mean_pp, self.del_ncfiles, True)
        self.assertEqual(
            mock_rm.mock_calls,
            [mock.call(['NCFILE2'], path='ShareDir'),
             mock.call(['NCFILE2.arch'], path='WorkDir', ignoreNonExist=True)]
            )

    @mock.patch('housekeeping.os.rename')
    def test_delete_pp_archived_debug(self, mock_rm):
        '''Test delete_ppfiles functionality - archived (debug_mode)'''
        func.logtest('Assert successful deletion of archived ppfiles - debug:')
        self.atmos.naml.delete_sc.gcmdel = True
        with mock.patch('housekeeping.utils.get_debugmode', return_value=True):
            housekeeping.delete_ppfiles(
                self.atmos, self.del_inst_pp,
                self.del_mean_pp, self.del_ncfiles, True
                )
        calls = [
            mock.call('ShareDir/MEAN1', 'ShareDir/MEAN1_ARCHIVED'),
            mock.call('ShareDir/MEAN3', 'ShareDir/MEAN3_ARCHIVED'),
            mock.call('WorkDir/MEAN1.arch', 'WorkDir/MEAN1.arch_ARCHIVED'),
            mock.call('WorkDir/MEAN3.arch', 'WorkDir/MEAN3.arch_ARCHIVED')
            ]
        self.assertEqual(sorted(mock_rm.mock_calls), sorted(calls))

    @mock.patch('housekeeping.get_marked_files')
    @mock.patch('housekeeping.FILETYPE')
    @mock.patch('housekeeping.utils.remove_files')
    def test_delete_inst_ppfiles(self, mock_rm, mock_ft, mock_mark):
        '''Test delete_ppfiles functionality - instantaneous files'''
        func.logtest('Assert successful deletion of inst. ppfiles:')
        self.atmos.naml.delete_sc.gpdel = True
        mock_ft.__getitem__().__getitem__().return_value = 'INST'
        mock_mark.return_value = [f[0] for f in self.del_inst_pp +
                                  self.del_mean_pp]
        housekeeping.delete_ppfiles(self.atmos, self.del_inst_pp,
                                    self.del_mean_pp, self.del_ncfiles, False)
        self.assertEqual(
            mock_rm.mock_calls,
            [mock.call(['INST1', 'INST2', 'INST3'], path='ShareDir'),
             mock.call(['INST1.arch', 'INST2.arch', 'INST3.arch'],
                       path='WorkDir', ignoreNonExist=True)]
            )

    @mock.patch('housekeeping.get_marked_files')
    @mock.patch('housekeeping.FILETYPE')
    @mock.patch('housekeeping.utils.remove_files')
    def test_delete_mean_ppfiles(self, mock_rm, mock_ft, mock_mark):
        '''Test delete_ppfiles functionality - mean files'''
        func.logtest('Assert successful deletion of mean ppfiles:')
        self.atmos.naml.delete_sc.gcmdel = True
        mock_ft.__getitem__().__getitem__().return_value = 'MEAN'
        mock_mark.return_value = [f[0] for f in self.del_inst_pp +
                                  self.del_mean_pp]
        housekeeping.delete_ppfiles(self.atmos, self.del_inst_pp,
                                    self.del_mean_pp, self.del_ncfiles, False)
        self.assertEqual(
            mock_rm.mock_calls,
            [mock.call(['MEAN1', 'MEAN2', 'MEAN3'], path='ShareDir'),
             mock.call(['MEAN1.arch', 'MEAN2.arch', 'MEAN3.arch'],
                       path='WorkDir', ignoreNonExist=True)]
            )
        arch_regex = '^RUNIDa\\.[pm][a-z1-9]*(_\\d{2})?\\.arch$'
        mock_mark.assert_called_once_with('WorkDir', arch_regex, '.arch')
        ppfiles = ['RUNIDa.pa11112233.arch', 'RUNIDa.pb11112233_44.arch',
                   'RUNIDa.pc1111mmm.arch']
        for fname in ppfiles:
            self.assertIsNotNone(re.match(arch_regex, fname))
        self.assertIsNone(re.match(arch_regex, 'GARBAGE'))

    def test_convert_convpp(self):
        '''Test convert_to_pp functionality with um-convpp'''
        func.logtest('Assert functionality of the convert_to_pp method:')
        um_utils_path = 'UMDIR/vn10.4/machine/utilities'
        with mock.patch('housekeeping.utils.exec_subproc') as mock_exec:
            with mock.patch('housekeeping.utils.remove_files') as mock_rm:
                mock_exec.return_value = (0, '')
                ppfile = housekeeping.convert_to_pp('Filename', um_utils_path,
                                                    False)
                mock_rm.assert_called_with('Filename', path='')
            cmd = um_utils_path + '/um-convpp Filename Filename.pp'
            mock_exec.assert_called_with(cmd, cwd='')
        self.assertEqual(ppfile, 'Filename.pp')

    def test_convert_to_pp(self):
        '''Test convert_to_pp functionality - default utility, keeping ffile'''
        func.logtest('Assert functionality of the convert_to_pp method:')
        with mock.patch('housekeeping.utils.exec_subproc') as mock_exec:
            with mock.patch('housekeeping.utils.remove_files') as mock_rm:
                mock_exec.return_value = (0, '')
                ppfile = housekeeping.convert_to_pp('Here/Filename',
                                                    self.umutils, True)
                self.assertListEqual(mock_rm.mock_calls, [])
            cmd = self.umutils + '/um-convpp Here/Filename Here/Filename.pp'
            mock_exec.assert_called_with(cmd, cwd='Here')
        self.assertEqual(ppfile, 'Here/Filename.pp')

    def test_convert_ff2pp(self):
        '''Test convert_to_pp functionality with um-ff2pp'''
        func.logtest('Assert functionality of the convert_to_pp method:')
        um_utils_path = 'UMDIR/vn10.3/machine/utilities'
        with mock.patch('housekeeping.utils.exec_subproc') as mock_exec:
            with mock.patch('housekeeping.utils.remove_files') as mock_rm:
                mock_exec.return_value = (0, '')
                ppfile = housekeeping.convert_to_pp('Here/Filename',
                                                    um_utils_path, False)
                mock_rm.assert_called_with('Here/Filename', path='Here')
            cmd = um_utils_path + '/um-ff2pp Here/Filename Here/Filename.pp'
            mock_exec.assert_called_with(cmd, cwd='Here')
        self.assertEqual(ppfile, 'Here/Filename.pp')

    def test_convert_to_pp_fail(self):
        '''Test convert_to_pp failure capture'''
        func.logtest('Assert failure capture of the convert_to_pp method:')
        with mock.patch('housekeeping.utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, 'I failed')
            with self.assertRaises(SystemExit):
                housekeeping.convert_to_pp('Filename', 'TestDir',
                                           self.umutils)
        self.assertIn('Conversion to pp format failed', func.capture('err'))
        self.assertIn('I failed', func.capture('err'))

    @mock.patch('housekeeping.utils.get_subset')
    @mock.patch('housekeeping.re.search')
    @mock.patch('housekeeping.utils.remove_files')
    def test_delete_dumps(self, mock_rm, mock_match, mock_set):
        '''Test delete_dumps functionality'''
        func.logtest('Assert successful deletion of dumps:')
        mock_set.return_value = self.del_dumps
        mock_match().group.side_effect = ['11', '22', '33', '44',
                                          '55', '66', '77', '88']
        self.atmos.suite.cyclestring = '44'
        housekeeping.delete_dumps(self.atmos, self.arch_dumps, False)
        mock_rm.assert_called_once_with(self.del_dumps[0:4], path='ShareDir')

    @mock.patch('housekeeping.utils.get_subset')
    @mock.patch('housekeeping.utils.remove_files')
    def test_delete_dumps_archived(self, mock_rm, mock_set):
        '''Test delete_dumps functionality - archived files'''
        func.logtest('Assert successful deletion of archived dumps:')
        self.atmos.final_dumpname = 'DUMP1a'
        mock_set.return_value = self.del_dumps
        housekeeping.delete_dumps(self.atmos, self.arch_dumps, True)
        self.assertEqual(
            mock_rm.mock_calls,
            [mock.call(['DUMP1', 'DUMP2a', 'DUMP3'], path='ShareDir')]
            )

    @mock.patch('housekeeping.utils.get_subset')
    @mock.patch('housekeeping.utils.remove_files')
    def test_del_dumps_archived_midrun(self, mock_rm, mock_set):
        '''Test delete_dumps functionality - archived files from mid-run'''
        func.logtest('Assert deletion of archived dumps - mid-run:')
        self.atmos.final_dumpname = 'DUMP1L'
        mock_set.return_value = self.del_dumps
        housekeeping.delete_dumps(self.atmos, self.arch_dumps, True)
        self.assertEqual(
            mock_rm.mock_calls,
            [mock.call(['DUMP1', 'DUMP1a', 'DUMP2a', 'DUMP3'], path='ShareDir')]
            )

    @mock.patch('housekeeping.utils.get_subset')
    @mock.patch('housekeeping.utils.remove_files')
    @mock.patch('housekeeping.os.rename')
    def test_del_dumps_archived_debug(self, mock_mv, mock_rm, mock_set):
        '''Test delete_dumps functionality - archived files (debug_mode)'''
        func.logtest('Assert successful deletion of archived dumps - debug:')
        self.atmos.final_dumpname = 'DUMP1a'
        mock_set.return_value = self.del_dumps
        with mock.patch('housekeeping.utils.get_debugmode', return_value=True):
            housekeeping.delete_dumps(self.atmos, self.arch_dumps, True)
        self.assertEqual(
            mock_mv.mock_calls,
            [mock.call('ShareDir/DUMP1', 'ShareDir/DUMP1_ARCHIVED'),
             mock.call('ShareDir/DUMP3', 'ShareDir/DUMP3_ARCHIVED')]
            )
        mock_rm.assert_called_once_with('DUMP2a', path='ShareDir')

    @mock.patch('housekeeping.utils.get_subset',
                return_value=['File1.sfx', 'File2.sfx'])
    def test_get_marked_files(self, mock_getfiles):
        '''Test list created by get_marked_files'''
        func.logtest('Assert creation of marked files list:')
        marked = housekeeping.get_marked_files('TestDir', 'pattern', '.sfx')
        self.assertListEqual(marked, ['File1', 'File2'])
        mock_getfiles.assert_called_once_with('TestDir', 'pattern')

    @mock.patch('housekeeping.utils.get_subset',
                return_value=['File1.sfx', 'File2.sfx'])
    def test_get_marked_files_nosuffix(self, mock_getfiles):
        '''Test list created by get_marked_files - no suffix'''
        func.logtest('Assert creation of marked files list - no suffix:')
        marked = housekeeping.get_marked_files('TestDir', 'pattern', '')
        self.assertListEqual(marked, ['File1.sfx', 'File2.sfx'])
        mock_getfiles.assert_called_once_with('TestDir', 'pattern')

    @mock.patch('housekeeping.utils.get_subset', return_value=[])
    def test_get_marked_files_none(self, mock_getfiles):
        '''Test list created by get_marked_files - empty list'''
        func.logtest('Assert creation of marked files list - empty list:')
        marked = housekeeping.get_marked_files('TestDir', 'pattern', '.sfx')
        self.assertListEqual(marked, [])
        mock_getfiles.assert_called_once_with('TestDir', 'pattern')


class HeaderTests(unittest.TestCase):
    '''Unit tests relating to file datestamp validity against the UM fixHD'''
    def setUp(self):
        self.umutils = atmosNamelist.AtmosNamelist().um_utils
        self.atmos = atmos.AtmosPostProc()
        self.fixhd = [('27', 'xx'), ('28', 'YY'), ('29', 'MM'),
                      ('30', 'DD'), ('31', 'xx'), ('32', 'xx'),
                      ('33', 'xx'), ('34', 'xx'), ('35', 'xx')]
        self.headers = {int(k): str(v).zfill(2) for k, v in self.fixhd}
        self.logfile = open('logfile', 'w')
        self.mule_avail = validation.MULE_AVAIL

    def tearDown(self):
        for fname in ['logfile'] + runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass
        validation.MULE_AVAIL = self.mule_avail

    @mock.patch('validation.mule_headers')
    @mock.patch('validation.genlist')
    @mock.patch('validation.identify_filedate', return_value=('YY', 'MM', 'DD'))
    def test_verify_header(self, mock_date, mock_pumf, mock_mule):
        '''Test verify_header functionality'''
        func.logtest('Assert functinality of the verify_header method:')
        mock_mule.return_value = (self.headers, False)
        validfile = validation.verify_header(self.atmos.naml.atmospp,
                                             'Filename',
                                             'LogDir/job',
                                             logfile=self.logfile)
        self.assertTrue(validfile)
        mock_date.assert_called_with('Filename')
        mock_mule.assert_called_once_with('Filename')
        self.assertListEqual(mock_pumf.mock_calls, [])

        self.logfile.close()
        self.assertEqual('', open('logfile', 'r').read())

    @mock.patch('validation.mule_headers')
    @mock.patch('validation.identify_filedate', return_value=('YY', 'MM', 'DD'))
    def test_verify_header_empty(self, mock_date, mock_mule):
        '''Test verify_header functionality - no valid fields'''
        func.logtest('Assert functinality of the verify_header method:')
        mock_mule.return_value = (self.headers, True)
        validfile = validation.verify_header(self.atmos.naml.atmospp,
                                             'Filename',
                                             'LogDir/job',
                                             logfile=self.logfile)
        self.assertFalse(validfile)
        mock_date.assert_called_with('Filename')
        mock_mule.assert_called_once_with('Filename')

        self.logfile.close()
        self.assertIn('FILE NOT ARCHIVED. Empty file',
                      open('logfile', 'r').read())

    @mock.patch('validation.genlist')
    @mock.patch('validation.identify_filedate', return_value=('YY', 'MM', 'DD'))
    def test_verify_header_pumf(self, mock_date, mock_gen):
        '''Test verify_header functionality - pumf'''
        func.logtest('Assert functionality of the verify_header method:')
        mock_gen.return_value = self.fixhd
        with mock.patch('validation.mule_headers', return_value=(None, False)):
            valid = validation.verify_header(self.atmos.naml.atmospp,
                                             'Filename', 'LogDir/job',
                                             logfile=self.logfile)
        self.assertTrue(valid)
        mock_date.assert_called_with('Filename')
        mock_gen.assert_called_with('Filename', 'LogDir/job-pumfhead.out',
                                    self.umutils + '/um-pumf')
        self.logfile.close()
        self.assertEqual('', open('logfile', 'r').read())

    @mock.patch('validation.mule_headers')
    def test_verify_header_mismatch(self, mock_mule):
        '''Test verify_header functionality - pumf ismatch'''
        func.logtest('Assert mismatch date in the verify_header method:')
        mock_mule.return_value = (self.headers, False)
        with mock.patch('validation.identify_filedate',
                        return_value=('YY', 'MM', 'D1')):
            with self.assertRaises(SystemExit):
                _ = validation.verify_header(self.atmos.naml.atmospp,
                                             'Filename', 'LogDir/job',
                                             logfile=self.logfile)
        self.assertIn('Validity time mismatch', func.capture('err'))
        self.logfile.close()
        self.assertIn('ARCHIVE FAILED', open('logfile', 'r').read())

    @mock.patch('validation.mule_headers')
    def test_verify_hdr_mismatch_debug(self, mock_mule):
        '''Test verify_header functionality - mismatch pumf (debug)'''
        func.logtest('Assert mismatch date in the verify_header method:')
        mock_mule.return_value = (self.headers, False)
        with mock.patch('validation.utils.get_debugmode', return_value=True):
            with mock.patch('validation.identify_filedate',
                            return_value=('YY', 'MM', 'D1')):
                valid = validation.verify_header(self.atmos.naml.atmospp,
                                                 'Filename', 'LogDir/job',
                                                 logfile=self.logfile)
        self.assertFalse(valid)
        self.assertIn('Validity time mismatch', func.capture('err'))
        self.logfile.close()
        self.assertIn('ARCHIVE FAILED', open('logfile', 'r').read())

    def test_verify_header_no_header(self):
        '''Test verify_header functionality - no header information'''
        func.logtest('Assert verify_header finding no header information:')
        with mock.patch('validation.mule_headers',
                        return_value=({1: 'a'}, False)):
            with mock.patch('validation.identify_filedate',
                            return_value=('YY', 'MM', 'DD')):
                with self.assertRaises(SystemExit):
                    _ = validation.verify_header(self.atmos.naml.atmospp,
                                                 'Filename', 'LogDir/job',
                                                 logfile=self.logfile)
        self.assertIn('No header information available', func.capture('err'))
        self.logfile.close()
        self.assertIn('ARCHIVE FAILED', open('logfile', 'r').read())

    @mock.patch('validation.mule')
    def test_mule_headers(self, mock_mule):
        ''' Test mule_headers '''
        func.logtest('Assert extraction of headers using Mule:')
        mock_mule.FieldsFile.from_file().fixed_length_header.raw = range(50)
        mock_mule.FieldsFile.from_file().fields = ['f1', 'f2', 'f3']
        headers, empty_file = validation.mule_headers('Filename')
        self.assertListEqual(headers.keys(), range(1, 40))
        self.assertListEqual(headers.values(),
                             [str(x).zfill(2) for x in range(1, 40)])
        self.assertFalse(empty_file)

    @mock.patch('validation.mule')
    def test_mule_headers_empty_file(self, mock_mule):
        ''' Test mule_headers - return an empty file'''
        func.logtest('Assert extraction of headers using Mule - empty file:')
        mock_mule.FieldsFile.from_file().fixed_length_header.raw = range(50)
        mock_mule.FieldsFile.from_file().fields = []
        headers, empty_file = validation.mule_headers('Filename')
        self.assertListEqual(headers.keys(), range(1, 40))
        self.assertListEqual(headers.values(),
                             [str(x).zfill(2) for x in range(1, 40)])
        self.assertTrue(empty_file)

    @mock.patch('validation.mule')
    def test_mule_headers_not_avail(self, mock_mule):
        ''' Test mule_headers - Mule not available'''
        func.logtest('Assert no headers using Mule - not available:')
        validation.MULE_AVAIL = False
        headers, empty_file = validation.mule_headers('Filename')
        self.assertListEqual(mock_mule.mock_calls, [])
        self.assertFalse(empty_file)
        self.assertIsNone(headers)


class DumpnameTests(unittest.TestCase):
    '''Unit tests covering the make_dump_name method'''

    def setUp(self):
        self.atmos = atmos.AtmosPostProc()
        self.atmos.suite = mock.Mock()
        self.atmos.suite.initpoint = [1980, 9, 1, 0, 0]
        self.atmos.suite.prefix = 'PREFIX'
        self.atmos.final_dumpname = None
        if 'monthly' in self.id():
            self.atmos.naml.archiving.arch_dump_freq = 'Monthly'
        elif 'seasonal' in self.id():
            self.atmos.naml.archiving.arch_dump_freq = 'Seasonal'
        elif 'annual' in self.id():
            self.atmos.naml.archiving.arch_dump_freq = 'Yearly'

    def tearDown(self):
        pass

    def test_monthly_dumpname(self):
        '''Test creation of a dumpname for monthly archive'''
        func.logtest('Assert creation of dumpname for monthly archive')
        func.logtest('Testing first year:')
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint=[1980, 10, 1, 0, 0, 0])
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['PREFIXa.da19801001_00'])

        func.logtest('Testing subsequent year:')
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19810401T0000Z')
        dumps = validation.make_dump_name(self.atmos)
        self.assertListEqual(dumps, ['PREFIXa.da19801001_00',
                                     'PREFIXa.da19801101_00',
                                     'PREFIXa.da19801201_00',
                                     'PREFIXa.da19810101_00',
                                     'PREFIXa.da19810201_00',
                                     'PREFIXa.da19810301_00',
                                     'PREFIXa.da19810401_00'])

    def test_monthly_offset_dumpname(self):
        '''Test creation of a dumpname for monthly archive - offset'''
        func.logtest('Assert creation of dumpname for monthly archive')
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19810501T0000Z')
        self.atmos.naml.archiving.arch_dump_offset = 6
        dumps = validation.make_dump_name(self.atmos)
        self.assertListEqual(dumps, ['PREFIXa.da19810401_00',
                                     'PREFIXa.da19810501_00'])

    def test_monthly_dump_finalcycle(self):
        '''Test creation of dumpnames for monthly archive - final cycle'''
        func.logtest('Assert dumpname creation for monthly archive - final')
        self.atmos.final_dumpname = 'FINALDUMP'
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19801001T0000Z')
        dumps = validation.make_dump_name(self.atmos)
        self.assertListEqual(dumps, ['FINALDUMP', 'PREFIXa.da19801001_00'])

    def test_monthly_dump_firstcycle(self):
        '''Test creation of dumpnames for monthly archive - first cycle'''
        func.logtest('Assert dumpname creation for monthly archive - first')
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19800901T0000Z')
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, [])

    def test_monthly_dump_mid_month(self):
        '''Test creation of dumpnames for monthly archive (mid month)'''
        func.logtest('Assert dumpname creation for monthly arch - mid month')
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19800915T0000Z')
        dumps = validation.make_dump_name(self.atmos)
        self.assertListEqual(dumps, ['PREFIXa.da19801001_00'])

    def test_seasonal_dumpnames_one(self):
        '''Test creation of one dumpname for seasonal archive'''
        func.logtest('Assert creation of one dumpname for seasonal archive')
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19801201T0000Z')
        dumps = validation.make_dump_name(self.atmos)
        self.assertListEqual(dumps, ['PREFIXa.da19801201_00'])

        for month in range(1, 3):
            func.logtest('testing date (1 seasonal dump): {}'.
                         format([1981, month, 1, 0, 0, 0]))
            self.atmos.suite.cyclepoint = \
                atmos.utils.CylcCycle(cyclepoint=[1981, month, 1, 0, 0, 0])
            dumps = validation.make_dump_name(self.atmos)
            self.assertListEqual(dumps, ['PREFIXa.da19801201_00'])

    def test_seasonal_dumpnames_two(self):
        '''Test creation of two dumpnames for seasonal archive'''
        func.logtest('Assert creation of two dumpnames for seasonal archive')
        for month in range(3, 6):
            func.logtest('testing date (2 seasonal dumps): {}'.
                         format([1981, month, 1, 0, 0, 0]))
            self.atmos.suite.cyclepoint = \
                atmos.utils.CylcCycle(cyclepoint=[1981, month, 1, 0, 0, 0])
            dumps = validation.make_dump_name(self.atmos)
            self.assertListEqual(dumps, ['PREFIXa.da19801201_00',
                                         'PREFIXa.da19810301_00'])

    def test_seasonal_dumpnames_three(self):
        '''Test creation of 3 dumpnames for seasonal archive'''
        func.logtest('Assert creation of 3 dumpnames for seasonal archive')
        for month in range(6, 9):
            func.logtest('testing date (3 seasonal dumps): {}'.
                         format([1981, month, 1, 0, 0, 0]))
            self.atmos.suite.cyclepoint = \
                atmos.utils.CylcCycle(cyclepoint=[1981, month, 1, 0, 0, 0])
            dumps = validation.make_dump_name(self.atmos)
            self.assertListEqual(sorted(dumps), ['PREFIXa.da19801201_00',
                                                 'PREFIXa.da19810301_00',
                                                 'PREFIXa.da19810601_00'])

    def test_seasonal_dumpnames_four(self):
        '''Test creation of 4 dumpnames for seasonal archive'''
        func.logtest('Assert creation of 4 dumpnames for seasonal archive')
        for month in range(9, 12):
            func.logtest('testing date (4 seasonal dumps): {}'.
                         format([1981, month, 1, 0, 0, 0]))
            self.atmos.suite.cyclepoint = \
                atmos.utils.CylcCycle(cyclepoint=[1981, month, 1, 0, 0, 0])
            dumps = validation.make_dump_name(self.atmos)
            self.assertListEqual(sorted(dumps), ['PREFIXa.da19801201_00',
                                                 'PREFIXa.da19810301_00',
                                                 'PREFIXa.da19810601_00',
                                                 'PREFIXa.da19810901_00'])

    def test_seasonal_dumpnames_none(self):
        '''Test creation of a dumpname for seasonal archive - None'''
        func.logtest('Assert creation of no dumpnames for seasonal archive')
        for month in range(10, 12):
            func.logtest('testing date (no seasonal dumps): {}'.
                         format([1980, month, 1, 0, 0, 0]))
            self.atmos.suite.cyclepoint = \
                atmos.utils.CylcCycle(cyclepoint=[1980, month, 1, 0, 0, 0])
            dumps = validation.make_dump_name(self.atmos)
            self.assertListEqual(dumps, [])

    def test_annual_jan_dumpname(self):
        '''Test creation of a dumpname for annual archive'''
        func.logtest('Assert creation of dumpname for annual archive (Jan)')
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19811201T0000Z')
        self.atmos.naml.archiving.arch_year_month = 'January'
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['PREFIXa.da19810101_00'])

        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19831201T0000Z')
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['PREFIXa.da19820101_00',
                                 'PREFIXa.da19830101_00'])

    def test_annual_july_dumpname(self):
        '''Test creation of a dumpname for annual archive'''
        func.logtest('Assert creation of dumpname for annual archive (Jan)')
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19811201T0000Z')
        self.atmos.naml.archiving.arch_year_month = 'July'
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['PREFIXa.da19810701_00'])

    def test_annual_dumpname_none(self):
        '''Test creation of no dumpnames for annual archive'''
        func.logtest('Assert creation of no dumpnames for annual archive')
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19801201T0000Z')
        self.atmos.naml.archiving.arch_year_month = 'January'
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, [])

    def test_dumpname_firstlast_cycle(self):
        '''Test creation of dumpnames for archive - first & last cycle'''
        func.logtest('Assert dumpname creation for archive - first/last cycle')
        self.atmos.final_dumpname = 'FINALDUMP'
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19800901T0000Z')
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['FINALDUMP'])

    def test_dumpname_timestamps_single(self):
        '''Test creation of dumpnames for archive - first & last cycle'''
        func.logtest('Assert dumpname creation for archive - first/last cycle')
        self.atmos.naml.archiving.arch_dump_freq = 'Timestamps'
        self.atmos.naml.archiving.arch_timestamps = '01-01'
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19820901T0000Z')
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['PREFIXa.da19810101_00',
                                 'PREFIXa.da19820101_00'])

    def test_dumpname_timestamps_multi(self):
        '''Test creation of dumpnames for archive - first & last cycle'''
        func.logtest('Assert dumpname creation for archive - first/last cycle')
        self.atmos.naml.archiving.arch_dump_freq = 'Timestamps'
        self.atmos.naml.archiving.arch_timestamps = ['01-01', '6-15_30',
                                                     '12-1_0']
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19820901T0000Z')
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['PREFIXa.da19810101_00',
                                 'PREFIXa.da19810615_30',
                                 'PREFIXa.da19811201_00',
                                 'PREFIXa.da19820101_00',
                                 'PREFIXa.da19820615_30'])

    def test_dumpname_tstamps_badformat(self):
        '''Test creation of dumpnames for archive - first & last cycle'''
        func.logtest('Assert dumpname creation for archive - first/last cycle')
        self.atmos.naml.archiving.arch_dump_freq = 'Timestamps'
        self.atmos.naml.archiving.arch_timestamps = ['01_01', '2-1']
        self.atmos.suite.cyclepoint = \
            atmos.utils.CylcCycle(cyclepoint='19820901T0000Z')
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['PREFIXa.da19810201_00',
                                 'PREFIXa.da19820201_00'])
        self.assertIn('timestamp "01_01" does not match the expected format',
                      func.capture('err'))


class TransformTests(unittest.TestCase):
    '''Unit tests relating to transformation of fieldsfiles'''
    def setUp(self):
        self.umutils = 'UMDIR/../utilities'
        if IRIS_DATA:
            self.ppfile = \
                housekeeping.iris_transform.iris.sample_data_path('air_temp.pp')
        else:
            self.ppfile = None

    def tearDown(self):
        pass

    def test_convert_convpp(self):
        '''Test convert_to_pp functionality with um-convpp'''
        func.logtest('Assert functionality of the convert_to_pp method:')
        um_utils_path = 'UMDIR/vn10.4/machine/utilities'
        with mock.patch('utils.exec_subproc') as mock_exec:
            with mock.patch('utils.remove_files') as mock_rm:
                mock_exec.return_value = (0, '')
                ppfile = housekeeping.convert_to_pp('Filename', um_utils_path,
                                                    False)
                mock_rm.assert_called_with('Filename', path='')
            cmd = um_utils_path + '/um-convpp Filename Filename.pp'
            mock_exec.assert_called_with(cmd, cwd='')
        self.assertEqual(ppfile, 'Filename.pp')

    def test_convert_to_pp(self):
        '''Test convert_to_pp functionality - default utility, keeping ffile'''
        func.logtest('Assert functionality of the convert_to_pp method:')
        with mock.patch('utils.exec_subproc') as mock_exec:
            with mock.patch('utils.remove_files') as mock_rm:
                mock_exec.return_value = (0, '')
                ppfile = housekeeping.convert_to_pp('Here/Filename',
                                                    self.umutils, True)
                self.assertListEqual(mock_rm.mock_calls, [])
            cmd = self.umutils + '/um-convpp Here/Filename Here/Filename.pp'
            mock_exec.assert_called_with(cmd, cwd='Here')
        self.assertEqual(ppfile, 'Here/Filename.pp')

    def test_convert_ff2pp(self):
        '''Test convert_to_pp functionality with um-ff2pp'''
        func.logtest('Assert functionality of the convert_to_pp method:')
        um_utils_path = 'UMDIR/vn10.3/machine/utilities'
        with mock.patch('utils.exec_subproc') as mock_exec:
            with mock.patch('utils.remove_files') as mock_rm:
                mock_exec.return_value = (0, '')
                ppfile = housekeeping.convert_to_pp('Here/Filename',
                                                    um_utils_path, False)
                mock_rm.assert_called_with('Here/Filename', path='Here')
            cmd = um_utils_path + '/um-ff2pp Here/Filename Here/Filename.pp'
            mock_exec.assert_called_with(cmd, cwd='Here')
        self.assertEqual(ppfile, 'Here/Filename.pp')

    def test_convert_to_pp_fail(self):
        '''Test convert_to_pp failure capture'''
        func.logtest('Assert failure capture of the convert_to_pp method:')
        with mock.patch('utils.exec_subproc') as mock_exec:
            mock_exec.return_value = (1, 'I failed')
            with self.assertRaises(SystemExit):
                housekeeping.convert_to_pp('Filename', 'TestDir',
                                           self.umutils)
        self.assertIn('Conversion to pp format failed', func.capture('err'))
        self.assertIn('I failed', func.capture('err'))

    @unittest.skipUnless(IRIS_AVAIL, 'Python module "Iris" is not available')
    @unittest.skipUnless(IRIS_DATA, 'Iris sample data is not available')
    @mock.patch('housekeeping.iris_transform.save_format', return_value=0)
    def test_extract_to_netcdf(self, mock_save):
        '''Test extraction of single field from single fieldsfile'''
        func.logtest('Assert extract to netCDF - single fieldsfile and field:')
        icode = housekeeping.extract_to_netcdf(self.ppfile,
                                               {'air_temperature': 'F1'},
                                               'NETCDF4', None)
        outfile = os.path.join(os.path.dirname(self.ppfile),
                               'atmos_suiteIDa_4y_19941201-19981201_p9-F1.nc')
        mock_save.assert_called_once_with(mock.ANY, outfile, 'netcdf',
                                          kwargs={'ncftype': 'NETCDF4',
                                                  'complevel': None})
        self.assertIsInstance(mock_save.call_args[0][0],
                              housekeeping.iris_transform.iris.cube.Cube)
        self.assertEqual(icode, 0)
        self.assertIn('Fieldsfile name does not match', func.capture('err'))

    @unittest.skipUnless(IRIS_AVAIL, 'Python module "Iris" is not available')
    @unittest.skipUnless(IRIS_DATA, 'Iris sample data is not available')
    @mock.patch('housekeeping.iris_transform.save_format', return_value=10)
    def test_extract_to_netcdf_failsave(self, mock_save):
        '''Test failure to save netCDF file'''
        func.logtest('Assert extract to netCDF - failed save:')
        icode = housekeeping.extract_to_netcdf(self.ppfile,
                                               {'air_temperature': 'F1'},
                                               'NETCDF', 5)
        outfile = os.path.join(os.path.dirname(self.ppfile),
                               'atmos_suiteIDa_4y_19941201-19981201_p9-F1.nc')
        mock_save.assert_called_once_with(mock.ANY, outfile, 'netcdf',
                                          kwargs={'ncftype': 'NETCDF',
                                                  'complevel': 5})

        self.assertEqual(icode, 10)

    @unittest.skipUnless(IRIS_AVAIL, 'Python module "Iris" is not available')
    @mock.patch('housekeeping.iris_transform.IrisCubes')
    @mock.patch('housekeeping.iris_transform.save_format')
    def test_extract_to_netcdf_suiteid(self, mock_save, mock_load):
        '''Test identification of suite and stream IDs'''
        func.logtest('Assert identification of suite and stream IDs:')

        class DummyLoad(object):
            ''' Dummy class to simulate iris.load return value '''
            field_attributes = {
                'field1': {'Descriptor': 'F1',
                           'StartDate': 'YYYYMMDD',
                           'EndDate': 'YYYYMMDD',
                           'DataFrequency': '1d',
                           'IrisCube': 'CUBE'}
                }

        mock_load.return_value = DummyLoad()
        _ = housekeeping.extract_to_netcdf('RUNIDa.mf2000',
                                           {}, 'TYPE', None)

        outfile = 'atmos_RUNIDa_1d_YYYYMMDD-YYYYMMDD_mf-F1.nc'
        mock_save.assert_called_once_with('CUBE', outfile, 'netcdf',
                                          kwargs={'ncftype': 'TYPE',
                                                  'complevel': None})
        mock_load.assert_called_once_with('RUNIDa.mf2000', {})

    @unittest.skipUnless(IRIS_AVAIL, 'Python module "Iris" is not available')
    @mock.patch('housekeeping.iris_transform')
    def test_iris_load_fail(self, mock_iris):
        '''Test failed import of iris_transform module'''
        func.logtest('Assert handling of failed import:')
        del mock_iris.IrisCubes
        with self.assertRaises(SystemExit):
            _ = housekeeping.extract_to_netcdf('RUNIDa.mf2000',
                                               {}, 'TYPE', None)

        with mock.patch('housekeeping.utils.get_debugmode', return_value=True):
            rtnval = housekeeping.extract_to_netcdf('RUNIDa.mf2000',
                                                    {}, 'TYPE', None)
            self.assertEqual(rtnval, -1)
        self.assertIn('Iris module is not available', func.capture('err'))
