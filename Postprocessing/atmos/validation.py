#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2017 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    validation.py

DESCRIPTION
    Atmosphere arhiving methods

'''

import os
import re

import timer
import utils

try:
    # Mule is not part of the standard Python package
    import mule
    MULE_AVAIL = True
except ImportError:
    utils.log_msg('Mule Module is not available. um-pumf will be used.',
                  level='WARN')
    MULE_AVAIL = False


def identify_filedate(fname):
    '''
    The pp files may be instantaneous, a monthly, seasonal, or annual mean.
    This function will return the date expected in the header.
    Remember there are also p1234 means.
    Dump files will have an 8 digit date
    '''
    # Regular expression construction for seasonal means, monthly means, and
    # monthly instantaneous pp files. All other files (yearly means, dumps,
    # period n means, and instantenous pp files can be caught with the
    # 8/9digit regex.
    # We do this one first as it is likely to be the most common,
    # as it catches the dumps
    # The expression starting with the letter m is a STASH time processed
    # PP file, as opposed to one produced by the climate meaning system.
    patterns = [re.compile(r'\d?(\d{4})(\d{2})(\d{2})'),
                re.compile(r'[pm][a-z1-9](\d{4})([a-z]{3})')]

    months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
              'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
              'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
              'djf': 3, 'mam': 6, 'jja': 9, 'son': 12}

    filedate = None
    for patt in patterns:
        if patt.search(fname):
            filedate = patt.search(fname).groups()
            if filedate[1] in months:
                month = months[filedate[1]]
                year = filedate[0]
                if '.pm' in fname:
                    month += 1
                    if month == 13:
                        month = 1
                        year = str(int(filedate[0])+1)
                filedate = (year, str(month).zfill(2), '01')
            break
    if filedate:
        return filedate
    else:
        msg = 'Unable to retrieve a valid date from the filename: ' + fname
        utils.log_msg(msg, level='ERROR')


@timer.run_timer
def verify_header(atmospp, fname, logdir, logfile=None):
    '''
    Returns True/False dependent on whether the (year, month, day) of the
    filename matches the validity time in the UM fixed header
    '''
    headers, empty_file = mule_headers(fname)
    if not headers:
        # Mule not available, or else failed to extract the headers. Try pumf
        pumfout = logdir + '-pumfhead.out'
        pumfexe = os.path.join(atmospp.um_utils, 'um-pumf')
        headers = {int(k): str(v).zfill(2) for k, v in genlist(fname, pumfout,
                                                               pumfexe)}
    try:
        valid_date = tuple([headers[hd] for hd in range(28, 34)])
    except KeyError:
        utils.log_msg('No header information available', level='WARN')
        valid_date = ('',)*6

    filedate = identify_filedate(fname)

    validfile = (filedate == valid_date[:len(filedate)] and not empty_file)
    if validfile:
        utils.log_msg('Validation OK.  File will be archived: ' + fname)
    elif empty_file:
        msg = 'No valid fields found in file {}.'.format(fname)
        msg += ' Archive not required'
        if logfile:
            logfile.write(fname + ' FILE NOT ARCHIVED. Empty file \n')
        utils.log_msg(msg, level='INFO')
    else:
        msg = 'Validity time mismatch in file {} to be archived'.format(fname)
        if logfile:
            logfile.write(fname + ' ARCHIVE FAILED. Validity mismatch \n')
        utils.log_msg(msg, level='ERROR')

    return validfile


@timer.run_timer
def genlist(ppfile, header, pumfpath):
    '''
    Generator function to extract key-value pairs from the fixed-length
    header of a given UM fieldsfile using the UM pumf utility.
    '''
    # This command will only work with pumf versions 9.1->
    # As such there is an assertion on the pumf to ensure it points
    # to version 9.1 or more recent.
    pumfpatt = re.compile(r'vn(\d+\.\d+)')
    pumfver = float(pumfpatt.search(pumfpath).groups()[0])
    # Verify that the version of pumf is suitable
    try:
        assert pumfver >= 9.1
    except AssertionError:
        msg = 'The version of pumf selected must vn9.1 or later. '
        msg += 'Currently attemping to use version {}'.format(str(pumfver))
        utils.log_msg(msg, level='FAIL')
    except AttributeError:
        msg = 'Unable to extract the version of pumf from the path provided.'
        utils.log_msg(msg, level='FAIL')

    cmd = '{} -h {} {}'.format(pumfpath, header, ppfile)
    pumf_rcode, _ = utils.exec_subproc(cmd)

    if pumf_rcode == 0 and os.path.isfile(header):
        patt = re.compile(r'(\d*):\s*([-\d]*)')
        fixedhd = done = False
        for line in open(header, 'r').readlines():
            if 'FIXED LENGTH HEADER' in line:
                fixedhd = True
            elif fixedhd and re.search(r'\d*:', line):
                for pair in patt.finditer(line.strip()):
                    yield pair.group(1, 2)
                # Begun populating the fixed header dictionary -
                # we can break at next blank line
                done = True
            elif line.strip() == '' and done:
                break
        utils.remove_files(header)
    else:
        msg = 'pumf: Failed to extract header information from file {}'
        utils.log_msg(msg.format(ppfile), level='ERROR')


@timer.run_timer
def mule_headers(filename):
    '''
    Generate a dictionary of key-value pairs from the fixed-length
    header of a given UM fieldsfile using Mule
    '''
    if MULE_AVAIL:
        ffile = mule.FieldsFile.from_file(filename, remove_empty_lookups=True)

        # Extract first 40 values only
        headers = {h: str(ffile.fixed_length_header.raw[h]).zfill(2)
                   for h in range(1, 40)}
        empty_file = len(ffile.fields) == 0

    else:
        headers = None
        empty_file = False

    return headers, empty_file


@timer.run_timer
def make_dump_name(atmos):
    '''
    What is the name of the restart dump to be archived? Will return a list
    of dumps to be archived. If there are no dumps, the list will be empty.
    As we are only concerned with runs using an absolute datestamp the file
    name will have the form abcde.da20100101
    '''
    dumps_to_archive = []

    if atmos.final_dumpname:
        # Perform the final dump archiving if the end of the run has been
        # reached. Do not worry about seasonal or annual archiving at
        # this point, as the point of archiving this last dump is so the run
        # can be restarted from where it left off
        dumps_to_archive.append(atmos.final_dumpname)

    cycledt = atmos.suite.cycledt
    dt_len = len(cycledt)
    basisdt = [int(elem) for elem in atmos.envars.MODELBASIS.split(',')]

    if cycledt == basisdt[:dt_len]:
        # This is the first cycle, only archive the final cycle dump name
        return dumps_to_archive

    # Process for yearly archiving to determine which month to archive
    if atmos.naml.archiving.arch_dump_freq == 'Yearly':
        months = {'January': 1, 'February': 2, 'March': 3, 'April': 4,
                  'May': 5, 'June': 6, 'July': 7, 'August': 8, 'September': 9,
                  'October': 10, 'November': 11, 'December': 12}
        month_for_yearly_arch = months[atmos.naml.archiving.arch_year_month]
    else:
        # Set a default that mimics existing behaviour
        month_for_yearly_arch = 1

    # cycledt is a tuple containing integer values
    # (year,month,day,hour,minute,second) for the start of a cycle in a
    # cycling model run.
    dumptype = {
        'Yearly': cycledt[1] == month_for_yearly_arch and
                  cycledt[2] == 1 and cycledt[3] == 0,
        'Seasonal': cycledt[1] in (12, 3, 6, 9) and cycledt[2] == 1 and
                    cycledt[3] == 0,
        'Monthly': cycledt >= utils.add_period_to_date(
            basisdt,
            [0, atmos.naml.archiving.arch_dump_offset + 1])[:dt_len] and
                   cycledt[2] == 1 and cycledt[3] == 0
    }

    if dumptype[atmos.naml.archiving.arch_dump_freq]:
        dumps_to_archive.append(atmos.dumpname())

    return dumps_to_archive
