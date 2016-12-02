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
import os
import re
import mock

import testing_functions as func
import runtime_environment

import atmosNamelist
import validation
import housekeeping
import utils
# Import of atmos requires RUNID from runtime_environment
runtime_environment.setup_env()
import atmos


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
        self.arch_dumps = [('DUMP1', True), ('DUMP2', False), ('DUMP3', True)]
        self.del_dumps = ['DUMP1', 'DUMP1a', 'DUMP2', 'DUMP2a',
                          'DUMP3', 'DUMP3a']

    def tearDown(self):
        for fname in runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass
        utils.set_debugmode(False)

    @mock.patch('utils.remove_files')
    def test_delete_inst_pp_archived(self, mock_rm):
        '''Test delete_ppfiles functionality - archived instantaneous files'''
        func.logtest('Assert successful deletion of archived inst. ppfiles:')
        self.atmos.naml.delete_sc.gpdel = True
        self.atmos.naml.delete_sc.gcmdel = False
        housekeeping.delete_ppfiles(self.atmos, self.del_inst_pp,
                                    self.del_mean_pp, True)
        self.assertEqual(
            mock_rm.mock_calls,
            [mock.call(['INST1', 'INST3'], path='ShareDir'),
             mock.call(['INST1.arch', 'INST3.arch'], path='WorkDir',
                       ignoreNonExist=True)]
            )

    @mock.patch('utils.remove_files')
    def test_delete_mean_pp_archived(self, mock_rm):
        '''Test delete_ppfiles functionality - archived mean ppfiles'''
        func.logtest('Assert successful deletion of archived mean ppfiles:')
        self.atmos.naml.delete_sc.gpdel = True
        self.atmos.naml.delete_sc.gcmdel = False
        housekeeping.delete_ppfiles(self.atmos, self.del_mean_pp,
                                    self.del_mean_pp, True)
        self.assertEqual(
            mock_rm.mock_calls,
            [mock.call(['MEAN1', 'MEAN3'], path='ShareDir'),
             mock.call(['MEAN1.arch', 'MEAN3.arch'], path='WorkDir',
                       ignoreNonExist=True)]
            )

    @mock.patch('os.rename')
    def test_delete_pp_archived_debug(self, mock_rm):
        '''Test delete_ppfiles functionality - archived (debug_mode)'''
        func.logtest('Assert successful deletion of archived ppfiles - debug:')
        utils.set_debugmode(True)
        self.atmos.naml.delete_sc.gcmdel = True
        housekeeping.delete_ppfiles(self.atmos, self.del_mean_pp,
                                    self.del_mean_pp, True)
        calls = [
            mock.call('ShareDir/MEAN1', 'ShareDir/MEAN1_ARCHIVED'),
            mock.call('ShareDir/MEAN3', 'ShareDir/MEAN3_ARCHIVED'),
            mock.call('WorkDir/MEAN1.arch', 'WorkDir/MEAN1.arch_ARCHIVED'),
            mock.call('WorkDir/MEAN3.arch', 'WorkDir/MEAN3.arch_ARCHIVED')
            ]
        self.assertEqual(sorted(mock_rm.mock_calls), sorted(calls))

    @mock.patch('housekeeping.get_marked_files')
    @mock.patch('housekeeping.FILETYPE')
    @mock.patch('utils.remove_files')
    def test_delete_inst_ppfiles(self, mock_rm, mock_ft, mock_mark):
        '''Test delete_ppfiles functionality - instantaneous files'''
        func.logtest('Assert successful deletion of inst. ppfiles:')
        self.atmos.naml.delete_sc.gpdel = True
        mock_ft.__getitem__().__getitem__().return_value = 'INST'
        mock_mark.return_value = [f[0] for f in self.del_inst_pp +
                                  self.del_mean_pp]
        housekeeping.delete_ppfiles(self.atmos, self.del_inst_pp,
                                    self.del_mean_pp, False)
        self.assertEqual(
            mock_rm.mock_calls,
            [mock.call(['INST1', 'INST2', 'INST3'], path='ShareDir'),
             mock.call(['INST1.arch', 'INST2.arch', 'INST3.arch'],
                       path='WorkDir', ignoreNonExist=True)]
            )

    @mock.patch('housekeeping.get_marked_files')
    @mock.patch('housekeeping.FILETYPE')
    @mock.patch('utils.remove_files')
    def test_delete_mean_ppfiles(self, mock_rm, mock_ft, mock_mark):
        '''Test delete_ppfiles functionality - mean files'''
        func.logtest('Assert successful deletion of mean ppfiles:')
        self.atmos.naml.delete_sc.gcmdel = True
        mock_ft.__getitem__().__getitem__().return_value = 'MEAN'
        mock_mark.return_value = [f[0] for f in self.del_inst_pp +
                                  self.del_mean_pp]
        housekeeping.delete_ppfiles(self.atmos, self.del_mean_pp,
                                    self.del_mean_pp, False)
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

    @mock.patch('utils.get_subset')
    @mock.patch('re.search')
    @mock.patch('utils.remove_files')
    def test_delete_dumps(self, mock_rm, mock_match, mock_set):
        '''Test delete_dumps functionality'''
        func.logtest('Assert successful deletion of dumps:')
        mock_set.return_value = self.del_dumps
        mock_match().group.side_effect = ['11', '22', '33', '44',
                                          '55', '66', '77', '88']
        self.atmos.suite.cyclestring = '44'
        housekeeping.delete_dumps(self.atmos, self.arch_dumps, False)

        housekeeping.delete_ppfiles(self.atmos, self.del_inst_pp,
                                    self.del_mean_pp, False)
        mock_rm.assert_called_once_with(self.del_dumps[0:4], path='ShareDir')

    @mock.patch('utils.get_subset')
    @mock.patch('utils.remove_files')
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

    @mock.patch('utils.get_subset')
    @mock.patch('utils.remove_files')
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

    @mock.patch('utils.get_subset')
    @mock.patch('utils.remove_files')
    @mock.patch('os.rename')
    def test_del_dumps_archived_debug(self, mock_mv, mock_rm, mock_set):
        '''Test delete_dumps functionality - archived files (debug_mode)'''
        func.logtest('Assert successful deletion of archived dumps - debug:')
        utils.set_debugmode(True)
        self.atmos.final_dumpname = 'DUMP1a'
        mock_set.return_value = self.del_dumps
        housekeeping.delete_dumps(self.atmos, self.arch_dumps, True)
        self.assertEqual(
            mock_mv.mock_calls,
            [mock.call('ShareDir/DUMP1', 'ShareDir/DUMP1_ARCHIVED'),
             mock.call('ShareDir/DUMP3', 'ShareDir/DUMP3_ARCHIVED')]
            )
        mock_rm.assert_called_once_with('DUMP2a', path='ShareDir')

    @mock.patch('utils.get_subset', return_value=['File1.sfx', 'File2.sfx'])
    def test_get_marked_files(self, mock_getfiles):
        '''Test list created by get_marked_files'''
        func.logtest('Assert creation of marked files list:')
        marked = housekeeping.get_marked_files('TestDir', 'pattern', '.sfx')
        self.assertListEqual(marked, ['File1', 'File2'])
        mock_getfiles.assert_caleld_once_with('TestDir', 'pattern')

    @mock.patch('utils.get_subset', return_value=['File1.sfx', 'File2.sfx'])
    def test_get_marked_files_nosuffix(self, mock_getfiles):
        '''Test list created by get_marked_files - no suffix'''
        func.logtest('Assert creation of marked files list - no suffix:')
        marked = housekeeping.get_marked_files('TestDir', 'pattern', '')
        self.assertListEqual(marked, ['File1.sfx', 'File2.sfx'])
        mock_getfiles.assert_caleld_once_with('TestDir', 'pattern')

    @mock.patch('utils.get_subset', return_value=[])
    def test_get_marked_files_none(self, mock_getfiles):
        '''Test list created by get_marked_files - empty list'''
        func.logtest('Assert creation of marked files list - empty list:')
        marked = housekeeping.get_marked_files('TestDir', 'pattern', '.sfx')
        self.assertListEqual(marked, [])
        mock_getfiles.assert_caleld_once_with('TestDir', 'pattern')


class HeaderTests(unittest.TestCase):
    '''Unit tests relating to file datestamp validity against the UM fixHD'''
    def setUp(self):
        self.umutils = atmosNamelist.AtmosNamelist().um_utils
        self.atmos = atmos.AtmosPostProc()
        self.fixhd = [('27', 'xx'), ('28', 'YY'), ('29', 'MM'),
                      ('30', 'DD'), ('31', 'xx'), ('32', 'xx'),
                      ('33', 'xx'), ('34', 'xx'), ('35', 'xx')]
        self.logfile = open('logfile', 'w')

    def tearDown(self):
        for fname in ['logfile'] + runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass
        utils.set_debugmode(False)

    def test_verify_header(self):
        '''Test verify_header functionality'''
        func.logtest('Assert functionality of the verify_header method:')
        with mock.patch('validation.genlist') as mock_gen:
            mock_gen.return_value = self.fixhd
            with mock.patch('validation.identify_filedate') as mock_date:
                mock_date.return_value = ('YY', 'MM', 'DD')
                valid = validation.verify_header(self.atmos.naml.atmospp,
                                                 'Filename', self.logfile,
                                                 'LogDir/job')
        self.assertTrue(valid)
        mock_date.assert_called_with('Filename')
        mock_gen.assert_called_with('Filename', 'LogDir/job-pumfhead.out',
                                    self.umutils + '/um-pumf')
        self.logfile.close()
        self.assertEqual('', open('logfile', 'r').read())

    def test_verify_header_mismatch(self):
        '''Test verify_header functionality - mismatch'''
        func.logtest('Assert mismatch date in the verify_header method:')
        with mock.patch('validation.genlist') as mock_gen:
            mock_gen.return_value = self.fixhd
            with mock.patch('validation.identify_filedate') as mock_date:
                mock_date.return_value = ('YY', 'MM', 'DD1')
                with self.assertRaises(SystemExit):
                    _ = validation.verify_header(self.atmos.naml.atmospp,
                                                 'Filename', self.logfile,
                                                 'LogDir/job')
        self.assertIn('Validity time mismatch', func.capture('err'))
        self.logfile.close()
        self.assertIn('ARCHIVE FAILED', open('logfile', 'r').read())

    def test_verify_hdr_mismatch_debug(self):
        '''Test verify_header functionality - mismatch (debug)'''
        func.logtest('Assert mismatch date in the verify_header method:')
        utils.set_debugmode(True)
        with mock.patch('validation.genlist') as mock_gen:
            mock_gen.return_value = self.fixhd
            with mock.patch('validation.identify_filedate') as mock_date:
                mock_date.return_value = ('YY', 'MM', 'DD1')
                valid = validation.verify_header(self.atmos.naml.atmospp,
                                                 'Filename', self.logfile,
                                                 'LogDir/job')
        self.assertFalse(valid)
        self.assertIn('Validity time mismatch', func.capture('err'))
        self.logfile.close()
        self.assertIn('ARCHIVE FAILED', open('logfile', 'r').read())

    def test_verify_header_no_header(self):
        '''Test verify_header functionality - no header information'''
        func.logtest('Assert verify_header finding no header information:')
        self.fixhd = self.fixhd[:2]
        with mock.patch('validation.genlist') as mock_gen:
            mock_gen.return_value = self.fixhd
            with mock.patch('validation.identify_filedate') as mock_date:
                mock_date.return_value = ('YY', 'MM', 'DD')
                with self.assertRaises(SystemExit):
                    _ = validation.verify_header(self.atmos.naml.atmospp,
                                                 'Filename', self.logfile,
                                                 'LogDir/job')
        self.assertIn('No header information available', func.capture('err'))
        self.logfile.close()
        self.assertIn('ARCHIVE FAILED', open('logfile', 'r').read())


class DumpnameTests(unittest.TestCase):
    '''Unit tests covering the make_dump_name method'''

    def setUp(self):
        self.atmos = atmos.AtmosPostProc()
        atmos.AtmosPostProc.dumpname = mock.Mock(return_value='CYCLEDUMP')
        self.atmos.suite = mock.Mock()
        self.atmos.envars = mock.Mock()
        self.atmos.envars.MODELBASIS = '1980,09,01,00,00,00'
        self.atmos.final_dumpname = None
        if 'monthly' in self.id():
            self.atmos.naml.archiving.arch_dump_freq = 'Monthly'
        elif 'seasonal' in self.id():
            self.atmos.naml.archiving.arch_dump_freq = 'Seasonal'
        elif 'annual' in self.id():
            self.atmos.naml.archiving.arch_dump_freq = 'Yearly'

    def tearDown(self):
        pass

    @mock.patch('utils.add_period_to_date')
    def test_monthly_dumpname(self, mock_adddate):
        '''Test creation of a dumpname for monthly archive'''
        func.logtest('Assert creation of dumpname for monthly archive')
        mock_adddate.return_value = [1980, 10, 1, 0, 0, 0]
        self.atmos.suite.cycledt = [1980, 10, 1, 0, 0, 0]
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['CYCLEDUMP'])
        mock_adddate.assert_called_with([1980, 9, 1, 0, 0, 0], [0, 1])

    @mock.patch('utils.add_period_to_date')
    def test_monthly_dumpname12h(self, mock_adddate):
        '''Test to ensure no creation of a dumpname with 12h timestamp
        when running 12h cycling'''
        func.logtest('Assure no creation of dumpname with 12h timestep'
                     ' when using monthly archiving')
        mock_adddate.return_value = [1980, 10, 1, 12, 0, 0]
        self.atmos.suite.cycledt = [1980, 10, 1, 12, 0, 0]
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, [])

    @mock.patch('utils.add_period_to_date')
    def test_monthly_offset_dumpname(self, mock_adddate):
        '''Test creation of a dumpname for monthly archive - offset'''
        func.logtest('Assert creation of dumpname for monthly archive')
        mock_adddate.return_value = [1980, 10, 1, 0, 0, 0]
        self.atmos.suite.cycledt = [1980, 10, 1, 0, 0, 0]
        self.atmos.naml.archiving.arch_dump_offset = 6
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['CYCLEDUMP'])
        mock_adddate.assert_called_with([1980, 9, 1, 0, 0, 0], [0, 7])

    @mock.patch('utils.add_period_to_date')
    def test_monthly_dump_finalcycle(self, mock_adddate):
        '''Test creation of dumpnames for monthly archive - final cycle'''
        func.logtest('Assert dumpname creation for monthly archive - final')
        mock_adddate.return_value = [1980, 10, 1, 0, 0, 0]
        self.atmos.final_dumpname = 'FINALDUMP'
        self.atmos.suite.cycledt = [1980, 10, 1, 0, 0, 0]
        dumps = validation.make_dump_name(self.atmos)
        self.assertListEqual(sorted(dumps), ['CYCLEDUMP', 'FINALDUMP'])
        mock_adddate.assert_called_with([1980, 9, 1, 0, 0, 0], [0, 1])

    @mock.patch('utils.add_period_to_date')
    def test_monthly_dump_firstcycle(self, mock_adddate):
        '''Test creation of dumpnames for monthly archive - first cycle'''
        func.logtest('Assert dumpname creation for monthly archive - first')
        self.atmos.suite.cycledt = [1980, 9, 1, 0, 0, 0]
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, [])
        self.assertEqual(mock_adddate.mock_calls, [])

    @mock.patch('utils.add_period_to_date')
    def test_monthly_dump_mid_month(self, mock_adddate):
        '''Test creation of no dumpnames for monthly archive (mid month)'''
        func.logtest('Assert dumpname creation for monthly arch - mid month')
        mock_adddate.return_value = [1980, 10, 1, 0, 0, 0]
        self.atmos.suite.cycledt = [1980, 10, 15, 0, 0, 0]
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, [])

    @mock.patch('utils.add_period_to_date')
    def test_monthly_dump_before_basis(self, mock_adddate):
        '''Test creation of no dumpnames for monthly archive (before basis)'''
        func.logtest('Assert dumpname creation for monthly arch - early')
        mock_adddate.return_value = [1980, 11, 1, 0, 0, 0]
        self.atmos.suite.cycledt = [1980, 10, 1, 0, 0, 0]
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, [])

    def test_seasonal_dumpname(self):
        '''Test creation of a dumpname for seasonal archive'''
        func.logtest('Assert creation of dumpname for seasonal archive')
        self.atmos.suite.cycledt = [1980, 12, 1, 0, 0, 0]
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['CYCLEDUMP'])

    def test_seasonal_dumpname12h(self):
        '''Test to ensure no creation of a dumpname with 12h timestamp
        when running 12h cycling'''
        func.logtest('Assure no creation of dumpname with 12h timestep'
                     ' when using seasonal archiving')
        self.atmos.suite.cycledt = [1981, 12, 1, 12, 0, 0]
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, [])

    def test_seasonal_dumpname_none(self):
        '''Test creation of no dumpnames for seasonal archive'''
        func.logtest('Assert creation of no dumpnames for seasonal archive')
        self.atmos.suite.cycledt = [1980, 10, 1, 0, 0, 0]
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, [])

    def test_annual_jan_dumpname(self):
        '''Test creation of a dumpname for annual archive'''
        func.logtest('Assert creation of dumpname for annual archive (Jan)')
        self.atmos.suite.cycledt = [1981, 1, 1, 0, 0, 0]
        self.atmos.naml.archiving.arch_year_month = 'January'
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['CYCLEDUMP'])

    def test_annual_jan_dumpname12h(self):
        '''Test to ensure no creation of a dumpname with 12h timestamp
        when running 12h cycling'''
        func.logtest('Assure no creation of dumpname with 12h timestep'
                     ' when using yearly archiving')
        self.atmos.suite.cycledt = [1981, 1, 1, 12, 0, 0]
        self.atmos.naml.archiving.arch_year_month = 'January'
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, [])

    def test_annual_july_dumpname(self):
        '''Test creation of a dumpname for annual archive'''
        func.logtest('Assert creation of dumpname for annual archive (Jan)')
        self.atmos.suite.cycledt = [1981, 7, 1, 0, 0, 0]
        self.atmos.naml.archiving.arch_year_month = 'July'
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['CYCLEDUMP'])

    def test_annual_dumpname_none(self):
        '''Test creation of no dumpnames for annual archive'''
        func.logtest('Assert creation of no dumpnames for annual archive')
        self.atmos.suite.cycledt = [1980, 10, 1, 0, 0, 0]
        self.atmos.naml.archiving.arch_year_month = 'January'
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, [])

    def test_dumpname_firstlast_cycle(self):
        '''Test creation of dumpnames for archive - first & last cycle'''
        func.logtest('Assert dumpname creation for archive - first/last cycle')
        self.atmos.final_dumpname = 'FINALDUMP'
        self.atmos.suite.cycledt = [1980, 9, 1, 0, 0, 0]
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['FINALDUMP'])
