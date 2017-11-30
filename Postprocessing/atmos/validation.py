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
        assert pumfver >= 9.1 and pumfver < 10.9
    except AssertionError:
        msg = 'This code is compatible with versions of um-pumf from vn9.1 ' + \
            'until its retirement at vn10.9. '
        msg += 'Currently attempting to use version {}'.format(str(pumfver))
        msg += '\n Please ensure Mule is available as an alternative utiltity.'
        utils.log_msg(msg, level='FAIL')
    except AttributeError:
        msg = 'Unable to extract the version of pumf from the path provided.'
        utils.log_msg(msg, level='FAIL')

    cmd = '{} -h {} {}'.format(pumfpath, header, ppfile)
    pumf_rcode, pumf_out = utils.exec_subproc(cmd)

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
        if 'Problem with PUMF' in pumf_out:
            msg = 'pumf: Failed to extract header information from file {}'
        else:
            msg = 'Failed to find pumf executable'
        utils.log_msg(msg.format(ppfile), level='ERROR')


@timer.run_timer
def mule_headers(filename):
    '''
    Generate a dictionary of key-value pairs from the fixed-length
    header of a given UM fieldsfile using Mule
    '''
    if MULE_AVAIL:
        umfile = mule.UMFile.from_file(filename, remove_empty_lookups=True)

        # Extract first 40 values only
        headers = {h: str(umfile.fixed_length_header.raw[h]).zfill(2)
                   for h in range(1, 40)}
        empty_file = len(umfile.fields) == 0

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

    cyclept = atmos.suite.cyclepoint
    dt_len = len(cyclept.endcycle['intlist'])

    no_arch_before = utils.add_period_to_date(
        atmos.suite.initpoint, [0, atmos.naml.archiving.arch_dump_offset]
        )[:dt_len]
    while len(no_arch_before) < dt_len:
        no_arch_before.append(0)

    months = [None, 'January', 'February', 'March', 'April', 'May',
              'June', 'July', 'August', 'September', 'October',
              'November', 'December']
    month_range = {
        'Yearly': (months.index(atmos.naml.archiving.arch_year_month),
                   months.index(atmos.naml.archiving.arch_year_month) + 1),
        'Seasonal': (3, 13, 3),
        'Monthly': (1, 13),
        }

    dump_freq = atmos.naml.archiving.arch_dump_freq
    dumpdates = []
    for year in range(cyclept.startcycle['intlist'][0] - 1,
                      cyclept.endcycle['intlist'][0] + 1):
        try:
            for month in range(*month_range[dump_freq]):
                dumpdates.append([year, month, 1, 0, 0, 0])
        except KeyError:
            # List of timestamps
            for tstamp in atmos.archive_tstamps:
                match = re.match(r'(\d{1,2})-(\d{1,2})_?(\d{1,2})?', tstamp)
                try:
                    month, day, hour = match.groups()
                except AttributeError:
                    msg = 'Archive restart dumps: timestamp "{}"'.format(tstamp)
                    msg += ' does not match the expected format: "MM-DD[_HH]"'
                    utils.log_msg(msg, level='WARN')
                    continue
                hour = int(hour) if hour else 0
                dumpdates.append([year, int(month), int(day), hour, 0, 0])

    for date in dumpdates:
        # Add dumpdates which fall between, but not including, "no_arch_before"
        # (offset from the model basis time) and the end of the current cycle.
        if date[:dt_len] < cyclept.endcycle['intlist'] and \
                date[:dt_len] > no_arch_before:
            dumps_to_archive.append(atmos.dumpname(dumpdate=date))

    return dumps_to_archive
