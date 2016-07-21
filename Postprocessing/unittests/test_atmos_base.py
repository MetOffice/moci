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


class ArchiveDeleteTests(unittest.TestCase):
    '''Unit tests relating to the atmosphere archive and delete methods'''
    def setUp(self):
        self.atmos = atmos.AtmosPostProc()
        self.atmos.suite = mock.Mock()
        self.atmos.suite.logfile = 'logfile'
        self.atmos.suite.prefix = 'RUNID'
        self.dfiles = ['RUNIDa.YYYYMMDD_00']
        self.ffiles = ['RUNIDa.paYYYYjan', 'RUNIDa.pb1111jan',
                       'RUNIDa.pc1111jan', 'RUNIDa.pd1111jan']

    def tearDown(self):
        files = ['logfile', self.dfiles[0], self.ffiles[0],
                 self.ffiles[0] + '.pp']
        for fname in runtime_environment.runtime_files + files:
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
        self.atmos.nl.archiving.archive_dumps = True
        open(self.dfiles[0], 'w').close()
        with mock.patch('validation.make_dump_name', return_value=self.dfiles):
            with mock.patch('validation.verify_header', return_value=True):
                self.atmos.do_archive()
                validation.make_dump_name.assert_called_once_with(self.atmos)
                validation.verify_header.assert_called_once_with(
                    mock.ANY, os.path.join(os.getcwd(), self.dfiles[0]),
                    mock.ANY, mock.ANY
                    )

        fnfull = os.path.join(os.getcwd(), self.dfiles[0])
        args, kwargs = self.atmos.suite.archive_file.call_args
        self.assertEqual(args, (fnfull, ))
        self.assertEqual(sorted(kwargs.keys()),
                         sorted(['debug', 'preproc', 'logfile']))

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

    @mock.patch('housekeeping.convert_to_pp')
    def test_do_archive_convertpp_all(self, mock_pp):
        '''Test do_archive - convert all fields file to pp format'''
        func.logtest('Assert do_archive conversion to pp - all files:')
        mock_pp.side_effect = [fn + '.pp' for fn in self.ffiles[1:]]
        self.atmos.nl.archiving.archive_pp = True
        with mock.patch('atmos.AtmosPostProc.get_marked_files',
                        return_value=self.ffiles[1:]):
            with mock.patch('os.path.exists', return_value=True):
                with mock.patch('validation.verify_header', return_value=True):
                    self.atmos.do_archive()

        for fname in self.ffiles[1:]:
            fnfull = os.path.join(os.getcwd(), fname)
            self.assertIn(mock.call(fnfull, os.getcwd(), mock.ANY),
                          mock_pp.mock_calls)
        args, kwargs = self.atmos.suite.archive_file.call_args
        self.assertEqual(args, (self.ffiles[-1] + '.pp',))
        self.assertEqual(kwargs['preproc'], True)

    @mock.patch('housekeeping.convert_to_pp')
    def test_do_archive_convertpp_sel(self, mock_pp):
        '''Test do_archive - convert selected fields file to pp format'''
        func.logtest('Assert do_archive conversion to pp - selected files:')
        mock_pp.side_effect = [fn + '.pp' for fn in self.ffiles[1:]]
        self.atmos.nl.archiving.archive_pp = True
        self.atmos.convpp_streams = '^d-f^1'
        with mock.patch('atmos.AtmosPostProc.get_marked_files',
                        return_value=self.ffiles[1:]):
            with mock.patch('os.path.exists', return_value=True):
                with mock.patch('validation.verify_header', return_value=True):
                    self.atmos.do_archive()

        for fname in self.ffiles[1:]:
            fnfull = os.path.join(os.getcwd(), fname)
            if fname == self.ffiles[-1]:
                self.assertNotIn(mock.call(fnfull, os.getcwd(), mock.ANY),
                                 mock_pp.mock_calls)
            else:
                self.assertIn(mock.call(fnfull, os.getcwd(), mock.ANY),
                              mock_pp.mock_calls)
        args, _ = self.atmos.suite.archive_file.call_args
        self.assertEqual(args, (os.path.join(os.getcwd(), self.ffiles[-1]),))

    @mock.patch('housekeeping.convert_to_pp')
    def test_do_archive_convertpp_none(self, mock_pp):
        '''Test do_archive - convert all fields file to pp format'''
        func.logtest('Assert do_archive conversion to pp - all files:')
        mock_pp.side_effect = [fn + '.pp' for fn in self.ffiles[1:]]
        self.atmos.nl.archiving.archive_pp = True
        self.atmos.convpp_streams = '^a-z'
        with mock.patch('atmos.AtmosPostProc.get_marked_files',
                        return_value=self.ffiles[1:]):
            with mock.patch('os.path.exists', return_value=True):
                with mock.patch('validation.verify_header', return_value=True):
                    self.atmos.do_archive()

        self.assertEqual(mock_pp.mock_calls, [])

    def test_do_archive_tidy_pp(self):
        '''Test do_archive functionality - tidy up ppfiles left on disk'''
        func.logtest('Assert do_archive method - tidy left over ppfile:')
        self.atmos.nl.archiving.archive_pp = True
        fnfull = os.path.join(os.getcwd(), self.ffiles[0])
        open(fnfull + '.pp', 'w').close()
        with mock.patch('atmos.AtmosPostProc.get_marked_files',
                        return_value=self.ffiles):
            self.atmos.do_archive()
            self.assertEqual(len(self.atmos.get_marked_files.mock_calls), 1)

        args, _ = self.atmos.suite.archive_file.call_args
        self.assertEqual(args, (fnfull + '.pp', ))


class PropertyTests(unittest.TestCase):
    '''Unit tests relating to the atmosphere property methods'''
    def setUp(self):
        self.atmos = atmos.AtmosPostProc()
        self.atmos.suite = mock.Mock()
        self.atmos.nl.archiving = atmosNamelist.Archiving()

    def tearDown(self):
        for fname in ['atmospp.nl']:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_convpp_single(self):
        '''Test _convpp_streams calculation of regular expression - single'''
        func.logtest('Assert _convpp_streams calculation of regex - single:')
        self.atmos.nl.archiving.archive_as_fieldsfiles = 'a'
        self.assertEqual(self.atmos._convpp_streams, '^a')

    def test_convpp_list(self):
        '''Test _convpp_streams calculation of regular expression - single'''
        func.logtest('Assert _convpp_streams calculation of regex - single:')
        self.atmos.nl.archiving.archive_as_fieldsfiles = ['a', '1-2']
        self.assertEqual(self.atmos._convpp_streams, '^a^1-2')

    def test_convpp_all(self):
        '''Test _convpp_streams calculation of regular expression - single'''
        func.logtest('Assert _convpp_streams calculation of regex - single:')
        for value in [None, '']:
            self.atmos.nl.archiving.archive_as_fieldsfiles = value
            self.assertEqual(self.atmos._convpp_streams, 'a-z1-9')

    def test_streams_property(self):
        '''Test the return value of the streams property'''
        func.logtest('Assert return value of the streams property:')
        self.assertEqual(self.atmos.nl.archiving.process_streams, None)
        self.assertEqual(self.atmos.streams, '1-9a-lp-rt-xz')
        self.atmos.nl.archiving.process_streams = 'at-z'
        self.assertEqual(self.atmos.streams, 'at-z')

    def test_means_property(self):
        '''Test the return value of the means property'''
        func.logtest('Assert return value of the means property:')
        self.assertEqual(self.atmos.nl.archiving.process_means, None)
        self.assertEqual(self.atmos.means, 'msy')
        self.atmos.nl.archiving.process_means = 'at-z'
        self.assertEqual(self.atmos.means, 'at-z')


def main():
    '''Main function'''
    unittest.main(buffer=True)


if __name__ == '__main__':
    main()
