#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016-2017 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    archive_integrity.py

DESCRIPTION
    Main function for the periodic verification of an archive
'''
import sys
import os
import re

import expected_content
import timer
import nlist
import utils


def dummy_cylc_environment():
    ''' Load CYLC environment for dummy testing '''
    os.environ['CYLC_TASK_CYCLE_POINT'] = '19800901T0000Z'
    os.environ['CYLC_SUITE_FINAL_CYCLE_POINT'] = '20000101T0000Z'
    os.environ['CYLC_CYCLING_MODE'] = '360day'


def archive_contents(listing):
    '''
    Return a dictionary containing all files in each data/fileset
    '''
    present_data = {}
    for line in listing:
        path, fname = os.path.split(line.strip())
        collection = os.path.basename(path)
        if collection.endswith('.file') or collection.endswith('.pp'):
            try:
                present_data[collection].append(fname)
            except KeyError:
                present_data[collection] = [fname]

    return present_data


def log_archive(dataset):
    ''' Debug mode only - read archived files from Cylc logs '''

    logfile = 'cylclog'
    cylclog = os.path.join(os.environ['CYLC_SUITE_SHARE_DIR'], logfile)
    utils.log_msg('Reading archive contents from file: ' + cylclog,
                  level='DEBUG')
    with open(cylclog, 'r') as logfile:
        files = [fn.strip('\n') for fn in logfile.readlines()
                 if dataset in fn]
    return archive_contents(files)


def moose_archive(dataset):
    ''' Return Moose archive listing '''
    if len(dataset.split('/')) == 1:
        dataset = 'moose:crum/' + dataset
    cmd = 'moo ls -r {}'.format(dataset)
    _, listing = utils.exec_subproc(cmd)
    utils.log_msg('Moose archive listing --->\n {}\n'.format(listing.strip()),
                  level='INFO')
    return archive_contents(listing.split())


def verify_archive(expected_files, archived_files):
    '''
    Verify contents of expected_files dictionary are present
    in the archive.
    '''
    verified = True
    for fileset in sorted(expected_files):
        try:
            missing = [d for d in expected_files[fileset] if
                       d not in archived_files[fileset] and
                       not d.endswith('$')]
            regex_defined = [d for d in expected_files[fileset] if
                             d.endswith('$')]
        except KeyError:
            missing = []
            regex_defined = []

        missing_regex = []
        for regex in regex_defined:
            no_match = True
            for arch_file in archived_files[fileset]:
                if re.match(regex, os.path.basename(arch_file)):
                    no_match = False
                    break
            if no_match:
                missing_regex.append(regex)

        msg = 'Collection {} '.format(fileset)
        if fileset not in archived_files.keys():
            verified = False
            utils.log_msg(msg + 'is missing from the archive.', level='WARN')
        elif missing or missing_regex:
            verified = False
            if missing:
                msg += '- Files missing from the archive:\n\t'
                msg += '\n\t'.join(missing)
            if missing_regex:
                if missing:
                    msg += '\nCollection {} '.format(fileset)
                msg += '- No files found to match regular expression: '
                msg += '\n\t'.join(missing_regex)
            utils.log_msg(msg + '\n\t'.join(missing_regex), level='WARN')
        else:
            utils.log_msg(msg + '- All expected files present in archive.',
                          level='OK')

    return verified


def check_archive_additional(expected_files, archived_files):
    '''
    Check contents of archive against expected files and return list of
    unexpected addition files.
    '''
    extra = False
    for fileset in sorted(archived_files):
        try:
            if expected_files[fileset][0].endswith('$'):
                additional = []
            else:
                additional = [d for d in archived_files[fileset] if
                              d not in expected_files[fileset]]
        except KeyError:
            additional = []

        msg = 'Collection {} '.format(fileset)
        if fileset not in expected_files.keys():
            extra = True
            utils.log_msg(msg + 'is unexpectedly present in the archive.',
                          level='WARN')
        elif additional:
            extra = True
            utils.log_msg(msg + '- Unexpected files in the archive:'
                          '\n\t{}'.format('\n\t'.join(additional)),
                          level='WARN')

    return extra


def main():
    '''
    Main function:
      Read in default namelists, overwriting where appropriate with app values.
      Call methods for:
        * Restart files
        * Means files
        * Atmosphere instantaneous fieldsfiles
'''
    timer.set_nulltimer()

    load_nl = nlist.loadNamelist('verify.nl')
    startdate = load_nl.commonverify.startdate
    enddate = load_nl.commonverify.enddate
    prefix = load_nl.commonverify.prefix
    dataset = load_nl.commonverify.dataset
    if load_nl.commonverify.testing:
        dummy_cylc_environment()

    models = [str(m).lower() for m in sys.argv[1:]]

    expected_files = {}
    for namelist in [m for m in dir(load_nl) if not m.startswith('_')]:
        try:
            verify_model = getattr(getattr(load_nl, namelist), 'verify_model')
        except AttributeError:
            # "verify_model" not present - not a verifiable model namelist
            continue

        model = namelist.replace('verify', '')
        if (models and model.lower() not in models) or not verify_model:
            # Specific models requested - this model is not in the list
            continue

        # Restart files
        restarts = expected_content.RestartFiles(
            startdate, enddate, prefix, model,
            getattr(load_nl, namelist)
            )
        expected_files.update(restarts.expected_files())

        # Diagnostic files
        diagnostics = expected_content.DiagnosticFiles(
            startdate, enddate, prefix, model,
            getattr(load_nl, namelist)
            )
        expected_files.update(diagnostics.expected_diags())

    if dataset == 'dummy':
        # Debug mode - read from log file
        archived_files = log_archive(dataset)
    else:
        archived_files = moose_archive(dataset)

    if load_nl.commonverify.check_additional_files_archived:
        if check_archive_additional(expected_files, archived_files):
            utils.log_msg('Unexpected files present in ' + dataset,
                          level='INFO')

    if verify_archive(expected_files, archived_files):
        utils.log_msg('All expected files present in ' + dataset, level='OK')
    else:
        utils.log_msg('Dataset incomplete - holes present in ' + dataset,
                      level='FAIL')


if __name__ == '__main__':
    main()
