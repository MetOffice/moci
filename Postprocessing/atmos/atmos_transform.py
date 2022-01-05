#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021-2022 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    atmos_transform.py

DESCRIPTION
    Transformation methods for UM atmosphere data files:
       Convertion from fieldsfile to pp format
       Extraction of a regional sub-domain from global fieldsfile
       Extraction of fields to NetCDF format (requires IRIS)
       creation of means
'''

import os
import re

import utils
import timer

from netcdf_filenames import NCF_TEMPLATE
from validation import MULE_AVAIL, VALID_STR, identify_dates

try:
    import iris_transform
except ImportError:
    # Iris is not part of the standard Python package
    utils.log_msg('Iris Module is not available', level='WARN')

if MULE_AVAIL:
    import mule
    class WeightedMeanOperator(mule.DataOperator):
        '''
        Operator which calculates a weighted mean between a number of fields
        '''
        def __init__(self, weights):
            '''
            Initialise operator, passing the list of weights for each field
            Arguments:
               weights <type int> list.  One element per component file.
            '''
            self.weights = utils.ensure_list(weights)

        def new_field(self, field_list):
            '''
            Return a copy of an incoming UM field as the new field object
            '''
            field = field_list[0].copy()
            return field

        def transform(self, field_list, new_field):
            ''' Perform the data manipulation '''
            data_list = []
            for field in field_list:
                data_list.append(field.get_data())
            if len(data_list) == len(self.weights):
                data_out = sum([a * b for a, b
                                in zip(data_list, self.weights)])
                # Denominator must a float - we do not want integer divison
                # rounding the data
                data_out = data_out / float(sum(self.weights))
            else:
                data_out = sum(data_list)/float(len(data_list))

            # If the first field defines MDI, reset missing points from
            # any of the original fields back to MDI in the output
            if hasattr(field_list[0], "bmdi"):
                mdi = field_list[0].bmdi
                for i in range(len(field_list)):
                    data_out[(data_list[i] == mdi)] = mdi

            return data_out


@timer.run_timer
def get_mule_util(mule_path, utility):
    '''
    Return the path to the given Mule utility providing the exec is available.
    Otherwise return None
    '''
    exec_path = str(utility)
    exec_present = False
    if mule_path and MULE_AVAIL:
        # If a path is passed in, create a full path to the executable
        exec_path = os.path.expandvars(os.path.join(mule_path, exec_path))
        exec_present = os.path.exists(exec_path)
    else:
        # Assume path the mule utilities is on the system $PATH
        ret_val, _ = utils.exec_subproc(utility + ' --help', verbose=False)
        exec_present = ret_val == 0

    return exec_path if exec_present else None


@timer.run_timer
def convert_to_pp(fieldsfile, umutils, muleutils, keep_ffile):
    '''
    Create the command to call the appropriate UM utility for file
    conversion to pp format.
        If Mule is available    : mule-convpp
        UM versions up to vn10.3: um-ff2pp
        UM versions 10.4 onwards: um-convpp
    '''
    ppfname = fieldsfile + '.pp'
    sharedir = os.path.dirname(fieldsfile)

    convpp = get_mule_util(muleutils, 'mule-convpp')
    if convpp:
        conv_exec = convpp
    else:
        try:
            version = re.match(r'.*/(vn|VN)(\d+\.\d+).*', umutils).group(2)
            conv_exec = 'um-convpp' if float(version) > 10.3 else 'um-ff2pp'
        except AttributeError:
            # Version number not in path
            conv_exec = 'um-convpp'
        conv_exec = os.path.join(umutils, conv_exec)

    cmd = ' '.join([conv_exec, fieldsfile, ppfname])
    ret_code, output = utils.exec_subproc(cmd, cwd=sharedir)

    if ret_code == 0:
        msg = 'convert_to_pp: Converted to pp format: ' + ppfname
        if not keep_ffile:
            utils.remove_files(fieldsfile, path=sharedir)
        utils.log_msg(msg, level='INFO')
    else:
        msg = 'convert_to_pp: Conversion to pp format failed: {}\n {}\n'
        utils.log_msg(msg.format(fieldsfile, output), level='ERROR')

    return ppfname


@timer.run_timer
def extract_to_netcdf(fieldsfile, fields, ncftype, complevel):
    '''
    Extract given field(s) to netCDF format.

    Multiple instances of the same field in the same file will result
    in only the final instance being extracted.

    Arguments:
       fieldsfile - Full filename (including path)
       fields     - <type dict> keys=fieldnames or STASHcodes
                                vals=descriptor for field
    '''
    dirname = os.path.dirname(fieldsfile)
    try:
        suite_id, stream_id = re.match(r'(.*)a\.({})\d{{4}}'.format(VALID_STR),
                                       os.path.basename(fieldsfile)).groups()
    except AttributeError:
        msg = 'PP/Fieldsfile name does not match expected format: '
        utils.log_msg(msg + os.path.basename(fieldsfile), level='WARN')
        suite_id = os.environ['CYLC_SUITE_NAME']
        stream_id = 'p9'
    ncf_prefix = 'atmos_{}a'.format(suite_id)
    try:
        all_cubes = iris_transform.IrisCubes(fieldsfile, fields)
        icode = 0
    except (AttributeError, NameError):
        # Iris module is not available
        utils.log_msg('Iris module is not available - '
                      'cannot extract fields to netCDF format', level='ERROR')
        icode = -1

    if icode == 0:
        current_output = ''
        # Loop over requested fields
        for field in sorted(all_cubes.field_attributes):
            fattr = all_cubes.field_attributes[field]
            descriptor = '_' + stream_id
            if fattr['Descriptor']:
                descriptor += '-' + fattr['Descriptor']
            ncfilename = NCF_TEMPLATE.format(P=ncf_prefix,
                                             B=fattr['DataFrequency'],
                                             S=fattr['StartDate'],
                                             E=fattr['EndDate'],
                                             C=descriptor)
            if ncfilename != current_output:
                # Failure recovery - remove any pre-existing files
                utils.remove_files(ncfilename, ignore_non_exist=True)
                current_output = ncfilename
            icode += iris_transform.save_format(fattr['IrisCube'],
                                                ncfilename,
                                                'netcdf',
                                                kwargs={'complevel': complevel,
                                                        'ncftype': ncftype})
            if dirname:
                utils.move_files(ncfilename, dirname)

    return icode


@timer.run_timer
def cutout_subdomain(full_fname, mule_utils, coord_type, coords):
    '''
    Use Mule to cut out a fieldsfile sub-domain - suitable for input to createbc

    Arguments:
      full_fname - <type str> Filename including full path
      mule_utils - Path to mule-cutout.
                   If <type NoneType> then mule-cutout is assumed to be on
                   the system $PATH variable.
      coord_type - Coordinate system argument for mule-cutout.  One of:
                     ['indices', 'coords', 'coords --native-grid']
      coords     - Integer coordinates to cut out:
                     indices: zx,zy,nz,ny
                     coords : SW_lon,SW_lat,NE_lon,NE_lat
    '''
    cutout = get_mule_util(mule_utils, 'mule-cutout')

    outfile = full_fname + '.cut'
    mlevel = 'ERROR'
    if os.path.exists(full_fname + '.cut'):
        # Cut out file already exists - skip to rename
        icode = 0

    elif cutout:
        # mule-cutout requires the mule Python module to be available
        cmd = ' '.join([cutout, coord_type, full_fname, outfile] +
                       [str(x) for x in coords])
        icode, msg = utils.exec_subproc(cmd)

        if icode != 0 and coord_type == 'indices':
            if 'Source grid is {}x{}'.format(coords[2], coords[3]) in msg:
                # This file has already been cut out with this gridbox
                msg = 'File already contains the required gridbox.'
                mlevel = 'INFO'

    else:
        msg = 'Unable to cut out subdomain - ' + \
            '{} utility does not exist'.format(cutout if cutout else
                                               'mule-cutout')
        icode = -99

    if icode == 0:
        try:
            os.rename(full_fname + '.cut', full_fname)
            msg = 'Successfully extracted sub-domain from {}'.\
                format(full_fname)
            mlevel = 'OK'
        except OSError:
            msg = 'Failed to rename sub-domain fieldsfile'
            icode = -59

    utils.log_msg(msg, level=mlevel)

    return icode


@timer.run_timer
def create_um_mean(meanfile):
    '''
    Create a meanfile from UM fieldsfile using Mule
    Arguments:
        meanfile <type climatemean.MeanFile>
                 Object representing the mean to be created
    '''
    # This method has no timer decoration due to the way it is passed as a
    # function wrapper
    icode = None
    msg = ''
    if MULE_AVAIL:
        utils.log_msg('Creating meanfile {} with components:\n\t{}'.format(
            meanfile.fname['file'], '\n\t'.join(meanfile.component_files)
            ), level='INFO')

        months_per_period = {'1m': 1, '1s': 3, '1y': 12, '1x': 120}
        if utils.calendar() == '360day' or \
                meanfile.component not in months_per_period:
            weights = [1]*len(meanfile.component_files)
        else:
            weights = []
            for component in meanfile.component_files:
                year, month = [int(d) for d in identify_dates(component)[0][:2]]
                cmpt_weight = 0
                for i in range(months_per_period[meanfile.component]):
                    cmpt_weight += utils.monthlength(month + i, year)
                weights.append(cmpt_weight)

        mean_operator = WeightedMeanOperator(weights)

        # Load component files into Mule, and sort into date order
        load_mule = [mule.load_umfile(f) for f in meanfile.component_files]
        load_mule.sort(key=lambda x: list(x.fixed_length_header.raw[28:34]),
                       reverse=True)

        ff_out = load_mule[0].copy()

        # Update end date of mean period to match the end-of-period
        daynum = count = 1
        year = int(meanfile.periodend[0])
        while count < int(meanfile.periodend[1]):
            daynum += utils.monthlength(count, year)
            count += 1
        fixhd = [int(i) for i in meanfile.periodend]
        while len(fixhd) < 6:
            fixhd.append(0)
        fixhd.append(daynum)
        utils.log_msg('Meanfile validity date: {} day number {}'.
                      format(','.join([str(i) for i in fixhd[:4]]),
                             fixhd[6]), level='INFO')
        # Update t2 date (end of period) in the fixed-length header
        ff_out.fixed_length_header.raw[28:35] = fixhd

        for field in load_mule[0].fields[:]:
            if field.lbrel not in (2, 3):
                # Ignore invalid field
                continue

            # Update field headers
            meanfields = [field]
            for component in load_mule[1:]:
                for newfield in component.fields[:]:
                    if newfield.lbrel not in (2, 3):
                        component.fields.remove(newfield)
                    elif ((field.lbuser4 == newfield.lbuser4) and
                          (field.lblev == newfield.lblev)):
                        # Update field t1 (validity time) to match 1st file
                        meanfields[0].raw[1:7] = newfield.raw[1:7]
                        meanfields.append(newfield)
                        component.fields.remove(newfield)
                        break

            if len(meanfields) > 1:
                # Perform the meaning
                ff_out.fields.append(mean_operator(meanfields))

        utils.log_msg('\tPPheader STARTdate: {}'.format(
            ','.join([str(i) for i in ff_out.fields[0].raw[1:7]]),
            level='INFO'
        ))
        utils.log_msg('\tPPheader ENDdate: {}'.format(
            ','.join([str(i) for i in ff_out.fields[0].raw[7:13]]),
            level='INFO'
        ))

        try:
            # Try-except-else construct required here because Mule creates
            # a file regardless of successful completion of to_file()
            ff_out.to_file(meanfile.fname['full'])
        except Exception as exc:
            # Tidy up corrupt output file ready for next attempt
            msg += 'atmos create_um_mean: Mule failed to create mean file:\n\t'
            msg += exc.message
            utils.remove_files(meanfile.fname['full'], ignore_non_exist=True)
        else:
            # Successfully wrote to file
            icode = 0

    else:
        msg += 'create_um_mean: Mule is not available. Cannot create means'

    return icode, msg
