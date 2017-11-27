#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016-2017 Met Office. All rights reserved.

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
import mock

import testing_functions as func

import archive_integrity
import filenames
import verify_namelist


class DummyNamelists(object):
    ''' Dummy namelist container object '''
    def __init__(self):
        self.commonverify = verify_namelist.PeriodicVerify()
        self.commonverify.startdate = '11112233'
        self.commonverify.enddate = '44445566'
        self.commonverify.dataset = 'moose:crum/suiteid'
        self.commonverify.prefix = 'runid'
        self.atmosverify = verify_namelist.AtmosVerify()
        self.nemoverify = verify_namelist.NemoVerify()

class FilenamesTests(unittest.TestCase):
    ''' Unit tests relating to the filenames module '''
    def setUp(self):
        archive_integrity.sys = mock.Mock()
        archive_integrity.sys.argv = []

    def tearDown(self):
        pass

    def test_atmos_components(self):
        ''' Assert realm and component for a given model and field '''
        func.logtest('Assert realm and component:')
        self.assertTupleEqual(filenames.model_components('atmos', None),
                              ('a', None))
        self.assertTupleEqual(filenames.model_components('atmos', 'pm'),
                              ('a', None))
        self.assertTupleEqual(filenames.model_components('atmos', '[abcde]*'),
                              ('a', 'atmos'))

    def test_nemo_components(self):
        ''' Assert realm and component for a given model and field '''
        func.logtest('Assert realm and component:')
        self.assertTupleEqual(filenames.model_components('nemo', None),
                              ('o', None))
        self.assertTupleEqual(filenames.model_components('nemo', 'grid-V'),
                              ('o', 'nemo'))
        self.assertTupleEqual(filenames.model_components('nemo', 'diad-T'),
                              ('o', 'medusa'))

    def test_cice_components(self):
        ''' Assert realm and component for a given model and field '''
        func.logtest('Assert realm and component:')
        self.assertTupleEqual(filenames.model_components('cice', None),
                              ('i', None))
        self.assertTupleEqual(filenames.model_components('cice', ''),
                              ('i', 'cice'))


class VerifyArchiveTests(unittest.TestCase):
    ''' Unit tests relating to the main archive_integrity app '''
    def setUp(self):
        self.archcontent = {'coll1.file': ['file1', 'file3'],
                            'coll2.pp': ['file2', 'file4']}
        self.listing = ['dataset/coll1.file/file1',
                        'dataset/coll2.pp/file2',
                        'dataset/coll1.file/file3',
                        'dataset/coll2.pp/file4']

    def tearDown(self):
        try:
            os.remove('cylclog')
        except OSError:
            pass

    def test_archive_contents(self):
        ''' Test return of the contents of a given archive listing '''
        func.logtest('Assert creation of dictionary for archive contents:')
        listing = ['dataset/coll1.file/file1', 'data/set/coll2.pp/file2',
                   'dataset/coll1.file/file3', 'data/set/coll2.pp/file4']
        self.assertEqual(archive_integrity.archive_contents(listing),
                         self.archcontent)

    def test_debug_logread(self):
        ''' Test reading of the archive log file - rose-stem test dummy '''
        func.logtest('Assert creation of archive listing from dummy logfile:')
        text = 'Data from random cycle: \n dataset/coll1.file/file1 \n'
        text += ' dataset/coll2.pp/file2 \n dataset/coll1.file/file3 \n'
        text += ' dataset/coll2.pp/file4 \n End data. '

        with open('cylclog', 'w') as logfile:
            logfile.write(text)
        with mock.patch.dict('os.environ', {'CYLC_TASK_SHARE_DIR': ''}):
            listing = archive_integrity.log_archive('dataset')
        self.assertEqual(listing, self.archcontent)

    @mock.patch('archive_integrity.utils.exec_subproc')
    def test_debug_mooread(self, mock_exec):
        ''' Test reading of the archive log file - Moose archive '''
        func.logtest('Assert creation of archive listing from Moose archive:')
        moo = 'dataset/coll1.file/file1 \n dataset/coll2.pp/file2 \n'
        moo += ' dataset/coll1.file/file3 \n dataset/coll2.pp/file4 \n'

        mock_exec.return_value = (0, moo)
        listing = archive_integrity.moose_archive('moose:ens/dataset/ensid')
        self.assertEqual(listing, self.archcontent)

    def test_verify_archive(self):
        ''' Test archive verification '''
        func.logtest('Assert complete log:')
        self.assertTrue(archive_integrity.verify_archive(self.archcontent,
                                                         self.archcontent))
        self.assertIn('All expected files present', func.capture())

    def test_verify_archive_false(self):
        ''' Test archive verification - false'''
        func.logtest('Assert incomplete log:')
        expected = {'coll1.file': self.archcontent['coll1.file'],
                    'coll2.pp': ['file5', r'model_xxxx_\.nc$'],
                    'newcoll.file': ['file6']}
        self.assertFalse(archive_integrity.verify_archive(expected,
                                                          self.archcontent))

        self.assertIn('Collection coll2.pp - Files missing from the'
                      ' archive:\n\tfile5', func.capture('err'))
        self.assertIn('Collection coll2.pp - No files found to match '
                      r'regular expression: model_xxxx_\.nc$',
                      func.capture('err'))
        self.assertIn('Collection newcoll.file is missing', func.capture('err'))
        self.assertNotIn('file6', func.capture('err'))
        self.assertNotIn('Collection coll1.file', func.capture('err'))

    def test_check_additional(self):
        ''' Test archive verification - check for unexpected files'''
        func.logtest('Assert presence of unexpected files:')
        expected = {'coll1.file': self.archcontent['coll1.file'],
                    'coll2.pp': ['file5']}
        self.archcontent['newcoll.file'] = ['file6']
        self.assertTrue(
            archive_integrity.check_archive_additional(expected,
                                                       self.archcontent)
            )
        self.assertIn('coll2.pp - Unexpected files in the archive:'
                      '\n\tfile2\n\tfile4', func.capture('err'))
        self.assertIn('newcoll.file is unexpectedly present',
                      func.capture('err'))
        self.assertNotIn('file6', func.capture('err'))
        self.assertNotIn('coll1.file', func.capture('err'))

    def test_check_additinal_false(self):
        ''' Test archive verification - check no unexpected files '''
        func.logtest('Assert no additional files:')
        self.assertFalse(
            archive_integrity.check_archive_additional(self.archcontent,
                                                       self.archcontent)
            )

    @mock.patch('archive_integrity.nlist.loadNamelist')
    @mock.patch('archive_integrity.expected_content.RestartFiles')
    @mock.patch('archive_integrity.expected_content.DiagnosticFiles')
    @mock.patch('archive_integrity.log_archive')
    @mock.patch('archive_integrity.moose_archive', return_value={})
    @mock.patch('archive_integrity.check_archive_additional')
    @mock.patch('archive_integrity.verify_archive')
    def test_main_function_nomodels(self, mock_verify, mock_add, mock_moo,
                                    mock_log, mock_diag, mock_rst, mock_nl):
        ''' Test main function '''
        func.logtest('Assert calls methods by main function - no models:')
        namelists = DummyNamelists()
        mock_nl.return_value = namelists

        archive_integrity.main()
        self.assertEqual(mock_rst.mock_calls, [])
        self.assertEqual(mock_diag.mock_calls, [])
        self.assertEqual(mock_log.mock_calls, [])
        self.assertEqual(mock_add.mock_calls, [])
        mock_moo.assert_called_once_with(namelists.commonverify.dataset)
        mock_verify.assert_called_once_with({}, {})
        self.assertIn('All expected files', func.capture())

    @mock.patch('archive_integrity.nlist.loadNamelist')
    @mock.patch('expected_content.RestartFiles.expected_files',
                return_value={'ada': ['dump1']})
    @mock.patch('archive_integrity.expected_content.DiagnosticFiles'
                '.expected_diags', return_value={'apa': ['pp1']})
    @mock.patch('archive_integrity.log_archive')
    @mock.patch('archive_integrity.moose_archive',
                return_value={'ada': ['dump1', 'dump2'], 'apa': ['pp1']})
    @mock.patch('archive_integrity.check_archive_additional')
    @mock.patch('archive_integrity.verify_archive')
    def test_main_function_atmos(self, mock_verify, mock_add, mock_moo,
                                 mock_log, mock_diag, mock_rst, mock_nl):
        ''' Test main function - atmos namelist'''
        func.logtest('Assert calls to methods by main function - atmos :')
        expected = {}
        expected.update({'ada': ['dump1']})
        expected.update({'apa': ['pp1']})

        namelists = DummyNamelists()
        setattr(namelists, 'atmosverify', verify_namelist.AtmosVerify())
        namelists.atmosverify.verify_model = True
        mock_nl.return_value = namelists
        with mock.patch('archive_integrity.utils.finalcycle'):
            archive_integrity.main()

        mock_rst.assert_called_once_with()
        mock_diag.assert_called_once_with()
        self.assertEqual(mock_log.mock_calls, [])
        self.assertEqual(mock_add.mock_calls, [])
        mock_moo.assert_called_once_with(namelists.commonverify.dataset)
        mock_verify.assert_called_once_with(expected, mock_moo.return_value)
        self.assertIn('All expected files', func.capture())
        self.assertNotIn('Unexpected files present in ada', func.capture())

        namelists.commonverify.check_additional_files_archived = True
        mock_nl.return_value = namelists
        with mock.patch('archive_integrity.utils.finalcycle'):
            archive_integrity.main()

        mock_add.assert_called_once_with(expected, mock_moo.return_value)
        self.assertIn('Unexpected files present in moose', func.capture())

    @mock.patch('archive_integrity.nlist.loadNamelist')
    @mock.patch('expected_content.RestartFiles.expected_files',
                return_value={'oda': ['rst1']})
    @mock.patch('archive_integrity.expected_content.DiagnosticFiles.'
                'expected_diags', return_value={'onm.nc.file': ['nc_m1']})
    @mock.patch('archive_integrity.log_archive')
    @mock.patch('archive_integrity.moose_archive',
                return_value={'oda': ['rst1', 'rst2'],
                              'onm.nc.file': ['nc_m1']})
    @mock.patch('archive_integrity.check_archive_additional')
    @mock.patch('archive_integrity.verify_archive')
    def test_main_function_nemo(self, mock_verify, mock_add, mock_moo,
                                mock_log, mock_diag, mock_rst, mock_nl):
        ''' Test main function - NEMO as script argument'''
        func.logtest('Assert calls by main function - NEMO script arg:')
        archive_integrity.sys.argv = ('script', 'nemo')
        expected = {}
        expected.update({'oda': ['rst1']})
        expected.update({'onm.nc.file': ['nc_m1']})

        namelists = DummyNamelists()
        setattr(namelists, 'atmosverify', verify_namelist.AtmosVerify())
        setattr(namelists, 'nemoverify', verify_namelist.CiceVerify())
        setattr(namelists, 'ciceverify', verify_namelist.NemoVerify())
        namelists.nemoverify.verify_model = True
        namelists.atmosverify.verify_model = True
        mock_nl.return_value = namelists
        with mock.patch('archive_integrity.utils.finalcycle'):
            archive_integrity.main()

        mock_rst.assert_called_once_with()
        mock_diag.assert_called_once_with()
        self.assertEqual(mock_log.mock_calls, [])
        self.assertEqual(mock_add.mock_calls, [])
        mock_moo.assert_called_once_with(namelists.commonverify.dataset)
        mock_verify.assert_called_once_with(expected, mock_moo.return_value)
        self.assertIn('All expected files', func.capture())
        self.assertNotIn('Unexpected files present in oda', func.capture())

        namelists.commonverify.check_additional_files_archived = True
        mock_nl.return_value = namelists
        with mock.patch('archive_integrity.utils.finalcycle'):
            archive_integrity.main()

        mock_add.assert_called_once_with(expected, mock_moo.return_value)
        self.assertIn('Unexpected files present in moose', func.capture())

    @mock.patch('archive_integrity.nlist.loadNamelist')
    def test_main_function_verify_fail(self, mock_nl):
        ''' Test main function - atmos namelist'''
        func.logtest('Assert calls to methods by main function - atmos :')

        namelists = DummyNamelists()
        mock_nl.return_value = namelists
        with mock.patch('archive_integrity.verify_archive', return_value=False):
            with mock.patch('archive_integrity.moose_archive'):
                with mock.patch('archive_integrity.utils.finalcycle'):
                    with self.assertRaises(SystemExit):
                        archive_integrity.main()
        self.assertIn('Dataset incomplete', func.capture('err'))
