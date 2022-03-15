#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2017-2022 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    iris_transform.py

DESCRIPTION
    Module containing methods for transforming input files to alternative
    formats via Iris
'''
import os
import re

import iris

import utils
import timer


if iris.__version__ < '2.0.0':
    # For operations with cube time coordinates -
    iris.FUTURE.cell_datetime_objects = True
    # For _save_netcdf -
    iris.FUTURE.netcdf_no_unlimited = True

class CubeContainer(object):
    ''' Container for field attributes associated with an Iris Cube '''
    def __init__(self, cube, name=None):
        self._cube = cube
        self.extract_data_period()
        self.extract_stash_code()
        self.set_fieldname(name)

    @property
    def cube(self):
        ''' Return <type iris.cube.Cube> Single Iris data cube '''
        return self._cube

    @property
    def startdate(self):
        ''' Return <type str> Cube start date '''
        return self._start

    @property
    def enddate(self):
        ''' Return <type str> Cube end date '''
        return self._end

    @property
    def data_frequency(self):
        ''' Return <type str> Cube data frequency '''
        return self._freq

    @property
    def stashcode(self):
        ''' Return <type str> STASHcode '''
        if self._stashcode:
            return str(self._stashcode).zfill(5)

    @property
    def fieldname(self):
        ''' Return <type str> Cube name '''
        return self._name

    def set_fieldname(self, name):
        ''' Set the cube name '''
        if not isinstance(name, str):
            name = self.cube.name()
        self._name = self.stashcode if 'unknown' in name else name

    def extract_stash_code(self):
        ''' Extract the STASH code if available '''
        try:
            # Regular expression to match STASH code: "mXXsXXiXXX"
            #  <match>.groups() = (<section number>, <item number>)
            mod_sec_item = re.match(r'm01s(\d{2})i(\d{3})',
                                    str(self.cube.attributes['STASH']))
            self._stashcode = int(''.join(mod_sec_item.groups()))
        except KeyError:
            # STASH code not available
            self._stashcode = None

    def compatible_data(self, new_item):
        '''
        Test whether a new cube is compatible with the existing cube
        Arguments:
            new_item <type CubeContainer>

        Return <type bool>
        '''
        return self.cube.is_compatible(new_item.cube)

    def extract_data_period(self):
        '''
        Extract the start date, end date and temporal resolution of the
        data in a given Iris cube field.
        Assumptions:
           The field has a single 'time' dimension
        '''
        try:
            time_coord = self.cube.coord('time')
        except iris.exceptions.CoordinateNotFoundError:
            # No 'time' information available
            self._start = self._end = ''
            self._freq = None

        else:
            start, cell0_end = time_coord.cell(0).bound
            end = time_coord.cell(-1).bound[1]
            self._start = '{:04}{:02}{:02}'.format(start.year, start.month,
                                                   start.day)
            self._end = '{:04}{:02}{:02}'.format(end.year, end.month,
                                                 end.day)

            try:
                # Iris 2.0+
                freq = (cell0_end - start).days
            except TypeError:
                # Assumption of 360d calendar
                start_days = (start.year * 360) + (start.month * 30) + start.day
                end_days = (cell0_end.year * 360) + (cell0_end.month * 30) + \
                           cell0_end.day
                freq = (end_days - start_days)

            if freq > 0:
                units = 'd'
                if freq % 30 == 0:
                    freq = freq // 30
                    units = 'm'
                if freq % 12 == 0:
                    freq = freq // 12
                    units = 'y'
            else:
                units = 'h'
                # Calculation of `freq` assumes period does not cross a day
                #boundary
                freq = cell0_end.hour - start.hour
                self._start += '{:02}'.format(start.hour)
                self._end += '{:02}'.format(end.hour)
            self._freq = str(freq) + units

    def update_cube(self, new_item):
        '''
        Update the cube with data from a <type CubeContainer> new_item.

        Return a <type iris.cube.Cube> ONLY if the update fails to produce
        a single merged cube.  Otherwise return <type None>

        Arguments:
            new_item <type CubeContainer>
        '''
        if not self.compatible_data(new_item):
            return None

        cubelist = iris.cube.CubeList([self.cube, new_item.cube])
        try:
            self._cube = cubelist.merge_cube()
        except (iris.exceptions.MergeError,
                iris.exceptions.DuplicateDataError):
            # Assess whether we have duplicate time slices.
            # Return the new cube if it fails to merge with self.cube
            return self.assess_time_slices(new_item.cube)
        finally:
            self.extract_data_period()

    def assess_time_slices(self, new_cube):
        '''
        Where duplicate time slices are encountered between old and new cubes
        replace the old slice with the new.
        Return <type iris.cube> The reduced cube
        Arguments:
            new_cube <type iris.cube.cube> - replacement cube
        '''
        old_cube = self.cube.copy()
        for nt_slice in new_cube.slices_over('time'):
            extract_target = iris.Constraint(
                time=lambda cell:
                cell.point != nt_slice.coord('time').cell(0).point
            )
            old_cube = old_cube.extract(extract_target)
            if old_cube is None:
                # Al time slices replaced - update CubeContainer.cube with new
                self._cube = new_cube
                return None

        try:
            self._cube = iris.cube.CubeList([new_cube, old_cube]).merge_cube()
            return None
        except (iris.exceptions.MergeError,
                iris.exceptions.DuplicateDataError):
            # Most plausible explanations for merge error are:
            #   * Different data types - cubes read from fieldsfiles
            #     are 64bit, from .pp they are 32bit
            #   * Pressure field changing which Iris cannot merge.
            # Update CubeContainer.cube with reduced time slices and
            # return new item instead.
            self._cube = old_cube
            return new_cube


class IrisCubes(object):
    ''' Container for Iris cube data with associated "field attributes" '''
    def __init__(self, fname, requested_fields):
        '''
        fname            - <type str> Source filename
        requested_fields - <type dict> keys=fieldnames or stashcodes
                                       vals=descriptor for field
        '''
        self._fields = []
        if requested_fields:
            for field, desc in requested_fields.items():
                for cube in utils.ensure_list(extract_data(fname, field)):
                    self.add_item(cube, description=desc)
        else:
            for cube in utils.ensure_list(extract_data(fname, None)):
                self.add_item(cube)

    @property
    def fields(self):
        ''' Return <type list of <type CubeContainer>> List of fields '''
        return self._fields

    @timer.run_timer
    def add_item(self, datafield, description=None):
        '''
        Add CubeContainer object to the fields list
        Arguments:
            cube <type iris.cube.Cube> or <type CubeContainer>
                 - Field data
        Optional Arguments:
            description <type str> Descriptive string for field
        '''
        if isinstance(datafield, CubeContainer):
            new_item = datafield
        else:
            new_item = CubeContainer(datafield, description)

        for field in self.fields:
            if field.compatible_data(new_item):
                add_cube = field.update_cube(new_item)
                if field.cube:
                    # Field has been updated
                    field.extract_data_period()
                else:
                    # Field has been replaced
                    self.fields.remove(field)
                if add_cube:
                    # Unable to merge field_item and new_item
                    self._fields.append(new_item)
                break

        else:
            # Finally add new item if no match is found
            self._fields.append(new_item)


@timer.run_timer
def extract_data(filename, fields):
    '''
    extract an iris cube from the file provided.
    optional argument:
    fields - extract specific field(s) from the file.
             default=all fields available.
    '''
    load_vars = [] if fields else None
    for field in utils.ensure_list(fields):
        try:
            load_vars.append(iris.AttributeConstraint(
                STASH='m01s{}i{}'.format(str(int(field)).zfill(5)[:2],
                                         str(field).zfill(5)[2:5]))
                            )
        except ValueError:
            load_vars.append(field)

    try:
        data_cube = iris.load(filename, constraints=load_vars)
    except IOError:
        msg = 'Iris extract data - File does not exist: '
        utils.log_msg(msg + str(filename), level='WARN')
        data_cube = None

    return data_cube


def _save_netcdf(cube, outfile, kwargs):
    ''' Save extracted data to netCDF format '''
    complevel = kwargs['complevel']
    zlib = isinstance(complevel, int) and complevel > 0
    iris.fileformats.netcdf.save(cube, outfile,
                                 netcdf_format=kwargs['ncftype'],
                                 zlib=zlib,
                                 complevel=complevel)


def _save_pp(cube, outfile, kwargs):
    ''' Save extracted field to PP format '''
    append_field = kwargs.get('append', False)
    iris.fileformats.pp.save(cube, outfile, append=append_field)


@timer.run_timer
def save_format(cube, outfile, fileformat, kwargs=None):
    '''
    Save  data to a given file format.
    Arguments:
        cube       - <type iris.cube.Cube> - Iris cube data (input)
        outfile    - <type str>            - Output filename
        fileformat - <type str>            - Output file format
    '''
    rtn_val = None
    if kwargs is None:
        kwargs = {}
    msg = 'IRIS save data - '
    call_method = '_save_' + fileformat
    try:
        globals()[call_method](cube, outfile, kwargs)
        rtn_val = 0
    except AttributeError:
        # Save to format method not defined
        msg += 'File format not recognised: {}'.format(fileformat)
        utils.log_msg(msg, level='WARN')
    except IOError:
        msg += 'Could not write to file: {}'.format(outfile)
        utils.log_msg(msg, level='WARN')
    except ValueError as err:
        msg += 'Could not extract data: {}'.format(err)
        utils.log_msg(msg, level='WARN')
    except KeyError as err:
        if call_method in str(err):
            msg += 'File format not recognised: {}'.format(fileformat)
        else:
            msg += 'Could not extract data - missing keyword: {}'
        utils.log_msg(msg.format(str(err)), level='WARN')

    if os.path.isfile(outfile) and rtn_val == 0:
        msg += 'Saved "{}" data to {} file: {}'.format(
            cube.name(), fileformat, outfile
            )
        utils.log_msg(msg, level='OK')
    else:
        msg += '\n --> Failed to create {} file: {}'.format(fileformat,
                                                            outfile)
        utils.log_msg(msg, level='WARN')
        rtn_val = -1

    return rtn_val
