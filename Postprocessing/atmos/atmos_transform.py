#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2018-22 Met Office. All rights reserved.

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
       Extraction of fields to PP format (requires IRIS)
       Creation of means
'''

import os
import re

import utils
import timer

from netcdf_filenames import NCF_TEMPLATE
from validation import MULE_AVAIL, VALID_STR, identify_dates

try:
    # Establish exception raised when a file does not exist
    FileNotFoundError
except NameError:
    # Python2 raises an IOError in lieu of FileNotFoundError
    FileNotFoundError = IOError

try:
    import iris_transform
    IRIS_AVAIL = True
except ImportError:
    # Iris is not part of the standard Python package
    utils.log_msg('Iris Module is not available', level='WARN')
    IRIS_AVAIL = False

if MULE_AVAIL:
    import mule
    from mule.pp import fields_from_pp_file, fields_to_pp_file

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
        for field in all_cubes.fields:
            descriptor = '_' + stream_id
            if field.fieldname:
                descriptor += '-' + field.fieldname
            ncfilename = NCF_TEMPLATE.format(P=ncf_prefix,
                                             B=field.data_frequency,
                                             S=field.startdate,
                                             E=field.enddate,
                                             C=descriptor)
            if ncfilename != current_output:
                # Failure recovery - remove any pre-existing files
                utils.remove_files(ncfilename, ignore_non_exist=True)
                current_output = ncfilename

            icode += iris_transform.save_format(
                field.cube, ncfilename, 'netcdf',
                kwargs={'complevel': complevel, 'ncftype': ncftype}
            )
            if dirname:
                utils.move_files(ncfilename, dirname)

    return icode


@timer.run_timer
def extract_to_pp(sourcefiles, fields, outstream, data_freq=None):
    '''
    Extract given fields to PP format - First choice using Mule
    Multiple instances of the same field in the same file will result
    in only the final instance being extracted.

    Arguments:
       sourcefiles - <type str>  Full filename(s), including path, of
                                 source data.  List permitted.
       fields      - <type list> fieldnames or STASHcodes.
                                 Mule only works with STASHcodes.
       outstream   - <type str>  2char stream identifier for output
    Optional Arguments:
       data_freq   - <type str>  Data frequency \d+[ymdh]
    '''
    # Regular expression to match UM output filename:
    #    "(<RUNID>a.)<STREAM ID>(<YEAR>)"
    #  match.group(1) = Filename prefix
    #  match.group(2) = Filename datestamp year (4 digit)
    source_regex = re.compile(r'^(.+a\.)\w{2}(\d{4})')
    current_year = utils.CylcCycle().startcycle['strlist'][0]
    sources = []

    prefix = os.environ['CYLC_SUITE_NAME'] + 'a.'
    for sfile in utils.ensure_list(sourcefiles):
        if not os.path.exists(sfile):
            continue
        try:
            prefix, year = source_regex.match(sfile).groups()
        except AttributeError:
            year = current_year
            prefix = os.path.join(os.path.dirname(sfile),
                                  os.path.basename(prefix))
        if year == current_year:
            # Only process source file from the current year
            sources.append(sfile)

    outfile = prefix + outstream + current_year + '.pp'
    tmpfile = None
    if len(sources) < 1:
        utils.log_msg('No source files found for field extraction\n\t',
                      level='WARN')
    elif MULE_AVAIL:
        tmpfile = _extract_to_pp_mule(sources, fields, outfile, data_freq)
    elif IRIS_AVAIL:
        tmpfile = _extract_to_pp_iris(sources, fields, outfile, data_freq)
    else:
        utils.log_msg(
            'Either Mule or IRIS required to extract fields to PP format',
            level='WARN'
        )
    if tmpfile:
        # Copy temporary file to destination
        utils.log_msg('Writing fields to ' + str(outfile))
        utils.move_files(tmpfile, os.path.dirname(outfile), fail_on_err=True)

    return 0 if tmpfile else None

@timer.run_timer
def _extract_to_pp_mule(sourcefiles, fields, outfile, data_freq):
    '''
    Extract given field(s) to PP format using Mule.

    Arguments:
       sourcefiles - <type list < type str>>
                                 Full filename(s), including path, of
                                 source data
       fields      - <type list> Fieldnames or STASHcodes
       outstream   - <type str>  Fully filename for output, including path
       data_freq   - <type str>  Data frequency \d+[ymdh]
    '''
    rval = None
    stashcodes = [int(x) for x in fields if str(x).isdigit()]
    try:
        # Update the existing PPfile contents
        output_items = fields_from_pp_file(outfile)
    except FileNotFoundError:
        output_items = []

    # Compare integer constants in lookup only, since reals may differ between
    # 64bit fieldsfile source and 32bit ppfile output.
    # Exclude data length and address info:
    #    15=LBLREC, 21=LBPACK, 29=LBEGIN, 30=LBNREC, 40=NADDR
    match_int_consts = [x for x in range(46) if x not in [15, 21, 29, 30, 40]]
    for sfile in sourcefiles:
        new_fields = []
        for field in mule.FieldsFile.from_file(sfile).fields:
            if field.lbrel not in (2, 3) or field.lbuser4 not in stashcodes:
                # Exclude fields not matching requested STASHcode
                continue

            if data_freq:
                # Exclude fields not matching the required data frequency
                freq = utils.add_period_to_date([0]*5,
                                                [field.lbyrd - field.lbyr,
                                                 field.lbmond - field.lbmon,
                                                 field.lbdatd - field.lbdat,
                                                 field.lbhrd - field.lbhr])
                if freq[2] < 0:
                    # Adjust over the end of a month
                    freq[1] -= 1
                    freq[2] += utils.monthlength(field.lbmon, field.lbyr)
                if freq[1] < 0:
                    # Adjust over the end of a year
                    freq[0] -= 1
                    freq[1] += 12
                freq = ''.join([str(freq[x]) + p for x, p in enumerate('ymdh')
                                if freq[x] > 0])
                if freq != data_freq:
                    continue

            # Check we're not duplicating the field
            for field_id, existing_field in enumerate(output_items[:]):
                for raw_id in match_int_consts:
                    if field.raw[raw_id] != existing_field.raw[raw_id]:
                        break
                else:
                    # Replace existing field
                    output_items[field_id] = field
                    break
            else:
                new_fields.append(field)
        output_items += new_fields

    if len(output_items) > 0:
        tmpfile = os.path.basename(outfile)
        fields_to_pp_file(tmpfile, output_items)
        if os.path.exists(tmpfile):
            rval = tmpfile
        else:
            utils.log_msg('Failed to extract field(s) to PP with Mule',
                          level='WARN')
    else:
        utils.log_msg('No requested fields found in source file:\n\t'
                      + sourcefiles[0],
                      level='WARN')
    return rval

@timer.run_timer
def _extract_to_pp_iris(sourcefiles, fields, outfile, data_freq):
    '''
    Extract given field(s) to PP format using Iris.

    Arguments:
       sourcefiles - <type list < type str>>
                                 Full filename(s), including path, of
                                 source data
       fields      - <type list> Fieldnames or STASHcodes
       outstream   - <type str>  Fully filename for output, including path
       data_freq   - <type str>  Data frequency \d+[ymdh]
    '''
    rval = None
    source_items = iris_transform.IrisCubes(sourcefiles,
                                            {f: None for f in fields})

    if data_freq:
        for item in source_items.fields:
            if item.data_frequency != data_freq:
                source_items.fields.remove(item)

    if len(source_items.fields) < 1:
        utils.log_msg('No requested fields found in source file:\n\t'
                      + sourcefiles[0],
                      level='WARN')
        return rval

    if os.path.isfile(outfile):
        # Update the existing file contents
        existing_items = iris_transform.IrisCubes(outfile, None)
        for add_field in source_items.fields:
            existing_items.add_item(add_field)
        source_items = existing_items

    # Write source_items to file - first item to new file, then append
    icode = 0
    tmpfile = os.path.basename(outfile)
    utils.remove_files(tmpfile, ignore_non_exist=True)
    for field in source_items.fields:
        icode += iris_transform.save_format(field.cube, tmpfile, 'pp',
                                            kwargs={'append': True})
    if icode == 0:
        rval = tmpfile
    else:
        utils.log_msg('Failed to extract field(s) to PP with Iris',
                      level='WARN')
    return rval

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
