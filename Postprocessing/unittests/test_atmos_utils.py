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

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'common'))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'atmos'))

import runtime_environment
runtime_environment.setup_env()
import testing_functions as func

import atmos
import atmosNamelist
import validation
import housekeeping


class HousekeepTests(unittest.TestCase):
    '''Unit tests relating to the atmosphere housekeeping utilities'''
    def setUp(self):
        self.umutils = os.path.join(os.environ['UMDIR'],
                                    'vn10.4', 'linux', 'utilities')

    def tearDown(self):
        pass

    def test_convert_to_pp(self):
        '''Test convert_to_pp functionality'''
        func.logtest('Assert functionality of the convert_to_pp method:')
        with mock.patch('utils.exec_subproc') as mock_exec:
            with mock.patch('utils.remove_files') as mock_rm:
                mock_exec.return_value = (0, '')
                ppfile = housekeeping.convert_to_pp('Filename', 'TestDir',
                                                    self.umutils)
                mock_rm.assert_Called_with('Filename', path='TestDir')
            cmd = self.umutils + '/um-ff2pp Filename Filename.pp'
            mock_exec.assert_called_with(cmd, cwd='TestDir')
        self.assertEqual(ppfile, 'Filename.pp')

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
        for fname in ['logfile'] + runtime_environment.runtime_files:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_verify_header(self):
        '''Test verify_header functionality'''
        func.logtest('Assert functionality of the verify_header method:')
        with mock.patch('validation.genlist') as mock_gen:
            mock_gen.return_value = self.fixhd
            with mock.patch('validation.identify_filedate') as mock_date:
                mock_date.return_value = ('YY', 'MM', 'DD')
                valid = validation.verify_header(self.atmos.nl.atmospp,
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
                valid = validation.verify_header(self.atmos.nl.atmospp,
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
                valid = validation.verify_header(self.atmos.nl.atmospp,
                                                 'Filename', self.logfile,
                                                 'LogDir/job')
        self.assertFalse(valid)
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
            self.atmos.nl.archiving.arch_dump_freq = 'Monthly'
        elif 'seasonal' in self.id():
            self.atmos.nl.archiving.arch_dump_freq = 'Seasonal'
        elif 'annual' in self.id():
            self.atmos.nl.archiving.arch_dump_freq = 'Yearly'

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
    def test_monthly_offset_dumpname(self, mock_adddate):
        '''Test creation of a dumpname for monthly archive - offset'''
        func.logtest('Assert creation of dumpname for monthly archive')
        mock_adddate.return_value = [1980, 10, 1, 0, 0, 0]
        self.atmos.suite.cycledt = [1980, 10, 1, 0, 0, 0]
        self.atmos.nl.archiving.arch_dump_offset = 6
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
        self.assertEqual(dumps, ['CYCLEDUMP', 'FINALDUMP'])
        mock_adddate.assert_called_with([1980, 9, 1, 0, 0, 0], [0, 1])

    @mock.patch('utils.add_period_to_date')
    def test_monthly_dump_firstcycle(self, mock_adddate):
        '''Test creation of dumpnames for monthly archive - first cycle'''
        func.logtest('Assert dumpname creation for monthly archive - first')
        self.atmos.final_dumpname = 'FINALDUMP'
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
        self.atmos.nl.archiving.arch_year_month = 'January'
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['CYCLEDUMP'])

    def test_annual_july_dumpname(self):
        '''Test creation of a dumpname for annual archive'''
        func.logtest('Assert creation of dumpname for annual archive (Jan)')
        self.atmos.suite.cycledt = [1981, 7, 1, 0, 0, 0]
        self.atmos.nl.archiving.arch_year_month = 'July'
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, ['CYCLEDUMP'])

    def test_annual_dumpname_none(self):
        '''Test creation of no dumpnames for annual archive'''
        func.logtest('Assert creation of no dumpnames for annual archive')
        self.atmos.suite.cycledt = [1980, 10, 1, 0, 0, 0]
        self.atmos.nl.archiving.arch_year_month = 'January'
        dumps = validation.make_dump_name(self.atmos)
        self.assertEqual(dumps, [])


def main():
    '''Main function'''
    unittest.main(buffer=True)


if __name__ == '__main__':
    main()
