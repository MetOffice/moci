#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016 Met Office. All rights reserved.

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
import utils

runtime_environment.setup_env()


class NCFilenameTests(unittest.TestCase):
    '''Unit tests for the netCDF filename variables container'''
    def setUp(self):
        self.ncf = netcdf_filenames.NCFilename('model', 'suite', 'x', base='1x',
                                               start_date=('2000', '12', '11'))

    def tearDown(self):
        utils.set_debugmode(False)

    def test_fname_instantiation(self):
        '''Test instantiation of the filename container'''
        func.logtest('Assert successful creation of the filename container:')
        self.assertEqual(self.ncf.prefix, 'model_suitex')
        self.assertEqual(self.ncf.base, '1x')
        self.assertEqual(self.ncf.start_date, ('2000', '12', '11'))
        self.assertEqual(self.ncf.custom, '')

    def test_calc_enddate_12h(self):
        '''Test calc_enddate method with 12h period'''
        func.logtest('Assert return from calc_enddate with 12h:')
        self.ncf.start_date = ('2000', '12', '11', '12')
        dates = [self.ncf.calc_enddate(target='hour', freq=12)]
        dates.append(self.ncf.calc_enddate(target='12h'))

        for date in dates:
            self.assertEqual(date, ('2000', '12', '12', '00'))

    def test_calc_enddate_1d(self):
        '''Test calc_enddate method with 1d period'''
        func.logtest('Assert return from calc_enddate with 1d:')
        self.ncf.start_date = ('2000', '12', '11', '12')
        self.ncf.base = 'daily'
        dates = [self.ncf.calc_enddate(target='hour', freq=24)]
        dates.append(self.ncf.calc_enddate(target='24h'))
        dates.append(self.ncf.calc_enddate(target='day'))
        dates.append(self.ncf.calc_enddate())
        for date in dates:
            self.assertEqual(date, ('2000', '12', '12', '12'))

    def test_calc_enddate_10d(self):
        '''Test calc_enddate method with 10d period'''
        func.logtest('Assert return from calc_enddate with 10d:')
        self.ncf.base = 'daily'
        dates = [self.ncf.calc_enddate(target='Day', freq=10)]
        dates.append(self.ncf.calc_enddate(target='10d'))
        dates.append(self.ncf.calc_enddate(freq=10))
        for date in dates:
            self.assertEqual(date, ('2000', '12', '21'))

    def test_calc_enddate_1m(self):
        '''Test get_enddate method with 1m period'''
        func.logtest('Assert return from calc_enddate with 1m:')
        self.ncf.base = 'Monthly'
        dates = [self.ncf.calc_enddate(target='Day', freq=30)]
        dates.append(self.ncf.calc_enddate(target='1M'))
        dates.append(self.ncf.calc_enddate())
        for date in dates:
            self.assertEqual(date, ('2001', '01', '11'))

    def test_calc_enddate_1m_shortdate(self):
        '''Test get_enddate method with 1m period - shortdate format'''
        func.logtest('Assert return from calc_enddate with 1m - shortdate:')
        self.ncf.base = 'Monthly'
        self.ncf.start_date = ('2000', '12')
        dates = [self.ncf.calc_enddate(target='Day', freq=30)]
        dates.append(self.ncf.calc_enddate(target='1M'))
        dates.append(self.ncf.calc_enddate())
        for date in dates:
            self.assertEqual(date, ('2001', '01'))

    def test_calc_enddate_1s(self):
        '''Test calc_enddate method with 1s period'''
        func.logtest('Assert return from calc_enddate with 1s:')
        self.ncf.base = 'Seasonal'
        dates = [self.ncf.calc_enddate(target='mth', freq=3)]
        dates.append(self.ncf.calc_enddate(target='1s'))
        dates.append(self.ncf.calc_enddate())
        for date in dates:
            self.assertEqual(date, ('2001', '03', '11'))

    def test_calc_enddate_1y(self):
        '''Test calc_enddate method with 1y period'''
        func.logtest('Assert return from calc_enddate with 1y:')
        self.ncf.base = 'Year'
        dates = [self.ncf.calc_enddate(target='ssn', freq=4)]
        dates.append(self.ncf.calc_enddate(target='1y'))
        dates.append(self.ncf.calc_enddate())
        for date in dates:
            self.assertEqual(date, ('2001', '12', '11'))

    def test_calc_enddate_10y(self):
        '''Test calc_enddate method with 10y period'''
        func.logtest('Assert return from calc_enddate with 10y:')
        self.ncf.base = 'Year'
        dates = [self.ncf.calc_enddate(target='yr', freq=10)]
        dates.append(self.ncf.calc_enddate(target='10yrs'))
        dates.append(self.ncf.calc_enddate(freq=10))
        for date in dates:
            self.assertEqual(date, ('2010', '12', '11'))

    def test_calc_enddate_fail(self):
        '''Test calc_enddate method with invalid period'''
        func.logtest('Assert return from calc_enddate with ?:')
        with self.assertRaises(SystemExit):
            _ = self.ncf.calc_enddate('period')
        self.assertIn('Invalid target provided', func.capture('err'))

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
            'here/model_suitex_1d_20001211-20001212.nc'
            )
        self.assertIn('Renaming here/filename as model_suitex_1d'
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
            'here/model_suitex_1m_20001201-20010101.nc'
            )
        self.assertIn('Renaming here/filename as model_suitex_1m'
                      '_20001201-20010101.nc', func.capture())

    @mock.patch('netcdf_filenames.os.rename')
    def test_rename_ncf_target(self, mock_mv):
        '''Test method for enforcing netCDF filename convention with target'''
        func.logtest('Assert conversion of filename with target:')
        self.ncf.base = '1d'
        self.ncf.rename_ncf('here/filename', target='1m')
        mock_mv.assert_called_once_with(
            'here/filename',
            'here/model_suitex_1d_20001211-20010111.nc'
            )
        self.assertIn('Renaming here/filename as model_suitex_1d'
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
        with self.assertRaises(SystemExit):
            self.ncf.rename_ncf('here/filename')
        self.assertIn('Failed to rename file: here/filename',
                      func.capture('err'))

    def test_rename_ncf_fail_debug(self):
        '''Test method for enforcing netCDF filename convention - debug fail'''
        func.logtest('Assert conversion of filename - debug failure mode:')
        self.ncf.base = '1d'
        utils.set_debugmode(True)
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
        '''Test month_end method'''
        func.logtest('Assert return from month_end method:')
        regex = netcdf_filenames.month_end(self.ncf)
        stencil = '^model_suitex_1x_\\d{8,10}-\\d{6}01(00)?\\.nc$'
        self.assertEqual(regex, stencil)

    def test_month_end_custom(self):
        '''Test month_end method with custom field'''
        func.logtest('Assert return from month_end method - custom field:')
        self.ncf.custom = '_field'
        regex = netcdf_filenames.month_end(self.ncf)
        stencil = '^model_suitex_1x_\\d{8,10}-\\d{6}01(00)?_field\\.nc$'
        self.assertEqual(regex, stencil)

    def test_season_end(self):
        '''Test season_end method'''
        func.logtest('Assert return from season_end method:')
        regex = netcdf_filenames.season_end(self.ncf)
        stencil = '^model_suitex_1m_\\d{6}01-\\d{4}(0301|0601|0901|1201)\\.nc$'
        self.assertEqual(regex, stencil)

    def test_season_end_custom(self):
        '''Test season_end method with custom field'''
        func.logtest('Assert return from season_end method - custom field:')
        self.ncf.custom = '_field'
        regex = netcdf_filenames.season_end(self.ncf)
        stencil = '^model_suitex_1m_\\d{6}01-\\d{4}(0301|0601|0901|1201)' \
            '_field\\.nc$'
        self.assertEqual(regex, stencil)

    def test_year_end(self):
        '''Test year_end method'''
        func.logtest('Assert return from year_end method:')
        regex = netcdf_filenames.year_end(self.ncf)
        stencil = '^model_suitex_1s_\\d{6}01-\\d{4}1201\\.nc$'
        self.assertEqual(regex, stencil)

    def test_year_end_custom(self):
        '''Test year_end method with custom field'''
        func.logtest('Assert return from year_end method - custom field:')
        self.ncf.custom = '_field'
        regex = netcdf_filenames.year_end(self.ncf)
        stencil = '^model_suitex_1s_\\d{6}01-\\d{4}1201_field\\.nc$'
        self.assertEqual(regex, stencil)

    def test_month_set(self):
        '''Test month_set method'''
        func.logtest('Assert return from month_end method:')
        self.ncf.start_date = ('2000', '12', '01')
        regex = netcdf_filenames.month_set(self.ncf)
        stencil = '^model_suitex_1x_200012\\d{2}-(200012\\d{2}|20010101)\\.nc$'
        self.assertEqual(regex, stencil)

    def test_month_set_custom(self):
        '''Test month_set method with custom field'''
        func.logtest('Assert return from month_set method - custom field:')
        self.ncf.custom = '_field'
        self.ncf.start_date = ('2000', '12', '01')
        regex = netcdf_filenames.month_set(self.ncf)
        stencil = '^model_suitex_1x_200012\\d{2}-(200012\\d{2}|20010101)' \
            '_field\\.nc$'
        self.assertEqual(regex, stencil)

    def test_season_set(self):
        '''Test season_set method'''
        func.logtest('Assert return from season_set method:')
        # ncf.start_date is start date of periodend - month=[02|05|08|11]
        self.ncf.start_date = ('2000', '02', '01')
        regex = netcdf_filenames.season_set(self.ncf)
        stencil = '^model_suitex_1m_\\d{6}01-2000(01|02|03)01\\.nc$'
        self.assertEqual(regex, stencil)

    def test_season_set_custom(self):
        '''Test season_set method with custom field'''
        func.logtest('Assert return from season_set method - custom field:')
        # ncf.start_date is start date of periodend - month=[02|05|08|11]
        self.ncf.start_date = ('2000', '08', '01')
        self.ncf.custom = '_field'
        regex = netcdf_filenames.season_set(self.ncf)
        stencil = '^model_suitex_1m_\\d{6}01-2000(07|08|09)01_field\\.nc$'
        self.assertEqual(regex, stencil)

    def test_year_set(self):
        '''Test year_set method'''
        func.logtest('Assert return from year_set method:')
        # ncf.start_date is start date of periodend - Set files end in start_yr
        self.ncf.start_date = ('2000', 'XX', 'XX')
        regex = netcdf_filenames.year_set(self.ncf)
        stencil = '^model_suitex_1s_\\d{6}01-2000\\d{2}01\\.nc$'
        self.assertEqual(regex, stencil)

    def test_year_set_custom(self):
        '''Test year_set method with custom field'''
        func.logtest('Assert return from year_set method - custom field:')
        # ncf.start_date is start date of periodend - Set files end in start_yr
        self.ncf.start_date = ('2000', 'XX', 'XX')
        self.ncf.custom = '_field'
        regex = netcdf_filenames.year_set(self.ncf)
        stencil = '^model_suitex_1s_\\d{6}01-2000\\d{2}01_field\\.nc$'
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
