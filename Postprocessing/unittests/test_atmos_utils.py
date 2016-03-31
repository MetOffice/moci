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
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'atmos'))
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
        for fname in ['logfile', 'atmospp.nl']:
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


def main():
    '''Main function'''
    unittest.main(buffer=True)


if __name__ == '__main__':
    main()
