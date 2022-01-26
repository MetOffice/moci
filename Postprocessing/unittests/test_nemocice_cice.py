#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2022 Met Office. All rights reserved.

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
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
    import mock

import testing_functions as func
import runtime_environment

# Import of cice requires 'RUNID' from runtime environment
runtime_environment.setup_env()
import cice


class StencilTests(unittest.TestCase):
    '''Unit tests relating to the CICE output filename stencils'''
    def setUp(self):
        self.files = [
            'RUNIDi.restart.1981-12-01-00000',
            'RUNIDi.restart.1981-12-01-00000.nc',
            'RUNIDi.6h.1985-11-11-13.nc',
            'RUNIDi.5d.1985-11-06.nc',
            'RUNIDi.10d.1985-11-11.nc',
            'RUNIDi.1m.1985-11.nc',
            'RUNIDi.1m.1985-11-03.nc',
            ]
        self.cice = cice.CicePostProc()
        self.cice.suite = mock.Mock()
        self.cice.suite.prefix = 'RUNID'

    def tearDown(self):
        for fname in runtime_environment.RUNTIME_FILES:
            try:
                os.remove(fname)
            except OSError:
                pass

    def test_rst_set_stencil(self):
        '''Test the regular expressions of the rst_set_stencil method'''
        func.logtest('Assert restart pattern matching of set_stencil:')
        patt = re.compile(self.cice.rst_set_stencil(''))
        cice_rst = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(cice_rst,
                         [fname for fname in self.files if 'restart' in fname])

    def test_general_mean_stencil(self):
        '''Test the regular expressions of the general_mean_stencil method'''
        func.logtest('Assert general pattern matching of mean_stencil:')
        patt = re.compile(self.cice.general_mean_stencil('FIELD'))
        gen_set = [fname for fname in self.files if patt.search(fname)]
        expected_set = [fname for fname in self.files if not
                        re.match(r'.*(1m|restart)\.\d{4}-\d{2}-\d{2}.*', fname)]
        self.assertEqual(gen_set, expected_set)

    def test_general_mean_stencil_6hr(self):
        '''Test the regular expressions of general_mean_stencil - hourly'''
        func.logtest('Assert hourly pattern matching of general_mean_stencil:')
        patt = re.compile(self.cice.mean_stencil('FIELD', base='6h'))
        sixhr_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(sixhr_set,
                         [fname for fname in self.files if '.6h.' in fname])

    def test_general_mean_stencil_10d(self):
        '''Test the regular expressions of general_mean_stencil - daily'''
        func.logtest('Assert daily pattern matching of general_mean_stencil:')
        patt = re.compile(self.cice.general_mean_stencil('FIELD', base='10d'))
        tenday_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(tenday_set,
                         [fname for fname in self.files if '.10d.' in fname])

    def test_general_mean_stencil_1m(self):
        '''Test the regular expressions of t general_mean_stencil - monthly'''
        func.logtest('Assert monthly pattern matching of general_mean_stencil:')
        patt = re.compile(self.cice.general_mean_stencil('FIELD', base='1m'))
        month_set = [fname for fname in self.files if patt.search(fname)]
        self.assertEqual(month_set,
                         [fname for fname in self.files if '.1m.' in fname])


class UtilityMethodTests(unittest.TestCase):
    '''Unit tests relating to the CICE utility methods'''
    def setUp(self):
        self.cice = cice.CicePostProc()
        self.cice.suite = mock.Mock()

    def tearDown(self):
        try:
            os.remove('nemocicepp.nl')
        except OSError:
            pass

    def test_get_date_yyyymmddhh(self):
        '''Test get_date method - YYYY-MM-DD format'''
        func.logtest('Assert functionality of get_date (YYYY-MM-DD-HH):')
        func.logtest('Testing file: ' + 'RUNIDi.6h.1982-11-01-05.nc')
        self.assertTupleEqual(self.cice.get_date('RUNIDi.6h.1982-11-01-05.nc'),
                              ('1982', '11', '01', '00'))
        func.logtest('Testing file: ' + 'RUNIDi.12h.1982-11-01-23.nc')
        self.assertTupleEqual(self.cice.get_date('RUNIDi.12h.1982-11-01-23.nc'),
                              ('1982', '11', '01', '12'))
        func.logtest('Testing file: ' + 'RUNIDi.12h.1982-11-01-05.nc')
        self.assertTupleEqual(self.cice.get_date('RUNIDi.12h.1982-11-01-05.nc'),
                              ('1982', '10', '30', '18'))

    def test_get_enddate_yyyymmddhh(self):
        '''Test get_date method - YYYY-MM-DD format - enddate'''
        func.logtest('Assert functionality of get_date (YYYY-MM-DD-HH) - end:')
        func.logtest('Testing file: ' + 'RUNIDi.6h.1982-11-01-05.nc')
        self.assertTupleEqual(
            self.cice.get_date('RUNIDi.6h.1982-11-01-05.nc', enddate=True),
            ('1982', '11', '01', '05')
            )
        func.logtest('Testing file: ' + 'RUNIDi.12h.1982-11-30-23.nc')
        self.assertTupleEqual(
            self.cice.get_date('RUNIDi.12h.1982-11-30-23.nc', enddate=True),
            ('1982', '11', '30', '23')
            )

    def test_get_date_yyyymmdd(self):
        '''Test get_date method - YYYY-MM-DD format'''
        func.logtest('Assert functionality of get_date method (YYYY-MM-DD):')
        func.logtest('Testing file: ' + 'RUNIDi.restart.1982-11-01-00000.nc')
        self.assertTupleEqual(
            self.cice.get_date('RUNIDi.restart.1982-11-01-00000.nc'),
            ('1982', '11', '01')
            )
        func.logtest('Testing file: ' + 'RUNIDi.1d.1982-11-10.nc')
        self.assertTupleEqual(self.cice.get_date('RUNIDi.1d.1982-11-10.nc'),
                              ('1982', '11', '10'))
        func.logtest('Testing file: ' + 'RUNIDi.10d.1982-11-10.nc')
        self.assertTupleEqual(self.cice.get_date('RUNIDi.10d.1982-11-10.nc'),
                              ('1982', '11', '01'))

    def test_get_enddate_yyyymmdd(self):
        '''Test get_date method - YYYY-MM-DD format - enddate'''
        func.logtest('Assert functionality of get_date (YYYY-MM-DD) - end:')
        func.logtest('Testing file: ' + 'RUNIDi.1d.1982-11-10.nc')
        self.assertTupleEqual(
            self.cice.get_date('RUNIDi.1d.1982-11-10.nc', enddate=True),
            ('1982', '11', '10')
            )
        func.logtest('Testing file: ' + 'RUNIDi.10d.1982-11-10.nc')
        self.assertTupleEqual(
            self.cice.get_date('RUNIDi.10d.1982-11-10.nc', enddate=True),
            ('1982', '11', '10')
            )

    def test_get_date_yyyymm(self):
        '''Test get_date method - YYYY-MM format'''
        func.logtest('Assert functionality of get_date method (YYYY-MM):')
        func.logtest('Testing file: ' + 'RUNIDi.1m.1982-11.nc')
        self.assertTupleEqual(self.cice.get_date('RUNIDi.1m.1982-11.nc'),
                              ('1982', '11', '01'))
        func.logtest('Testing file: ' + 'RUNIDi.1m.1983-01.nc')
        self.assertTupleEqual(self.cice.get_date('RUNIDi.1m.1983-01.nc'),
                              ('1983', '01', '01'))

    def test_get_enddate_yyyymm(self):
        '''Test get_date method - YYYY-MM format - enddate'''
        func.logtest('Assert functionality of get_date (YYYY-MM) - end:')
        self.cice.suite.monthlength.return_value = 25
        func.logtest('Testing file: ' + 'RUNIDi.1m.1982-06.nc')
        self.assertTupleEqual(
            self.cice.get_date('RUNIDi.1m.1982-06.nc', enddate=True),
            ('1982', '06', '25')
            )
        func.logtest('Testing file: ' + 'RUNIDi.1m.1982-12.nc')
        self.assertTupleEqual(
            self.cice.get_date('RUNIDi.1m.1982-12.nc', enddate=True),
            ('1982', '12', '25')
            )

    def test_get_date_failure(self):
        '''Test get_date method - catch failure'''
        func.logtest('Assert error trapping in get_date method:')
        date = self.cice.get_date('RUNIDi_1m_YYYY-MM-DD.nc')
        self.assertTupleEqual(date, (None,)*3)
        self.assertIn('[WARN]  Unable to get date', func.capture('err'))

    @mock.patch('cice.utils.get_subset', return_value=['RUNIDi.1d.1111-22.nc'])
    @mock.patch('cice.os.rename')
    @mock.patch('cice.mt.ModelTemplate.move_to_share')
    def test_move_to_share(self, mock_mts, mock_rename, mock_set):
        '''Test move_to_share method'''
        func.logtest('Assert call to super(move_to_share):')
        self.cice.work = 'WorkDir'
        with mock.patch('cice.mt.ModelTemplate.prefix',
                        new_callable=mock.PropertyMock,
                        return_value='RUNID'):
            self.cice.move_to_share()
        mock_set.assert_called_once_with('WorkDir',
                                         r'^RUNIDi\.1d\.\d{4}-\d{2}\.nc$')
        mock_rename.assert_called_once_with('WorkDir/RUNIDi.1d.1111-22.nc',
                                            'WorkDir/RUNIDi.1m.1111-22.nc')
        mock_mts.assert_called_once_with(pattern=None)

    @mock.patch('cice.utils.get_subset', return_value=['RUNIDi.1d.1111-22.nc'])
    @mock.patch('cice.os.rename')
    @mock.patch('cice.mt.ModelTemplate.move_to_share')
    def test_move_to_share_pattern(self, mock_mts, mock_rename, mock_set):
        '''Test move_to_share method with pattern'''
        func.logtest('Assert call to super(move_to_share) with pattern:')
        self.cice.work = 'WorkDir'
        with mock.patch('cice.mt.ModelTemplate.prefix',
                        new_callable=mock.PropertyMock,
                        return_value='RUNID'):
            self.cice.move_to_share(pattern='pattern')
        mock_set.assert_called_once_with('WorkDir',
                                         r'^RUNIDi\.1d\.\d{4}-\d{2}\.nc$')
        mock_rename.assert_called_once_with('WorkDir/RUNIDi.1d.1111-22.nc',
                                            'WorkDir/RUNIDi.1m.1111-22.nc')
        mock_mts.assert_called_once_with(pattern='pattern')

class MeansProcessingTests(unittest.TestCase):
    '''Unit tests relating to the processing of means files'''
    def setUp(self):
        self.cice = cice.CicePostProc()
        self.cice.share = self.cice.work = '.'
        self.cice.suite = mock.Mock()
        self.cice.suite.prefix = 'RUNID'
        self.cice.suite.preprocess_file.return_value = 0
        self.cice.suite.monthlength.return_value = 30

    def tearDown(self):
        for fname in ['nemocicepp.nl']:
            try:
                os.remove(fname)
            except OSError:
                pass

    @mock.patch('cice.utils.get_subset')
    @mock.patch('cice.CicePostProc.move_to_share')
    @mock.patch('cice.utils.remove_files')
    @mock.patch('cice.netcdf_filenames.os.rename')
    def test_create_concat_daily(self, mock_rn, mock_rm, mock_mv, mock_set):
        '''Test method to compile list of means to concatenate'''
        func.logtest('Assert compilation of means to concatenate:')
        catsets = ['SET' + str(i) for i in range(1, 30)]
        mock_set.side_effect = [['END.1111-02-01.nc'], catsets]
        _ = self.cice.create_concat_daily_means()
        procsets = sorted(['./' + s for s in catsets])
        self.cice.suite.preprocess_file.assert_called_with(
            'ncrcat', ['./END.1111-02-01.nc'] + procsets,
            outfile='./cicecat'
            )
        self.assertEqual(mock_mv.mock_calls, [])
        self.assertListEqual(sorted(mock_rm.call_args[0][0]),
                             sorted(['./END.1111-02-01.nc'] + procsets))

        mock_rn.assert_called_once_with('./cicecat',
                                        './cice_runidi_1d_11110101-11110201.nc')
        # Check call to get_subset for end-of-set files:
        self.assertEqual(mock_set.mock_calls[0],
                         mock.call('.', r'^RUNIDi\.[0-9hdm]*_?24h\.\d{4}' +
                                   r'-\d{2}-01(-\d{5})?\.nc$'))
        # Check call to get_subset for 1m-set of files:
        self.assertEqual(mock_set.mock_calls[1],
                         mock.call('.', r'^RUNIDi\.[0-9hdm]*_?24h\.1111-01-' +
                                   r'(0[2-9]|[1-3][0-9])(-\d{5})?\.nc$'))

    @mock.patch('cice.utils.get_subset')
    @mock.patch('cice.utils.remove_files')
    @mock.patch('cice.netcdf_filenames.os.rename')
    def test_create_concat_1dfiles(self, mock_rn, mock_rm, mock_set):
        '''Test compile list of means to concatenate: _1d_ Gregorian files'''
        func.logtest('Assert compilation of means to concatenate - _1d_ files:')
        self.cice.suite.meanref = [0, 12, 1]
        catsets = ['SET' + str(i) for i in range(1, 31)]
        mock_set.side_effect = [[],
                                ['END_1d_11110228-11110301.nc'],
                                catsets]

        with mock.patch('cice.utils.calendar', return_value='gregorian'):
            _ = self.cice.create_concat_daily_means()
            procsets = sorted(['./' + s for s in catsets])
            self.cice.suite.preprocess_file.assert_called_with(
                'ncrcat', procsets,
                outfile='./cicecat'
            )
        self.assertListEqual(sorted(mock_rm.call_args[0][0]),
                             sorted(procsets))

        mock_rn.assert_called_once_with(
            './cicecat',
            './cice_runidi_1d_11110201-11110301.nc'
        )
        # Check call to get_subset for end-of-set files:
        self.assertEqual(mock_set.mock_calls[0],
                         mock.call('.', r'^RUNIDi\.[0-9hdm]*_?24h\.\d{4}' +
                                   r'-\d{2}-01(-\d{5})?\.nc$'))
        # Check call to get_subset for netCDF fname object:
        self.assertEqual(mock_set.mock_calls[1],
                         mock.call('.', r'^cice_runidi_1d_\d{8,10}-\d{4}' +
                                   r'\d{2}01(00)?\.nc$'))

        self.assertEqual(
            mock_set.mock_calls[2],
            mock.call('.', '^cice_runidi_1d_(11110201|11110202|11110203|' +
                      '11110204|11110205|11110206|11110207|11110208|' +
                      '11110209|11110210|11110211|11110212|11110213|' +
                      '11110214|11110215|11110216|11110217|11110218|' +
                      '11110219|11110220|11110221|11110222|11110223|' +
                      '11110224|11110225|11110226|11110227|11110228)' +
                      r'(\d{2})?-\d{8,10}\.nc$')
        )

    @mock.patch('cice.utils.get_subset')
    @mock.patch('cice.utils.remove_files')
    @mock.patch('cice.netcdf_filenames.os.rename')
    def test_create_concat_shift_year(self, mock_rn, mock_rm, mock_set):
        '''Test method to compile list of means to concatenate - year shift'''
        func.logtest('Assert compilation of means to concatenate - yr shift:')
        catsets = ['SET' + str(i) for i in range(1, 30)]
        mock_set.side_effect = [['END.1111-01-01.nc'], catsets, []]
        _ = self.cice.create_concat_daily_means()
        procsets = sorted(['./' + s for s in catsets])
        self.cice.suite.preprocess_file.assert_called_with(
            'ncrcat', ['./END.1111-01-01.nc'] + procsets,
            outfile='./cicecat'
            )
        self.assertListEqual(sorted(mock_rm.call_args[0][0]),
                             sorted(['./END.1111-01-01.nc'] + procsets))

        mock_rn.assert_called_once_with('./cicecat',
                                        './cice_runidi_1d_11101201-11110101.nc')

    def test_create_concat_patterns(self):
        '''Test method to compile list of means to concatenate - patterns'''
        func.logtest('Assert compilation of means to concatenate - patterns:')
        meanfiles = [
            'RUNIDi.10d_24h.1987-12-13.nc',
            'RUNIDi.10d_24h.1988-01-01.nc',
            'RUNIDi.10d_24h.1988-01-02.nc',
            'RUNIDi.10d_24h.1988-01-17.nc',
            'RUNIDi.10d_24h.1988-01-30.nc',
            'RUNIDi.10d_24h.1988-02-01.nc',
            'RUNIDi.10d_24h.1988-02-10.nc',
            'RUNIDi.24h.1989-05-01.nc',
            'RUNIDi.1m_24h.1990-06-01.nc',
            ]
        for fname in meanfiles:
            open(fname, 'w').close()

        with mock.patch('cice.utils.log_msg') as mock_log:
            # Mock log since it would raise a SystemExit due to number of
            # matching files being less than 30
            _ = self.cice.create_concat_daily_means()
        self.assertIn('only got 2 files:', str(mock_log.mock_calls[0]))
        self.assertIn('only got 4 files:', str(mock_log.mock_calls[1]))
        self.assertIn(r"only got 1 files:\n['RUNIDi.1m_24h.1990-06-01.nc']",
                      str(mock_log.mock_calls[2]))
        self.assertIn(r"only got 1 files:\n['RUNIDi.24h.1989-05-01.nc']",
                      str(mock_log.mock_calls[3]))
        self.assertEqual(mock_log.call_count, 4)

        for fname in meanfiles:
            os.remove(fname)

    @mock.patch('cice.CicePostProc.move_to_share')
    def test_create_concat_move(self, mock_mv):
        '''Test method to compile list of means to concatenate - move'''
        func.logtest('Assert compilation of means to concatenate - move:')
        self.cice.work = 'TestDir'
        with mock.patch('cice.utils.get_subset', return_value=[]):
            with mock.patch('cice.mt.ModelTemplate.end_stencil'):
                self.cice.create_concat_daily_means()
        mock_mv.assert_called_once_with(pattern=mock.ANY)

    @mock.patch('cice.utils.get_subset')
    def test_create_concat_insuffient(self, mock_set):
        '''Test concatenation of means - insufficent components'''
        func.logtest('Assert concatenation not possible:')
        mock_set.side_effect = [['END.1111-22-33.nc'], ['SET1', 'SET2']]
        with self.assertRaises(SystemExit):
            self.cice.create_concat_daily_means()
        self.assertIn('only got 3 files', func.capture('err'))

    @mock.patch('cice.utils.get_subset')
    def test_create_concat_fail_debug(self, mock_set):
        '''Test concatenation of means with insufficent components - debug'''
        func.logtest('Assert concatenation not possible - debug mode:')
        mock_set.side_effect = [['END.1111-22-33.nc'], ['SET1', 'SET2']]
        with mock.patch('cice.utils.get_debugmode', return_value=True):
            self.cice.create_concat_daily_means()
        self.assertIn('only got 3 files', func.capture('err'))

    @mock.patch('cice.utils.remove_files')
    @mock.patch('cice.mt.ModelTemplate.archive_files')
    def test_archive_concat_daily(self, mock_arch, mock_rm):
        '''Test concatenation of means - archive'''
        func.logtest('Assert archive of catted file:')
        mock_arch.return_value = {'ARCH1': 'SUCCESS', 'ARCH2': 'SUCCESS'}
        with mock.patch('cice.utils.get_subset'):
            self.cice.archive_concat_daily_means()
        mock_rm.assert_called_once_with(['ARCH1', 'ARCH2'], path='.')

    @mock.patch('cice.utils.remove_files')
    @mock.patch('cice.mt.ModelTemplate.archive_files')
    def test_archive_concat_daily_fail(self, mock_arch, mock_rm):
        '''Test concatenation of means - failed to archive'''
        func.logtest('Assert failure to archive catted file:')
        mock_arch.return_value = {'ARCH1': 'FAILED', 'ARCH2': 'SUCCESS'}
        with mock.patch('cice.utils.get_subset'):
            self.cice.archive_concat_daily_means()
        mock_rm.assert_called_with(['ARCH2'], path='.')

    @mock.patch('cice.os.rename')
    @mock.patch('cice.mt.ModelTemplate.archive_files')
    def test_archive_concat_daily_debug(self, mock_arch, mock_rm):
        '''Test concatenation of means - archive'''
        func.logtest('Assert archive of catted file:')
        mock_arch.return_value = {'ARCH1': 'FAILED', 'ARCH2': 'SUCCESS'}
        with mock.patch('utils.get_debugmode', return_value=True):
            with mock.patch('cice.utils.get_subset'):
                self.cice.archive_concat_daily_means()
        self.assertIn('means: deleting archived file(s)', func.capture())
        mock_rm.assert_called_once_with('./ARCH2', './ARCH2_ARCHIVED')
