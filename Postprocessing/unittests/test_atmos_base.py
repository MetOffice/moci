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
import validation
import housekeeping


class ArchiveDeleteTests(unittest.TestCase):
    '''Unit tests relating to the atmosphere archive and delete methods'''
    def setUp(self):
        self.atmos = atmos.AtmosPostProc()
        self.atmos.suite = mock.Mock()
        self.atmos.suite.logfile = 'logfile'
        self.dfiles = ['RUNIDa.YYYYMMDD_00']
        self.ffiles = ['RUNIDa.paYYYYjan']

    def tearDown(self):
        for fname in ['logfile', 'atmospp.nl']:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_do_archive_nothing(self):
        '''Test do_archive functionality - nothingto archive'''
        func.logtest('Assert do_archive behaviour with nothing ato archive:')
        with mock.patch('os.path.exists', return_value=True):
            self.atmos.do_archive()
        self.assertIn('Nothing to archive', func.capture())

    def test_do_archive_dump(self):
        '''Test do_archive functionality - dump file'''
        func.logtest('Assert functionality of the do_archive method:')
#        with mock.patch('atmos.AtmosPostProc.get_marked_files') as mock_mk:
        self.atmos.nl.archiving.archive_dumps = True
        with mock.patch('validation.make_dump_name', return_value=self.dfiles):
            with mock.patch('os.path.exists', return_value=True):
                with mock.patch('validation.verify_header', return_value=True):
                    self.atmos.do_archive()
                    validation.make_dump_name.assert_called_once()
                    validation.verify_header.assert_called_once()

        fnfull = os.path.join(os.getcwd(), self.dfiles[0])
        args, kwargs = self.atmos.suite.archive_file.call_args
        self.assertEqual(args, (fnfull, ))
        self.assertEqual(sorted(kwargs.keys()), sorted(['debug', 'logfile']))

    def test_do_archive_non_existent(self):
        '''Test do_archive functionality with non-existent dump'''
        func.logtest('Assert behaviour of do_archive - non-existent dump:')
        self.atmos.nl.archiving.archive_dumps = True
        with mock.patch('os.path.exists', return_value=False):
            with mock.patch('validation.make_dump_name',
                            return_value=self.dfiles):
                self.atmos.do_archive()
        self.assertIn('Nothing to archive', func.capture())
        self.assertIn('does not exist', func.capture('err'))
        self.assertIn('FILE NOT ARCHIVED', open('logfile', 'r').read())

    def test_do_archive_convert_pp(self):
        '''Test do_archive functionality - convert fields file to pp format'''
        func.logtest('Assert functionality of do_archive method - pp file:')
        self.atmos.nl.archiving.archive_pp = True
        fnfull = os.path.join(os.getcwd(), self.ffiles[0])
        with mock.patch('atmos.AtmosPostProc.get_marked_files',
                        return_value=self.ffiles):
            with mock.patch('os.path.exists', return_value=True):
                with mock.patch('validation.verify_header', return_value=True):
                    with mock.patch('housekeeping.convert_to_pp',
                                    return_value=fnfull + '.pp'):
                        self.atmos.do_archive()
                        validation.verify_header.assert_called_once()
                        self.atmos.get_marked_files.assert_called_once()

        args, _ = self.atmos.suite.archive_file.call_args
        self.assertEqual(args, (fnfull + '.pp', ))

    def test_do_archive_no_convert_pp(self):
        '''Test do_archive functionality - no conversion to pp format'''
        func.logtest('Assert functionality of do_archive method - pp file:')
        self.atmos.nl.archiving.archive_pp = True
        self.atmos.nl.archiving.convert_pp = False
        fnfull = os.path.join(os.getcwd(), self.ffiles[0])
        with mock.patch('atmos.AtmosPostProc.get_marked_files',
                        return_value=self.ffiles):
            with mock.patch('os.path.exists', return_value=True):
                with mock.patch('validation.verify_header', return_value=True):
                    with mock.patch('housekeeping.convert_to_pp',
                                    return_value=fnfull + '.pp'):
                        self.atmos.do_archive()
                        housekeeping.convert_to_pp.assert_not_called()

        args, _ = self.atmos.suite.archive_file.call_args
        self.assertEqual(args, (fnfull, ))


def main():
    '''Main function'''
    unittest.main(buffer=True)


if __name__ == '__main__':
    main()
