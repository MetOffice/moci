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
import runtime_environment

import netcdf_filenames

runtime_environment.setup_env()


class NCFilenameTests(unittest.TestCase):
    '''Unit tests for the netCDF filename variables container'''
    def setUp(self):
        self.ncf = netcdf_filenames.NCFilename('model', 'my_SUITE', 'x',
                                               base='1x',
                                               start_date=('2000', '12', '11'))

    def tearDown(self):
        pass

    def test_fname_instantiation(self):
        '''Test instantiation of the filename container'''
        func.logtest('Assert successful creation of the filename container:')
        self.assertEqual(self.ncf.prefix, 'model_my-suitex')
        self.assertEqual(self.ncf.base, '1x')
        self.assertEqual(self.ncf.start_date, ('2000', '12', '11'))
        self.assertEqual(self.ncf.custom, '')

    @mock.patch('netcdf_filenames.calc_enddate')
    def test_calc_enddate_ncf(self, mock_calc):
        '''Test calc_enddate method from NCfilename object'''
        func.logtest('Assert call to external calc_enddate method:')
        _ = self.ncf.calc_enddate()
        _ = self.ncf.calc_enddate(target='BASE')
        self.assertListEqual(mock_calc.mock_calls,
                             [mock.call(self.ncf.start_date, self.ncf.base),
                              mock.call(self.ncf.start_date, 'BASE')])

    def test_ncmatch_true(self):
        '''Test netCDF filename regular expression - positive match'''
        func.logtest('Assert return from nc_match property - positive:')
        files = ['nemo_abcdeo_10d_11112233-44445566_grid_0000.nc',
                 'medusa_gc3aoo_1m_11112233-44445566_diad-T.nc',
                 'cice_1-2-3i_1s_111122-444455.nc',
                 'model_suitea_12h_1111223344-5555667788.nc']
        for fname in files:
            func.logtest('[DEBUG] Testing file:' + fname)
            self.assertTrue(self.ncf.nc_match(fname))

    def test_ncmatch_false(self):
        '''Test netCDF filename regex - negative match'''
        func.logtest('Assert return from nc_match property - negative:')
        files = [
            # Missing component:
            'abcdeo_10d_11112233-44445566_grid_0000.nc',
            # '_' in custom field - 'diad_T'
            'medusa_gc3aoo_1m_11112233-44445566_diad_T.nc',
            # Invalid uppercase realm ID - 'I'
            'cice_ab123I_1s_111122-444455.nc',
            # Invalid character in suite ID - '~'
            'cice_ab1~3i_1s_111122-444455.nc',
            # Invalid uppercase component - 'MODEL'
            'MODEL_suitex_12h_1111223344-5555667788.nc',
            # Invalid realm ID - 'x'
            'model_suitex_1x_11112233-44445566.nc'
            ]
        for fname in files:
            func.logtest('[DEBUG] Testing file:' + fname)
            self.assertFalse(self.ncf.nc_match(fname))

    @mock.patch('netcdf_filenames.os.rename')
    def test_convention(self, mock_mv):
        '''Test method for enforcing the netCDF filename convention'''
        func.logtest('Assert conversion of filename:')
        self.ncf.base = '1d'
        self.ncf.rename_ncf('here/filename')
        mock_mv.assert_called_once_with(
            'here/filename',
            'here/model_my-suitex_1d_20001211-20001212.nc'
            )
        self.assertIn('Renaming here/filename as model_my-suitex_1d'
                      '_20001211-20001212.nc', func.capture())

    @mock.patch('netcdf_filenames.os.rename')
    def test_rename_ncf_shortdate(self, mock_mv):
        '''Test method for enforcing the netCDF filename convention -short'''
        func.logtest('Assert conversion of filename - short date:')
        self.ncf.base = '1m'
        self.ncf.start_date = ('2000', '12')
        self.ncf.rename_ncf('here/filename')
        mock_mv.assert_called_once_with(
            'here/filename',
            'here/model_my-suitex_1m_20001201-20010101.nc'
            )
        self.assertIn('Renaming here/filename as model_my-suitex_1m'
                      '_20001201-20010101.nc', func.capture())

    @mock.patch('netcdf_filenames.os.rename')
    def test_rename_ncf_target(self, mock_mv):
        '''Test method for enforcing netCDF filename convention with target'''
        func.logtest('Assert conversion of filename with target:')
        self.ncf.base = '1d'
        self.ncf.rename_ncf('here/filename', target='1m')
        mock_mv.assert_called_once_with(
            'here/filename',
            'here/model_my-suitex_1d_20001211-20010111.nc'
            )
        self.assertIn('Renaming here/filename as model_my-suitex_1d'
                      '_20001211-20010111.nc', func.capture())

    @mock.patch('netcdf_filenames.os.rename')
    def test_rename_ncf_nochange(self, mock_mv):
        '''Test method for enforcing netCDF filename convention - no change'''
        func.logtest('Assert conversion of filename - no change required:')
        self.ncf.base = '1m'
        self.ncf.rename_ncf('here/model_suitea_1d_00000000-11111111.nc')
        self.assertEqual(len(mock_mv.mock_calls), 0)
        self.assertNotIn('netcdf_fname_convention', func.capture())
        self.assertNotIn('netcdf_fname_convention', func.capture('err'))

    def test_rename_ncf_fail(self):
        '''Test method for enforcing the netCDF filename convention - fail'''
        func.logtest('Assert conversion of filename - failure mode:')
        self.ncf.base = '1d'
        with mock.patch('netcdf_filenames.utils.get_debugmode',
                        return_value=False):
            with self.assertRaises(SystemExit):
                self.ncf.rename_ncf('here/filename')
        self.assertIn('Failed to rename file: here/filename',
                      func.capture('err'))

    def test_rename_ncf_fail_debug(self):
        '''Test method for enforcing netCDF filename convention - debug fail'''
        func.logtest('Assert conversion of filename - debug failure mode:')
        self.ncf.base = '1d'
        with mock.patch('netcdf_filenames.utils.get_debugmode',
                        return_value=True):
            self.ncf.rename_ncf('here/filename')
        self.assertIn('Failed to rename file: here/filename',
                      func.capture('err'))


class StencilTests(unittest.TestCase):
    '''Unit tests for the Met Office netCDF filenaming convention methods'''
    def setUp(self):
        self.ncf = netcdf_filenames.NCFilename('model', 'suite', 'x', base='1x')

    def tearDown(self):
        pass

    def test_month_end(self):
        '''Test period_end method - Month'''
        func.logtest('Assert return from period_end method - Month:')
        self.ncf.base = '10d'
        regex = netcdf_filenames.period_end('1m', self.ncf, [0, 12, 1])
        stencil = '^model_suitex_10d_\\d{8,10}-\\d{4}(\\d{2}01)(00)?\\.nc$'

        self.ncf.base = '12h'
        regex = netcdf_filenames.period_end('1m', self.ncf, [0, 12, 15])
        stencil = '^model_suitex_12h_\\d{8,10}-\\d{4}(\\d{2}15)(00)?\\.nc$'
        self.assertEqual(regex, stencil)

    def test_month_end_custom(self):
        '''Test period_end method with custom field - Month'''
        func.logtest('Assert return from period_end method - Month, custom:')
        self.ncf.custom = '_field'
        regex = netcdf_filenames.period_end('1m', self.ncf, [0, 12, 1])
        stencil = '^model_suitex_1x_\\d{8,10}-\\d{4}(\\d{2}01)(00)?_field\\.nc$'
        self.assertEqual(regex, stencil)

    def test_season_end(self):
        '''Test period_end method - Season'''
        func.logtest('Assert return from period_end method - Season:')
        self.ncf.base = '1m'
        regex = netcdf_filenames.period_end('1s', self.ncf, [0, 12, 1])
        stencil = '^model_suitex_1m_\\d{8,10}-\\d{4}' \
            '(0301|0601|0901|1201)(00)?\\.nc$'
        self.assertEqual(regex, stencil)

    def test_season_end_custom(self):
        '''Test period_end method - Season with custom field'''
        func.logtest('Assert return from period_end method - Season, custom:')
        self.ncf.base = '10d'
        self.ncf.custom = '_field'
        regex = netcdf_filenames.period_end('1s', self.ncf, [0, 1, 15])
        stencil = '^model_suitex_10d_\\d{8,10}-\\d{4}' \
            '(0115|0415|0715|1015)(00)?_field\\.nc$'
        self.assertEqual(regex, stencil)

    def test_year_end(self):
        '''Test period_end method - Year'''
        func.logtest('Assert return from period_end method - Year:')
        self.ncf.base = '1s'
        regex = netcdf_filenames.period_end('1y', self.ncf, [0, 12, 1])
        stencil = '^model_suitex_1s_\\d{8,10}-\\d{4}(1201)(00)?\\.nc$'
        self.assertEqual(regex, stencil)

    def test_year_end_custom(self):
        '''Test period_end method - Year with custom field'''
        func.logtest('Assert return from period_end method - Year, custom:')
        self.ncf.base = '1m'
        self.ncf.custom = '_field'
        regex = netcdf_filenames.period_end('1y', self.ncf, [0, 1, 15])
        stencil = '^model_suitex_1m_\\d{8,10}-\\d{4}(0115)(00)?_field\\.nc$'
        self.assertEqual(regex, stencil)

    def test_month_set(self):
        '''Test period_set method - Month'''
        func.logtest('Assert return from period_end method - Month:')
        self.ncf.start_date = ('2000', '12', '01')
        self.ncf.base = '10d'
        regex = netcdf_filenames.period_set('1m', self.ncf)
        stencil = '^model_suitex_10d_(20001111|20001121|20001201)(\\d{2})?' \
            '-\\d{8,10}\\.nc$'
        self.assertEqual(regex, stencil)

    def test_month_set_custom(self):
        '''Test period_set method - Month with custom field'''
        func.logtest('Assert return from period_end method - Month:')
        self.ncf.start_date = ('2000', '01', '16')
        self.ncf.base = '15d'
        self.ncf.custom = '_field'
        regex = netcdf_filenames.period_set('1m', self.ncf)
        stencil = '^model_suitex_15d_(20000101|20000116)(\\d{2})?' \
            '-\\d{8,10}_field\\.nc$'
        self.assertEqual(regex, stencil)

    def test_season_set(self):
        '''Test period_set method - Season'''
        func.logtest('Assert return from period_end method - Season:')
        self.ncf.start_date = ('2000', '12', '01')
        self.ncf.base = '1m'
        regex = netcdf_filenames.period_set('1s', self.ncf)
        stencil = '^model_suitex_1m_(20001001|20001101|20001201)(\\d{2})?' \
            '-\\d{8,10}\\.nc$'
        self.assertEqual(regex, stencil)

    def test_season_set_custom(self):
        '''Test period_set method - Season with custom field'''
        func.logtest('Assert return from period_end method - Season:')
        self.ncf.start_date = ('2000', '01', '16')
        self.ncf.base = '15d'
        self.ncf.custom = '_field'
        regex = netcdf_filenames.period_set('1s', self.ncf)
        stencil = '^model_suitex_15d_(19991101|19991116|19991201|19991216|' \
            '20000101|20000116)(\\d{2})?-\\d{8,10}_field\\.nc$'
        self.assertEqual(regex, stencil)

    def test_year_set(self):
        '''Test period_set method - Year'''
        func.logtest('Assert return from period_end method - Year:')
        self.ncf.start_date = ('2000', '12', '01')
        self.ncf.base = '1s'
        regex = netcdf_filenames.period_set('1y', self.ncf)
        stencil = '^model_suitex_1s_(20000301|20000601|20000901|20001201)' \
            '(\\d{2})?-\\d{8,10}\\.nc$'
        self.assertEqual(regex, stencil)

    def test_year_set_custom(self):
        '''Test period_set method - Year with custom field'''
        func.logtest('Assert return from period_end method - Year:')
        self.ncf.start_date = ('2000', '01', '16')
        self.ncf.base = '1m'
        self.ncf.custom = '_field'
        regex = netcdf_filenames.period_set('1y', self.ncf)
        stencil = '^model_suitex_1m_(19990216|19990316|19990416|19990516|' \
            '19990616|19990716|19990816|19990916|19991016|19991116|19991216|' \
            '20000116)(\\d{2})?-\\d{8,10}_field\\.nc$'
        self.assertEqual(regex, stencil)

    def test_10d_stencil(self):
        '''Test mean_stencil method - 10days'''
        func.logtest('Assert return from mean_stencil method - 10days:')
        self.ncf.start_date = ('2000', '12', '01')
        self.ncf.base = '1m'
        regex = netcdf_filenames.mean_stencil(self.ncf, target='10days')
        stencil = 'model_suitex_1m_20001201-20001211.nc'
        self.assertEqual(regex, stencil)

    def test_month_stencil(self):
        '''Test mean_stencil method - month'''
        func.logtest('Assert return from mean_stencil method - month:')
        self.ncf.start_date = ('2000', '12', '01')
        self.ncf.base = '1m'
        regex = netcdf_filenames.mean_stencil(self.ncf)
        stencil = 'model_suitex_1m_20001201-20010101.nc'
        self.assertEqual(regex, stencil)

    def test_month_stencil_custom(self):
        '''Test month_stencil method with custom field'''
        func.logtest('Assert return from mean_stencil - month, custom field:')
        self.ncf.start_date = ('2000', '12', '01')
        self.ncf.base = '1m'
        self.ncf.custom = '_field'
        regex = netcdf_filenames.mean_stencil(self.ncf)
        stencil = 'model_suitex_1m_20001201-20010101_field.nc'
        self.assertEqual(regex, stencil)

    def test_season_stencil(self):
        '''Test mean_stencil method - season'''
        func.logtest('Assert return from mean_stencil method - season:')
        self.ncf.start_date = ('2000', '12', '01')
        self.ncf.base = '1s'
        regex = netcdf_filenames.mean_stencil(self.ncf)
        stencil = 'model_suitex_1s_20001201-20010301.nc'
        self.assertEqual(regex, stencil)

    def test_year_stencil(self):
        '''Test mean_stencil method - year'''
        func.logtest('Assert return from mean_stencil method - year:')
        self.ncf.start_date = ('2000', '12', '01')
        self.ncf.base = '1y'
        regex = netcdf_filenames.mean_stencil(self.ncf)
        stencil = 'model_suitex_1y_20001201-20011201.nc'
        self.assertEqual(regex, stencil)

    def test_all_years_stencil(self):
        '''Test mean_stencil method - all years'''
        func.logtest('Assert return from mean_stencil method - year:')
        self.ncf.base = '1y'
        regex = netcdf_filenames.mean_stencil(self.ncf)
        stencil = r'model_suitex_1y_\d{4}\d{2}\d{2}-\d{4}\d{2}\d{2}.nc'
        self.assertEqual(regex, stencil)

    def test_mean_stencil_target(self):
        '''Test mean_stencil method - all files with target'''
        func.logtest('Assert return from mean_stencil method - target:')
        self.ncf.start_date = ('2000', '12', '01')
        self.ncf.base = '1x'
        regex = netcdf_filenames.mean_stencil(self.ncf, target='month')
        stencil = 'model_suitex_1x_20001201-20010101.nc'
        self.assertEqual(regex, stencil)


class DateTests(unittest.TestCase):
    ''' Unit tests for mean reference date manipulation '''
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ncf_getdate(self):
        '''Test ncf_getdate method'''
        func.logtest('Assert return from ncf_getdate method:')
        files = ['nemo_abcdeo_10d_11112233-44445566_grid_0000.nc',
                 'medusa_gc3aoo_1m_11112233-44445566_diad-T.nc']
        for fname in files:
            func.logtest('Testing filename: ' + fname)
            rdate = netcdf_filenames.ncf_getdate(fname)
            self.assertTupleEqual(rdate, ('1111', '22', '33'))

    def test_ncf_getdate_long(self):
        '''Test ncf_getdate method - yyyymmddhh'''
        func.logtest('Assert return from ncf_getdate method - yyyymmddhh:')
        rdate = netcdf_filenames.ncf_getdate(
            'model_suitea_12h_1111223344-5555667788.nc'
            )
        self.assertTupleEqual(rdate, ('1111', '22', '33', '44'))

    def test_ncf_getdate_short(self):
        '''Test ncf_getdate method - yyyymm'''
        func.logtest('Assert return from ncf_getdate method - yyyymm:')
        rdate = netcdf_filenames.ncf_getdate('cice_1-2-3i_1s_111122-444455.nc')
        self.assertTupleEqual(rdate, ('1111', '22'))

    def test_ncf_getenddate(self):
        '''Test ncf_getdate method - end'''
        func.logtest('Assert return from ncf_getdate method - end:')
        files = ['nemo_abcdeo_10d_11112233-44445566_grid_0000.nc',
                 'medusa_gc3aoo_1m_11112233-44445566_diad-T.nc']
        for fname in files:
            func.logtest('Testing filename: ' + fname)
            rdate = netcdf_filenames.ncf_getdate(fname, enddate=True)
            self.assertTupleEqual(rdate, ('4444', '55', '66'))

    def test_ncf_getenddate_long(self):
        '''Test ncf_getdate method - yyyymmddhh (end)'''
        func.logtest('Assert return from ncf_getenddate method - yyyymmddhh:')
        rdate = netcdf_filenames.ncf_getdate(
            'model_suitea_12h_1111223344-5555667788.nc', enddate=True
            )
        self.assertTupleEqual(rdate, ('5555', '66', '77', '88'))

    def test_ncf_getenddate_short(self):
        '''Test ncf_getdate method - yyyymm (end'''
        func.logtest('Assert return from ncf_getenddate method - yyyymm:')
        rdate = netcdf_filenames.ncf_getdate('cice_1-2-3i_1s_111122-444455.nc',
                                             enddate=True)
        self.assertTupleEqual(rdate, ('4444', '55'))

    def test_ncf_getdate_none(self):
        '''Test ncf_getdate method - none'''
        func.logtest('Assert return from ncf_getdate method - none:')
        rdate = netcdf_filenames.ncf_getdate('model_suitea_12h_0000.nc')
        self.assertEqual(rdate, None)

    def test_calc_enddate_12h(self):
        '''Test calc_enddate method with 12h period'''
        func.logtest('Assert return from calc_enddate with 12h:')
        startdate = ('2000', '12', '11', '12')
        dates = [netcdf_filenames.calc_enddate(startdate, 'hour', freq=12)]
        dates.append(netcdf_filenames.calc_enddate(startdate, '12h'))

        for date in dates:
            self.assertEqual(date, ('2000', '12', '12', '00'))

    def test_calc_enddate_1d(self):
        '''Test calc_enddate method with 1d period'''
        func.logtest('Assert return from calc_enddate with 1d:')
        startdate = ('2000', '12', '11', '12')
        dates = [netcdf_filenames.calc_enddate(startdate, 'hour', freq=24)]
        dates.append(netcdf_filenames.calc_enddate(startdate, '24h'))
        dates.append(netcdf_filenames.calc_enddate(startdate, 'day'))
        dates.append(netcdf_filenames.calc_enddate(startdate, 'daily'))
        for date in dates:
            self.assertEqual(date, ('2000', '12', '12', '12'))

    def test_calc_enddate_10d(self):
        '''Test calc_enddate method with 10d period'''
        func.logtest('Assert return from calc_enddate with 10d:')
        startdate = ('2000', '12', '11')
        dates = [netcdf_filenames.calc_enddate(startdate, 'Day', freq=10)]
        dates.append(netcdf_filenames.calc_enddate(startdate, '10d'))
        dates.append(netcdf_filenames.calc_enddate(startdate, 'daily', freq=10))
        for date in dates:
            self.assertEqual(date, ('2000', '12', '21'))

    def test_calc_enddate_1m(self):
        '''Test get_enddate method with 1m period'''
        func.logtest('Assert return from calc_enddate with 1m:')
        startdate = ('2000', '12', '11')
        dates = [netcdf_filenames.calc_enddate(startdate, 'Day', freq=30)]
        dates.append(netcdf_filenames.calc_enddate(startdate, '1M'))
        dates.append(netcdf_filenames.calc_enddate(startdate, 'Monthly'))
        for date in dates:
            self.assertEqual(date, ('2001', '01', '11'))

    def test_calc_enddate_1m_shortdate(self):
        '''Test get_enddate method with 1m period - shortdate format'''
        func.logtest('Assert return from calc_enddate with 1m - shortdate:')
        startdate = ('2000', '12')
        dates = [netcdf_filenames.calc_enddate(startdate, 'Day', freq=30)]
        dates.append(netcdf_filenames.calc_enddate(startdate, '1M'))
        dates.append(netcdf_filenames.calc_enddate(startdate, 'Monthly'))
        for date in dates:
            self.assertEqual(date, ('2001', '01'))

    def test_calc_enddate_1s(self):
        '''Test calc_enddate method with 1s period'''
        func.logtest('Assert return from calc_enddate with 1s:')
        startdate = ('2000', '12', '11')
        dates = [netcdf_filenames.calc_enddate(startdate, 'mth', freq=3)]
        dates.append(netcdf_filenames.calc_enddate(startdate, '1s'))
        dates.append(netcdf_filenames.calc_enddate(startdate, 'Seasonal'))
        for date in dates:
            self.assertEqual(date, ('2001', '03', '11'))

    def test_calc_enddate_1y(self):
        '''Test calc_enddate method with 1y period'''
        func.logtest('Assert return from calc_enddate with 1y:')
        startdate = ('2000', '12', '11')
        dates = [netcdf_filenames.calc_enddate(startdate, 'ssn', freq=4)]
        dates.append(netcdf_filenames.calc_enddate(startdate, '1y'))
        dates.append(netcdf_filenames.calc_enddate(startdate, 'Year'))
        for date in dates:
            self.assertEqual(date, ('2001', '12', '11'))

    def test_calc_enddate_10y(self):
        '''Test calc_enddate method with 10y period'''
        func.logtest('Assert return from calc_enddate with 10y:')
        startdate = ('2000', '12', '11')
        dates = [netcdf_filenames.calc_enddate(startdate, 'yr', freq=10)]
        dates.append(netcdf_filenames.calc_enddate(startdate, '10yrs'))
        dates.append(netcdf_filenames.calc_enddate(startdate, 'Year', freq=10))
        for date in dates:
            self.assertEqual(date, ('2010', '12', '11'))

    def test_calc_enddate_fail(self):
        '''Test calc_enddate method with invalid period'''
        func.logtest('Assert return from calc_enddate with ?:')
        with self.assertRaises(SystemExit):
            _ = netcdf_filenames.calc_enddate('startdate', 'period')
        self.assertIn('Invalid target provided', func.capture('err'))

    def test_seasonend(self):
        '''Test seasonend for various mean_ref_dates'''
        func.logtest('Assert creation of season ends for mean_ref_dates:')
        self.assertEqual(netcdf_filenames.seasonend([0, 12, 1]),
                         ('0301', '0601', '0901', '1201'))

        self.assertEqual(netcdf_filenames.seasonend([0, 1, 1]),
                         ('0101', '0401', '0701', '1001'))

        self.assertEqual(netcdf_filenames.seasonend([0, 6, 15]),
                         ('0315', '0615', '0915', '1215'))
