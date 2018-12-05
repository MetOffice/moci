#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2018 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''
import os
import unittest
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
    import mock

import testing_functions as func

import climatemean


class InputNamelist(object):
    ''' Dummy object representing an input namelist '''
    def __init__(self):
        self.create_monthly_mean = True
        self.create_seasonal_mean = True
        self.create_annual_mean = True

    def set_base(self, base):
        ''' Set optional attribute: base_component '''
        setattr(self, 'base_component', base)

    def set_mean(self, mean, val):
        ''' Set optional attribute: base_component '''
        setattr(self, 'create_{}_mean'.format(mean), val)


class MeanFileTests(unittest.TestCase):
    ''' Unit tests for the MeanFile class '''
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_meanfile_instantiation(self):
        '''Test instantiation of a MeanFile object'''
        func.logtest('Assert instantiation of a MeanFile object:')
        meanfile = climatemean.MeanFile('1s', '12h')
        self.assertEqual(meanfile.period, '1s')
        self.assertEqual(meanfile.title, 'Seasonal')
        self.assertEqual(meanfile.component, '12h')
        self.assertEqual(meanfile.num_components, 2*30*3)
        self.assertListEqual(meanfile.component_files, [])
        self.assertEqual(meanfile.fname, {})

    def test_num_components(self):
        '''Test calculation of number of components'''
        func.logtest('Assert correct calculation of number of components:')
        meanfile = climatemean.MeanFile('1m', '12h')
        self.assertEqual(meanfile.num_components, 2*30)
        meanfile = climatemean.MeanFile('1m', '1d')
        self.assertEqual(meanfile.num_components, 30)
        meanfile = climatemean.MeanFile('1m', '1m')
        self.assertEqual(meanfile.num_components, 1)
        meanfile = climatemean.MeanFile('1s', '1m')
        self.assertEqual(meanfile.num_components, 3)
        meanfile = climatemean.MeanFile('1y', '1s')
        self.assertEqual(meanfile.num_components, 4)
        meanfile = climatemean.MeanFile('1x', '1y')
        self.assertEqual(meanfile.num_components, 10)
        meanfile = climatemean.MeanFile('1m', 'qm')
        self.assertEqual(meanfile.num_components, 1)

    def test_num_components_gregorian(self):
        '''Test calculation of number of components'''
        func.logtest('Assert correct calculation of number of components:')
        with mock.patch('climatemean.utils.calendar', return_value='gregorian'):
            meanfile = climatemean.MeanFile('1m', '12h')
            self.assertEqual(meanfile.num_components, None)
            meanfile = climatemean.MeanFile('1m', '1d')
            self.assertEqual(meanfile.num_components, None)
            meanfile = climatemean.MeanFile('1m', '1m')
            self.assertEqual(meanfile.num_components, 1)
            meanfile = climatemean.MeanFile('1s', '1m')
            self.assertEqual(meanfile.num_components, 3)
            meanfile = climatemean.MeanFile('1y', '1s')
            self.assertEqual(meanfile.num_components, 4)
            meanfile = climatemean.MeanFile('1x', '1y')
            self.assertEqual(meanfile.num_components, 10)

    def test_describe_mean_monthly(self):
        '''Test compostion of mean description - monthly'''
        func.logtest('Assert correct composition of monthly mean description:')
        meanfile = climatemean.MeanFile('1m', '10d')
        meanfile.periodend = ('1111', '07', '01')
        self.assertIn('Monthly mean for June 1111',
                      meanfile.description)

    def test_describe_mean_mth_field(self):
        '''Test compostion of mean description - monthly field'''
        func.logtest('Assert correct composition of monthly mean description:')
        meanfile = climatemean.MeanFile('1m', '10d')
        meanfile.periodend = ('1111', '07', '01')
        meanfile.set_title(prefix='FIELD')
        self.assertIn('FIELD Monthly mean for June 1111',
                      meanfile.description)

    def test_describe_mean_seasonal(self):
        '''Test compostion of mean description - seasonal'''
        func.logtest('Assert correct composition of seasonal mean description:')
        meanfile = climatemean.MeanFile('1s', '1m')
        meanfile.periodend = ['1111', '09', '01']
        self.assertIn('Seasonal mean for Summer 1111',
                      meanfile.description)

        meanfile.periodend = ('1112', '03', '01')
        self.assertIn('Seasonal mean for Winter, ending 1112',
                      meanfile.description)

        meanfile.periodend = ['1111', '05', '01']
        self.assertIn('Seasonal mean for Feb-Mar-Apr 1111',
                      meanfile.description)

        meanfile.periodend = ('1111', '01', '01')
        self.assertIn('Seasonal mean for Oct-Nov-Dec 1110',
                      meanfile.description)

        meanfile.periodend = ('1111', '02', '01')
        self.assertIn('Seasonal mean for Nov-Dec-Jan, ending 1111',
                      meanfile.description)

    def test_describe_mean_annual(self):
        '''Test compostion of mean description - annual'''
        func.logtest('Assert correct composition of annual mean description:')
        meanfile = climatemean.MeanFile('1y', '1s')
        meanfile.periodend = ('2003', '01', '01')
        self.assertIn('Annual mean for year ending December 2002',
                      meanfile.description)

        meanfile.periodend = ('2002', '04', '01')
        self.assertIn('Annual mean for year ending March 2002',
                      meanfile.description)

    def test_describe_mean_decadal(self):
        '''Test compostion of mean description - decadal'''
        func.logtest('Assert correct composition of decadal mean description:')
        meanfile = climatemean.MeanFile('1x', '1y')
        meanfile.periodend = ('2012', '01', '01')
        self.assertIn('Decadal mean for period ending December 2011',
                      meanfile.description)

        meanfile.periodend = ('2011', '04', '01')
        self.assertIn('Decadal mean for period ending March 2011',
                      meanfile.description)

    def test_describe_mean_unknown(self):
        '''Test compostion of mean description - unknown period'''
        func.logtest('Assert correct composition of unknown mean description:')
        meanfile = climatemean.MeanFile('1z', '1m')
        meanfile.periodend = ('2001', '05', '01')
        self.assertIn('Unknown mean for period ending April 2001',
                      meanfile.description)

    def test_set_filename(self):
        '''Test population of the filename property'''
        func.logtest('Assert population of the filename property:')
        meanfile = climatemean.MeanFile('', '')
        self.assertEqual(meanfile.fname, {})
        meanfile.set_filename('MeanFileName', os.getcwd())
        self.assertEqual(meanfile.fname['full'],
                         os.path.join(os.getcwd(), 'MeanFileName'))
        self.assertEqual(meanfile.fname['file'], 'MeanFileName')
        self.assertEqual(meanfile.fname['path'], os.getcwd())

    def test_set_filname_fail(self):
        '''Test failure to populate of the filename property'''
        func.logtest('Assert failure to populate of the filename property:')
        meanfile = climatemean.MeanFile('', '')
        with self.assertRaises(SystemExit):
            meanfile.set_filename('MeanFileName', 'NoDir')
        self.assertIn('Directory does not exist: NoDir', func.capture('err'))

    def test_set_title(self):
        '''Test creation of the mean title'''
        func.logtest('Assert creation of the mean title:')
        meanfile = climatemean.MeanFile('1m', '')
        self.assertEqual(meanfile.title, 'Monthly')
        meanfile = climatemean.MeanFile('1s', '')
        meanfile.set_title(prefix='FIELD')
        self.assertEqual(meanfile.title, 'FIELD Seasonal')


class MeansMethodsTests(unittest.TestCase):
    ''' Unit tests for the module level methods relating to climate means '''
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_available_means(self):
        ''' Test instantiation of MeansRequest object '''
        func.logtest('Assert successful instantiation of MeansRequest object:')
        namelist = InputNamelist()

        namelist.set_mean('annual', False)
        namelist.set_base('6h')
        avail = climatemean.available_means(namelist)
        self.assertEqual(len(avail), 2)
        self.assertEqual(avail['1m'].component, '6h')
        self.assertEqual(avail['1m'].num_components, 4*30)
        self.assertEqual(avail['1s'].component, '1m')
        self.assertEqual(avail['1s'].num_components, 3)

        namelist.set_base('10d')
        avail = climatemean.available_means(namelist)
        self.assertEqual(len(avail), 2)
        self.assertEqual(avail['1m'].component, '10d')
        self.assertEqual(avail['1m'].num_components, 3)
        self.assertEqual(avail['1s'].component, '1m')
        self.assertEqual(avail['1s'].num_components, 3)

        namelist.set_mean('seasonal', False)
        namelist.set_mean('decadal', True)
        namelist.set_base('1m')
        avail = climatemean.available_means(namelist)
        self.assertEqual(len(avail), 2)
        self.assertEqual(avail['1m'].component, '1m')
        self.assertEqual(avail['1m'].num_components, 1)
        self.assertEqual(avail['1x'].component, '1m')
        self.assertEqual(avail['1x'].num_components, 3*4*10)

    def test_available_means_reject(self):
        ''' Test rejected means with invalid component '''
        func.logtest('Assert rejected means with invalid component:')
        namelist = InputNamelist()
        namelist.set_mean('decadal', True)
        namelist.set_base('2m')
        avail = climatemean.available_means(namelist)
        self.assertEqual(len(avail), 2)
        self.assertIn('rejected: 1m', func.capture('err'))
        self.assertIn('rejected: 1s', func.capture('err'))
        self.assertEqual(avail['1y'].component, '2m')
        self.assertEqual(avail['1y'].num_components, 6)
        self.assertEqual(avail['1x'].component, '1y')
        self.assertEqual(avail['1x'].num_components, 10)

    def test_available_means_greg(self):
        '''Test rejected means with invalid Gregorian components'''
        func.logtest('Assert rejected means with invalid Gregorian components:')
        namelist = InputNamelist()
        namelist.set_mean('seasonal', False)
        namelist.set_mean('annual', False)
        namelist.set_base('6h')
        with mock.patch('climatemean.utils.calendar',
                        return_value='Gregorian'):
            avail = climatemean.available_means(namelist)
            self.assertEqual(len(avail), 0)
            self.assertIn('rejected: 1m', func.capture('err'))

            namelist.set_mean('seasonal', True)
            namelist.set_base('10d')
            avail = climatemean.available_means(namelist)
            self.assertEqual(len(avail), 0)
            self.assertIn('rejected: 1s', func.capture('err'))

            namelist.set_mean('seasonal', False)
            namelist.set_mean('decadal', True)
            namelist.set_base('1m')
            avail = climatemean.available_means(namelist)
            self.assertEqual(avail['1m'].component, '1m')
            self.assertEqual(avail['1m'].num_components, 1)
            self.assertEqual(avail['1x'].component, '1m')
            self.assertEqual(avail['1x'].num_components, 12*10)

    def test_default_base_component(self):
        '''Test the default base component setting for available means'''
        func.logtest('Assert correct default setting for base component:')
        namelist = InputNamelist()
        namelist.set_mean('monthly', False)
        _ = climatemean.available_means(namelist)

        self.assertIn('Assuming first request (1s) is the base',
                      func.capture('err'))

    def test_monthly_mean_spinup(self):
        '''Test evaluation of the spinup period for monthly means'''
        func.logtest('Assert correct evaluation of the month spinup period:')
        monthmean = climatemean.MeanFile('1m', '10d')

        monthmean.periodend = ('1995', '08', '01')
        self.assertTrue(climatemean.mean_spinup(monthmean, [1995, 8, 1, 0, 0]))

        monthmean.periodend = ('1995', '08', '11')
        self.assertTrue(climatemean.mean_spinup(monthmean, [1995, 8, 1, 0, 0]))

        monthmean.periodend = ('1995', '09', '01')
        self.assertFalse(climatemean.mean_spinup(monthmean, [1995, 8, 1, 0, 0]))

        monthmean.periodend = ('1995', '09', '01')
        self.assertTrue(climatemean.mean_spinup(monthmean, [1995, 8, 11, 0, 0]))

        monthmean.periodend = ('1995', '09', '11')
        self.assertFalse(climatemean.mean_spinup(monthmean,
                                                 [1995, 8, 11, 0, 0]))

    @mock.patch('climatemean.utils.exec_subproc', return_value=(0, ''))
    @mock.patch('climatemean.os.rename')
    def test_create_mean_monthly_5dbase(self, mock_rename, mock_exec):
        '''Test successful creation of monthly mean'''
        func.logtest('Assert successful creation of monthly mean:')
        monthly = climatemean.MeanFile('1m', '5d')
        monthly.set_filename('MeanFileName', os.getcwd())
        monthly.component_files = ['F' + str(x) for x in range(1, 7)]

        with mock.patch('climatemean.os.path.isfile',
                        side_effect=[False, False, True, True]):
            # Side effects:
            #   False - Pre-existing mean not present
            #   False - Completed meanfile not present
            #   True  - Temporary meanfile present
            #   True  - Temporary meanfile present
            with mock.patch('climatemean.MeanFile.description',
                            new_callable=mock.PropertyMock,
                            return_value='FIELD monthly mean for PERIOD'):
                climatemean.create_mean(monthly, 'exec arg1 path/MeanFileName',
                                        [0]*5)

        mock_exec.assert_called_once_with('exec arg1 path/MeanFileName.tmp',
                                          cwd=os.getcwd())
        self.assertIn('Created FIELD monthly mean for PERIOD: MeanFileName',
                      func.capture())
        mock_rename.assert_called_once_with(
            os.path.join(os.getcwd(), 'MeanFileName.tmp'),
            os.path.join(os.getcwd(), 'MeanFileName')
            )

    @mock.patch('climatemean.utils.exec_subproc', return_value=(0, ''))
    def test_create_mean_monthly_1mbase(self, mock_exec):
        '''Test successful creation of monthly mean'''
        func.logtest('Assert successful creation of monthly mean:')
        monthly = climatemean.MeanFile('1m', '1m')
        monthly.set_filename('MeanFileName', os.getcwd())

        with mock.patch('climatemean.os.path.isfile', side_effect=[True]):
            # Side effects:
            #   True - Pre-existing mean present
            with mock.patch('climatemean.MeanFile.description',
                            new_callable=mock.PropertyMock,
                            return_value='FIELD monthly mean for PERIOD'):
                climatemean.create_mean(monthly, 'exec arg1 arg2', [0]*5)

        self.assertFalse(mock_exec.called)

    @mock.patch('climatemean.utils.exec_subproc', return_value=(0, ''))
    @mock.patch('climatemean.os.rename')
    def test_create_mean_seasonal(self, mock_rename, mock_exec):
        '''Test successful creation of seasonal mean'''
        func.logtest('Assert successful creation of seasonal mean:')
        seasonal = climatemean.MeanFile('1s', '1m')
        seasonal.set_filename('MeanFileName', os.getcwd())
        seasonal.component_files = ['F' + str(x) for x in range(1, 4)]

        with mock.patch('climatemean.os.path.isfile',
                        side_effect=[False, True, False]):
            # Side effects:
            #   False - Pre-existing mean not present
            #   True  - Completed meanfile present
            #   False - Temporary meanfile not present
            with mock.patch('climatemean.MeanFile.description',
                            new_callable=mock.PropertyMock,
                            return_value='FIELD seasonal mean for PERIOD'):
                climatemean.create_mean(seasonal, 'exec arg1 arg2', [0]*5)

        mock_exec.assert_called_once_with('exec arg1 arg2', cwd=os.getcwd())
        self.assertIn('Created FIELD seasonal mean for PERIOD: MeanFileName',
                      func.capture())
        self.assertFalse(mock_rename.called)

    @mock.patch('climatemean.utils.exec_subproc', return_value=(0, ''))
    @mock.patch('climatemean.os.rename')
    def test_create_mean_annual(self, mock_rename, mock_exec):
        '''Test successful creation of annual mean'''
        func.logtest('Assert successful creation of annual mean:')
        annual = climatemean.MeanFile('1y', '1s')
        annual.set_filename('MeanFileName', os.getcwd())
        annual.component_files = ['F' + str(x) for x in range(1, 5)]

        with mock.patch('climatemean.os.path.isfile',
                        side_effect=[False, True, False]):
           # Side effects:
            #   False - Pre-existing mean not present
            #   True  - Completed meanfile present
            #   False - Temporary meanfile not present
            with mock.patch('climatemean.MeanFile.description',
                            new_callable=mock.PropertyMock,
                            return_value='FIELD annual mean for PERIOD'):
                climatemean.create_mean(annual, 'exec arg1 arg2', [0]*5)

        mock_exec.assert_called_once_with('exec arg1 arg2', cwd=os.getcwd())
        self.assertIn('Created FIELD annual mean for PERIOD: MeanFileName',
                      func.capture())
        self.assertFalse(mock_rename.called)


    @mock.patch('climatemean.utils.exec_subproc', return_value=(0, ''))
    @mock.patch('climatemean.os.rename')
    def test_create_mean_decadal(self, mock_rename, mock_exec):
        '''Test successful creation of decadal mean'''
        func.logtest('Assert successful creation of decadal mean:')
        decadal = climatemean.MeanFile('1x', '1y')
        decadal.set_filename('MeanFileName', os.getcwd())
        decadal.component_files = ['F' + str(x) for x in range(1, 11)]

        with mock.patch('climatemean.os.path.isfile',
                        side_effect=[False, True, True]):
            # Side effects:
            #   False - Pre-existing mean not present
            #   True - Completed meanfile present
            #   True  - Temporary meanfile present
            with mock.patch('climatemean.MeanFile.description',
                            new_callable=mock.PropertyMock,
                            return_value='FIELD decadal mean for PERIOD'):
                climatemean.create_mean(decadal, 'exec path/MeanFileName',
                                        [0]*5)

        mock_exec.assert_called_once_with('exec path/MeanFileName.tmp',
                                          cwd=os.getcwd())
        self.assertIn('Created FIELD decadal mean for PERIOD: MeanFileName',
                      func.capture())
        mock_rename.assert_called_once_with(
            os.path.join(os.getcwd(), 'MeanFileName.tmp'),
            os.path.join(os.getcwd(), 'MeanFileName')
            )

    @mock.patch('climatemean.utils.exec_subproc', return_value=(0, ''))
    def test_create_mean_existing(self, mock_exec):
        '''Test assertion of unnecessary means creation'''
        func.logtest('Assert unnecessary creation of monthly mean:')
        monthly = climatemean.MeanFile('1m', '10d')
        monthly.set_filename('MeanFileName', os.getcwd())

        with mock.patch('climatemean.os.path.isfile', side_effect=[True]):
            with mock.patch('climatemean.MeanFile.description',
                            new_callable=mock.PropertyMock,
                            return_value='FIELD monthly mean for PERIOD'):
                climatemean.create_mean(monthly, 'exec arg1 arg2', [0]*5)

        self.assertListEqual(mock_exec.mock_calls, [])
        self.assertIn('FIELD monthly mean for PERIOD already exists:',
                      func.capture())
        self.assertNotIn('Monthly mean output directly by the model',
                         func.capture())

    @mock.patch('climatemean.utils.exec_subproc', return_value=(0, ''))
    def test_create_mean_spinup(self, mock_exec):
        '''Test failure to create mean - incorrect number of components'''
        func.logtest('Assert incorrect number of mean components:')
        annual = climatemean.MeanFile('1y', '1m')
        annual.set_filename('MeanFileName', os.getcwd())
        annual.component_files = ['F' + str(x) for x in range(1, 6)]

        with mock.patch('climatemean.os.path.isfile',
                        side_effect=[False, True]):
            with mock.patch('climatemean.MeanFile.description',
                            new_callable=mock.PropertyMock,
                            return_value='FIELD annual mean for PERIOD'):
                with mock.patch('climatemean.mean_spinup', return_value=True):
                    climatemean.create_mean(annual, 'exec arg1 arg2', [1]*5)

        self.assertListEqual(mock_exec.mock_calls, [])
        self.assertIn(
            'FIELD annual mean for PERIOD not possible as only got 5 file(s)',
            func.capture()
            )
        self.assertIn('Means creation in spinup mode', func.capture())

    @mock.patch('climatemean.utils.exec_subproc', return_value=(0, ''))
    def test_create_mean_fail_cmpts(self, mock_exec):
        '''Test failure to create mean - incorrect number of components'''
        func.logtest('Assert incorrect number of mean components:')
        annual = climatemean.MeanFile('1y', '1m')
        annual.set_filename('MeanFileName', os.getcwd())
        annual.component_files = ['F' + str(x) for x in range(1, 6)]

        with mock.patch('climatemean.os.path.isfile',
                        side_effect=[False, True]):
            with mock.patch('climatemean.MeanFile.description',
                            new_callable=mock.PropertyMock,
                            return_value='FIELD annual mean for PERIOD'):
                with mock.patch('climatemean.mean_spinup', return_value=False):
                    with self.assertRaises(SystemExit):
                        climatemean.create_mean(annual, 'exec arg1 arg2', [1]*5)

        self.assertListEqual(mock_exec.mock_calls, [])
        self.assertIn(
            'FIELD annual mean for PERIOD not possible as only got 5 file(s)',
            func.capture('err')
            )


    @mock.patch('climatemean.utils.exec_subproc',
                return_value=(5, 'Not possible!'))
    @mock.patch('climatemean.utils.remove_files')
    def test_create_mean_fail_exec(self, mock_rm, mock_exec):
        '''Test failed means command'''
        func.logtest('Assert failed means command:')
        monthly = climatemean.MeanFile('1m', '10d')
        monthly.set_filename('MeanFileName', os.getcwd())
        monthly.component_files = ['F' + str(x) for x in range(1, 4)]

        with mock.patch('climatemean.os.path.isfile',
                        side_effect=[False, True]):
            with mock.patch('climatemean.MeanFile.description',
                            new_callable=mock.PropertyMock,
                            return_value='FIELD monthly mean for PERIOD'):
                with self.assertRaises(SystemExit):
                    climatemean.create_mean(monthly, 'exec arg1 arg2', [0]*5)

        mock_exec.assert_called_once_with('exec arg1 arg2', cwd=os.getcwd())
        self.assertIn('Error=5\nNot possible!\nFailed to create FIELD monthly',
                      func.capture('err'))
        mock_rm.assert_called_once_with(
            [os.path.join(os.getcwd(), 'MeanFileName'),
             os.path.join(os.getcwd(), 'MeanFileName.tmp')],
            ignore_non_exist=True
            )

    def test_seasonal_mean_spinup_yr1(self):
        '''Test Spinup period for seasonal means - first year'''
        func.logtest('Assert initial spinup period for seasonal means - yr1:')
        seasonmean = climatemean.MeanFile('1s', '1m')
        seasonmean.periodend = ('1995', '12', '01')

        for startdate in [1995, 9, 11], [1995, 10, 1], [1995, 11, 1]:
            func.logtest('Autumn mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.assertTrue(climatemean.mean_spinup(seasonmean, startdate))

        for startdate in [1995, 8, 1], [1995, 9, 1]:
            func.logtest('Autumn mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.assertFalse(climatemean.mean_spinup(seasonmean, startdate))

    def test_seasonal_mean_spinup_yr2(self):
        '''Test Spinup period for seasonal means - second year'''
        func.logtest('Assert initial spinup period for seasonal means - yr2:')
        seasonmean = climatemean.MeanFile('1s', '1m')
        seasonmean.periodend = ('1996', '03', '01')

        for startdate in [1995, 12, 11], [1995, 12, 21]:
            func.logtest('Autumn mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.assertTrue(climatemean.mean_spinup(seasonmean, startdate))

        for startdate in [1995, 12, 1], [1995, 10, 1]:
            func.logtest('Autumn mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.assertFalse(climatemean.mean_spinup(seasonmean, startdate))

        seasonmean.periodend = ('1996', '06', '01')
        for startdate in [1995, 12, 21], [1995, 9, 1]:
            func.logtest('Autumn mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.assertFalse(climatemean.mean_spinup(seasonmean, startdate))

    def test_annual_mean_spinup(self):
        '''Test Spinup period for annual means'''
        func.logtest('Assert initial spinup period for annual means:')
        yearmean = climatemean.MeanFile('1y', '1s')
        yearmean.periodend = ('1995', '12', '01')

        for startdate in [1994, 12, 11], [1995, 12, 1]:
            func.logtest('Annual mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.assertTrue(climatemean.mean_spinup(yearmean, startdate))

        for startdate in [1994, 12, 1], [1994, 11, 11]:
            func.logtest('Annual mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.assertFalse(climatemean.mean_spinup(yearmean, startdate))

    def test_decadal_mean_spinup(self):
        '''Test Spinup period for decadal means'''
        func.logtest('Assert initial spinup period for decadal means:')
        decademean = climatemean.MeanFile('1y', '1s')
        decademean.periodend = ('1995', '12', '01')

        for startdate in [1994, 12, 11], [1995, 12, 1]:
            func.logtest('Decadal mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.assertTrue(climatemean.mean_spinup(decademean, startdate))

        for startdate in [1985, 1, 11], [1985, 12, 1]:
            func.logtest('Decadal mean - Testing start date: ' +
                         '{}{:0>2}{:0>2}T0000Z'.format(*startdate))
            self.assertFalse(climatemean.mean_spinup(decademean, startdate))

    def test_spinup_invalid(self):
        '''Test Spinup period for invalid means'''
        func.logtest('Assert initial spinup period for invalid means:')
        meanfile = climatemean.MeanFile('1z', '1h')
        meanfile.periodend = ('1995', '10', '01')
        self.assertFalse(climatemean.mean_spinup(meanfile, [1995, 8, 1, 0, 0]))
        self.assertIn('[WARN]', func.capture('err'))
        self.assertIn('unknown meantype', func.capture('err'))


class DateRegexTests(unittest.TestCase):
    ''' Unit tests for the module level methods relating to dates'''
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_calc_enddate_12h(self):
        '''Test calc_enddate method with 12h period'''
        func.logtest('Assert return from calc_enddate with 12h:')
        startdate = ('2000', '12', '11', '12')
        dates = [climatemean.calc_enddate(startdate, '12HOURS')]
        dates.append(climatemean.calc_enddate(startdate, '12h'))

        for date in dates:
            self.assertTupleEqual(date, ('2000', '12', '12', '00'))

    def test_calc_enddate_1d(self):
        '''Test calc_enddate method with 1d period'''
        func.logtest('Assert return from calc_enddate with 1d:')
        startdate = ('2000', '12', '11', '12')
        dates = [climatemean.calc_enddate(startdate, '24HOURS')]
        dates.append(climatemean.calc_enddate(startdate, '24h'))
        dates.append(climatemean.calc_enddate(startdate, 'day'))
        dates.append(climatemean.calc_enddate(startdate, 'daily'))
        for date in dates:
            self.assertTupleEqual(date, ('2000', '12', '12', '12'))

    def test_calc_enddate_10d(self):
        '''Test calc_enddate method with 10d period'''
        func.logtest('Assert return from calc_enddate with 10d:')
        startdate = ('2000', '12', '11')
        dates = [climatemean.calc_enddate(startdate, '10DAYS')]
        dates.append(climatemean.calc_enddate(startdate, '10d'))
        dates.append(climatemean.calc_enddate(startdate, '10daily'))
        for date in dates:
            self.assertTupleEqual(date, ('2000', '12', '21'))

    def test_calc_enddate_1m(self):
        '''Test get_enddate method with 1m period'''
        func.logtest('Assert return from calc_enddate with 1m:')
        startdate = ('2000', '12', '11')
        dates = [climatemean.calc_enddate(startdate, '30DAYS')]
        dates.append(climatemean.calc_enddate(startdate, '1M'))
        dates.append(climatemean.calc_enddate(startdate, 'Monthly'))
        for date in dates:
            self.assertTupleEqual(date, ('2001', '01', '11'))

    def test_calc_enddate_1m_shortdate(self):
        '''Test get_enddate method with 1m period - shortdate format'''
        func.logtest('Assert return from calc_enddate with 1m - shortdate:')
        startdate = ('2000', '12')
        dates = [climatemean.calc_enddate(startdate, '30Day')]
        dates.append(climatemean.calc_enddate(startdate, '1M'))
        dates.append(climatemean.calc_enddate(startdate, 'Monthly'))
        for date in dates:
            self.assertTupleEqual(date, ('2001', '01'))

    def test_calc_enddate_1s(self):
        '''Test calc_enddate method with 1s period'''
        func.logtest('Assert return from calc_enddate with 1s:')
        startdate = ('2000', '12', '11')
        dates = [climatemean.calc_enddate(startdate, '3mth')]
        dates.append(climatemean.calc_enddate(startdate, '1s'))
        dates.append(climatemean.calc_enddate(startdate, 'Seasonal'))
        for date in dates:
            self.assertTupleEqual(date, ('2001', '03', '11'))

    def test_calc_enddate_1y(self):
        '''Test calc_enddate method with 1y period'''
        func.logtest('Assert return from calc_enddate with 1y:')
        startdate = ('2000', '12', '11')
        dates = [climatemean.calc_enddate(startdate, '4ssn')]
        dates.append(climatemean.calc_enddate(startdate, '1y'))
        dates.append(climatemean.calc_enddate(startdate, 'Year'))
        for date in dates:
            self.assertTupleEqual(date, ('2001', '12', '11'))

    def test_calc_enddate_1x(self):
        '''Test calc_enddate method with 10y (1x) period'''
        func.logtest('Assert return from calc_enddate with 10y (1x):')
        startdate = ('2000', '12', '11')
        dates = [climatemean.calc_enddate(startdate, '10YR')]
        dates.append(climatemean.calc_enddate(startdate, '10yrs'))
        dates.append(climatemean.calc_enddate(startdate, '1x'))
        for date in dates:
            self.assertTupleEqual(date, ('2010', '12', '11'))

    def test_calc_enddate_fail(self):
        '''Test calc_enddate method with invalid period'''
        func.logtest('Assert return from calc_enddate with ?:')
        with self.assertRaises(SystemExit):
            _ = climatemean.calc_enddate('startdate', 'period')
        self.assertIn('Invalid target provided', func.capture('err'))

    def test_end_date_regex_monthly(self):
        '''Test calculation of regular expression for endates - monthly'''
        func.logtest('Assert monthly period enddate regular expression:')
        self.assertEqual(climatemean.end_date_regex('1m', [1000, 12, 15]),
                         r'\d{4}\d{2}15')

    def test_end_date_regex_seasonal(self):
        '''Test calculation of regular expression for endates - seasonal'''
        func.logtest('Assert seasonal period enddate regular expression:')
        self.assertEqual(climatemean.end_date_regex('1s', [1000, 12, 15]),
                         r'\d{4}(12|03|06|09)15')

        self.assertEqual(climatemean.end_date_regex('1s', [1000, 1, 1]),
                         r'\d{4}(01|04|07|10)01')

    def test_end_date_regex_annual(self):
        '''Test calculation of regular expression for endates - annual'''
        func.logtest('Assert annual period enddate regular expression:')
        self.assertEqual(climatemean.end_date_regex('1y', [1000, 12, 15]),
                         r'\d{4}1215')

        self.assertEqual(climatemean.end_date_regex('1y', [1000, 1, 1]),
                         r'\d{4}0101')

    def test_end_date_regex_decadal(self):
        '''Test calculation of regular expression for endates - decadal'''
        func.logtest('Assert decadal period enddate regular expression:')
        self.assertEqual(climatemean.end_date_regex('1x', [1000, 12, 15]),
                         r'\d{3}01215')

        self.assertEqual(climatemean.end_date_regex('1x', [1005, 1, 1]),
                         r'\d{3}50101')

    def test_set_date_regex_monthly(self):
        '''Test calculation of regular expression for set dates - monthly'''
        func.logtest('Assert monthly period set date regular expression:')
        self.assertEqual(climatemean.set_date_regex('1m', '10d',
                                                    [1987, 12, 11]),
                         '(19871111|19871121|19871201)')

        self.assertEqual(
            climatemean.set_date_regex('1m', '10d', [1987, 12, 11],
                                       rtnend=True),
            '(19871121|19871201|19871211)'
            )

    def test_set_date_regex_seasonal(self):
        '''Test calculation of regular expression for set dates - seasonal'''
        func.logtest('Assert seasonal period set date regular expression:')
        self.assertEqual(
            climatemean.set_date_regex('1s', 'month', [1987, 12, 1]),
            '(19870901|19871001|19871101)'
            )

        self.assertEqual(
            climatemean.set_date_regex('1s', '10days', [1987, 1, 1],
                                       rtnend=True),
            '(19861011|19861021|19861101|19861111|19861121|'
            '19861201|19861211|19861221|19870101)'
            )

    def test_set_date_regex_annual(self):
        '''Test calculation of regular expression for set dates - annual'''
        func.logtest('Assert annual period set date regular expression:')
        self.assertEqual(
            climatemean.set_date_regex('1y', 'ssn', [1987, 11, 1]),
            '(19861101|19870201|19870501|19870801)'
            )
        self.assertEqual(
            climatemean.set_date_regex('1y', '1m', [1987, 11, 1], rtnend=True),
            '(19861201|19870101|19870201|19870301|19870401|19870501|19870601|'
            '19870701|19870801|19870901|19871001|19871101)'
            )

    def test_set_date_regex_decadal(self):
        '''Test calculation of regular expression for set dates - decadal'''
        func.logtest('Assert decadal period set date regular expression:')
        self.assertEqual(
            climatemean.set_date_regex('1x', 'ssn', [1996, 11, 1]),
            '(19861101|19870201|19870501|19870801|19871101|19880201|19880501|'
            '19880801|19881101|19890201|19890501|19890801|19891101|19900201|'
            '19900501|19900801|19901101|19910201|19910501|19910801|19911101|'
            '19920201|19920501|19920801|19921101|19930201|19930501|19930801|'
            '19931101|19940201|19940501|19940801|19941101|19950201|19950501|'
            '19950801|19951101|19960201|19960501|19960801)'
            )

        self.assertEqual(
            climatemean.set_date_regex('1x', 'year', [1996, 11, 1],
                                       rtnend=True),
            '(19871101|19881101|19891101|19901101|19911101|19921101|19931101|'
            '19941101|19951101|19961101)'
            )
