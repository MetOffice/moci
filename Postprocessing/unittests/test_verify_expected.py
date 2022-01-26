#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016-2022 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''
import unittest
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
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
        self.assertIn('my date should consist of 8-10 digits: "00YY1111"',
                      func.capture('err'))


class ArchivedFilesTests(unittest.TestCase):
    ''' Unit tests relating to the ArchivedFiles (parent) class methods '''
    def setUp(self):
        with mock.patch('expected_content.utils.finalcycle',
                        return_value=False):
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

    def test_extract_start_date_atmos(self):
        '''Assert correct extraction of date from various filenames '''
        func.logtest('Assert correct extraction of date - atmos')
        self.assertListEqual(self.files.extract_date('runida.pa1988jan'),
                             [1988, 1, 1])
        self.assertListEqual(self.files.extract_date('runida.pa1988djf'),
                             [1987, 12, 1])
        self.assertListEqual(self.files.extract_date('runida.pa1988mam'),
                             [1988, 3, 1])

        self.assertListEqual(self.files.extract_date('runida.pb19880115'),
                             [1988, 1, 15])
        self.assertListEqual(self.files.extract_date('runida.da19880115_12'),
                             [1988, 1, 15, 12])

    def test_extract_start_date_ncf(self):
        '''Assert correct extraction of date from various filenames '''
        func.logtest('Assert correct extraction of date - NetCDF')
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
            self.files.extract_date('si3_runidi_1s_198812-198903_grid.nc'),
            [1988, 12, 1]
            )
        self.assertListEqual(
            self.files.extract_date('nemo_runido_10d_19880115-19881115'
                                    '_grid.nc'), [1988, 1, 15]
            )
        self.assertListEqual(
            self.files.extract_date('cice_runidi_1d_1988011012-1988011112.nc'),
            [1988, 1, 10, 12]
            )

    def test_extract_end_date_atmos(self):
        '''Assert correct extraction of date from various filenames '''
        func.logtest('Assert correct extraction of date - atmos')
        self.assertListEqual(
            self.files.extract_date('runida.pa1988nov', start=False),
            [1988, 12, 1]
            )
        self.assertListEqual(
            self.files.extract_date('runida.pa1988dec', start=False),
            [1989, 1, 1]
            )
        self.assertListEqual(
            self.files.extract_date('runida.pa1988jan', start=False),
            [1988, 2, 1]
            )
        self.assertListEqual(
            self.files.extract_date('runida.pa1988son', start=False),
            [1988, 12, 1]
            )
        self.assertListEqual(
            self.files.extract_date('runida.pa1988ond', start=False),
            [1989, 1, 1]
            )
        self.assertListEqual(
            self.files.extract_date('runida.pa1988ndj', start=False),
            [1988, 2, 1]
            )

    def test_extract_end_date_ncf(self):
        '''Assert correct extraction of date from various filenames '''
        func.logtest('Assert correct extraction of date - ncf')
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

    def test_seasons(self):
        '''Assert return of available seasons'''
        func.logtest('Assert return of available seasons:')
        self.assertTupleEqual(expected_content.SEASONS,
                              ('djf', 'jfm', 'fma', 'mam', 'amj', 'mjj', 'jja',
                               'jas', 'aso', 'son', 'ond', 'ndj'))
        self.assertListEqual(expected_content.season_starts(12), [3, 6, 9, 12])
        self.assertListEqual(expected_content.season_starts(11), [2, 5, 8, 11])
        self.assertListEqual(expected_content.season_starts('1'), [1, 4, 7, 10])

    def test_filename_dict_atmos(self):
        '''Assert return of key, realm and component for atmosphere'''
        func.logtest('Assert successful return of atmos key and realm:')
        self.files.model = 'atmos'
        self.files.naml = verify_namelist.AtmosVerify()
        self.files.naml.ff_streams = []
        self.assertTupleEqual(self.files.get_fn_components('atmos_rst'),
                              ('rst', 'a', None))
        self.assertTupleEqual(self.files.get_fn_components('pk'),
                              ('atmos_pp', 'a', None))
        self.files.naml.ff_streams = 'mk'
        self.assertTupleEqual(self.files.get_fn_components('mk'),
                              ('atmos_ff', 'a', None))
        self.assertTupleEqual(self.files.get_fn_components(r'[a-zA-Z0-9\-]*'),
                              ('ncf_mean', 'a', 'atmos'))

    def test_filename_dict_nemocice(self):
        '''Assert return of key, realm and component for nemocice'''
        func.logtest('Assert return of nemocice key, realm and component:')
        self.files.model = 'nemo'
        self.files.naml = verify_namelist.NemoVerify()
        self.assertTupleEqual(self.files.get_fn_components('nemo_rst'),
                              ('rst', 'o', None))
        self.assertTupleEqual(self.files.get_fn_components('nemo_icebergs_rst'),
                              ('rst', 'o', None))
        self.assertTupleEqual(self.files.get_fn_components('nemo_ptracer_rst'),
                              ('rst', 'o', None))
        self.assertTupleEqual(self.files.get_fn_components('nemo_ice_rst'),
                              ('rst', 'i', None))
        self.assertTupleEqual(self.files.get_fn_components('grid-T'),
                              ('ncf_mean', 'o', 'nemo'))

        self.files.model = 'cice'
        self.assertTupleEqual(self.files.get_fn_components('cice_rst'),
                              ('rst', 'i', None))
        self.assertTupleEqual(self.files.get_fn_components('cice_age_rst'),
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
        self.assertEqual(self.files.get_collection(period='10d', stream='mk'),
                         'amk.pp')
        mock_cmp.return_value = ('atmos_ff', 'a', None)
        self.assertEqual(self.files.get_collection(stream='pk'), 'apk.file')
        mock_cmp.return_value = ('ncf_mean', 'a', 'atmos')
        self.assertEqual(self.files.get_collection(stream='mk'), 'ank.nc.file')

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
        mock_cmp.return_value = ('ncf_mean', 'i', 'si3')
        self.assertEqual(self.files.get_collection(period='1s', stream='grid'),
                         'ins.nc.file')

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
        mock_cmp.return_value = ('ncf_mean', 'i', 'cice')
        self.assertEqual(self.files.get_collection(period='1y', stream=''),
                         'iny.nc.file')

    def test_modify_atmos_namelist(self):
        '''Assert update to atmosphere streams list namelist items'''
        func.logtest('Assert updating of streams lists in  atmos namelist:')
        naml = verify_namelist.AtmosVerify()
        naml.streams_1d = 'a'
        naml.streams_2d = ['a', 'mb']
        naml.streams_90d = 'abc'
        naml.ff_streams = 1
        naml.spawn_netcdf_streams = ''
        with mock.patch('expected_content.utils.get_debugmode',
                        return_value=True):
            naml = expected_content.atmos_stream_items(naml)
        self.assertListEqual(naml.streams_1d, ['pa'])
        self.assertListEqual(naml.streams_2d, ['pa', 'mb'])
        self.assertListEqual(naml.streams_30d, [])
        self.assertListEqual(naml.streams_90d, ['abc'])
        self.assertListEqual(naml.spawn_netcdf_streams, [])
        self.assertListEqual(naml.ff_streams, ['p1'])
        self.assertIn('Unidentifiable atmosphere streamID "abc" in '
                      '&atmosverify/streams_90d', func.capture('err'))


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

        with mock.patch('expected_content.utils.finalcycle',
                        return_value=False):
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
        actual = self.files.expected_files()
        self.assertListEqual(actual['ada.file'], expect[:-1])
        self.assertListEqual(list(actual.keys()), ['ada.file'])

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
        actual = self.files.expected_files()
        self.assertListEqual(actual['oda.file'], expect)
        self.assertListEqual(list(actual.keys()), ['oda.file'])

    def test_expected_nemo_ice_dumps(self):
        ''' Test calculation of expected nemo ICE restart files '''
        func.logtest('Assert list of archived nemo ice dumps:')
        # Default setting is bi-annual archive
        self.files.rst_types.append('nemo_ice_rst')
        expect = sorted(['PREFIXo_19951201_restart_ice.nc',
                         'PREFIXo_19960601_restart_ice.nc',
                         'PREFIXo_19961201_restart_ice.nc',
                         'PREFIXo_19970601_restart_ice.nc',
                         'PREFIXo_19971201_restart_ice.nc',
                         'PREFIXo_19980601_restart_ice.nc'])
        actual = self.files.expected_files()
        self.assertListEqual(sorted(actual['ida.file']), expect)
        self.assertListEqual(sorted(actual.keys()), ['ida.file', 'oda.file'])

    def test_expected_nemo_dumps_buffer(self):
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
        self.files.naml.buffer_restart = 4  # 40 days

        with mock.patch('expected_content.utils.CylcCycle._cyclepoint',
                        return_value={'iso': '19980621T0000Z',
                                      'intlist':  [1998, 6, 21, 0, 0]}):
            files_returned = self.files.expected_files()['oda.file']
            self.assertListEqual(files_returned, expect[:-2])

            self.files.finalcycle = True
            dict_returned = self.files.expected_files()
            self.assertListEqual(dict_returned['oda.file'], expect)
            self.assertListEqual(list(dict_returned.keys()), ['oda.file'])

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
        actual_final = self.files.expected_files()
        self.assertListEqual(actual_final['oda.file'], expect)
        self.assertListEqual(list(actual_final.keys()), ['oda.file'])

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
        actual = self.files.expected_files()
        self.assertListEqual(actual['ida.file'], expect)
        self.assertListEqual(list(actual.keys()), ['ida.file'])

    def test_expected_cice_dumps_buffer(self):
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
        self.files.naml.buffer_restart = 9  # 9*1m --> effective edate=1998,3,1
        with mock.patch('expected_content.utils.CylcCycle._cyclepoint',
                        return_value={'iso': '19981001T0000Z',
                                      'intlist':  [1998, 10, 1, 0, 0]}):
            self.assertListEqual(self.files.expected_files()['ida.file'],
                                 expect[:-4])

            self.files.finalcycle = True
            self.assertListEqual(self.files.expected_files()['ida.file'],
                                 expect)

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

        actual = self.files.expected_files()
        self.assertListEqual(actual['ida.file'], expect)
        self.assertListEqual(list(actual.keys()), ['ida.file'])


class DiagnosticFilesTests(unittest.TestCase):
    ''' Unit tests relating to the DiagnosticFiles (child) class methods '''
    def setUp(self):
        model = 'model'
        naml = verify_namelist.AtmosVerify()
        if 'atmos' in self.id():
            model = 'atmos'
            naml.ff_streams = []
        elif 'nemo' in self.id():
            model = 'nemo'
            naml = verify_namelist.NemoVerify()
        elif 'cice' in self.id():
            model = 'cice'
            naml = verify_namelist.CiceVerify()
            naml.cice_age_rst = True
        with mock.patch('expected_content.utils.finalcycle',
                        return_value=False):
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
        self.assertListEqual(self.files.meanfields, [''])
        self.assertEqual(self.files.tlim, {})

    def test_reinit_generator_atmos(self):
        ''' Test performance of the reinit periods generator - atmos'''
        func.logtest('Test performance of the reinit periods generator:')
        yield_rtn = []
        self.files.naml.streams_1d = []
        self.files.naml.streams_2d = ''
        self.files.naml.streams_90d = ['ma']
        for rval in self.files.gen_reinit_period(['m', '2s', 'y', 'streams_1d',
                                                  'streams_2d', 'streams_10d',
                                                  'streams_90d']):
            yield_rtn.append(rval)
        self.assertListEqual(yield_rtn,
                             [('m', 'm', ['pm'], 'mean'),
                              ('2s', '2s', ['ps'], 'mean'),
                              ('y', 'y', ['py'], 'mean'),
                              ('90d', '90d', ['ma'], 'instantaneous')])

    def test_reinit_generator_nemo(self):
        ''' Test performance of the reinit periods generator - nemo '''
        func.logtest('Test performance of the reinit periods generator:')
        yield_rtn = []
        self.files.naml.meanstreams = ['1m', '1s', '1y']
        self.files.naml.streams_1d = 'grid-T'
        self.files.naml.streams_6h_1m = ['OtherFld1', 'OtherFld2']
        for rval in self.files.gen_reinit_period(['streams_6h_1m', 'streams_1d',
                                                  '1m', '2s', 'y']):
            yield_rtn.append(rval)

        expected = [('6h', '1m', ['OtherFld1', 'OtherFld2'], 'instantaneous'),
                    ('1d', '1d', ['grid-T'], 'instantaneous'),
                    ('1m', '1m', self.files.naml.meanfields, 'mean'),
                    ('2s', '2s', self.files.naml.meanfields, 'mean'),
                    ('y', 'y', self.files.naml.meanfields, 'mean')]

        for exp, act in zip(expected, yield_rtn):
            for elem in range(len(exp)):
                if isinstance(elem, str):
                    self.assertEqual(exp[elem], act[elem])
                else:
                    self.assertListEqual(sorted(exp[elem]), sorted(act[elem]))

        self.assertListEqual(self.files.naml.meanfields,
                             verify_namelist.NemoVerify().meanfields)

    def test_reinit_generator_cice(self):
        ''' Test performance of the reinit periods generator - nemo '''
        func.logtest('Test performance of the reinit periods generator:')
        yield_rtn = []
        self.files.naml.streams_1d_1m = True
        for rval in self.files.gen_reinit_period(['streams_1d_1m',
                                                  'm', 's', 'y']):
            yield_rtn.append(rval)

        expected = [('1d', '1m', [''], 'instantaneous'),
                    ('m', 'm', [''], 'mean'),
                    ('s', 's', [''], 'mean'),
                    ('y', 'y', [''], 'mean')]
        self.assertListEqual(yield_rtn, expected)

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
        self.assertListEqual(list(timlim.keys()), ['x'])

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
                   'PREFIXo_trajectory_icebergs_001440.nc',  # To 19950901
                   'PREFIXo_trajectory_icebergs_002160.nc',
                   'PREFIXo_trajectory_icebergs_002880.nc',
                   'PREFIXo_trajectory_icebergs_003600.nc',  # To 19951001
                   'PREFIXo_trajectory_icebergs_004320.nc',
                   'PREFIXo_trajectory_icebergs_005040.nc',
                   'PREFIXo_trajectory_icebergs_005760.nc']  # To 19951101
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
        outlist = ['PREFIXo_trajectory_icebergs_003000.nc',  # To 19950911
                   'PREFIXo_trajectory_icebergs_006000.nc']  # To 19951011
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

    def test_expected_atmos(self):
        ''' Assert correct list of expected atmos files '''
        func.logtest('Assert correct return of atmos files:')
        # startdate: 19950811, enddate: 19981101
        self.files.naml.streams_10d = ['pe']
        self.files.tlim = {'pe': ([1997, 1, 1], [1998, 2, 1])}
        outfiles = {
            'apy.pp': ['PREFIXa.py19961201.pp', 'PREFIXa.py19971201.pp'],
            'aps.pp': ['PREFIXa.ps1995son.pp', 'PREFIXa.ps1996djf.pp',
                       'PREFIXa.ps1996mam.pp', 'PREFIXa.ps1996jja.pp',
                       'PREFIXa.ps1996son.pp', 'PREFIXa.ps1997djf.pp',
                       'PREFIXa.ps1997mam.pp', 'PREFIXa.ps1997jja.pp',
                       'PREFIXa.ps1997son.pp', 'PREFIXa.ps1998djf.pp',
                       'PREFIXa.ps1998mam.pp', 'PREFIXa.ps1998jja.pp'],
            'apm.pp': ['PREFIXa.pm1995sep.pp', 'PREFIXa.pm1995oct.pp',
                       'PREFIXa.pm1998sep.pp', 'PREFIXa.pm1998oct.pp'],
            'ape.pp': ['PREFIXa.pe19970101.pp', 'PREFIXa.pe19970111.pp',
                       'PREFIXa.pe19980111.pp', 'PREFIXa.pe19980121.pp']
            }
        expected = self.files.expected_diags()
        self.assertListEqual(expected['apy.pp'], outfiles['apy.pp'])
        self.assertListEqual(expected['aps.pp'], outfiles['aps.pp'])
        self.assertListEqual(expected['apm.pp'][:2], outfiles['apm.pp'][:2])
        self.assertListEqual(expected['apm.pp'][-2:], outfiles['apm.pp'][-2:])
        self.assertListEqual(expected['ape.pp'][:2], outfiles['ape.pp'][:2])
        self.assertListEqual(expected['ape.pp'][-2:], outfiles['ape.pp'][-2:])
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_atmos_ppcmean(self):
        ''' Assert correct list of expected atmos files - pp climate means '''
        func.logtest('Assert correct return of atmos files - pp c.means:')
        # startdate: 19950811, enddate: 20150601, meanref: ???01201
        self.files.edate = [2015, 6, 1]
        self.files.naml.pp_climatemeans = True
        self.files.naml.meanstreams = ['1s', '1y', '1x']
        self.files.naml.base_mean = 'ma'
        self.files.naml.streams_10d = ['ma']
        expected = self.files.expected_diags()
        self.assertListEqual(expected['apx.pp'], ['PREFIXa.px20101201.pp'])
        self.assertListEqual(expected['apy.pp'][:2],
                             ['PREFIXa.py19961201.pp', 'PREFIXa.py19971201.pp'])
        self.assertListEqual(expected['apy.pp'][-2:],
                             ['PREFIXa.py20091201.pp', 'PREFIXa.py20101201.pp'])
        self.assertListEqual(expected['aps.pp'][:2],
                             ['PREFIXa.ps1995son.pp', 'PREFIXa.ps1996djf.pp'])
        self.assertListEqual(expected['aps.pp'][-2:],
                             ['PREFIXa.ps2014jja.pp', 'PREFIXa.ps2014son.pp'])
        self.assertListEqual(expected['ama.pp'][:2],
                             ['PREFIXa.ma19950811.pp', 'PREFIXa.ma19950821.pp'])
        self.assertListEqual(expected['ama.pp'][-2:],
                             ['PREFIXa.ma20150211.pp', 'PREFIXa.ma20150221.pp'])

        self.assertListEqual(sorted(expected.keys()),
                             ['ama.pp', 'aps.pp', 'apx.pp', 'apy.pp'])

    def test_expect_atmos_ppcmean_mref(self):
        ''' Assert correct list of expected atmos files - means at meanref '''
        func.logtest('Assert correct return of atmos means at meanref:')
        # startdate: 19950811, enddate: 20201101
        self.files.naml.pp_climatemeans = True
        self.files.naml.meanstreams = ['1m', '1s', '1y', '1x']
        self.files.edate = [2020, 1, 1]
        self.files.meanref = [0, 1, 1]
        expected = self.files.expected_diags()

        self.assertListEqual(expected['apx.pp'],
                             ['PREFIXa.px20100101.pp', 'PREFIXa.px20200101.pp'])
        self.assertListEqual(expected['apy.pp'][-2:],
                             ['PREFIXa.py20190101.pp', 'PREFIXa.py20200101.pp'])
        self.assertListEqual(expected['aps.pp'][-2:],
                             ['PREFIXa.ps2019jas.pp', 'PREFIXa.ps2019ond.pp'])
        self.assertListEqual(expected['apm.pp'][-2:],
                             ['PREFIXa.pm2019nov.pp', 'PREFIXa.pm2019dec.pp'])
        self.assertListEqual(sorted(expected.keys()),
                             ['apm.pp', 'aps.pp', 'apx.pp', 'apy.pp'])

    def test_expect_atmos_ppcmean_final(self):
        ''' Assert list of expected atmos files - pp climate means (final)'''
        func.logtest('Assert correct atmos files - pp c.means (final cycle):')
        # startdate: 19950811, enddate: 20150501
        self.files.naml.pp_climatemeans = True
        self.files.naml.meanstreams = ['1s', '1y', '1x']
        self.files.naml.base_mean = 'pm'
        self.files.naml.streams_1m = ['pm']
        self.files.edate = [2015, 5, 1]
        self.files.meanref = [0, 12, 1]

        self.files.finalcycle = True
        final = self.files.expected_diags()

        self.assertListEqual(final['apx.pp'], ['PREFIXa.px20101201.pp'])
        self.assertListEqual(final['apy.pp'][-2:],
                             ['PREFIXa.py20131201.pp', 'PREFIXa.py20141201.pp'])
        self.assertListEqual(final['aps.pp'][-2:],
                             ['PREFIXa.ps2014son.pp', 'PREFIXa.ps2015djf.pp'])
        self.assertListEqual(final['apm.pp'][-2:],
                             ['PREFIXa.pm2015mar.pp', 'PREFIXa.pm2015apr.pp'])
        self.assertListEqual(sorted(final.keys()),
                             ['apm.pp', 'aps.pp', 'apx.pp', 'apy.pp'])

    def test_expected_atmos_altdates(self):
        ''' Assert correct list of expected atmos files - alternative dates'''
        func.logtest('Assert correct return of atmos files - alt. dates:')
        self.files.naml.streams_10d = ['pe']
        self.files.tlim = {'pe': ([2015, 10, 1], [2020, 1, 1])}
        self.files.meanref = [1992, 2, 1]
        self.files.edate = [2015, 11, 1]
        outfiles = {
            'apx.pp': ['PREFIXa.px20120201.pp'],
            'apy.pp': ['PREFIXa.py19970201.pp', 'PREFIXa.py19980201.pp',
                       'PREFIXa.py20140201.pp', 'PREFIXa.py20150201.pp'],
            'aps.pp': ['PREFIXa.ps1996ndj.pp', 'PREFIXa.ps1996fma.pp',
                       'PREFIXa.ps2015mjj.pp', 'PREFIXa.ps2015aso.pp'],
            'apm.pp': ['PREFIXa.pm1995sep.pp', 'PREFIXa.pm1995oct.pp',
                       'PREFIXa.pm2015sep.pp', 'PREFIXa.pm2015oct.pp'],
            'ape.pp': ['PREFIXa.pe20151001.pp', 'PREFIXa.pe20151011.pp']
            }
        expected = self.files.expected_diags()
        self.assertListEqual(expected['apx.pp'], outfiles['apx.pp'])
        self.assertListEqual(expected['apy.pp'][:2], outfiles['apy.pp'][:2])
        self.assertListEqual(expected['apy.pp'][-2:], outfiles['apy.pp'][-2:])
        self.assertListEqual(expected['aps.pp'][:2], outfiles['aps.pp'][:2])
        self.assertListEqual(expected['aps.pp'][-2:], outfiles['aps.pp'][-2:])
        self.assertListEqual(expected['apm.pp'][:2], outfiles['apm.pp'][:2])
        self.assertListEqual(expected['apm.pp'][-2:], outfiles['apm.pp'][-2:])
        self.assertListEqual(expected['ape.pp'], outfiles['ape.pp'])
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_atmos_1s1x(self):
        ''' Assert correct list of expected atmos files - 1s & 1x only'''
        func.logtest('Assert correct return of atmos files - 1s,1x only:')
        self.files.naml.meanstreams = ['1s', '1x']
        self.files.naml.base_mean = 'ps'
        self.files.meanref = [1992, 2, 1]
        self.files.edate = [2015, 11, 1]
        outfiles = {
            'apx.pp': ['PREFIXa.px20120201.pp'],
            'aps.pp': ['PREFIXa.ps1996ndj.pp', 'PREFIXa.ps1996fma.pp',
                       'PREFIXa.ps2015mjj.pp', 'PREFIXa.ps2015aso.pp'],
            }
        expected = self.files.expected_diags()
        self.assertListEqual(expected['apx.pp'], outfiles['apx.pp'])
        self.assertListEqual(expected['aps.pp'][:2], outfiles['aps.pp'][:2])
        self.assertListEqual(expected['aps.pp'][-2:], outfiles['aps.pp'][-2:])
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_atmos_1m1s(self):
        ''' Assert correct list of expected atmos files - 1m & 1s only'''
        func.logtest('Assert correct return of atmos files - 1m,1s only:')
        self.files.naml.meanstreams = ['1m', '1s']
        self.files.meanref = [1992, 2, 1]
        self.files.edate = [2015, 11, 1]
        outfiles = {
            'apm.pp': ['PREFIXa.pm1995sep.pp', 'PREFIXa.pm1995oct.pp',
                       'PREFIXa.pm2015sep.pp', 'PREFIXa.pm2015oct.pp'],
            'aps.pp': ['PREFIXa.ps1996ndj.pp', 'PREFIXa.ps1996fma.pp',
                       'PREFIXa.ps2015mjj.pp', 'PREFIXa.ps2015aso.pp'],
            }
        expected = self.files.expected_diags()
        self.assertListEqual(expected['apm.pp'][:2], outfiles['apm.pp'][:2])
        self.assertListEqual(expected['apm.pp'][-2:], outfiles['apm.pp'][-2:])
        self.assertListEqual(expected['aps.pp'][:2], outfiles['aps.pp'][:2])
        self.assertListEqual(expected['aps.pp'][-2:], outfiles['aps.pp'][-2:])
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_atmos_ppff(self):
        ''' Assert correct list of expected files - pp and f files'''
        func.logtest('Assert correct return of atmos files - pp & f files:')
        # startdate: 19950811, enddate: 19981101, meanref: ???01201
        self.files.naml.meanstreams = '1x'
        self.files.naml.ff_streams = ['pa']
        self.files.naml.streams_90d = ['pa', 'pb']
        self.files.naml.streams_30d = ['p1']
        self.files.naml.streams_1d = []
        self.files.naml.streams_10h = ['md']
        self.files.naml.spawn_netcdf_streams = ['pb']

        outfiles = {
            'apa.file': ['PREFIXa.pa19950811', 'PREFIXa.pa19951111',
                         'PREFIXa.pa19980211', 'PREFIXa.pa19980511'],
            'apb.pp': ['PREFIXa.pb19950811.pp', 'PREFIXa.pb19951111.pp',
                       'PREFIXa.pb19980211.pp', 'PREFIXa.pb19980511.pp'],
            'ap1.pp': ['PREFIXa.p11995aug.pp', 'PREFIXa.p11995sep.pp',
                       'PREFIXa.p11998aug.pp', 'PREFIXa.p11998sep.pp'],
            'amd.pp': ['PREFIXa.md19950811_00.pp', 'PREFIXa.md19950811_10.pp',
                       'PREFIXa.md19981029_18.pp', 'PREFIXa.md19981030_04.pp'],
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

    def test_expected_atmos_periodic(self):
        ''' Assert correct list of periodically intermittent atmos files '''
        func.logtest('Assert correct return of intermittent atmos files:')
        self.files.naml.meanstreams = []
        self.files.naml.streams_10d = ['pa', 'pb', 'pc']
        self.files.naml.intermittent_streams = ['pb', 'pc']
        self.files.naml.intermittent_patterns = ['ox', 'xxoxoox']
        self.files.edate = [1995, 12, 1]
        outfiles = {
            'apa.pp': ['PREFIXa.pa19950811.pp', 'PREFIXa.pa19950821.pp',
                       'PREFIXa.pa19950901.pp', 'PREFIXa.pa19950911.pp',
                       'PREFIXa.pa19950921.pp', 'PREFIXa.pa19951001.pp',
                       'PREFIXa.pa19951011.pp', 'PREFIXa.pa19951021.pp',
                       'PREFIXa.pa19951101.pp', 'PREFIXa.pa19951111.pp'],
            'apb.pp': ['PREFIXa.pb19950811.pp', 'PREFIXa.pb19950901.pp',
                       'PREFIXa.pb19950921.pp', 'PREFIXa.pb19951011.pp',
                       'PREFIXa.pb19951101.pp'],
            'apc.pp': ['PREFIXa.pc19950901.pp', 'PREFIXa.pc19950921.pp',
                       'PREFIXa.pc19951001.pp', 'PREFIXa.pc19951111.pp']
            }
        expected = self.files.expected_diags()
        for key in outfiles:
            self.assertListEqual(sorted(expected[key]), sorted(outfiles[key]))
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_atmos_final(self):
        ''' Assert correct list of expected files - atmos finalcycle'''
        func.logtest('Assert correct return of atmos files - finalcycle:')
        self.files.naml.streams_90d = ['pa']
        self.files.naml.streams_10h = ['pd', 'pe']
        self.files.tlim = {'pe': ([1997, 1, 1], [1998, 1, 2])}
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
        self.files.meanfields = ['grid-W', 'diad-T', 'icemod']
        self.files.naml.streams_1d_10d = 'UK-shelf-V'
        self.files.naml.streams_1m = 'UK-shelf'
        self.files.edate = [1996, 5, 1]
        outfiles = {
            'ond.nc.file': ['nemo_prefixo_1d_19950811-19950821_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19950821-19950901_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19950901-19950911_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19950911-19950921_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19950921-19951001_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19951001-19951011_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19951011-19951021_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19951021-19951101_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19951101-19951111_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19951111-19951121_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19951121-19951201_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19951201-19951211_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19951211-19951221_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19951221-19960101_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19960101-19960111_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19960111-19960121_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19960121-19960201_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19960201-19960211_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19960211-19960221_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19960221-19960301_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19960301-19960311_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19960311-19960321_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19960321-19960401_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19960401-19960411_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19960411-19960421_UK-shelf-V.nc',
                            'nemo_prefixo_1d_19960421-19960501_UK-shelf-V.nc'],
            'onm.nc.file': ['nemo_prefixo_1m_19950901-19951001_UK-shelf.nc',
                            'nemo_prefixo_1m_19951001-19951101_UK-shelf.nc',
                            'nemo_prefixo_1m_19951101-19951201_UK-shelf.nc',
                            'nemo_prefixo_1m_19951201-19960101_UK-shelf.nc',
                            'nemo_prefixo_1m_19960101-19960201_UK-shelf.nc',
                            'nemo_prefixo_1m_19960201-19960301_UK-shelf.nc',
                            'nemo_prefixo_1m_19960301-19960401_UK-shelf.nc',
                            'nemo_prefixo_1m_19960401-19960501_UK-shelf.nc',
                            'nemo_prefixo_1m_19950901-19951001_grid-W.nc',
                            'medusa_prefixo_1m_19950901-19951001_diad-T.nc',
                            'nemo_prefixo_1m_19951001-19951101_grid-W.nc',
                            'medusa_prefixo_1m_19951001-19951101_diad-T.nc',
                            'nemo_prefixo_1m_19951101-19951201_grid-W.nc',
                            'medusa_prefixo_1m_19951101-19951201_diad-T.nc',
                            'nemo_prefixo_1m_19951201-19960101_grid-W.nc',
                            'medusa_prefixo_1m_19951201-19960101_diad-T.nc',
                            'nemo_prefixo_1m_19960101-19960201_grid-W.nc',
                            'medusa_prefixo_1m_19960101-19960201_diad-T.nc',
                            'nemo_prefixo_1m_19960201-19960301_grid-W.nc',
                            'medusa_prefixo_1m_19960201-19960301_diad-T.nc'],
            'ons.nc.file': ['nemo_prefixo_1s_19950901-19951201_grid-W.nc',
                            'medusa_prefixo_1s_19950901-19951201_diad-T.nc'],
            'inm.nc.file': ['si3_prefixi_1m_19950901-19951001_icemod.nc',
                            'si3_prefixi_1m_19951001-19951101_icemod.nc',
                            'si3_prefixi_1m_19951101-19951201_icemod.nc',
                            'si3_prefixi_1m_19951201-19960101_icemod.nc'],
            'ins.nc.file': ['si3_prefixi_1s_19950901-19951201_icemod.nc']
            }

        expected = self.files.expected_diags()
        self.assertListEqual(sorted(expected['onm.nc.file']),
                             sorted(outfiles['onm.nc.file']))
        self.assertListEqual(sorted(expected['ons.nc.file']),
                             sorted(outfiles['ons.nc.file']))

        self.files.finalcycle = True
        additional = {
            'ond.nc.file': [],
            'onm.nc.file': ['nemo_prefixo_1m_19960301-19960401_grid-W.nc',
                            'medusa_prefixo_1m_19960301-19960401_diad-T.nc',
                            'nemo_prefixo_1m_19960401-19960501_grid-W.nc',
                            'medusa_prefixo_1m_19960401-19960501_diad-T.nc'],
            'ons.nc.file': ['nemo_prefixo_1s_19951201-19960301_grid-W.nc',
                            'medusa_prefixo_1s_19951201-19960301_diad-T.nc'],
            'inm.nc.file': ['si3_prefixi_1m_19960101-19960201_icemod.nc',
                            'si3_prefixi_1m_19960201-19960301_icemod.nc',
                            'si3_prefixi_1m_19960301-19960401_icemod.nc',
                            'si3_prefixi_1m_19960401-19960501_icemod.nc'],
            'ins.nc.file': ['si3_prefixi_1s_19951201-19960301_icemod.nc']
            }

        expected = self.files.expected_diags()
        for key in outfiles:
            self.assertListEqual(sorted(expected[key]),
                                 sorted(outfiles[key] + additional[key]))

        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_nemo_topmean(self):
        ''' Assert correct list of expected nemo files - topmean = 1s'''
        func.logtest('Assert correct return of expected nemo files - top=1s:')
        self.files.naml.meanstreams = '1s'
        self.files.meanfields = ['grid-W', 'diad-T']
        self.files.edate = [1996, 3, 1]
        outfiles = {
            'ons.nc.file': ['nemo_prefixo_1s_19950901-19951201_grid-W.nc',
                            'medusa_prefixo_1s_19950901-19951201_diad-T.nc',
                            'nemo_prefixo_1s_19951201-19960301_grid-W.nc',
                            'medusa_prefixo_1s_19951201-19960301_diad-T.nc']
            }

        expected = self.files.expected_diags()
        self.assertListEqual(sorted(expected['ons.nc.file']),
                             sorted(outfiles['ons.nc.file']))

        self.files.finalcycle = True
        expected = self.files.expected_diags()
        self.assertListEqual(sorted(expected['ons.nc.file']),
                             sorted(outfiles['ons.nc.file']))

    def test_expected_nemo_buffer(self):
        ''' Assert correct list of expected nemo files - buffered'''
        func.logtest('Assert correct return of expected nemo files buffer=2:')
        # startdate: 19950811, meanref: ???01201, default base_mean=10d
        self.files.naml.meanstreams = ['10d', '1m']
        self.files.meanfields = ['grid-W', 'diad-T']
        self.files.naml.streams_10d = 'my10d'
        self.files.edate = [1996, 2, 1]
        self.files.naml.buffer_mean = 4
        regex = '{M}_prefixo_{P}_{D}_{F}.nc'
        dailydates = [
            '19950811-19950821', '19950821-19950901', '19950901-19950911',
            '19950911-19950921', '19950921-19951001', '19951001-19951011',
            '19951011-19951021', '19951021-19951101', '19951101-19951111',
            '19951111-19951121', '19951121-19951201', '19951201-19951211',
            '19951211-19951221', '19951221-19960101', '19960101-19960111',
            '19960111-19960121', '19960121-19960201'
            ]
        gridw_d = [regex.format(M='nemo', P='10d', D=d, F='grid-W')
                   for d in dailydates]
        diadt_d = [regex.format(M='medusa', P='10d', D=d, F='diad-T')
                   for d in dailydates]
        my10d = [regex.format(M='nemo', P='10d', D=d, F='my10d')
                 for d in dailydates]

        monthlydates = ['19950901-19951001', '19951001-19951101',
                        '19951101-19951201', '19951201-19960101',
                        '19960101-19960201']
        gridw_m = [regex.format(M='nemo', P='1m', D=d, F='grid-W')
                   for d in monthlydates]
        diadt_m = [regex.format(M='medusa', P='1m', D=d, F='diad-T')
                   for d in monthlydates]

        expected = self.files.expected_diags()
        self.assertListEqual(sorted(expected['onm.nc.file']),
                             sorted(gridw_m[:-2] + diadt_m[:-2]))
        self.assertListEqual(sorted(expected['ond.nc.file']),
                             sorted(gridw_d[:-6] + diadt_d[:-6] + my10d))

        self.files.finalcycle = True
        expected = self.files.expected_diags()
        self.assertListEqual(sorted(expected['onm.nc.file']),
                             sorted(gridw_m + diadt_m))
        self.assertListEqual(sorted(expected['ond.nc.file']),
                             sorted(gridw_d + diadt_d + my10d))

    def test_expected_cice_hourly(self):
        '''Assert correct return of expected cice hourly files'''
        func.logtest('Assert correct return of expected cice hourly files:')
        self.files.naml.meanstreams = []
        self.files.naml.streams_12h = True
        self.files.edate = [1995, 10, 1]

        hr_files = ['cice_prefixi_12h_1995081100-1995081112.nc',
                    'cice_prefixi_12h_1995081112-1995081200.nc',
                    'cice_prefixi_12h_1995093000-1995093012.nc',
                    'cice_prefixi_12h_1995093012-1995100100.nc',]
        expected = self.files.expected_diags()
        self.assertListEqual(expected['inh.nc.file'][:2], hr_files[:2])
        self.assertListEqual(expected['inh.nc.file'][-2:], hr_files[-2:])

    def test_expected_cice_meanbase(self):
        '''Assert correct return of expected cice files with mean_base'''
        func.logtest('Assert correct return of expected cice files:')
        # startdate: 19950811, meanref: ???01201, default base_mean=10d
        self.files.naml.meanstreams = ['1m']
        self.files.naml.streams_10d = True
        self.files.edate = [1995, 10, 21]

        daily_files = ['cice_prefixi_10d_19950811-19950821.nc',
                       'cice_prefixi_10d_19950821-19950901.nc',
                       'cice_prefixi_10d_19950901-19950911.nc',
                       'cice_prefixi_10d_19950911-19950921.nc',
                       'cice_prefixi_10d_19950921-19951001.nc']
        expected = self.files.expected_diags()
        self.assertListEqual(expected['ind.nc.file'], daily_files)

    def test_expected_cice_final(self):
        ''' Assert correct list of expected cice files'''
        func.logtest('Assert correct return of expected cice files:')
        self.files.naml.meanstreams = ['1s', '1y', '1x']
        self.files.edate = [2011, 10, 1]
        self.files.finalcycle = True
        outfiles = {
            'ins.nc.file': ['cice_prefixi_1s_19950901-19951201.nc',
                            'cice_prefixi_1s_19951201-19960301.nc',
                            'cice_prefixi_1s_20110301-20110601.nc',
                            'cice_prefixi_1s_20110601-20110901.nc'],
            'iny.nc.file': ['cice_prefixi_1y_19951201-19961201.nc',
                            'cice_prefixi_1y_19961201-19971201.nc',
                            'cice_prefixi_1y_20081201-20091201.nc',
                            'cice_prefixi_1y_20091201-20101201.nc'],
            'inx.nc.file': ['cice_prefixi_1x_20001201-20101201.nc'],
            }
        expected = self.files.expected_diags()
        for key in outfiles:
            self.assertListEqual(expected[key][:2], outfiles[key][:2])
            self.assertListEqual(expected[key][-2:], outfiles[key][-2:])
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_cice_concat_means(self):
        ''' Assert correct list of expected cice files - concatenated means'''
        func.logtest('Assert correct return of expected cice concat means:')
        self.files.naml.meanstreams = []
        self.files.naml.streams_1d_1m = True
        self.files.sdate = [1995, 9, 1]
        self.files.finalcycle = True

        concat_files = ['cice_prefixi_1d_19950901-19951001.nc',
                        'cice_prefixi_1d_19951001-19951101.nc',
                        'cice_prefixi_1d_19980901-19981001.nc',
                        'cice_prefixi_1d_19981001-19981101.nc']

        expected = self.files.expected_diags()
        self.assertListEqual(sorted(expected['ind.nc.file'][:2]),
                             sorted(concat_files[:2]))
        self.assertListEqual(sorted(expected['ind.nc.file'][-2:]),
                             sorted(concat_files[2:]))
        self.assertListEqual(sorted(expected.keys()), ['ind.nc.file'])

    def test_expect_cice_concat_meanstr(self):
        ''' Assert correct list of expected cice files - concat meanstream'''
        func.logtest('Assert correct return of expected cice concat means:')
        self.files.naml.streams_1d_1m = False
        self.files.naml.meanstreams = ['1d_1m']
        self.files.sdate = [1995, 9, 1]
        self.files.finalcycle = True

        concat_files = ['cice_prefixi_1d_19950901-19951001.nc',
                        'cice_prefixi_1d_19951001-19951101.nc',
                        'cice_prefixi_1d_19980901-19981001.nc',
                        'cice_prefixi_1d_19981001-19981101.nc']

        expected = self.files.expected_diags()
        self.assertListEqual(sorted(expected['ind.nc.file'][:2]),
                             sorted(concat_files[:2]))
        self.assertListEqual(sorted(expected['ind.nc.file'][-2:]),
                             sorted(concat_files[2:]))

    def test_expected_cice_concat_plus(self):
        ''' Assert correct list of expected cice files - concat means plus 1m'''
        func.logtest('Assert correct return of expected cice concat means:')
        self.files.naml.meanstreams = ['1m']
        self.files.naml.streams_1d_1m = True
        self.files.sdate = [1995, 9, 1]
        self.files.finalcycle = False

        concat_files = ['cice_prefixi_1d_19950901-19951001.nc',
                        'cice_prefixi_1d_19951001-19951101.nc',
                        'cice_prefixi_1d_19980901-19981001.nc',
                        'cice_prefixi_1d_19981001-19981101.nc']
        mean_files = ['cice_prefixi_1m_19950901-19951001.nc',
                      'cice_prefixi_1m_19951001-19951101.nc',
                      'cice_prefixi_1m_19980901-19981001.nc',
                      'cice_prefixi_1m_19981001-19981101.nc']
        expected = self.files.expected_diags()
        self.assertListEqual(sorted(expected['ind.nc.file'][:2]),
                             sorted(concat_files[:2]))
        self.assertListEqual(sorted(expected['ind.nc.file'][-2:]),
                             sorted(concat_files[2:]))
        self.assertListEqual(sorted(expected['inm.nc.file'][:2]),
                             sorted(mean_files[:2]))
        self.assertListEqual(sorted(expected['inm.nc.file'][-2:]),
                             sorted(mean_files[2:]))
        self.assertListEqual(sorted(expected.keys()),
                             ['ind.nc.file', 'inm.nc.file'])

    def test_expected_nemo_concat_6h_1m(self):
        ''' Assert correct list of expected concatenated files - hours -> 1m'''
        func.logtest('Assert correct return of expected concatenated files:')
        self.files.naml.meanstreams = []
        self.files.naml.streams_6h_1m = 'UK-shelf-T'
        self.files.sdate = [1995, 8, 21]
        self.files.finalcycle = True
        outfiles = {
            'onh.nc.file': ['nemo_prefixo_6h_19950901-19951001_UK-shelf-T.nc',
                            'nemo_prefixo_6h_19951001-19951101_UK-shelf-T.nc',
                            'nemo_prefixo_6h_19980901-19981001_UK-shelf-T.nc',
                            'nemo_prefixo_6h_19981001-19981101_UK-shelf-T.nc'],
            }
        expected = self.files.expected_diags()
        for key in outfiles:
            self.assertListEqual(expected[key][:2], outfiles[key][:2])
            self.assertListEqual(expected[key][-2:], outfiles[key][-2:])
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))

    def test_expected_nemo_concat_6h_1d(self):
        ''' Assert correct list of expected concatenated files - hours -> 1d'''
        func.logtest('Assert correct return of expected concatenated files:')
        self.files.naml.meanstreams = []
        self.files.naml.streams_6h_1d = 'UK-shelf-T'
        self.files.sdate = [1995, 9, 11]
        self.files.finalcycle = True
        outfiles = {
            'onh.nc.file': ['nemo_prefixo_6h_19950911-19950912_UK-shelf-T.nc',
                            'nemo_prefixo_6h_19950912-19950913_UK-shelf-T.nc',
                            'nemo_prefixo_6h_19981029-19981030_UK-shelf-T.nc',
                            'nemo_prefixo_6h_19981030-19981101_UK-shelf-T.nc'],
            }
        expected = self.files.expected_diags()

        for key in outfiles:
            self.assertListEqual(expected[key][:2], outfiles[key][:2])
            self.assertListEqual(expected[key][-2:], outfiles[key][-2:])
        self.assertListEqual(sorted(expected.keys()), sorted(outfiles.keys()))


class ClimateMeanTests(unittest.TestCase):
    ''' Unit tests relating to the ClimateMean class methods '''
    def setUp(self):
        self.dmean = expected_content.ClimateMean('10d', '1m',
                                                  {'base_cmpt': '1d'})
        self.mmean = expected_content.ClimateMean('1m', '1s',
                                                  {'base_cmpt': '1m',
                                                   'fileid': 'pa'})
        self.smean = expected_content.ClimateMean('1s', '1y',
                                                  {'base_cmpt': '1m'})
        self.ymean = expected_content.ClimateMean('1y', '1x',
                                                  {'base_cmpt': '1s'})
        self.xmean = expected_content.ClimateMean('1x', None,
                                                  {'base_cmpt': '1y'})

        with mock.patch('expected_content.utils.finalcycle',
                        return_value=False):

            self.diags = expected_content.DiagnosticFiles(
                '19900601', '20021201', 'PREFIX', 'atmos',
                verify_namelist.AtmosVerify()
                )

    def tearDown(self):
        pass

    def test_climatmean_instantiation(self):
        '''Assert instantiation of the ClimateMean object'''
        func.logtest('Assert instantiation of the Climatemean object:')
        self.assertEqual(self.dmean.period, '10d')
        self.assertEqual(self.dmean.next, '1m')
        self.assertEqual(self.dmean.previous, '1d')

        self.assertEqual(self.mmean.component_stream, 'pa')
        self.assertEqual(self.xmean.next, None)

    def test_climatmean_availability(self):
        '''Assert availability of a climate mean file'''
        func.logtest('Assert availability of a climate mean file:')
        self.assertTrue(self.dmean.get_availability([1980, 6, 1],
                                                    [1978, 12, 1]))
        self.assertFalse(self.dmean.get_availability([1980, 6, 11],
                                                     [1978, 12, 1]))

        self.assertTrue(self.mmean.get_availability([1980, 3, 1],
                                                    [1978, 12, 1]))
        self.assertFalse(self.mmean.get_availability([1980, 11, 1],
                                                     [1978, 12, 1]))

        self.assertTrue(self.smean.get_availability([1980, 12, 1],
                                                    [1978, 12, 1]))
        self.assertFalse(self.smean.get_availability([1980, 11, 1],
                                                     [1978, 12, 1]))

        self.assertTrue(self.ymean.get_availability([1988, 12, 1],
                                                    [1978, 12, 1]))
        self.assertFalse(self.ymean.get_availability([1985, 12, 1],
                                                     [1978, 12, 1]))

        self.assertTrue(self.xmean.get_availability([1978, 3, 15],
                                                    [1978, 12, 1]))

    def test_climate_meanfiles(self):
        '''Assert creation of the climate meanfiles dictionary'''
        func.logtest('Assert creation of climate meanfile dictionary:')
        means = self.diags.climate_meanfiles(['1m', '1y', '1x'])
        self.assertEqual(means['1m'].previous, '1m')
        self.assertEqual(means['1m'].next, '1y')

        self.assertEqual(means['1y'].previous, '1m')
        self.assertEqual(means['1y'].next, '1x')

        self.assertEqual(means['1x'].previous, '1y')
        self.assertEqual(means['1x'].next, None)

        self.assertListEqual(sorted(list(means.keys())),
                             ['1m', '1x', '1y'])
