#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015 Met Office. All rights reserved.

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

import utils


def identify_filedate(fn):
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

    months = {'jan': 1, 'feb': 2,  'mar': 3,  'apr': 4,
              'may': 5, 'jun': 6,  'jul': 7,  'aug': 8,
              'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
              'djf': 3, 'mam': 6,  'jja': 9,  'son': 12}

    filedate = None
    for patt in patterns:
        if patt.search(fn):
            filedate = patt.search(fn).groups()
            if filedate[1] in months:
                month = months[filedate[1]]
                year = filedate[0]
                if '.pm' in fn:
                    month += 1
                    if month == 13:
                        month = 1
                        year = str(int(filedate[0])+1)
                filedate = (year, str(month).zfill(2), '01')
            break
    if filedate:
        return filedate
    else:
        msg = 'Unable to retrieve a valid date from the filename: ' + fn
        utils.log_msg(msg, level=5)


def verify_header(atmospp, fname, logfile, logdir):
    '''
    Returns True/False dependent on whether the (year, month, day) of the
    filename matches the validity time in the UM fixed header
    '''
    pumfout = logdir + '-pumfhead.out'
    pumfexe = os.path.join(atmospp.um_utils, 'um-pumf')
    headers = {int(k): str(v).zfill(2) for k, v in genlist(fname, pumfout,
                                                           pumfexe)}
    try:
        valid_date = tuple([headers[hd] for hd in range(28, 34)])
    except KeyError:
        utils.log_msg('No header information available', level=3)
        valid_date = ('',)*6

    filedate = identify_filedate(fname)

    validfile = (filedate == valid_date[:len(filedate)])
    if validfile:
        utils.log_msg('Validation OK.  File will be archived: ' + fname)
    else:
        msg = 'Validity time mismatch in file {} to be archived: Ignoring'.\
            format(fname)
        utils.log_msg(msg, level=3)
        logfile.write(fname + ' ARCHIVE FAILED. Validity mismatch \n')

    return validfile


def genlist(ppfile, header, pumfpath):
    # This command will only work with pumf versions 9.1->
    # As such there is an assertion on the pumf to ensure it points
    # to version 9.1 or more recent.
    pumfpatt = re.compile('vn(\d+\.\d+)')
    pumfver = float(pumfpatt.search(pumfpath).groups()[0])
    # Verify that the version of pumf is suitable
    try:
        assert(pumfver >= 9.1)
    except AssertionError:
        msg = 'The version of pumf selected must vn9.1 or later. '
        msg += 'Currently attemping to use version {}'.format(str(pumfver))
        utils.log_msg(msg, level=5)
    cmd = '{} -h {} {}'.format(pumfpath, header, ppfile)
    pumf_rcode, _ = utils.exec_subproc(cmd)

    if pumf_rcode == 0 and os.path.isfile(header):
        patt = re.compile('(\d*):\s*([-\d]*)')
        fixedhd = done = False
        for line in open(header, 'r').readlines():
            if 'FIXED LENGTH HEADER' in line:
                fixedhd = True
            elif fixedhd and re.search('\d*:', line):
                for pair in patt.finditer(line.strip()):
                    yield pair.group(1, 2)
                # Begun populating the fixed header dictionary -
                # we can break at next blank line
                done = True
            elif line.strip() == '' and done:
                break
        utils.remove_files(header)


def make_dump_name(atmos):
    '''
    What is the name of the restart dump to be archived? Will return a list
    of dumps to be archived. If there are no dumps, the list will be empty.
    As we are only concerned with runs using an absolute datestamp the file
    name will have the form abcde.da20100101
    '''
    cycledt = atmos.suite.cycledt
    basisdt = [int(elem) for elem in atmos.envars.MODELBASIS.split(',')]

    if cycledt == basisdt[:len(cycledt)]:
        # This is the first cycle, definitely do not archive any dumps
        return []

    # Process for yearly archiving to determine which month to archive
    if atmos.nl.archiving.arch_dump_freq == 'Yearly':
        months = {'January': 1, 'February': 2, 'March': 3, 'April': 4,
                  'May': 5, 'June': 6, 'July': 7, 'August': 8, 'September': 9,
                  'October': 10, 'November': 11, 'December': 12}
        month_for_yearly_archiving = months[atmos.nl.archiving.arch_year_month]
    else:
        # Set a default that mimics existing behaviour
        month_for_yearly_archiving = 1

    # cycledt is a tuple containing integer values (year,month,day) for
    # the start of a cycle in a cycling model run.
    dumptype = {
        'Yearly':   cycledt[1] == month_for_yearly_archiving and
        cycledt[2] == 1,
        'Seasonal': cycledt[1] in (12, 3, 6, 9) and cycledt[2] == 1,
        'Monthly':  cycledt >= utils.add_period_to_date(
            basisdt,
            [0, atmos.nl.archiving.arch_dump_offset + 1])[:len(cycledt)] and \
            cycledt[2] == 1
    }

    dumps_to_archive = []
    if dumptype[atmos.nl.archiving.arch_dump_freq]:
        dumps_to_archive.append(atmos.dumpname())

    # Perform the final dump archiving if the end of the run has been reached
    # Do not worry about seasonal or annual archiving at this point, as the
    # point of archiving this last dump is so the run can be restarted from
    # where it left off
    #
    if atmos.final_dumpname:
        dumps_to_archive.append(atmos.final_dumpname)

    return dumps_to_archive
