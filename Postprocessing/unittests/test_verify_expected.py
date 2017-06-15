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
import mock

import testing_functions as func

import expected_content
import verify_namelist

class DateTests(unittest.TestCase):
    ''' Unit test for 8char datestring conversion to 3 element date lists '''
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_nlist_date(self):
        '''Assert correct conversion to list from 8char string'''
        func.logtest('Assert correct conversion to list from 8char string:')
        self.assertEqual(expected_content.nlist_date(801, 'my date'),
                         [0, 8, 1])

        self.assertEqual(expected_content.nlist_date(19810821, 'my date'),
                         [1981, 8, 21])

        self.assertEqual(expected_content.nlist_date('1981081106', 'my date'),
                         [1981, 8, 11, 6])

    def test_nlist_date_fail(self):
        '''Assert failure mode of date conversion method'''
        func.logtest('Assert exit on failure of date conversion:')
        with self.assertRaises(SystemExit):
            _ = expected_content.nlist_date('YY1111', 'my date')
        self.assertIn('my date should consist of 8 digits: "00YY1111"',
                      func.capture('err'))

class ArchivedFilesTests(unittest.TestCase):
    ''' Unit tests relating to the ArchivedFiles (parent) class methods '''
    def setUp(self):
        with mock.patch('utils.finalcycle', return_value=False):
            self.files = expected_content.ArchivedFiles(
                '11112233', '44445566', 'PREFIX', 'model',
                verify_namelist.AtmosVerify()
                )

    def tearDown(self):
        pass

    def test_archived_files_instance(self):
        '''Assert correct attributes of the ArchivedFiles instance'''
        func.logtest('Assert correct attributes for ArchivedFiles instance:')
        self.assertListEqual(self.files.sdate, [1111, 22, 33])
        self.assertListEqual(self.files.edate, [4444, 55, 66])
        self.assertEqual(self.files.prefix, 'PREFIX')
        self.assertEqual(self.files.model, 'model')
        self.assertFalse(self.files.finalcycle)


    def test_extract_start_date(self):
        '''Assert correct extraction of date from various filenames '''
        func.logtest('Assert correct extraction of date')
        self.assertListEqual(self.files.extract_date('runida.pa1988jan'),
                             [1988, 1, 1])
        self.assertListEqual(self.files.extract_date('runida.pa19880115'),
                             [1988, 1, 15])
        self.assertListEqual(self.files.extract_date('runida.da19880115_12'),
                             [1988, 1, 15, 12])
        self.assertListEqual(
            self.files.extract_date('runido_19880115_rst.nc'), [1988, 1, 15]
            )
        self.assertListEqual(
            self.files.extract_date('runido_iberg_runido_19880115_rst.nc'),
            [1988, 1, 15]
            )
        self.assertListEqual(
            self.files.extract_date('runidi.restart.1988-01-15-00000.nc'),
            [1988, 1, 15, 0]
            )
        self.assertListEqual(
            self.files.extract_date('medusa_runido_1m_198801-198802_grid.nc'),
            [1988, 1, 1]
            )
        self.assertListEqual(
            self.files.extract_date('nemo_runido_10d_19880115-19881115'
                                    '_grid.nc'), [1988, 1, 15]
            )
        self.assertListEqual(
            self.files.extract_date('cice_runidi_1d_1988011012-1988011112.nc'),
            [1988, 1, 10, 12]
            )

    def test_extract_end_date(self):
        '''Assert correct extraction of date from various filenames '''
        func.logtest('Assert correct extraction of date')
        self.assertListEqual(self.files.extract_date('runida.pa1988jan',
                                                     start=False),
                             [1988, 1, 1])
        self.assertListEqual(
            self.files.extract_date('medusa_runido_1m_198801-198802_grid.nc',
                                    start=False), [1988, 2, 1]
            )
        self.assertListEqual(
            self.files.extract_date('nemo_runido_10d_19880115-19881115'
                                    '_grid.nc', start=False), [1988, 11, 15]
            )
        self.assertListEqual(
            self.files.extract_date('cice_runidi_1d_1988011012-1988011112.nc',
                                    start=False), [1988, 1, 11, 12]
            )

    def test_extract_seasonal_date(self):
        '''Assert correct handling of atmosphere seasonal means'''
        func.logtest('Assert correct handling of atmosphere seasonal means:')
        with self.assertRaises(SystemExit):
            _ = self.files.extract_date('runida.pa1988djf')
        self.assertIn('Mean reference date required', func.capture('err'))

        self.files.meanref = [2000, 12, 1]
        self.assertListEqual(self.files.extract_date('runida.pa1988djf'),
                             [1987, 12, 1])
        self.assertListEqual(self.files.extract_date('runida.pa1988mam'),
                             [1988, 3, 1])
        self.assertListEqual(self.files.extract_date('runida.pa1988djf',
                                                     start=False), [1988, 3, 1])
        self.assertListEqual(self.files.extract_date('runida.pa1988mam',
                                                     start=False), [1988, 6, 1])

    def test_seasons(self):
        '''Assert return of available seasons'''
        func.logtest('Assert return of available seasons:')
        self.assertListEqual(self.files.seasons([2000, 12, 1]),
                             [(3, 'mam'), (6, 'jja'), (9, 'son'), (12, 'djf')])
        self.assertListEqual(self.files.seasons([2010, 11, 15]),
                             [(2, 'fma'), (5, 'mjj'), (8, 'aso'), (11, 'ndj')])
        self.assertListEqual(self.files.seasons([2000, 1, 1]),
                             [(1, 'jfm'), (4, 'amj'), (7, 'jas'), (10, 'ond')])

    def test_seasons_shift(self):
        '''Assert return of available seasons'''
        func.logtest('Assert return of available seasons:')
        self.assertListEqual(self.files.seasons([2000, 12, 1], shift=1),
                             [(1, 'jfm'), (4, 'amj'), (7, 'jas'), (10, 'ond')])
        self.assertListEqual(self.files.seasons([2000, 12, 1], shift=2),
                             [(2, 'fma'), (5, 'mjj'), (8, 'aso'), (11, 'ndj')])
        self.assertListEqual(self.files.seasons([2000, 12, 1], shift=3),
                             [(3, 'mam'), (6, 'jja'), (9, 'son'), (12, 'djf')])
        self.assertListEqual(self.files.seasons([2000, 12, 1], shift=4),
                             [(1, 'jfm'), (4, 'amj'), (7, 'jas'), (10, 'ond')])

    def test_filename_dict_atmos(self):
        '''Assert return of key, realm and component for atmosphere'''
        func.logtest('Assert successful return of atmos key and realm:')
        self.files.model = 'atmos'
        self.files.naml = verify_namelist.AtmosVerify()
        self.assertTupleEqual(self.files.get_fn_components(None),
                              ('rst', 'a', None))
        self.assertTupleEqual(self.files.get_fn_components('k'),
                              ('atmos_pp', 'a', None))
        self.files.naml.ff_streams = 'k'
        self.assertTupleEqual(self.files.get_fn_components('k'),
                              ('atmos_ff', 'a', None))
        self.assertTupleEqual(self.files.get_fn_components(r'[a-zA-Z0-9\-]*'),
                              ('ncf_mean', 'a', 'atmos'))

    def test_filename_dict_nemocice(self):
        '''Assert return of key, realm and component for nemocice'''
        func.logtest('Assert return of nemocice key, realm and component:')
        self.files.model = 'nemo'
        self.files.naml = verify_namelist.NemoVerify()
        self.assertTupleEqual(self.files.get_fn_components(None),
                              ('rst', 'o', None))
        self.assertTupleEqual(self.files.get_fn_components('grid-T'),
                              ('ncf_mean', 'o', 'nemo'))
        self.files.model = 'cice'
        self.assertTupleEqual(self.files.get_fn_components(None),
                              ('rst', 'i', None))
        self.assertTupleEqual(self.files.get_fn_components(''),
                              ('ncf_mean', 'i', 'cice'))

    @mock.patch('expected_content.ArchivedFiles.get_fn_components')
    def test_collection_atmos(self, mock_cmp):
        ''' Assert return of collection name - atmos '''
        func.logtest('Assert successful return of an atmos collection name')
        self.files.model = 'atmos'
        mock_cmp.return_value = ('rst', 'a', None)
        self.assertEqual(self.files.get_collection(), 'ada.file')
        mock_cmp.return_value = ('atmos_pp', 'a', None)
        self.assertEqual(self.files.get_collection(period='10d', stream='k'),
                         'apk.pp')
        mock_cmp.return_value = ('atmos_ff', 'a', None)
        self.assertEqual(self.files.get_collection(stream='k'), 'apk.file')
        mock_cmp.return_value = ('ncf_mean', 'a', 'atmos')
        self.assertEqual(self.files.get_collection(stream='k'), 'ank.nc.file')

    @mock.patch('expected_content.ArchivedFiles.get_fn_components')
    def test_collection_nemo(self, mock_cmp):
        ''' Assert return of collection name - nemo '''
        func.logtest('Assert successful return of an nemo collection name')
        self.files.model = 'nemo'
        mock_cmp.return_value = ('rst', 'o', None)
        self.assertEqual(self.files.get_collection(), 'oda.file')
        mock_cmp.return_value = ('ncf_mean', 'o', 'nemo')
        self.assertEqual(self.files.get_collection(period='10d', stream='grid'),
                         'ond.nc.file')
        mock_cmp.return_value = ('ncf_mean', 'o', 'medusa')
        self.assertEqual(self.files.get_collection(period='1m', stream='grid'),
                         'onm.nc.file')

    @mock.patch('expected_content.ArchivedFiles.get_fn_components')
    def test_collection_cice(self, mock_cmp):
        ''' Assert return of collection name - cice '''
        func.logtest('Assert successful return of an cice collection name')
        self.files.model = 'cice'
        mock_cmp.return_value = ('rst', 'i', None)
        self.assertEqual(self.files.get_collection(), 'ida.file')
        mock_cmp.return_value = ('ncf_mean', 'i', 'cice')
        self.assertEqual(self.files.get_collection(period='1s', stream=''),
                         'ins.nc.file')
        mock_cmp.return_value = ('ncf_mean', 'i', 'medusa')
        self.assertEqual(self.files.get_collection(period='1y', stream=''),
                         'iny.nc.file')


class RestartFilesTests(unittest.TestCase):
    ''' Unit tests relating to the RestartFiles (child) class methods '''
    def setUp(self):
        model = 'model'
        naml = verify_namelist.AtmosVerify()
        if 'atmos' in self.id():
            model = 'atmos'
        elif 'nemo' in self.id():
            model = 'nemo'
            naml = verify_namelist.NemoVerify()
        elif 'cice' in self.id():
            model = 'cice'
            naml = verify_namelist.CiceVerify()
            naml.cice_age_rst = True
        elif '10d_delay' in self.id():
            naml.delay_rst_archive = '10days'
        elif '6m_delay' in self.id():
            naml.delay_rst_archive = '6M'

        with mock.patch('utils.finalcycle', return_value=False):
            self.files = expected_content.RestartFiles('19950811', '19981101',
                                                       'PREFIX', model, naml)

    def tearDown(self):
        pass

    def test_restart_files_instance(self):
        ''' Assert successful instantiation of a RestartFiles object '''
        func.logtest('Assert successful instantiation of RestartFiles:')
        self.assertListEqual(self.files.timestamps,
                             [[3, 1], [6, 1], [9, 1], [12, 1]])
        self.assertListEqual(self.files.rst_types, ['model_rst'])
        self.assertIsNone(self.files.naml.streams_1d)

    def test_rst_archive_10d_delay(self):
        ''' Assert correct addition of delay to start date for dump archive '''
        func.logtest('Assert delay to dump archive - 10days:')
        self.assertEqual(self.files.sdate, [1995, 8, 21, 0, 0])

    def test_rst_archive_6m_delay(self):
        ''' Assert correct addition of delay to start date for dump archive '''
        func.logtest('Assert delay to dump archive - 6months:')
        self.assertEqual(self.files.sdate, [1996, 2, 11, 0, 0])

    def test_timestamps(self):
        ''' Assert correct return of timestamps to archive '''
        func.logtest('Assert return of list of archiving timestamps:')
        self.files.naml.mean_reference_date = '20000515'
        self.files.naml.archive_timestamps = 'Monthly'
        self.assertListEqual(self.files._timestamps(),
                             [[1, 15], [2, 15], [3, 15], [4, 15], [5, 15],
                              [6, 15], [7, 15], [8, 15], [9, 15], [10, 15],
                              [11, 15], [12, 15]])
        self.files.naml.archive_timestamps = 'Seasonal'
        self.assertListEqual(self.files._timestamps(),
                             [[2, 15], [5, 15], [8, 15], [11, 15]])
        self.files.naml.archive_timestamps = 'Biannual'
        self.assertListEqual(self.files._timestamps(), [[5, 15], [11, 15]])
        self.files.naml.archive_timestamps = 'Annual'
        self.assertListEqual(self.files._timestamps(), [[5, 15]])
        self.files.naml.archive_timestamps = '03-12'
        self.assertListEqual(self.files._timestamps(), [[3, 12]])

    def test_timestamps_fail(self):
        ''' Test failure mode of timestamps method '''
        func.logtest('Assert handling of incorrect timestamp namelist format:')
        self.files.naml.archive_timestamps = 'garbage'
        with self.assertRaises(SystemExit):
            _ = self.files._timestamps()
        self.assertIn('Format for archive_timestamps should be',
                      func.capture('err'))

    def test_expected_atmos_dumps(self):
        ''' Test calculation of expected restart files '''
        func.logtest('Assert list of archived atmos dumps:')
        # Default setting is seasonal archive
        expect = ['PREFIXa.da19950901_00', 'PREFIXa.da19951201_00',
                  'PREFIXa.da19960301_00', 'PREFIXa.da19960601_00',
                  'PREFIXa.da19960901_00', 'PREFIXa.da19961201_00',
                  'PREFIXa.da19970301_00', 'PREFIXa.da19970601_00',
                  'PREFIXa.da19970901_00', 'PREFIXa.da19971201_00',
                  'PREFIXa.da19980301_00', 'PREFIXa.da19980601_00',
                  'PREFIXa.da19980901_00', 'PREFIXa.da19981101_00']
        self.assertListEqual(self.files.expected_files()['ada.file'],
                             expect[:-1])
        self.assertListEqual(self.files.expected_files().keys(), ['ada.file'])

        self.files.finalcycle = True
        self.assertListEqual(self.files.expected_files()['ada.file'], expect)

        self.files.edate = [1998, 9, 1]
        self.assertListEqual(self.files.expected_files()['ada.file'],
                             expect[:-1])


    def test_expected_atmos_nodumps(self):
        ''' Test calculation of expected restart files - none in period'''
        func.logtest('Assert list of archived atmos dumps - none:')
        self.files.sdate = [1995, 12, 1]
        self.files.edate = [1995, 3, 1]
        self.assertEqual(self.files.expected_files(), {})

    def test_expected_atmos_oneyear(self):
        ''' Test calculation of expected restart files - none in period'''
        func.logtest('Assert list of archived atmos dumps - none:')
        self.files.sdate = [1995, 1, 1]
        self.files.edate = [1995, 12, 1]
        self.assertEqual(self.files.expected_files(),
                         {'ada.file': ['PREFIXa.da19950301_00',
                                       'PREFIXa.da19950601_00',
                                       'PREFIXa.da19950901_00']})

    def test_expected_nemo_dumps(self):
        ''' Test calculation of expected nemo restart files '''
        func.logtest('Assert list of archived nemo dumps:')
        # Default setting is bi-annual archive
        expect = ['PREFIXo_19951201_restart.nc',
                  'PREFIXo_19960601_restart.nc',
                  'PREFIXo_19961201_restart.nc',
                  'PREFIXo_19970601_restart.nc',
                  'PREFIXo_19971201_restart.nc',
                  'PREFIXo_19980601_restart.nc',
                  'PREFIXo_19981101_restart.nc']
        self.assertListEqual(self.files.expected_files()['oda.file'],
                             expect[:-1])

        self.files.finalcycle = True
        self.assertListEqual(self.files.expected_files()['oda.file'], expect)
        self.assertListEqual(self.files.expected_files().keys(), ['oda.file'])

    @mock.patch('utils.cyclestring',
                return_value=['1998', '06', '21', '00', '00'])
    def test_expected_nemo_dumps_buffer(self, mock_ctime):
        ''' Test calculation of expected nemo restart files buffer=3'''
        func.logtest('Assert list of archived nemo dumps - buffered:')
        # Default setting is bi-annual archive
        self.files.edate = [1998, 7, 1]
        expect = ['PREFIXo_19951201_restart.nc',
                  'PREFIXo_19960601_restart.nc',
                  'PREFIXo_19961201_restart.nc',
                  'PREFIXo_19970601_restart.nc',
                  'PREFIXo_19971201_restart.nc',
                  'PREFIXo_19980601_restart.nc',
                  'PREFIXo_19980701_restart.nc']
        self.files.naml.buffer_restart = 4 # 40 days
        files_returned = self.files.expected_files()['oda.file']
        self.assertListEqual(files_returned, expect[:-2])
        mock_ctime.assert_called_once_with()

        self.files.finalcycle = True
        dict_returned = self.files.expected_files()
        self.assertListEqual(dict_returned['oda.file'], expect)
        self.assertListEqual(dict_returned.keys(), ['oda.file'])

    def test_expected_nemo_olddumps(self):
        ''' Test calculation of expected nemo restarts with 3.1 datestamp'''
        func.logtest('Assert list of archived nemo with 3.1 datestamp dumps:')
        self.files.timestamps = [[5, 30], [11, 30]]
        expect = ['PREFIXo_19951130_restart.nc',
                  'PREFIXo_19960530_restart.nc',
                  'PREFIXo_19961130_restart.nc',
                  'PREFIXo_19970530_restart.nc',
                  'PREFIXo_19971130_restart.nc',
                  'PREFIXo_19980530_restart.nc',
                  'PREFIXo_19981030_restart.nc']
        self.assertListEqual(self.files.expected_files()['oda.file'],
                             expect[:-1])

        self.files.finalcycle = True
        self.assertListEqual(self.files.expected_files()['oda.file'], expect)
        self.assertListEqual(self.files.expected_files().keys(), ['oda.file'])

    def test_expected_cice_dumps(self):
        ''' Test calculation of expected cice restart files '''
        func.logtest('Assert list of archived cice dumps:')
        self.files.timestamps = [[3, 1]]
        expect = ['PREFIXi.restart.1996-03-01-00000.nc',
                  'PREFIXi.restart.age.1996-03-01-00000.nc',
                  'PREFIXi.restart.1997-03-01-00000.nc',
                  'PREFIXi.restart.age.1997-03-01-00000.nc',
                  'PREFIXi.restart.1998-03-01-00000.nc',
                  'PREFIXi.restart.age.1998-03-01-00000.nc',
                  'PREFIXi.restart.1998-11-01-00000.nc',
                  'PREFIXi.restart.age.1998-11-01-00000.nc']
        self.assertListEqual(self.files.expected_files()['ida.file'],
                             expect[:-2])

        self.files.finalcycle = True
        self.assertListEqual(self.files.expected_files()['ida.file'], expect)
        self.assertListEqual(self.files.expected_files().keys(), ['ida.file'])

    @mock.patch('utils.cyclestring',
                return_value=['1998', '10', '01', '00', '00'])
    def test_expected_cice_dumps_buffer(self, mock_ctime):
        ''' Test calculation of expected cice restart files - buffer=2'''
        func.logtest('Assert list of archived cice dumps - buffered:')
        self.files.timestamps = [[3, 1]]
        expect = ['PREFIXi.restart.1996-03-01-00000.nc',
                  'PREFIXi.restart.age.1996-03-01-00000.nc',
                  'PREFIXi.restart.1997-03-01-00000.nc',
                  'PREFIXi.restart.age.1997-03-01-00000.nc',
                  'PREFIXi.restart.1998-03-01-00000.nc',
                  'PREFIXi.restart.age.1998-03-01-00000.nc',
                  'PREFIXi.restart.1998-11-01-00000.nc',
                  'PREFIXi.restart.age.1998-11-01-00000.nc']
        self.files.naml.buffer_restart = 9 # 9*1m --> effective edate=1998,3,1
        self.assertListEqual(self.files.expected_files()['ida.file'],
                             expect[:-4])

        self.files.finalcycle = True
        self.assertListEqual(self.files.expected_files()['ida.file'], expect)
        mock_ctime.assert_called_once_with()

    def test_expected_cice_dumps_suffix(self):
        ''' Test calculation of expected cice restarts - with suffix'''
        func.logtest('Assert list of archived cice dumps - with suffix:')
        self.files.timestamps = [[3, 1]]
        self.files.naml.restart_suffix = '*blue'
        expect = ['PREFIXi.restart.1996-03-01-00000*blue',
                  'PREFIXi.restart.age.1996-03-01-00000*blue',
                  'PREFIXi.restart.1997-03-01-00000*blue',
                  'PREFIXi.restart.age.1997-03-01-00000*blue',
                  'PREFIXi.restart.1998-03-01-00000*blue',
                  'PREFIXi.restart.age.1998-03-01-00000*blue']
        self.assertListEqual(self.files.expected_files()['ida.file'], expect)
        self.assertListEqual(self.files.expected_files().keys(), ['ida.file'])


class DiagnosticFilesTests(unittest.TestCase):
    ''' Unit tests relating to the DiagnosticFiles (child) class methods '''
    def setUp(self):
        model = 'model'
        naml = verify_namelist.AtmosVerify()
        if 'atmos' in self.id():
            model = 'atmos'
        elif 'nemo' in self.id():
            model = 'nemo'
            naml = verify_namelist.NemoVerify()
        elif 'cice' in self.id():
            model = 'cice'
            naml = verify_namelist.CiceVerify()
            naml.cice_age_rst = True
        with mock.patch('utils.finalcycle', return_value=False):
            self.files = expected_content.DiagnosticFiles(
                '19950811', '19981101', 'PREFIX', model, naml
                )

    def tearDown(self):
        pass

    def test_diagnostic_files_instance(self):
        '''Assert correct attributes of the ArchivedFiles instance'''
        func.logtest('Assert correct attributes for ArchivedFiles instance:')
        # Default namelist is AtmosVerify
        self.assertListEqual(self.files.meanref, [1000, 12, 1])
        self.assertListEqual(self.files.fields, [''])
        self.assertEqual(self.files.tlim, {})

    def test_reinit_generator_atmos(self):
        ''' Test performance of the reinit periods generator - atmos'''
        func.logtest('Test performance of the reinit periods generator:')
        yield_rtn = []
        self.files.naml.streams_1d = []
        self.files.naml.streams_2d = ''
        self.files.naml.streams_90d = 'a'
        for rval in self.files.gen_reinit_period(['m', '2s', 'y', 'streams_1d',
                                                  'streams_2d', 'streams_10d',
                                                  'streams_90d']):
            yield_rtn.append(rval)
        self.assertListEqual(yield_rtn, [(1, 'm', 1, ['m'], 'mean'),
                                         (2, 's', 1, ['s'], 'mean'),
                                         (1, 'y', 1, ['y'], 'mean'),
                                         (90, 'd', 1, ['a'], 'instantaneous')])

    def test_reinit_generator_nemo(self):
        ''' Test performance of the reinit periods generator - nemo '''
        func.logtest('Test performance of the reinit periods generator:')
        yield_rtn = []
        for rval in self.files.gen_reinit_period(['m', '2s', 'y']):
            yield_rtn.append(rval)
        self.assertListEqual(yield_rtn,
                             [(1, 'm', 1, self.files.naml.fields, 'mean'),
                              (2, 's', 1, self.files.naml.fields, 'mean'),
                              (1, 'y', 1, self.files.naml.fields, 'mean')])
        self.assertListEqual(self.files.naml.fields,
                             verify_namelist.NemoVerify().fields)

    def test_reinit_generator_cice(self):
        ''' Test performance of the reinit periods generator - nemo '''
        func.logtest('Test performance of the reinit periods generator:')
        yield_rtn = []
        for rval in self.files.gen_reinit_period(['m', '2s', 'y']):
            yield_rtn.append(rval)
        self.assertListEqual(yield_rtn,
                             [(1, 'm', 1, [''], 'mean'),
                              (2, 's', 1, [''], 'mean'),
                              (1, 'y', 1, [''], 'mean')])

    def test_get_period_startdate(self):
        ''' Assert return of adjusted startdate for a given period '''
        func.logtest('Assert return of adjusted startdate for a given period:')
        # start: 19950811, meanref: 10001201
        self.assertListEqual(self.files.get_period_startdate('h'),
                             [1995, 8, 11, 0, 0])
        self.assertListEqual(self.files.get_period_startdate('d'),
                             [1995, 8, 11, 0, 0])
        self.assertListEqual(self.files.get_period_startdate('m'),
                             [1995, 9, 1, 0, 0])
        self.assertListEqual(self.files.get_period_startdate('s'),
                             [1995, 9, 1, 0, 0])
        self.assertListEqual(self.files.get_period_startdate('y'),
                             [1995, 12, 1, 0, 0])
        self.assertListEqual(self.files.get_period_startdate('x'),
                             [2000, 12, 1, 0, 0])

        # Alternative dates
        self.files.sdate = [1995, 12, 11]
        self.files.meanref = [1990, 1, 15]
        self.assertListEqual(self.files.get_period_startdate('h'),
                             [1995, 12, 11, 0, 0])
        self.assertListEqual(self.files.get_period_startdate('d'),
                             [1995, 12, 11, 0, 0])
        self.assertListEqual(self.files.get_period_startdate('m'),
                             [1995, 12, 15, 0, 0])
        self.assertListEqual(self.files.get_period_startdate('m', refday=False),
                             [1995, 12, 11, 0, 0])
        self.assertListEqual(self.files.get_period_startdate('s'),
                             [1996, 1, 15, 0, 0])
        self.assertListEqual(self.files.get_period_startdate('y'),
                             [1996, 1, 15, 0, 0])
        self.assertListEqual(self.files.get_period_startdate('x'),
                             [2000, 1, 15, 0, 0])

    def test_timelimited_single(self):
        ''' Assert time limited streams - single stream '''
        func.logtest('Assert return time limited stream dictionary (single):')
        self.files.naml.timelimitedstreams = True
        self.files.naml.tlim_streams = 'x'
        self.files.naml.tlim_starts = '19900201'
        self.files.naml.tlim_ends = '19900801'
        timlim = self.files.time_limited_streams()

        self.assertTupleEqual(timlim['x'], ([1990, 2, 1], [1990, 8, 1]))
        self.assertListEqual(timlim.keys(), ['x'])

    def test_timelimited_multi(self):
        ''' Assert time limited streams - multi stream '''
        func.logtest('Assert return time limited stream dictionary (multi):')
        self.files.naml.timelimitedstreams = True
        self.files.naml.tlim_streams = ['x', 'y', 'z']
        self.files.naml.tlim_starts = ['19900201', '19950101', '20001230']
        self.files.naml.tlim_ends = ['19900801', '19951201', '20011230']
        timlim = self.files.time_limited_streams()

        self.assertTupleEqual(timlim['x'], ([1990, 2, 1], [1990, 8, 1]))
        self.assertTupleEqual(timlim['y'], ([1995, 1, 1], [1995, 12, 1]))
        self.assertTupleEqual(timlim['z'], ([2000, 12, 30], [2001, 12, 30]))
        self.assertListEqual(sorted(timlim.keys()), sorted(['x', 'y', 'z']))

    def test_timelimited_none(self):
        ''' Assert time-limited streams - none '''
        func.logtest('Assert return time limited stream dictionary (none):')
        self.files.naml.timelimitedstreams = True
        self.files.naml.tlim_streams = None
        timlim = self.files.time_limited_streams()
        self.assertEqual(timlim, {})

        self.files.naml.tlim_streams = []
        timlim = self.files.time_limited_streams()
        self.assertEqual(timlim, {})

    def test_timelimited_fail(self):
        ''' Assert time limited streams - fail '''
        func.logtest('Assert return time limited stream dictionary (fail):')
        self.files.naml.timelimitedstreams = True
        self.files.naml.tlim_streams = ['x', 'y', 'z']
        self.files.naml.tlim_starts = ['19900201', '19950101']
        self.files.naml.tlim_ends = None
        with self.assertRaises(SystemExit):
            _ = self.files.time_limited_streams()
        self.assertIn('dates are provided for each time', func.capture('err'))

    def test_nemo_iberg_traj(self):
        ''' Assert return of dictionary containing iberg trajectory files '''
        func.logtest('Assert return of iberg trajectory dictionary:')
        self.files.edate = [1995, 11, 1]
        # startdate=19950811 --> total length=80 days (8 files produced)
        self.files.naml.iberg_traj = True
        self.files.naml.iberg_traj_tstamp = 'Timestep'
        ibergs = self.files.iceberg_trajectory()
        outlist = ['PREFIXo_trajectory_icebergs_000720.nc',
                   'PREFIXo_trajectory_icebergs_001440.nc', # To 19950901
                   'PREFIXo_trajectory_icebergs_002160.nc',
                   'PREFIXo_trajectory_icebergs_002880.nc',
                   'PREFIXo_trajectory_icebergs_003600.nc', # To 19951001
                   'PREFIXo_trajectory_icebergs_004320.nc',
                   'PREFIXo_trajectory_icebergs_005040.nc',
                   'PREFIXo_trajectory_icebergs_005760.nc'] # To 19951101
        self.assertEqual(ibergs, {'oni.nc.file': outlist})

    def test_nemo_iberg_traj_30days(self):
        ''' Assert return of dictionary containing iberg trajectory files '''
        func.logtest('Assert return of iberg trajectory dictionary:')
        self.files.edate = [1995, 11, 1]
        # startdate=19950811 --> total length=80 days (2 files produced)
        self.files.naml.iberg_traj = True
        self.files.naml.iberg_traj_tstamp = 'Timestep'
        self.files.naml.iberg_traj_freq = '30d'
        self.files.naml.iberg_traj_ts_per_day = 100
        ibergs = self.files.iceberg_trajectory()
        outlist = ['PREFIXo_trajectory_icebergs_003000.nc', # To 19950911
                   'PREFIXo_trajectory_icebergs_006000.nc'] # To 19951011
        self.assertEqual(ibergs, {'oni.nc.file': outlist})

    def test_nemo_iberg_traj_cal_fail(self):
        ''' Assert return of dictionary containing iberg trajectory files '''
        func.logtest('Assert failure mode with non-360day calendar:')
        self.files.edate = [1995, 11, 1]
        self.files.naml.iberg_traj = True
        self.files.naml.iberg_traj_tstamp = 'Timestep'
        self.files.naml.iberg_traj_freq = '1m'
        with mock.patch('expected_content.utils.calendar',
                        return_value='SomeCalendar'):
            with self.assertRaises(SystemExit):
                _ = self.files.iceberg_trajectory()
        self.assertIn('only be determined with frequency 1m',
                      func.capture('err'))
        self.assertIn('Please use hours or days', func.capture('err'))

    def test_nemo_iberg_traj_datestamp(self):
        ''' Assert return of dictionary containing iberg trajectory files '''
        func.logtest('Assert return of datestamped iberg trajectory files:')
        self.files.edate = [1995, 11, 1]
        # startdate=19950811 --> total length=80 days (2 files produced)
        self.files.naml.iberg_traj = True
        self.files.naml.iberg_traj_tstamp = 'YYYYMMDD'
        self.files.naml.iberg_traj_freq = '30d'
        ibergs = self.files.iceberg_trajectory()
        outlist = ['PREFIXo_trajectory_icebergs_19950811-19950911.nc',
                   'PREFIXo_trajectory_icebergs_19950911-19951011.nc']
        self.assertEqual(ibergs, {'oni.nc.file': outlist})

    def test_nemo_iberg_traj_off(self):
        ''' Assert return of dictionary containing iberg trajectory files '''
        func.logtest('Assert return of iberg trajectory dictionary (no files):')
        # Default setting: naml.iberg_traj=False
        self.assertEqual(self.files.iceberg_trajectory(), {'oni.nc.file': []})

    def test_rm_component_above_day(self):
        ''' Assert correct removal of higher mean components (day) '''
        func.logtest('Assert correct removal of higher mean components:')
        infiles = ['file_19900101-19900111.nc', 'file_19900111-19900121.nc',
                   'file_19900121-19900201.nc', 'file_19900201-19900211.nc',
                   'file_19900211-19900221.nc']

        self.files.meanref = [1000, 12, 1]
        outfiles = self.files.remove_higher_mean_components(infiles[:], 'd')
        self.assertListEqual(outfiles, infiles[:-2])

        self.files.meanref = [1000, 5, 21]
        outfiles = self.files.remove_higher_mean_components(infiles[:], 'd')
        self.assertListEqual(outfiles, infiles)

    def test_rm_component_above_season(self):
        ''' Assert correct removal of higher mean components (season) '''
        func.logtest('Assert correct removal of higher mean components:')
        infiles = ['file_19900301-19900601.nc', 'file_19900601-19900901.nc',
                   'file_19900901-19901201.nc', 'file_19901201-19910301.nc',
                   'file_19910301-19910601.nc']

        self.files.meanref = [1000, 12, 1]
        outfiles = self.files.remove_higher_mean_components(infiles[:], 's')
        self.assertListEqual(outfiles, infiles[:-2])

        self.files.meanref = [1000, 6, 1]
        outfiles = self.files.remove_higher_mean_components(infiles[:], 's')
        self.assertListEqual(outfiles, infiles)

    def test_rm_component_ds_only(self):
        ''' Assert correct removal of higher mean components (d,s only) '''
        func.logtest('Assert correct removal of higher mean components:')
        dfiles = ['file_19900101-19900111.nc', 'file_19900111-19900121.nc',
                  'file_19900121-19900201.nc', 'file_19900201-19900211.nc',
                  'file_19900211-19900221.nc', 'file_19900221-19900301.nc',
                  'file_19900301-19900311.nc', 'file_19900311-19900321.nc',
                  'file_19900321-19900401.nc', 'file_19900201-19900411.nc',
                  'file_19900411-19900421.nc', 'file_19900421-19900501.nc']
        sfiles = ['file_19900301-19900601.nc', 'file_19900601-19900901.nc',
                  'file_19900901-19901201.nc', 'file_19901201-19910301.nc',
                  'file_19910301-19910601.nc', 'file_19910601-19910901.nc']

        self.files.meanref = [1000, 12, 1]
        self.files.naml.meanstreams = ['10d', '1s']
        # Monthly mean is missing. Shift output condition for daily files
        outfiles = self.files.remove_higher_mean_components(dfiles[:], 'd')
        self.assertListEqual(outfiles, dfiles[:-6])

        # Seasonal mean is the top mean - all files archived
        outfiles = self.files.remove_higher_mean_components(sfiles[:], 's')
        self.assertListEqual(outfiles, sfiles)

    def test_expected_atmos(self):
        ''' Assert correct list of expected atmos files '''
        func.logtest('Assert correct return of atmos files:')
        # startdate: 19950811, enddate: 19981101
        outfiles = {
            'apy.pp': ['PREFIXa.py19961201.pp', 'PREFIXa.py19971201.pp'],
            'aps.pp': ['PREFIXa.ps1995son.pp', 'PREFIXa.ps1996djf.pp',
                       'PREFIXa.ps1996mam.pp', 'PREFIXa.ps1996jja.pp',
                       'PREFIXa.ps1996son.pp', 'PREFIXa.ps1997djf.pp',
                       'PREFIXa.ps1997mam.pp', 'PREFIXa.ps1997jja.pp',
                       'PREFIXa.ps1997son.pp', 'PREFIXa.ps1998djf.pp',
                       'PREFIXa.ps1998mam.pp', 'PREFIXa.ps1998jja.pp'],
            'apm.pp': ['PREFIXa.pm1995sep.pp', 'PREFIXa.pm1995oct.pp',
                       'PREFIXa.pm1998sep.pp', 'PREFIXa.pm1998oct.pp']
            }
        expected = self.files.expected_diags()
        self.assertListEqual(expected['apy.pp'], outfiles['apy.pp'])
        self.assertListEqual(expected['aps.pp'], outfiles['aps.pp'])
        self.assertListEqual(expected['apm.pp'][:2], outfiles['apm.pp'][:2])
        self.assertListEqual(expected['apm.pp'][-2:], outfiles['apm.pp'][-2:])
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_atmos_altdates(self):
        ''' Assert correct list of expected atmos files - alternative dates'''
        func.logtest('Assert correct return of atmos files - alt. dates:')
        self.files.meanref = [1992, 2, 1]
        self.files.edate = [2015, 11, 1]
        outfiles = {
            'apx.pp': ['PREFIXa.px20120201.pp'],
            'apy.pp': ['PREFIXa.py19970201.pp', 'PREFIXa.py19980201.pp',
                       'PREFIXa.py20140201.pp', 'PREFIXa.py20150201.pp'],
            'aps.pp': ['PREFIXa.ps1996ndj.pp', 'PREFIXa.ps1996fma.pp',
                       'PREFIXa.ps2015mjj.pp', 'PREFIXa.ps2015aso.pp'],
            'apm.pp': ['PREFIXa.pm1995sep.pp', 'PREFIXa.pm1995oct.pp',
                       'PREFIXa.pm2015sep.pp', 'PREFIXa.pm2015oct.pp']
            }
        expected = self.files.expected_diags()
        self.assertListEqual(expected['apx.pp'], outfiles['apx.pp'])
        self.assertListEqual(expected['apy.pp'][:2], outfiles['apy.pp'][:2])
        self.assertListEqual(expected['apy.pp'][-2:], outfiles['apy.pp'][-2:])
        self.assertListEqual(expected['aps.pp'][:2], outfiles['aps.pp'][:2])
        self.assertListEqual(expected['aps.pp'][-2:], outfiles['aps.pp'][-2:])
        self.assertListEqual(expected['apm.pp'][:2], outfiles['apm.pp'][:2])
        self.assertListEqual(expected['apm.pp'][-2:], outfiles['apm.pp'][-2:])
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_atmos_ppff(self):
        ''' Assert correct list of expected files - pp and f files'''
        func.logtest('Assert correct return of atmos files - pp & f files:')
        self.files.naml.meanstreams = '1x'
        self.files.naml.ff_streams = 'a'
        self.files.naml.streams_90d = ['a', 'b']
        self.files.naml.streams_30d = 1
        self.files.naml.streams_1d = ''
        self.files.naml.streams_10h = 'd'
        self.files.naml.spawn_netcdf_streams = 'b'

        outfiles = {
            'apa.file': ['PREFIXa.pa19950811', 'PREFIXa.pa19951111',
                         'PREFIXa.pa19980211', 'PREFIXa.pa19980511'],
            'apb.pp': ['PREFIXa.pb19950811.pp', 'PREFIXa.pb19951111.pp',
                       'PREFIXa.pb19980211.pp', 'PREFIXa.pb19980511.pp'],
            'ap1.pp': ['PREFIXa.p11995aug.pp', 'PREFIXa.p11995sep.pp',
                       'PREFIXa.p11998aug.pp', 'PREFIXa.p11998sep.pp'],
            'apd.pp': ['PREFIXa.pd19950811_00.pp', 'PREFIXa.pd19950811_10.pp',
                       'PREFIXa.pd19981029_18.pp', 'PREFIXa.pd19981030_04.pp'],
            'anb.nc.file': [r'atmos_prefixa_\d+[hdmsyx]_19950811-19951111_'
                            r'[a-zA-Z0-9\-]*\.nc$',
                            r'atmos_prefixa_\d+[hdmsyx]_19951111-19960211_'
                            r'[a-zA-Z0-9\-]*\.nc$',
                            r'atmos_prefixa_\d+[hdmsyx]_19980211-19980511_'
                            r'[a-zA-Z0-9\-]*\.nc$',
                            r'atmos_prefixa_\d+[hdmsyx]_19980511-19980811_'
                            r'[a-zA-Z0-9\-]*\.nc$']
            }
        expected = self.files.expected_diags()
        for key in outfiles:
            self.assertListEqual(expected[key][:2], outfiles[key][:2])
            self.assertListEqual(expected[key][-2:], outfiles[key][-2:])
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_atmos_final(self):
        ''' Assert correct list of expected files - atmos finalcycle'''
        func.logtest('Assert correct return of atmos files - finalcycle:')
        self.files.naml.streams_90d = 'a'
        self.files.naml.streams_10h = ['d', 'e']
        self.files.tlim = {'e': ([1997, 1, 1], [1998, 1, 2])}
        self.files.finalcycle = True
        lastout = {
            'apa.pp': 'PREFIXa.pa19980811.pp',
            'apd.pp': 'PREFIXa.pd19981030_14.pp',
            'ape.pp': 'PREFIXa.pe19980101_20.pp',
            'apm.pp': 'PREFIXa.pm1998oct.pp',
            'aps.pp': 'PREFIXa.ps1998jja.pp',
            'apy.pp': 'PREFIXa.py19971201.pp',
            }

        expected = self.files.expected_diags()
        for key in lastout:
            self.assertEqual(expected[key][-1], lastout[key])
        self.assertListEqual(sorted(expected.keys()), sorted(lastout.keys()))

    def test_expected_nemo(self):
        ''' Assert correct list of expected nemo files'''
        func.logtest('Assert correct return of expected nemo files:')
        self.files.fields = ['grid-W', 'diad-T']
        self.files.edate = [1996, 1, 1]
        outfiles = {
            'onm.nc.file': ['nemo_prefixo_1m_19950901-19951001_grid-W.nc',
                            'medusa_prefixo_1m_19950901-19951001_diad-T.nc',
                            'nemo_prefixo_1m_19951001-19951101_grid-W.nc',
                            'medusa_prefixo_1m_19951001-19951101_diad-T.nc',
                            'nemo_prefixo_1m_19951101-19951201_grid-W.nc',
                            'medusa_prefixo_1m_19951101-19951201_diad-T.nc',
                            'nemo_prefixo_1m_19951201-19960101_grid-W.nc',
                            'medusa_prefixo_1m_19951201-19960101_diad-T.nc'],
            'ons.nc.file': ['nemo_prefixo_1s_19950901-19951201_grid-W.nc',
                            'medusa_prefixo_1s_19950901-19951201_diad-T.nc']
            }
        expected = self.files.expected_diags()
        self.assertListEqual(expected['onm.nc.file'],
                             outfiles['onm.nc.file'][:-2])
        self.assertListEqual(expected['ons.nc.file'], outfiles['ons.nc.file'])

        self.files.finalcycle = True
        expected = self.files.expected_diags()
        for key in outfiles:
            self.assertListEqual(expected[key], outfiles[key])

        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_nemo_topmean(self):
        ''' Assert correct list of expected nemo files - topmean = 1s'''
        func.logtest('Assert correct return of expected nemo files - top=1s:')
        self.files.naml.meanstreams = '1s'
        self.files.fields = ['grid-W', 'diad-T']
        self.files.edate = [1996, 3, 1]
        outfiles = {
            'ons.nc.file': ['nemo_prefixo_1s_19950901-19951201_grid-W.nc',
                            'medusa_prefixo_1s_19950901-19951201_diad-T.nc',
                            'nemo_prefixo_1s_19951201-19960301_grid-W.nc',
                            'medusa_prefixo_1s_19951201-19960301_diad-T.nc']
            }
        expected = self.files.expected_diags()
        self.assertListEqual(expected['ons.nc.file'], outfiles['ons.nc.file'])

        self.files.finalcycle = True
        expected = self.files.expected_diags()
        for key in outfiles:
            self.assertListEqual(expected[key], outfiles[key])

        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_nemo_buffer(self):
        ''' Assert correct list of expected nemo files - buffered'''
        func.logtest('Assert correct return of expected nemo files buffer=2:')
        self.files.naml.meanstreams = '1m'
        self.files.fields = ['grid-W', 'diad-T']
        self.files.edate = [1996, 2, 1]
        outfiles = {
            'onm.nc.file': ['nemo_prefixo_1m_19950901-19951001_grid-W.nc',
                            'medusa_prefixo_1m_19950901-19951001_diad-T.nc',
                            'nemo_prefixo_1m_19951001-19951101_grid-W.nc',
                            'medusa_prefixo_1m_19951001-19951101_diad-T.nc',
                            'nemo_prefixo_1m_19951101-19951201_grid-W.nc',
                            'medusa_prefixo_1m_19951101-19951201_diad-T.nc',
                            'nemo_prefixo_1m_19951201-19960101_grid-W.nc',
                            'medusa_prefixo_1m_19951201-19960101_diad-T.nc',
                            'nemo_prefixo_1m_19960101-19960201_grid-W.nc',
                            'medusa_prefixo_1m_19960101-19960201_diad-T.nc']
            }
        # Default base_mean=10d
        self.files.naml.buffer_mean = 4
        expected = self.files.expected_diags()
        for key in outfiles:
            self.assertListEqual(expected[key], outfiles[key][:-4])

        self.files.finalcycle = True
        expected = self.files.expected_diags()
        for key in outfiles:
            self.assertListEqual(expected[key], outfiles[key])

    def test_expected_cice_final(self):
        ''' Assert correct list of expected cice files'''
        func.logtest('Assert correct return of expected cice files:')
        self.files.naml.meanstreams = ['1s', '1y']
        self.files.finalcycle = True
        outfiles = {
            'ins.nc.file': ['cice_prefixi_1s_19950901-19951201.nc',
                            'cice_prefixi_1s_19951201-19960301.nc',
                            'cice_prefixi_1s_19980301-19980601.nc',
                            'cice_prefixi_1s_19980601-19980901.nc'],
            'iny.nc.file': ['cice_prefixi_1y_19951201-19961201.nc',
                            'cice_prefixi_1y_19961201-19971201.nc',],
            }
        expected = self.files.expected_diags()
        for key in outfiles:
            self.assertListEqual(expected[key][:2], outfiles[key][:2])
            self.assertListEqual(expected[key][-2:], outfiles[key][-2:])
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))


    def test_expected_cice_concat_means(self):
        ''' Assert correct list of expected cice files - concatenated means'''
        func.logtest('Assert correct return of expected cice concat means:')
        self.files.naml.meanstreams = ['1d_30']
        self.files.sdate = [1995, 9, 1]
        self.files.finalcycle = True
        outfiles = {
            'ind.nc.file': ['cice_prefixi_1d_19950901-19951001.nc',
                            'cice_prefixi_1d_19951001-19951101.nc',
                            'cice_prefixi_1d_19980901-19981001.nc',
                            'cice_prefixi_1d_19981001-19981101.nc'],
            }
        expected = self.files.expected_diags()
        for key in outfiles:
            self.assertListEqual(expected[key][:2], outfiles[key][:2])
            self.assertListEqual(expected[key][-2:], outfiles[key][-2:])
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))
