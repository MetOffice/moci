#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2018-2025 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''
import os
import copy
import numpy
import unittest
try:
    # mock is integrated into unittest as of Python 3.3
    import unittest.mock as mock
except ImportError:
    # mock is a standalone package (back-ported)
    import mock

import testing_functions as func
import runtime_environment

try:
    import iris_transform
    IRIS_AVAIL = True
    import cf_units
except ImportError:
    IRIS_AVAIL = False
    func.logtest('\n*** Iris is not available.  '
                 'All 14 IRIS tests (CubesClassTests) will be skipped.\n')

runtime_environment.setup_env()


@unittest.skipUnless(IRIS_AVAIL, 'Python module "Iris" is not available')
class CubeContainerClassTests(unittest.TestCase):
    '''Unit tests for the CubeContainer class methods'''
    def setUp(self):
        self.testfile = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'air_temp.pp'
            )
        self.fields = {'air_temperature': 'AIR-T'}
        self.transform = iris_transform.IrisCubes(self.testfile, self.fields)
        self.cubecontainer = self.transform.fields[0]
        self.outfile = 'output.ext'

    def tearDown(self):
        try:
            os.remove(self.outfile)
        except OSError:
            pass

    def test_cubecontainer_object(self):
        '''Test instantiation if CubeContainer object'''
        self.assertEqual(self.cubecontainer.fieldname, 'AIR-T')
        self.assertEqual(self.cubecontainer.stashcode, '16203')
        # The test data has a single time data point spanning a 4 year period
        self.assertEqual(self.cubecontainer.startdate, '19941201')
        self.assertEqual(self.cubecontainer.enddate, '19981201')
        self.assertEqual(self.cubecontainer.data_frequency, '4y')
        self.assertIsInstance(self.cubecontainer.cube,
                              iris_transform.iris.cube.Cube)

    def test_instantiation_stashcode(self):
        '''Test instantiation of IrisCubes with STASHcode'''
        func.logtest('Assert instantiation of IrisCubes object with stashcode:')
        transform = iris_transform.IrisCubes(self.testfile, {'16203': 'STASH1'})
        self.assertEqual(transform.fields[0].fieldname, 'STASH1')
        self.assertEqual(transform.fields[0].stashcode, '16203')
        self.assertIsInstance(transform.fields[0], iris_transform.CubeContainer)

    def test_instantiation_all_cubes(self):
        '''Test instantiation of IrisCubes - all fields'''
        all_cubes = iris_transform.IrisCubes(self.testfile, None)
        self.assertEqual(all_cubes.fields[0].cube, self.cubecontainer.cube)
        self.assertEqual(all_cubes.fields[0].fieldname, 'air_temperature')

    def test_instantiation_no_file(self):
        '''Test instantiation of IrisCubes - file does not exist'''
        all_cubes = iris_transform.IrisCubes('NOFILE', None)
        self.assertIsInstance(all_cubes, iris_transform.IrisCubes)
        self.assertListEqual(all_cubes.fields, [])

    def test_extract_data_period_months(self):
        '''Test extraction of date/period info from Iris cube - no time coord'''
        func.logtest('Assert dates extraction from Iris cube - monthly data')
        new_time = self.cubecontainer.cube.coord('time') / (4 * 3)
        self.cubecontainer.cube.replace_coord(new_time)
        self.cubecontainer.extract_data_period()
        self.assertEqual(self.cubecontainer.startdate, '19720128')
        self.assertEqual(self.cubecontainer.enddate, '19720528')
        self.assertEqual(self.cubecontainer.data_frequency, '4m')

    def test_extract_data_period_days(self):
        '''Test extraction of date/period info from Iris cube - daily data'''
        func.logtest('Assert dates extraction from Iris cube - daily data')
        new_time = self.cubecontainer.cube.coord('time') / (4 * 72)
        self.cubecontainer.cube.replace_coord(new_time)
        self.cubecontainer.extract_data_period()
        self.assertEqual(self.cubecontainer.startdate, '19700202')
        self.assertEqual(self.cubecontainer.enddate, '19700207')
        self.assertEqual(self.cubecontainer.data_frequency, '5d')

    def test_extract_data_period_hours(self):
        '''Test extraction of date/period info from Iris cube - daily data'''
        func.logtest('Assert dates extraction from Iris cube - daily data')
        new_time = self.cubecontainer.cube.coord('time') / (4 * 360 * 2)
        self.cubecontainer.cube.replace_coord(new_time)
        self.cubecontainer.extract_data_period()
        self.assertEqual(self.cubecontainer.startdate, '1970010402')
        self.assertEqual(self.cubecontainer.enddate, '1970010414')
        self.assertEqual(self.cubecontainer.data_frequency, '12h')

    def test_extract_data_period_greg(self):
        '''Test extraction of date/period info from Iris cube - Gregorian'''
        func.logtest('Assert dates extraction from Iris cube - Gregorian')
        greg_cal = cf_units.Unit(self.cubecontainer.cube.units.origin,
                                 calendar='Gregorian')
        self.cubecontainer.cube.units = greg_cal
        new_time = self.cubecontainer.cube.coord('time') / 4
        self.cubecontainer.cube.replace_coord(new_time)
        self.cubecontainer.extract_data_period()
        self.assertEqual(self.cubecontainer.startdate, '19760323')
        self.assertEqual(self.cubecontainer.enddate, '19770323')
        self.assertEqual(self.cubecontainer.data_frequency, '1y')

    def test_extract_data_period_notime(self):
        '''Test extraction of date/period info from Iris cube - no time coord'''
        func.logtest('Assert dates extraction from Iris cube - no time coord')
        self.cubecontainer.cube.remove_coord('time')
        self.cubecontainer.extract_data_period()
        self.assertEqual(self.cubecontainer.startdate, '')
        self.assertEqual(self.cubecontainer.enddate, '')
        self.assertEqual(self.cubecontainer.data_frequency, None)

    def test_extract_stashcode_none(self):
        '''Test failed extraction of the STASHcode from the Iris cube'''
        func.logtest('Assert no STASHcode extracted from the cube')
        del self.cubecontainer.cube.attributes['STASH']
        self.cubecontainer.extract_stash_code()
        self.assertIsNone(self.cubecontainer.stashcode)

    def test_compatible_data(self):
        '''Test matching attributes of cubes'''
        func.logtest('Assert data compatibility')
        newitem = copy.deepcopy(self.cubecontainer)
        self.assertTrue(self.cubecontainer.compatible_data(newitem))

    def test_compatible_data_no_match(self):
        '''Test no match of STASH attribute'''
        func.logtest('Assert data is incompatible')
        newitem = copy.deepcopy(self.cubecontainer)
        self.assertTrue(self.cubecontainer.compatible_data(newitem))
        newitem.cube.attributes['STASH'] = 'm01s00i123'
        self.assertFalse(self.cubecontainer.compatible_data(newitem))

        with mock.patch('iris_transform.iris.cube.CubeList') as mock_iriscube:
            self.assertIsNone(self.cubecontainer.update_cube(newitem))
        self.assertListEqual(mock_iriscube.mock_calls, [])
                            
    def test_update_cube_extend(self):
        '''Test extend cube with addition of new (slices)'''
        func.logtest('Assert cube with additional time slice(s)')
        self.assertEqual(self.cubecontainer.startdate, '19941201')
        self.assertEqual(self.cubecontainer.enddate, '19981201')

        newitem = copy.deepcopy(self.cubecontainer)
        newitem.cube.replace_coord(newitem.cube.coord('time')
                                   + (24 * 12 * 30 * 4))

        add_new = self.cubecontainer.update_cube(newitem)
        self.assertEqual(self.cubecontainer.startdate, '19941201')
        self.assertEqual(self.cubecontainer.enddate, '20021201')
        self.assertEqual(len(self.cubecontainer.cube.coord('time').points), 2)
        self.assertIsNone(add_new)

    def test_update_cube_fail_merge(self):
        '''Test update of cube - merge failure due to data type'''
        func.logtest('Assert merge failure due to float difference')
        self.assertEqual(self.cubecontainer.startdate, '19941201')
        self.assertEqual(self.cubecontainer.enddate, '19981201')

        newitem = copy.deepcopy(self.cubecontainer)
        newitem.cube.replace_coord(newitem.cube.coord('time')
                                   + (24 * 12 * 30 * 4))
        newitem.cube.data = [numpy.float64(b) for b in newitem.cube.data]

        add_new = self.cubecontainer.update_cube(newitem)
        self.assertNotIn('target time = ', func.capture())
        self.assertEqual(self.cubecontainer.startdate, '19941201')
        self.assertEqual(self.cubecontainer.enddate, '19981201')
        self.assertEqual(len(self.cubecontainer.cube.coord('time').points), 1)
        self.assertEqual(add_new, newitem.cube)

    def test_update_cube_replace(self):
        '''Test update of cube replacing with new slice(s)'''
        func.logtest('Assert cube with replacement time slice(s)')
        newitem1 = copy.deepcopy(self.cubecontainer)
        newitem2 = copy.deepcopy(self.cubecontainer)
        newitem1.cube.replace_coord(newitem1.cube.coord('time')
                                    + (24 * 12 * 30 * 4))
        _ = self.cubecontainer.update_cube(newitem1)
        add_new = self.cubecontainer.update_cube(newitem2)
        self.assertEqual(self.cubecontainer.startdate, '19941201')
        self.assertEqual(self.cubecontainer.enddate, '20021201')
        self.assertEqual(len(self.cubecontainer.cube.coord('time').points), 2)
        self.assertIsNone(add_new)


@unittest.skipUnless(IRIS_AVAIL, 'Python module "Iris" is not available')
class IrisCubesTests(unittest.TestCase):
    '''Unit tests for the CubeContainer class methods'''
    def setUp(self):
        self.testfile = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'air_temp.pp'
            )
        self.fields = {'air_temperature': 'AIR-T'}
        self.transform = iris_transform.IrisCubes(self.testfile, self.fields)
        self.newitem = copy.deepcopy(self.transform.fields[0])

    def tearDown(self):
        pass

    def test_iriscubes_instantiation(self):
        '''Test instantiation of IrisCubes object'''
        func.logtest('Assert instantiation of IrisCubes object:')
        self.assertEqual(len(self.transform.fields), 1)
        self.assertIsInstance(self.transform.fields[0],
                              iris_transform.CubeContainer)

    def test_add_cubecontainer_update(self):
        '''Test add_item method with cube extended in time'''
        func.logtest('Assert CubeContainer added to IrisCubes object')
        self.newitem.cube.replace_coord(self.newitem.cube.coord('time')
                                        + (24 * 12 * 30 * 4))

        self.assertEqual(self.transform.fields[0].startdate, '19941201')
        self.assertEqual(self.transform.fields[0].enddate, '19981201')
        self.transform.add_item(self.newitem)

        self.assertEqual(len(self.transform.fields), 1)
        self.assertEqual(self.transform.fields[0].startdate, '19941201')
        self.assertEqual(self.transform.fields[0].enddate, '20021201')

    def test_add_cube_no_merge(self):
        '''Test add_item method with no merge possible'''
        func.logtest('Assert no merge of cubes by field in IrisCubes object')
        self.newitem.cube.replace_coord(self.newitem.cube.coord('time')
                                        + (24 * 12 * 30 * 4))

        self.newitem.cube.data = [numpy.float64(b)
                                  for b in self.newitem.cube.data]

        self.assertEqual(self.transform.fields[0].startdate, '19941201')
        self.assertEqual(self.transform.fields[0].enddate, '19981201')
        self.transform.add_item(self.newitem.cube)

        self.assertEqual(len(self.transform.fields), 2)
        self.assertEqual(self.transform.fields[0].startdate, '19941201')
        self.assertEqual(self.transform.fields[0].enddate, '19981201')
        self.assertEqual(self.transform.fields[1].startdate, '19981201')
        self.assertEqual(self.transform.fields[1].enddate, '20021201')
        self.assertEqual(self.transform.fields[0].cube.name(),
                         self.transform.fields[1].cube.name())

    def test_add_cube_replace(self):
        '''Test add_item method with data replaced on the cube'''
        func.logtest('Assert cube replaced by field in IrisCubes object')
        self.assertEqual(self.transform.fields[0].startdate, '19941201')
        self.assertEqual(self.transform.fields[0].enddate, '19981201')
        self.transform.add_item(self.newitem.cube, description='NewField')

        self.assertEqual(len(self.transform.fields), 1)
        self.assertEqual(self.transform.fields[0].startdate, '19941201')
        self.assertEqual(self.transform.fields[0].enddate, '19981201')

    def test_add_item_not_compatible(self):
        '''Test add_item method with incompatible data'''
        func.logtest('Assert incompatible data added to IrisCubes object')
        self.newitem.cube.replace_coord(self.newitem.cube.coord('time')
                                        + (24 * 12 * 30 * 4))
        self.newitem.extract_data_period()
        self.newitem.cube.standard_name = 'surface_temperature'

        self.assertEqual(self.transform.fields[0].startdate, '19941201')
        self.assertEqual(self.transform.fields[0].enddate, '19981201')
        self.transform.add_item(self.newitem.cube, description='TempField')

        self.assertEqual(len(self.transform.fields), 2)
        self.assertEqual(self.transform.fields[0].startdate, '19941201')
        self.assertEqual(self.transform.fields[0].enddate, '19981201')
        self.assertEqual(self.transform.fields[1].startdate, '19981201')
        self.assertEqual(self.transform.fields[1].enddate, '20021201')
        self.assertEqual(self.transform.fields[1].fieldname,
                         'TempField')
         

@unittest.skipUnless(IRIS_AVAIL, 'Python module "Iris" is not available')
class IrisMethodsTests(unittest.TestCase):
    '''Unit tests for the iris_transform module methods'''
    def setUp(self):
        testfile = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'air_temp.pp'
            )
        transform = iris_transform.IrisCubes(testfile, None)
        self.testcube = transform.fields[0].cube
        self.outfile = 'output.ext'

    def tearDown(self):
        try:
            os.remove(self.outfile)
        except OSError:
            pass

    @mock.patch('iris_transform.iris.load')
    def test_extract_data(self, mock_load):
        '''Test composition of load constraint for loading an Iris cube'''
        func.logtest('Assert composition of single constraint for Iris cube')
        _ = iris_transform.extract_data('testfile', 'field')
        mock_load.assert_called_once_with('testfile', constraints=['field'])

    @mock.patch('iris_transform.iris.load')
    def test_extract_data_list(self, mock_load):
        '''Test composition of load constraints for loading an Iris cube'''
        func.logtest('Assert composition of load constraints for Iris cube')
        _ = iris_transform.extract_data('testfile', ['field1', 'field2'])
        mock_load.assert_called_once_with('testfile',
                                          constraints=['field1', 'field2'])

    @mock.patch('iris_transform.iris.load')
    def test_extract_data_stash(self, mock_load):
        '''Test composition of STASH load constraints for loading Iris cube'''
        func.logtest('Assert composition of STASH constraints for Iris cube')
        fields = {'16203': 'AIR-T', '24': 'SURF-T'}

        _ = iris_transform.extract_data('testfile', fields.keys())

        constraints = [
            iris_transform.iris.AttributeConstraint(STASH='m01s00i024'),
            iris_transform.iris.AttributeConstraint(STASH='m01s16i203')
            ]
        # I can't seem verify the call to mock_load directly, since apparently:
        #           iris.AttributeConstraint() != iris.AttributeConstraint()
        # mock_load.assert_called_once_with(self.testfile,
        #                                   constraints=constraints)

        self.assertEqual(mock_load.call_args[0], ('testfile',))
        for arg in mock_load.call_args[1]['constraints']:
            self.assertIn(repr(arg), [repr(c) for c in constraints])
            self.assertIsInstance(arg, iris_transform.iris.AttributeConstraint)

    def test_extract_data_error(self):
        '''Test IOError exception for non-existent file in extract_data '''
        func.logtest('Assert IOError exception in extract_data')
        cube = iris_transform.extract_data('NO_FILE', ['field1', 'field2'])
        self.assertTrue(cube is None)
        self.assertIn('File does not exist', func.capture('err'))

    def test_save_netcdf(self):
        '''Test save as netCDF format'''
        func.logtest('Assert creation of netCDF file:')
        iris_transform.save_format(self.testcube, self.outfile, 'netcdf',
                                   {'ncftype': 'NETCDF4', 'complevel': None})
        self.assertTrue(os.path.isfile(self.outfile))
        self.assertIn('Saved "air_temperature" data to netcdf file: output.ext',
                      func.capture())

    def test_save_pp(self):
        '''Test save as PP format'''
        func.logtest('Assert creation of PP file:')
        iris_transform.save_format(self.testcube, self.outfile, 'pp', None)
        self.assertTrue(os.path.isfile(self.outfile))
        self.assertIn('Saved "air_temperature" data to pp file: output.ext',
                      func.capture())

    def test_save_format_valueerror(self):
        '''Test save as given format - ValueError'''
        func.logtest('Assert creation of given format file - ValueError:')
        iris_transform.save_format(self.testcube, self.outfile, 'netcdf',
                                   {'ncftype': 'MYTYPE', 'complevel': 1})
        self.assertFalse(os.path.isfile(self.outfile))
        self.assertIn("Unknown netCDF file format, got 'MYTYPE'",
                      func.capture('err'))
        self.assertIn('Failed to create netcdf file',
                      func.capture('err'))

    def test_save_format_keyerror(self):
        '''Test save as given format - KeyError'''
        func.logtest('Assert creation of given format file - KeyError:')
        iris_transform.save_format(self.testcube, self.outfile, 'netcdf',
                                   {'ncftype': 'NETCDF4'})
        self.assertFalse(os.path.isfile(self.outfile))
        self.assertIn("missing keyword: 'complevel'",
                      func.capture('err'))
        self.assertIn('Failed to create netcdf file',
                      func.capture('err'))

    def test_save_format_bad_filetype(self):
        '''Test save as given format - Unrecognised filetype'''
        func.logtest('Assert creation of given format file - Bad filetype:')
        iris_transform.save_format(self.testcube, self.outfile, 'sometype', {})
        self.assertFalse(os.path.isfile(self.outfile))
        self.assertIn("File format not recognised: sometype",
                      func.capture('err'))
        self.assertIn('Failed to create sometype file',
                      func.capture('err'))

    def test_save_format_ioerror(self):
        '''Test save as given format - IOError'''
        func.logtest('Assert creation of given format file - IOError:')
        iris_transform.save_format(self.testcube,
                                   os.path.join('NO_SUCH_DIR', self.outfile),
                                   'netcdf',
                                   {'ncftype': 'NETCDF4', 'complevel': None})
        self.assertFalse(os.path.isfile(self.outfile))
        self.assertIn("Could not write to file: NO_SUCH_DIR/output.ext",
                      func.capture('err'))
        self.assertIn('Failed to create netcdf file',
                      func.capture('err'))
