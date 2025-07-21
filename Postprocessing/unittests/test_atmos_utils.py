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
import re
import shutil

try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
    import mock

import testing_functions as func
import runtime_environment

import atmos_namelist
import validation
import housekeeping
import atmos_transform

# Import of atmos requires RUNID from runtime_environment
runtime_environment.setup_env()
import atmos

if not atmos_transform.IRIS_AVAIL:
    func.logtest('\n*** Iris is not available.  '
                 '7 ATMOS_UTILS tests (TransformTests) will be skipped.\n')
if not atmos_transform.MULE_AVAIL:
    func.logtest('\n*** Mule is not available.\n'
                 '3 ATMOS_UTILS tests (MeaningTests) will be skipped.\n'
                 '3 ATMOS_UTILS tests (TransformTests) will be skipped.\n')

class HousekeepTests(unittest.TestCase):
    """
    Unit tests relating to the atmosphere housekeeping utilities
    """
    def setUp(self):
        self.umutils = 'UMDIR/../utilities'
        self.atmos = atmos.AtmosPostProc()
        self.atmos.work = 'WorkDir'
        self.atmos.share = 'ShareDir'
        self.atmos.suite = mock.Mock()
        self.atmos.suite.prefix = 'RUNID'
        self.atmos.ff_pattern = r'^RUNIDa\.[pm][{}]' + \
                r'\d{{4}}(\d{{4}}|\w{{3}})(_\d{{2}})?(\.pp)?(\.arch)?$'

        self.del_inst_pp = [('INST1', True), ('INST2', False), ('INST3', True)]
        self.del_mean_pp = [('MEAN1', True), ('MEAN2', False), ('MEAN3', True)]
        self.del_ncfiles = [('NCFILE1', False), ('NCFILE2', True)]
        self.arch_dumps = [('DUMP1', True), ('DUMP2', False), ('DUMP3', True)]
        self.del_dumps = ['DUMP1', 'DUMP1a', 'DUMP2', 'DUMP2a',
                          'DUMP3', 'DUMP3a']

    def tearDown(self):
        for fname in runtime_environment.RUNTIME_FILES + ['LOGFILE']:
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
                       ignore_non_exist=True)]
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
                       ignore_non_exist=True)]
            )

    def test_read_log(self):
        '''Test read the archive log file'''
        logs = '''
RUNIDa.da19790901_00 ARCHIVE OK
RUNIDa.da19850101_00 ARCHIVE FAILED
RUNIDa.pb20010511.pp NOT ARCHIVED. Empty file
RUNIDa.mb20010521.pp ARCHIVE OK
RUNIDa.pf2000may.pp ARCHIVE_OK
RUNIDa.ps2000djf.pp ARCHIVE_OK
atmos_runida_1d_1999010100_1999010200_ph-tag.nc ARCHIVE OK
atmos_runida_1m_1999010100_1999020100_generic-tag.nc ARCHIVE OK
'''
        with open('LOGFILE', 'w') as logfile:
            logfile.write(logs)

        rval = housekeeping.read_arch_logfile('LOGFILE', 'RUNID',
                                              '([pm][a-c])', '([p][msy])', '')

        expected = (
            [('RUNIDa.da19790901_00', True), ('RUNIDa.da19850101_00', False)],
            [('RUNIDa.mb20010521.pp', True), ('RUNIDa.pb20010511.pp', True)],
            [('RUNIDa.ps2000djf.pp', True)],
            [('atmos_runida_1d_1999010100_1999010200_ph-tag.nc', True),
             ('atmos_runida_1m_1999010100_1999020100_generic-tag.nc', True)]
        )

        for i, item in enumerate(rval):
            self.assertListEqual(sorted(item), expected[i])

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
             mock.call(['NCFILE2.arch'], path='WorkDir', ignore_non_exist=True)]
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
                       path='WorkDir', ignore_non_exist=True)]
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
                       path='WorkDir', ignore_non_exist=True)]
            )
        arch_regex = \
            '^RUNIDa\\.[pm][a-z1-9]\\d{4}(\\d{4}|[a-z]{3})(_\\d{2})?\\.arch$'
        mock_mark.assert_called_once_with('WorkDir', arch_regex, '.arch')
        ppfiles = ['RUNIDa.pa11112233.arch', 'RUNIDa.pb11112233_44.arch',
                   'RUNIDa.pc1111mmm.arch']
        for fname in ppfiles:
            self.assertIsNotNone(re.match(arch_regex, fname))
        self.assertIsNone(re.match(arch_regex, 'GARBAGE'))

    @mock.patch('housekeeping.utils.get_subset')
    @mock.patch('housekeeping.re.search')
    @mock.patch('housekeeping.utils.remove_files')
    def test_delete_dumps(self, mock_rm, mock_match, mock_set):
        '''Test delete_dumps functionality'''
        func.logtest('Assert successful deletion of dumps:')
        mock_set.return_value = self.del_dumps
        mock_match().group.side_effect = [
            'YYYYMM11', 'YYYYMM22', 'YYYYMM33', 'YYYYMM44',
            'YYYYMM55', 'YYYYMM66', 'YYYYMM77', 'YYYYMM88'
            ]
        self.atmos.suite.cyclepoint.startcycle = {'iso': 'YYYYMM44T0000Z'}
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
        marked = housekeeping.get_marked_files('TestDir', 'pattern$', '.sfx')
        self.assertListEqual(marked, ['File1', 'File2'])
        mock_getfiles.assert_called_once_with('TestDir', 'pattern.sfx$')

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
        marked = housekeeping.get_marked_files('TestDir', 'pattern$', '.sfx')
        self.assertListEqual(marked, [])
        mock_getfiles.assert_called_once_with('TestDir', 'pattern.sfx$')


class HeaderTests(unittest.TestCase):
    '''Unit tests relating to file datestamp validity against the UM fixHD'''
    def setUp(self):
        self.umutils = atmos_namelist.AtmosNamelist().um_utils
        self.atmos = atmos.AtmosPostProc()
        self.fixhd = [('27', 0), ('28', 1111), ('29', 22),
                      ('30', 33), ('31', 0), ('32', 0),
                      ('33', 0), ('34', 0), ('35', 0)]
        self.headers = {int(k): int(v) for k, v in self.fixhd}
        self.logfile = open('logfile', 'w')

    def tearDown(self):
        for fname in ['logfile'] + runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass

    @mock.patch('validation.mule_headers')
    @mock.patch('validation.genlist')
    @mock.patch('validation.identify_dates', return_value=[(1111, 22, 33)])
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
    @mock.patch('validation.identify_dates', return_value=[(1111, 22, 33)])
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
    @mock.patch('validation.identify_dates', return_value=[(1111, 22, 33)])
    def test_verify_header_pumf(self, mock_date, mock_gen):
        '''Test verify_header functionality - pumf'''
        func.logtest('Assert functionality of the verify_header method:')
        mock_gen.return_value = self.fixhd
        with mock.patch('validation.mule_headers', return_value=(None, False)):
            valid = validation.verify_header(self.atmos.naml.atmospp,
                                             'a.pa1234', 'LogDir/job',
                                             logfile=self.logfile)
        self.assertTrue(valid)
        mock_date.assert_called_with('a.pa1234')
        mock_gen.assert_called_with('a.pa1234', 'LogDir/job-pumfhead.out',
                                    self.umutils + '/um-pumf')
        self.logfile.close()
        self.assertEqual('', open('logfile', 'r').read())

    def test_genlist_invalid_pumfver(self):
        '''Test genlist assertion of pumf version'''
        func.logtest('Test genlist assertion of pumf version:')
        with mock.patch('validation.utils.exec_subproc',
                        return_value=[1, '']):
            with self.assertRaises(SystemExit):
                _ = {
                    int(k): str(v) for k, v in validation.genlist(
                        'ppfile', 'headerfile', 'path/vn8.6/um-pumf')
                    }
            self.assertIn('Currently attempting to use version 8.6',
                          func.capture('err'))

            with self.assertRaises(SystemExit):
                _ = {
                    int(k): str(v) for k, v in validation.genlist(
                        'ppfile', 'headerfile', 'path/vn10.9/um-pumf')
                    }
            self.assertIn('Currently attempting to use version 10.9',
                          func.capture('err'))

    def test_genlist_pumf_failure(self):
        '''Test genlist assertion of pumf failure'''
        func.logtest('Test genlist assertion of pumf failure:')
        with mock.patch('validation.utils.exec_subproc',
                        return_value=[1, 'Problem with PUMF program']):
            with self.assertRaises(SystemExit):
                _ = {
                    int(k): str(v) for k, v in validation.genlist(
                        'ppfile', 'headerfile', 'path/vn10.0/um-pumf')
                    }
            self.assertIn('Failed to extract header information',
                          func.capture('err'))

    def test_genlist_pumf_unavailable(self):
        '''Test genlist assertion of invalid pumf path'''
        func.logtest('Test genlist assertion of invalid pumf path:')
        with mock.patch('validation.utils.exec_subproc',
                        return_value=[1, 'No such file or directory']):
            with self.assertRaises(SystemExit):
                _ = {
                    int(k): str(v) for k, v in validation.genlist(
                        'ppfile', 'headerfile', 'path/vn10.0/um-pumf')
                    }
            self.assertIn('Failed to find pumf executable',
                          func.capture('err'))

    @mock.patch('validation.mule_headers')
    def test_verify_header_mismatch(self, mock_mule):
        '''Test verify_header functionality - pumf ismatch'''
        func.logtest('Assert mismatch date in the verify_header method:')
        mock_mule.return_value = (self.headers, False)
        with mock.patch('validation.identify_dates',
                        return_value=[(1111, 22, 44)]):
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
            with mock.patch('validation.identify_dates',
                            return_value=[(1111, 22, 44)]):
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
            with mock.patch('validation.identify_dates',
                            return_value=[(1111, 22, 33)]):
                with self.assertRaises(SystemExit):
                    _ = validation.verify_header(self.atmos.naml.atmospp,
                                                 'Filename', 'LogDir/job',
                                                 logfile=self.logfile)
        self.assertIn('No header information available', func.capture('err'))
        self.logfile.close()
        self.assertIn('ARCHIVE FAILED', open('logfile', 'r').read())

    @unittest.skipUnless(validation.MULE_AVAIL,
                         'Python module "Mule" is not available')
    @mock.patch('validation.mule')
    def test_mule_headers(self, mock_mule):
        ''' Test mule_headers '''
        func.logtest('Assert extraction of headers using Mule:')
        mock_mule.UMFile.from_file().fixed_length_header.raw = range(50)
        mock_mule.UMFile.from_file().fields = ['f1', 'f2', 'f3']
        headers, empty_file = validation.mule_headers('Filename')
        self.assertListEqual(list(headers.keys()), list(range(1, 40)))
        self.assertListEqual(list(headers.values()), [x for x in range(1, 40)])
        self.assertFalse(empty_file)

    @unittest.skipUnless(validation.MULE_AVAIL,
                         'Python module "Mule" is not available')
    @mock.patch('validation.mule')
    def test_mule_headers_empty_file(self, mock_mule):
        ''' Test mule_headers - return an empty file'''
        func.logtest('Assert extraction of headers using Mule - empty file:')
        mock_mule.UMFile.from_file().fixed_length_header.raw = range(50)
        mock_mule.UMFile.from_file().fields = []
        headers, empty_file = validation.mule_headers('Filename')
        self.assertListEqual(list(headers.keys()), list(range(1, 40)))
        self.assertListEqual(list(headers.values()), [x for x in range(1, 40)])
        self.assertTrue(empty_file)

    @mock.patch('validation.MULE_AVAIL', False)
    def test_mule_headers_not_avail(self):
        ''' Test mule_headers - Mule not available'''
        func.logtest('Assert no headers using Mule - not available:')
        headers, empty_file = validation.mule_headers('Filename')
        self.assertFalse(empty_file)
        self.assertIsNone(headers)


class DumpnameTests(unittest.TestCase):
    '''Unit tests covering the make_dump_name method'''

    def setUp(self):
        self.atmos = atmos.AtmosPostProc()
        self.atmos.suite = mock.Mock()
        self.atmos.suite.initpoint = [1980, 9, 1, 0, 0]
        self.atmos.suite.prefix = 'PREFIX'
        self.atmos.suite.meanref = ('1978', '12', '01')
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

        self.atmos.suite.initpoint = [1980, 11, 1, 0, 0]
        self.atmos.suite.meanref = [1978, 10, 1]
        for month in range(1, 3):
            func.logtest('testing date (1 seasonal dump): {}'.
                         format([1981, month, 1, 0, 0, 0]))
            self.atmos.suite.cyclepoint = \
                atmos.utils.CylcCycle(cyclepoint=[1981, month, 1, 0, 0, 0])
            dumps = validation.make_dump_name(self.atmos)
            self.assertListEqual(dumps, ['PREFIXa.da19810101_00'])

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


class AtmosTransformTests(unittest.TestCase):
    '''Unit tests relating to atmos_transformation of fieldsfiles'''
    def setUp(self):
        self.umutils = 'UMDIR/../utilities'
        self.ppfile = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   'air_temp.pp')
        self.ffile = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   'air_temp.ff')
    def tearDown(self):
        for fname in ['FNAME', 'FNAME.cut']:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_convert_to_pp(self):
        '''Test convert_to_pp functionality - default utility, keeping ffile'''
        func.logtest('Assert functionality of the convert_to_pp method:')
        with mock.patch('atmos_transform.get_mule_util',
                        return_value='mule-convpp'):
            with mock.patch('utils.exec_subproc') as mock_exec:
                with mock.patch('utils.remove_files') as mock_rm:
                    mock_exec.return_value = (0, '')
                    ppfile = atmos_transform.convert_to_pp(
                        'Here/Filename', self.umutils, None, True
                    )
        self.assertListEqual(mock_rm.mock_calls, [])
        cmd = 'mule-convpp Here/Filename Here/Filename.pp'
        mock_exec.assert_called_with(cmd, cwd='Here')
        self.assertEqual(ppfile, 'Here/Filename.pp')

    def test_convert_umconvpp(self):
        '''Test convert_to_pp functionality - default utility, keeping ffile'''
        func.logtest('Assert functionality of the convert_to_pp method:')
        with mock.patch('utils.exec_subproc') as mock_exec:
            with mock.patch('utils.remove_files') as mock_rm:
                mock_exec.return_value = (0, '')
                ppfile = atmos_transform.convert_to_pp('Here/Filename',
                                                       self.umutils,
                                                       'NoMule', True)
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
                ppfile = atmos_transform.convert_to_pp('Here/Filename',
                                                       um_utils_path,
                                                       'NoMule', False)
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
                atmos_transform.convert_to_pp('Filename', 'umutils',
                                              None, False)
        self.assertIn('Conversion to pp format failed', func.capture('err'))
        self.assertIn('I failed', func.capture('err'))

    @unittest.skipUnless(atmos_transform.IRIS_AVAIL,
                         'Python module "Iris" is not available')
    @mock.patch('atmos_transform.iris_transform.save_format', return_value=0)
    def test_extract_to_netcdf(self, mock_save):
        '''Test extraction of single field from single fieldsfile'''
        func.logtest('Assert extract to netCDF - single fieldsfile and field:')
        icode = atmos_transform.extract_to_netcdf(self.ppfile,
                                                  {'air_temperature': 'F1'},
                                                  'NETCDF4', None)
        outfile = 'atmos_suiteida_4y_19941201-19981201_p9-F1.nc'
        mock_save.assert_called_once_with(mock.ANY, outfile, 'netcdf',
                                          kwargs={'ncftype': 'NETCDF4',
                                                  'complevel': None})
        self.assertIsInstance(mock_save.call_args[0][0],
                              atmos_transform.iris_transform.iris.cube.Cube)
        self.assertEqual(icode, 0)
        self.assertIn('Fieldsfile name does not match', func.capture('err'))

    @unittest.skipUnless(atmos_transform.IRIS_AVAIL,
                         'Python module "Iris" is not available')
    @mock.patch('atmos_transform.iris_transform.save_format', return_value=10)
    def test_extract_to_netcdf_failsave(self, mock_save):
        '''Test failure to save netCDF file'''
        func.logtest('Assert extract to netCDF - failed save:')
        icode = atmos_transform.extract_to_netcdf(self.ppfile,
                                                  {'air_temperature': 'F1'},
                                                  'NETCDF', 5)
        outfile = 'atmos_suiteida_4y_19941201-19981201_p9-F1.nc'
        mock_save.assert_called_once_with(mock.ANY, outfile, 'netcdf',
                                          kwargs={'ncftype': 'NETCDF',
                                                  'complevel': 5})
        self.assertEqual(icode, 10)

    @unittest.skipUnless(atmos_transform.IRIS_AVAIL,
                         'Python module "Iris" is not available')
    @mock.patch('atmos_transform.iris_transform.IrisCubes')
    @mock.patch('atmos_transform.iris_transform.save_format')
    def test_extract_to_netcdf_suiteid(self, mock_save, mock_load):
        '''Test identification of suite and stream IDs'''
        func.logtest('Assert identification of suite and stream IDs:')

        class DummyCube(object):
            '''
            Dummy class to simulate a <type iris_transform.CubeContainer>
            '''
            def __init__(self):
                self.fieldname = 'F1'
                self.startdate = 'YYY1M1D1'
                self.enddate = 'YYY2M2D2'
                self.data_frequency = '1d'
                self.cube = 'CUBE'

        type(mock_load.return_value).fields = \
            mock.PropertyMock(return_value=[DummyCube()])
        _ = atmos_transform.extract_to_netcdf('RUNIDa.mf2000', {}, 'TYPE', None)

        outfile = 'atmos_runida_1d_YYY1M1D1-YYY2M2D2_mf-F1.nc'
        mock_save.assert_called_once_with('CUBE', outfile, 'netcdf',
                                          kwargs={'ncftype': 'TYPE',
                                                  'complevel': None})
        mock_load.assert_called_once_with('RUNIDa.mf2000', {})

    @unittest.skipUnless(atmos_transform.IRIS_AVAIL,
                         'Python module "Iris" is not available')
    @mock.patch('atmos_transform.iris_transform')
    def test_iris_load_fail(self, mock_iris):
        '''Test failed import of iris_transform module'''
        func.logtest('Assert handling of failed import:')
        del mock_iris.IrisCubes
        with self.assertRaises(SystemExit):
            _ = atmos_transform.extract_to_netcdf('RUNIDa.mf2000', {},
                                                  'TYPE', None)

        with mock.patch('atmos_transform.utils.get_debugmode',
                        return_value=True):
            rtnval = atmos_transform.extract_to_netcdf('RUNIDa.mf2000',
                                                       {}, 'TYPE', None)
        self.assertEqual(rtnval, -1)
        self.assertIn('Iris module is not available', func.capture('err'))

    @mock.patch('atmos_transform._extract_to_pp_mule', return_value='filename')
    @mock.patch('atmos_transform.utils.move_files')
    def test_extract_to_pp_mule_avail(self, mock_move, mock_ppmule):
        '''Test extraction to pp - Mule available'''
        func.logtest('Assert extract to PP - Mule available:')
        with mock.patch('atmos_transform.os.path.exists', return_value=True):
            with mock.patch('atmos_transform.MULE_AVAIL', True):
                rval = atmos_transform.extract_to_pp(
                    'dir/sfile', ['field'], 'po'
                    )
        self.assertEqual(rval, 0)
        mock_ppmule.assert_called_once_with(['dir/sfile'], ['field'],
                                            'dir/suiteIDa.po2000.pp', None)
        mock_move.assert_called_once_with('filename', 'dir',
                                          fail_on_err=True)

    @mock.patch('atmos_transform._extract_to_pp_iris', return_value='filename')
    @mock.patch('atmos_transform.utils.move_files')
    def test_extract_to_pp_iris_avail(self, mock_move, mock_ppiris):
        '''Test extraction to pp - Iris available'''
        func.logtest('Assert extract to PP -Iris available:')
        with mock.patch('atmos_transform.os.path.exists', return_value=True):
            with mock.patch('atmos_transform.MULE_AVAIL', False):
                with mock.patch('atmos_transform.IRIS_AVAIL', True):
                    rval = atmos_transform.extract_to_pp(
                        'dir/sfile', ['field'], 'po', '1m'
                    )
        self.assertEqual(rval, 0)
        mock_ppiris.assert_called_once_with(['dir/sfile'], ['field'],
                                            'dir/suiteIDa.po2000.pp', '1m')
        mock_move.assert_called_once_with('filename', 'dir',
                                          fail_on_err=True)

    def test_extract_to_pp_no_method(self):
        '''Test extraction to pp - no Mule or Iris available'''
        func.logtest('Assert extract to PP - no Iris or Mule:')
        with mock.patch('atmos_transform.os.path.exists', return_value=True):
            with mock.patch('atmos_transform.MULE_AVAIL', False):
                with mock.patch('atmos_transform.IRIS_AVAIL', False):
                    self.assertIsNone(
                        atmos_transform.extract_to_pp('sfile', ['field'], 'po')
                    )
        self.assertIn(
            'Either Mule or IRIS required to extract fields to PP format',
            func.capture('err')
        )

    def test_extract_to_pp_no_sourcefile(self):
        '''Test extraction to pp - no source files found'''
        func.logtest('Assert extract to PP - no source files:')
        rval = atmos_transform.extract_to_pp('filename',
                                             ['air_temperature'],
                                             'po',
                                             data_freq='1d')
        self.assertIn('No source files found', func.capture('err'))
        self.assertEqual(rval, None)

    @mock.patch('atmos_transform._extract_to_pp_mule', return_value=None)
    def test_extract_to_pp_fail(self, mock_ppmule):
        '''Test extraction to pp - failure'''
        func.logtest('Assert extract to PP - failure:')
        with mock.patch('atmos_transform.os.path.exists', return_value=True):
            with mock.patch('atmos_transform.MULE_AVAIL', return_value=True):
                rval = atmos_transform.extract_to_pp('fname',
                                                     ['field'], 'po')
        mock_ppmule.assert_called_once_with(['fname'], ['field'],
                                            'suiteIDa.po2000.pp', None)
        self.assertEqual(func.capture('err'), '')
        self.assertEqual(rval, None)

    @unittest.skipUnless(atmos_transform.MULE_AVAIL,
                         'Python module "Mule" is not available')
    def test_extract_to_pp_mule(self):
        '''Test call to Mule to extract a single field to PP format'''
        func.logtest('Assert extract to PP via Mule - single field:')
        outfile = 'outfile.pp'
        shutil.copy(self.ppfile, outfile)
        rval = atmos_transform._extract_to_pp_mule(
            [self.ffile], ['16203'], outfile, None
        )
        outfields = atmos_transform.fields_from_pp_file(outfile)
        self.assertEqual(len(outfields), 1)
        self.assertEqual(rval, outfile)
        os.remove(outfile)

    @unittest.skipUnless(atmos_transform.MULE_AVAIL,
                         'Python module "Mule" is not available')
    def test_extract_to_pp_mule_no_data(self):
        '''Test Mule to extract a single field to PP format - no data'''
        func.logtest('Assert extract to PP via Mule - no data:')
        rval = atmos_transform._extract_to_pp_mule(
            [self.ffile], ['16203'], 'outfile.pp', '1m'
        )

        self.assertIn('No requested fields found in source file:\n\t'
                      + self.ffile, func.capture('err'))
        self.assertFalse(os.path.exists('outfile.pp'))
        self.assertEqual(rval, None)

    @unittest.skipUnless(atmos_transform.MULE_AVAIL,
                         'Python module "Mule" is not available')
    def test_extract_to_pp_mule_fail(self):
        '''Test Mule to extract a single field to PP format - fail save'''
        func.logtest('Assert extract to PP via Mule - fail save:')
        with mock.patch('atmos_transform.os.path.exists', return_value=False):
            rval = atmos_transform._extract_to_pp_mule(
                [self.ffile], ['16203'], 'outfile.pp', '4y'
            )
        os.remove('outfile.pp')
        self.assertIn('Failed to extract field(s) to PP with Mule',
                      func.capture('err'))
        self.assertEqual(rval, None)

    @unittest.skipUnless(atmos_transform.IRIS_AVAIL,
                         'Python module "Iris" is not available')
    @mock.patch('atmos_transform.iris_transform.save_format', return_value=0)
    def test_extract_to_pp_iris(self, mock_save):
        '''Test call to Iris to extract a single field to PP format'''
        func.logtest('Assert extract to PP via Iris - single field:')
        rval = atmos_transform._extract_to_pp_iris(
            [self.ffile], ['air_temperature'], 'dir/outfile.pp', None
        )
        mock_save.assert_called_once_with(mock.ANY, 'outfile.pp', 'pp',
                                          kwargs={'append': True})
        self.assertIsInstance(mock_save.call_args[0][0],
                              atmos_transform.iris_transform.iris.cube.Cube)
        self.assertEqual(rval, 'outfile.pp')


    @unittest.skipUnless(atmos_transform.IRIS_AVAIL,
                         'Python module "Iris" is not available')
    @mock.patch('atmos_transform.iris_transform.save_format', return_value=0)
    def test_extract_to_pp_iris_nodata(self, mock_save):
        '''Test Iris to extract a single field to PP format - no data'''
        func.logtest('Assert extract to PP via Iris - no data:')
        rval = atmos_transform._extract_to_pp_iris(
            [self.ffile], ['air_temperature'], 'dir/outfile.pp', '1m'
        )
        self.assertEqual(len(mock_save.mock_calls), 0)
        self.assertIn('No requested fields found in source file:\n\t'
                      + self.ffile, func.capture('err'))
        self.assertEqual(rval, None)

    @unittest.skipUnless(atmos_transform.IRIS_AVAIL,
                         'Python module "Iris" is not available')
    @mock.patch('atmos_transform.iris_transform.save_format', return_value=-1)
    def test_extract_to_pp_iris_fail(self, mock_save):
        '''Test Iris to extract a single field to PP format - fail save'''
        func.logtest('Assert extract to PP via Iris - fail save:')
        rval = atmos_transform._extract_to_pp_iris(
            [self.ffile], ['air_temperature'], 'dir/outfile.pp', '4y'
        )
        mock_save.assert_called_once_with(mock.ANY, 'outfile.pp', 'pp',
                                          kwargs={'append': True})
        self.assertIn('Failed to extract field(s) to PP with Iris',
                      func.capture('err'))
        self.assertEqual(rval, None)

    @mock.patch('atmos_transform.MULE_AVAIL', True)
    @mock.patch('atmos_transform.utils.exec_subproc',
                return_value=(0, 'OUTPUT'))
    @mock.patch('atmos_transform.os.rename')
    def test_cutout_subdomain(self, mock_rename, mock_exec):
        '''Test call to cutout_subdomain'''
        func.logtest('Assert call to cutout_subdomain:')
        with mock.patch('atmos_transform.os.path.exists',
                        side_effect=[True, False]):
            icode = atmos_transform.cutout_subdomain(
                'path/to/file/FNAME', 'MULEDIR', '-CTYPE', [1, 2, 3, 4]
                )
            self.assertEqual(icode, 0)
        mock_exec.assert_called_with(
            'MULEDIR/mule-cutout -CTYPE path/to/file/FNAME ' +
            'path/to/file/FNAME.cut 1 2 3 4'
            )
        mock_rename.assert_called_once_with('path/to/file/FNAME.cut',
                                            'path/to/file/FNAME')
        self.assertNotIn('OUTPUT', func.capture())
        self.assertNotIn('OUTPUT', func.capture('err'))

    @mock.patch('atmos_transform.MULE_AVAIL', True)
    @mock.patch('atmos_transform.utils.exec_subproc',
                return_value=(0, 'OUTPUT'))
    @mock.patch('atmos_transform.os.rename')
    def test_cutout_subdomain_preexist(self, mock_rename, mock_exec):
        '''Test call to cutout_subdomain - prexisting .cut file'''
        func.logtest('Assert call to cutout_subdomain - pre-existing cutout:')
        with mock.patch('atmos_transform.os.path.exists',
                        side_effect=[True, True]):
            icode = atmos_transform.cutout_subdomain(
                'FNAME', 'MULEDIR', '-CTYPE', [1, 2, 3, 4]
                )
            self.assertEqual(icode, 0)

        self.assertListEqual(mock_exec.mock_calls, [])
        mock_rename.assert_called_once_with('FNAME.cut', 'FNAME')
        self.assertIn('Successfully extracted', func.capture())
        self.assertNotIn('OUTPUT', func.capture('err'))

    @mock.patch('atmos_transform.MULE_AVAIL', True)
    @mock.patch('atmos_transform.utils.exec_subproc',
                return_value=(10, 'OUTPUT'))
    @mock.patch('atmos_transform.os.rename')
    def test_cutout_subdomain_fail(self, mock_rename, mock_exec):
        '''Test call to cutout_subdomain - failure'''
        func.logtest('Assert call to cutout_subdomain - failure:')
        with mock.patch('atmos_transform.os.path.exists',
                        side_effect=[True, False]):
            with self.assertRaises(SystemExit):
                icode = atmos_transform.cutout_subdomain(
                    'path/to/file/FNAME', 'MULEDIR', '-CTYPE', [1, 2, 3, 4]
                    )
                self.assertEqual(icode, 10)

        mock_exec.assert_called_once_with(
            'MULEDIR/mule-cutout -CTYPE path/to/file/FNAME ' +
            'path/to/file/FNAME.cut 1 2 3 4'
            )
        self.assertListEqual(mock_rename.mock_calls, [])
        self.assertIn('OUTPUT', func.capture('err'))

    @mock.patch('atmos_transform.MULE_AVAIL', True)
    @mock.patch('atmos_transform.utils.exec_subproc',
                return_value=(1, 'Source grid is NXxNY points'))
    def test_cutout_same_gridbox(self, mock_exec):
        '''Test call to cutout_subdomain - source file already cutout'''
        func.logtest('Assert call to cutout_subdomain - same gridbox:')
        open('FNAME', 'w').close()
        open('FNAME.cut', 'w').close()
        with mock.patch('atmos_transform.os.path.exists',
                        side_effect=[True, False]):
            icode = atmos_transform.cutout_subdomain(
                'FNAME', 'UMDIR', 'indices', ['ZX', 'ZY', 'NX', 'NY']
                )
            self.assertEqual(icode, 1)
        self.assertIn('contains the required gridbox', func.capture())
        self.assertNotIn('Source grid is NXxNY', func.capture())
        mock_exec.assert_called_once_with(
            'UMDIR/mule-cutout indices FNAME FNAME.cut ZX ZY NX NY'
            )

    @mock.patch('atmos_transform.MULE_AVAIL', True)
    @mock.patch('atmos_transform.utils.exec_subproc',
                return_value=(0, 'OUTPUT'))
    @mock.patch('atmos_transform.utils.get_utility_avail', return_value=True)
    def test_cutout_rename(self, mock_util, mock_exec):
        '''Test call to cutout_subdomain - rename file'''
        func.logtest('Assert call to cutout_subdomain - rename file:')
        open('FNAME', 'w').close()
        open('FNAME.cut', 'w').close()
        with mock.patch('atmos_transform.os.path.exists',
                        side_effect=[False, True]):
            icode = atmos_transform.cutout_subdomain('FNAME', None, '-CTYPE',
                                                     [1, 2, 3, 4])
            self.assertEqual(icode, 0)

        expected_cmd_str = 'mule-cutout -CTYPE FNAME FNAME.cut 1 2 3 4'
        mock_exec.assert_has_calls([mock.call(expected_cmd_str)])
        mock_util.assert_has_calls([mock.call('mule-cutout')])

        self.assertTrue(os.path.exists('FNAME'))
        self.assertFalse(os.path.exists('FNAME.cut'))
        self.assertIn('Successfully extracted sub-domain', func.capture())

    @mock.patch('atmos_transform.MULE_AVAIL', True)
    @mock.patch('atmos_transform.utils.exec_subproc',
                return_value=(0, 'OUTPUT'))
    def test_cutout_rename_fail(self, mock_exec):
        '''Test call to cutout_subdomain - failure'''
        func.logtest('Assert call to cutout_subdomain - failure:')
        with mock.patch('atmos_transform.os.path.exists',
                        side_effect=[True, False]):
            with self.assertRaises(SystemExit):
                icode = atmos_transform.cutout_subdomain('FNAME', 'MULEDIR',
                                                         '-CTYPE', [1, 2, 3, 4])
                self.assertEqual(icode, -59)

        mock_exec.assert_called_once_with(
            'MULEDIR/mule-cutout -CTYPE FNAME FNAME.cut 1 2 3 4'
            )
        self.assertIn('Failed to rename', func.capture('err'))

    @mock.patch('atmos_transform.utils.exec_subproc',
                return_value=(0, 'OUTPUT'))
    def test_cutout_util_non_exist(self, mock_exec):
        '''Test call to cutout_subdomain - utility does not exist'''
        func.logtest('Assert call to cutout_subdomain - non-existent utility:')
        with self.assertRaises(SystemExit):
            _ = atmos_transform.cutout_subdomain('path/to/file/FILENAME',
                                                 'MULEDIR',
                                                 '-CTYPE', [1, 2, 3, 4])

        self.assertListEqual(mock_exec.mock_calls, [])
        self.assertIn('Unable to cut out subdomain', func.capture('err'))
        self.assertIn('mule-cutout utility does not exist', func.capture('err'))

    @mock.patch('atmos_transform.utils.exec_subproc',
                return_value=(0, 'OUTPUT'))
    def test_cutout_util_nonexist_debug(self, mock_exec):
        '''Test call to cutout_subdomain - utility does not exist, debug mode'''
        func.logtest('Assert call to cutout_subdomain - no utility, debug:')
        with mock.patch('atmos_transform.utils.get_debugmode',
                        return_value=True):
            icode = atmos_transform.cutout_subdomain('path/to/file/FILENAME',
                                                     'MULEDIR',
                                                     '-CTYPE',
                                                     [1, 2, 3, 4])
            self.assertEqual(icode, -99)

        self.assertListEqual(mock_exec.mock_calls, [])
        self.assertIn('Unable to cut out subdomain', func.capture('err'))


class MeaningTests(unittest.TestCase):
    ''' Unit tests for climate meaning '''

    class DummyField(object):
        ''' Dummy object to represent a UM field '''
        def __init__(self, value):
            self.data = None
            self.lbrel = value
            self.lblev = None
            self.lbuser4 = 'X{}'.format(value)
            self.raw = []

        def copy(self):
            ''' Replicate mule.umfile.copy() '''
            func.logtest('DUMMY.copy field')
            return self

        def get_data(self):
            ''' replicate mule.umfile.get_data() '''
            return 2 * self.lbrel

    class DummyFixHd(object):
        ''' Dummy object to represent a UM fixed-length header '''
        def __init__(self):
            self.raw = list(range(40))

    class DummyMuleFile(object):
        ''' Dummy class to a UMfile loaded by Mule '''
        def __init__(self):
            self.fixed_length_header = MeaningTests.DummyFixHd()
            self.fields = [MeaningTests.DummyField(1),
                           MeaningTests.DummyField(2),
                           MeaningTests.DummyField(3)]

        def copy(self):
            ''' Replicate mule.umfile.copy() '''
            func.logtest('DUMMY.copy file')
            return self

        def to_file(self, filename):
            ''' Replicate mule.umfile.to_file() '''
            func.logtest('DUMMY.to_file: ' + filename)

    def setUp(self):
        if 'operator' in self.id():
            self.fieldlist = []
            for dummy in [2, 5, 10]:
                self.fieldlist.append(MeaningTests.DummyField(dummy))
            self.operator = atmos_transform.WeightedMeanOperator([1, 1, 1])
        elif not validation.MULE_AVAIL:
            # Set up dummy Mule for mocking later
            atmos_transform.mule = None
            atmos_transform.WeightedMeanOperator = None

        self.meanfile = atmos.climatemean.MeanFile('1m', '10d')
        self.meanfile.set_filename('MEANFILE', os.getcwd())
        self.meanfile.periodend = [2000, 6, 1]

    @unittest.skipUnless(validation.MULE_AVAIL,
                         'Python module "Mule" is not available')
    def test_operator(self):
        ''' Test intstantiation of the WeightedMeanOperator object '''
        func.logtest('Assert instantiation of a WeightedMeanOperator:')
        self.assertTrue(isinstance(self.operator,
                                   atmos_transform.WeightedMeanOperator))
        self.assertListEqual(self.operator.weights, [1, 1, 1])

    @unittest.skipUnless(validation.MULE_AVAIL,
                         'Python module "Mule" is not available')
    def test_operator_methods(self):
        ''' Test methods of the WeightedMeanOperator object '''
        func.logtest('Assert method functionality of a WeightedMeanOperator:')
        operator = atmos_transform.WeightedMeanOperator([1, 2, 3])
        self.assertTrue(isinstance(operator.new_field(self.fieldlist),
                                   MeaningTests.DummyField))
        self.assertEqual(operator.new_field(self.fieldlist).get_data(),
                         4)

        self.assertEqual(
            operator.transform(self.fieldlist,
                               operator.new_field(self.fieldlist)),
            ((1 * 2) + (2 * 5) + (3 * 10)) * 2 / float(1 + 2 + 3)
            )

    @unittest.skipUnless(validation.MULE_AVAIL,
                         'Python module "Mule" is not available')
    def test_operator_methods_badwts(self):
        ''' Test the WeightedMeanOperator object - mismatched weights'''
        func.logtest('Assert mismatched weights in a WeightedMeanOperator:')
        operator = atmos_transform.WeightedMeanOperator([1, 2, 3, 4])
        self.assertTrue(isinstance(operator.new_field(self.fieldlist),
                                   MeaningTests.DummyField))
        self.assertEqual(operator.new_field(self.fieldlist).get_data(),
                         4)

        self.assertEqual(
            operator.transform(self.fieldlist,
                               operator.new_field(self.fieldlist)),
            (2 + 5 + 10) * 2 / 3.
            )

    @mock.patch('atmos_transform.MULE_AVAIL', True)
    @mock.patch('atmos_transform.mule')
    @mock.patch('atmos_transform.WeightedMeanOperator')
    def test_create_um_mean(self, mock_op, mock_mule):
        ''' Test the create_um_mean method'''
        func.logtest('Assert call to create_um_mean:')
        self.meanfile.component_files = ['FILE1', 'FILE2', 'FILE3']
        df1 = MeaningTests.DummyMuleFile()
        df2 = MeaningTests.DummyMuleFile()
        df3 = MeaningTests.DummyMuleFile()
        mock_mule.load_umfile.side_effect = [df1, df2, df3]

        atmos_transform.create_um_mean(self.meanfile)

        mock_op.assert_called_once_with([1, 1, 1])
        self.assertListEqual(mock_op().mock_calls,
                             [mock.call([df1.fields[1], mock.ANY, mock.ANY]),
                              mock.call([df1.fields[2], mock.ANY, mock.ANY])])
        self.assertListEqual(
            mock_mule.load_umfile.mock_calls,
            [mock.call('FILE1'), mock.call('FILE2'), mock.call('FILE3')]
            )

        self.assertIn(
            'Creating meanfile MEANFILE with components:'
            '\n\tFILE1\n\tFILE2\n\tFILE3'
            '\n[TEST] DUMMY.copy file'
            '\n[INFO]  Meanfile validity date: 2000,6,1,0 day number 151'
            '\n[INFO]  \tPPheader STARTdate: '
            '\n[INFO]  \tPPheader ENDdate: '
            '\n[TEST] DUMMY.to_file: ' + os.path.join(os.getcwd(), 'MEANFILE'),
            func.capture())

    @mock.patch('atmos_transform.MULE_AVAIL', True)
    @mock.patch('atmos_transform.mule')
    @mock.patch('atmos_transform.WeightedMeanOperator')
    def test_mean_weights_gregorian_10d(self, mock_op, mock_mule):
        ''' Test the create_um_mean method - mean weights for Gregorian'''
        func.logtest('Assert Gregorian mean weights - 10d base:')
        self.meanfile.component_files = ['FILE1', 'FILE2']
        mock_mule.load_umfile.return_value = MeaningTests.DummyMuleFile()

        with mock.patch('atmos_transform.utils.calendar',
                        return_value='gregorian'):
            atmos_transform.create_um_mean(self.meanfile)
        self.assertIn('Creating meanfile MEANFILE with components:',
                      func.capture())
        self.assertIn('FILE1\n\tFILE2', func.capture())
        mock_op.assert_called_once_with([1, 1])

        self.assertIn('Meanfile validity date: 2000,6,1,0 day number 153',
                      func.capture())

    @mock.patch('atmos_transform.MULE_AVAIL', True)
    @mock.patch('atmos_transform.mule')
    @mock.patch('atmos_transform.WeightedMeanOperator')
    def test_mean_weights_gregorian_1m(self, mock_op, mock_mule):
        ''' Test the create_um_mean method - 1m base, Gregorian'''
        func.logtest('Assert Gregorian mean weights - 1m base:')
        mock_mule.load_umfile.return_value = MeaningTests.DummyMuleFile()

        meanfile = atmos.climatemean.MeanFile('1s', '1m')
        meanfile.set_filename('MEANFILE', os.getcwd())
        meanfile.component_files = ['2000jan', '2000feb', '2000mar']
        meanfile.periodend = [2000, 4, 1]

        with mock.patch('atmos_transform.utils.calendar',
                        return_value='gregorian'):
            atmos_transform.create_um_mean(meanfile)

        self.assertIn('Creating meanfile MEANFILE with components:',
                      func.capture())
        self.assertIn('2000jan\n\t2000feb\n\t2000mar', func.capture())
        mock_op.assert_called_once_with([31, 29, 31])

        self.assertIn('Meanfile validity date: 2000,4,1,0 day number 92',
                      func.capture())

    @mock.patch('atmos_transform.MULE_AVAIL', True)
    @mock.patch('atmos_transform.mule')
    @mock.patch('atmos_transform.WeightedMeanOperator')
    def test_mean_weights_gregorian_1s(self, mock_op, mock_mule):
        ''' Test the create_um_mean method'''
        func.logtest('Assert Gregorian mean weights - 1s base:')
        mock_mule.load_umfile.return_value = MeaningTests.DummyMuleFile()

        meanfile = atmos.climatemean.MeanFile('1y', '1s')
        meanfile.set_filename('MEANFILE', os.getcwd())
        meanfile.component_files = ['2000son', '2001djf',
                                    '2001mam', '2001jja']
        meanfile.periodend = [2000, 9, 1]

        with mock.patch('atmos_transform.utils.calendar',
                        return_value='gregorian'):
            atmos_transform.create_um_mean(meanfile)

        self.assertIn('Creating meanfile MEANFILE with components:',
                      func.capture())
        self.assertIn('2000son\n\t2001djf\n\t2001mam\n\t2001jja',
                      func.capture())
        mock_op.assert_called_once_with([91, 90, 92, 92])

        self.assertIn('Meanfile validity date: 2000,9,1,0 day number 245',
                      func.capture())

    @mock.patch('atmos_transform.MULE_AVAIL', False)
    def test_create_um_mean_no_mule(self):
        ''' Test the create_um_mean method - Mule not available'''
        func.logtest('Assert call to create_um_mean - Mule not available:')
        with mock.patch('validation.MULE_AVAIL', return_value=False):
            rtn = atmos_transform.create_um_mean(self.meanfile)
        self.assertTupleEqual(rtn, (None, 'create_um_mean: Mule is not '
                                    'available. Cannot create means'))


class DatestringTests(unittest.TestCase):
    '''Unit tests relating extraction of dates from an inputstring'''
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_identify_dates_none(self):
        ''' Test identify_dates functionality - none found'''
        func.logtest('Assert return from identify_dates - none:')
        self.assertIsNone(validation.identify_dates('RUNIDa.daDUMPDATE'))

    def test_identify_dates_digitonly(self):
        ''' Test identify_dates functionality - digit dates only'''
        func.logtest('Assert return from identify_dates - digit dates:')
        self.assertListEqual(validation.identify_dates('RUNIDa.da11112233'),
                             [['1111', '22', '33']])
        self.assertListEqual(
            validation.identify_dates('RUNIDa.p911112233'),
            [['1111', '22', '33']]
            )
        self.assertListEqual(
            validation.identify_dates('RUNIDa.p911112233_44'),
            [['1111', '22', '33', '44']]
            )

    def test_identify_dates_month(self):
        ''' Test identify_dates functionality - 3char month id (start)'''
        func.logtest('Assert return from identify_dates - start month:')
        self.assertListEqual(
            validation.identify_dates('RUNIDa.pa1111nov'),
            [['1111', '11', '01']]
            )
        self.assertListEqual(
            validation.identify_dates('RUNIDa.pa1111dec'),
            [['1111', '12', '01']]
            )
        self.assertListEqual(
            validation.identify_dates('RUNIDa.pa1111jan'),
            [['1111', '01', '01']]
            )

    def test_identify_dates_season(self):
        ''' Test identify_dates functionality - 3char season id (start)'''
        func.logtest('Assert return from identify_dates - start season:')
        self.assertListEqual(
            validation.identify_dates('RUNIDa.pa1111son'),
            [['1111', '09', '01']]
            )
        self.assertListEqual(
            validation.identify_dates('RUNIDa.pa1111ond'),
            [['1111', '10', '01']]
            )
        self.assertListEqual(
            validation.identify_dates('RUNIDa.pa1111ndj'),
            [['1110', '11', '01']]
            )
        self.assertListEqual(
            validation.identify_dates('RUNIDa.pa1111djf'),
            [['1110', '12', '01']]
            )
        self.assertListEqual(
            validation.identify_dates('RUNIDa.pa1111jfm'),
            [['1111', '01', '01']]
            )

    def test_identify_dates_regex(self):
        ''' Test identify_dates returned regular expression '''
        func.logtest('Assert return from identify_dates - regex input:')
        # Example climatemean.set_date_regex
        self.assertListEqual(validation.identify_dates(
            r'(19950301|19950601|19950901|19951201)'
        ),
                             [['1995', '03', '01'], ['1995', '06', '01'],
                              ['1995', '09', '01'], ['1995', '12', '01']])

        # Example climatemean.end_date_regex
        self.assertListEqual(
            validation.identify_dates(r'\d{4}(01|04|07|10)01'),
            [[r'\d{4}', '(01|04|07|10)', '01']]
            )
        self.assertListEqual(
            validation.identify_dates(r'\d{3}50101'),
            [[r'\d{3}5', '01', '01']]
            )

    def test_get_filedate_hourly(self):
        ''' Test creation of UM file datestring from datelist -hour reinit '''
        func.logtest('Assert UM filename is created from date list, hourly:')
        self.assertEqual(validation.get_filedate([2005, 6, 1], '12h'),
                         '20050601_00')
        self.assertEqual(validation.get_filedate([2005, 12, 1, 12], '12h'),
                         '20051201_12')
        self.assertEqual(
            validation.get_filedate([r'\d{4}', r'\d{2}', '01', '12'], '12h'),
            r'\d{4}(01|02|03|04|05|06|07|08|09|10|11|12)01_12'
            )
        self.assertEqual(validation.get_filedate([2005, 6, 1, 12], '12h',
                                                 end_of_period=True),
                         '20050601_00')

    def test_get_filedate_daily(self):
        ''' Test creation of UM file datestring from datelist - daily reinit '''
        func.logtest('Assert UM filename is created from date list, daily:')
        self.assertEqual(validation.get_filedate([2005, 6, 1], '10d'),
                         '20050601')
        self.assertEqual(
            validation.get_filedate([r'\d{4}', r'\d{2}', '01'], '10d'),
            r'\d{4}(01|02|03|04|05|06|07|08|09|10|11|12)01'
            )
        self.assertEqual(validation.get_filedate([2005, 12, 1], '10d',
                                                 end_of_period=True),
                         '20051121')

    def test_get_filedate_monthly(self):
        ''' Test creation of UM file datestring from datelist - 1m reinit '''
        func.logtest('Assert UM filename is created from date list, 1m:')
        self.assertEqual(validation.get_filedate([2005, 6, 1], '1m'),
                         '2005jun')
        self.assertEqual(validation.get_filedate([2005, 6, 1], '1m',
                                                 end_of_period=True),
                         '2005may')
        self.assertEqual(
            validation.get_filedate([r'\d{4}', r'\d{2}', '01'], '1m'),
            r'\d{4}(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
            )
        self.assertEqual(
            validation.get_filedate(['1991', [1, 4, 7, 10], '01'], '1m'),
            r'1991(jan|apr|jul|oct)'
            )
        self.assertEqual(
            validation.get_filedate([r'\d{4}', '(01|04|07|10)', '01'], '1m',
                                    end_of_period=True),
            r'\d{4}(dec|mar|jun|sep)'
            )
        self.assertEqual(
            validation.get_filedate([r'\d{3}5', '1', '01'], '1m',
                                    end_of_period=True),
            r'\d{3}4dec'
            )

    def test_get_filedate_seasonal(self):
        ''' Test creation of UM file datestring from datelist - 1s reinit '''
        func.logtest('Assert UM filename is created from date list, 1s:')
        self.assertEqual(validation.get_filedate([2005, 6, 1], '1s'),
                         '2005jja')
        self.assertEqual(
            validation.get_filedate([2005, 6, 1], '1s', end_of_period=True),
            '2005mam'
            )
        self.assertEqual(
            validation.get_filedate([r'\d{4}', [3, 6, 9, 12], '01'], '1s'),
            r'\d{4}(mam|jja|son|djf)'
            )
        self.assertEqual(
            validation.get_filedate([r'\d{4}', '(03|06|09|12)', '01'], '1s',
                                    end_of_period=True),
            r'\d{4}(djf|mam|jja|son)'
            )
        self.assertEqual(
            validation.get_filedate(
                [r'\d{3}5', '1', '01'], '1s', end_of_period=True),
            r'\d{3}4ond'
            )

    def test_get_filedate_annual(self):
        ''' Test creation of UM file datestring from datelist - 1s reinit '''
        func.logtest('Assert UM filename is created from date list, 1s:')
        self.assertEqual(validation.get_filedate([2005, 6, 1], '1y'),
                         '20050601')
        self.assertEqual(validation.get_filedate([2005, 6, 1], '1y',
                                                 end_of_period=True),
                         '20040601')
        self.assertEqual(
            validation.get_filedate([r'\d{4}', [3, 6, 9, 12], '01'], '1y'),
            r'\d{4}(03|06|09|12)01'
            )
        self.assertEqual(
            validation.get_filedate([r'\d{4}', '(03|06|09|12)', '01'], '1y',
                                    end_of_period=True),
            r'\d{4}(03|06|09|12)01'
            )
        self.assertEqual(validation.get_filedate([r'\d{3}5', '1', '01'], '1y',
                                                 end_of_period=True),
                         r'\d{3}50101')
