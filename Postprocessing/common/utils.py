#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
(C) Crown copyright Met Office. All rights reserved.
For further details please refer to the file COPYRIGHT.txt
which you should have received as part of this distribution.
*****************************COPYRIGHT******************************
--------------------------------------------------------------------
 Code Owner: Please refer to the UM file CodeOwners.txt
 This file belongs in section: Rose scripts
--------------------------------------------------------------------
NAME
    utils.py

DESCRIPTION
    Common utilities for post-processing methods

'''
import sys
import re
import os
import shutil


class Variables:
    '''Object to hold a group of variables'''
    pass


def loadEnv(*envars, **append):
    ''' Load Environment Variables '''
    append = append.pop('append', False)
    container = Variables()
    if append:
        for var in [v for v in dir(append) if not v.startswith('_')]:
            setattr(container, var, getattr(append, var))

    for var in envars:
        try:
            setattr(container, var, os.environ[var])
        except KeyError:
            msg = 'Unable to find the environment variable:' + var
            level = 1 if var == 'ARCHIVE_FINAL' else 5
            log_msg(msg, level)

    return container


def exec_subproc(cmd, verbose=True):
    import subprocess
    process = subprocess.Popen(cmd, shell=True,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    output, error = process.communicate()
    if verbose and output:
        print >> sys.stdout, '[SUBPROCESS OUTPUT]', output
    if error:
        print >> sys.stderr, '[SUBPROCESS ERROR]', error
    return process.returncode, output


def catch_failure(ignore=False):
    if ignore:
        log_msg('Ignoring failed external command. Continuing...', 0)
    else:
        log_msg('Command Terminated', 5)


def get_subset(datadir, pattern):
    '''Returns a list of files matching a given regex'''
    check_directory(datadir)
    patt = re.compile(pattern)
    return [fn for fn in sorted(os.listdir(datadir)) if patt.search(fn)]


def check_directory(datadir):
    if not os.path.isdir(datadir):
        log_msg('Exiting - Directory does not exist: ' + datadir, 5)


def add_path(files, path):
    check_directory(path)
    if type(files) == list:
        outfiles = map(lambda f: os.path.join(path, f), files)
    else:
        outfiles = os.path.join(path, files)
    return outfiles


def remove_files(delfiles, path=None):
    if path:
        check_directory(path)
        delfiles = add_path(delfiles, path)
    if type(delfiles) == list:
        for fn in delfiles:
            try:
                os.remove(fn)
            except OSError:
                log_msg('File does not exist: ' + fn, 3)
    else:
        try:
            os.remove(delfiles)
        except OSError:
            log_msg('File to be deleted does not exist: ' + delfiles, 3)


def move_files(mvfiles, destination, originpath=None):
    check_directory(destination)

    if originpath:
        mvfiles = add_path(mvfiles, originpath)

    if type(mvfiles) == list:
        for fn in mvfiles:
            try:
                shutil.move(fn, destination)
            except IOError:
                log_msg('File does not exist:\n\t' + fn, 3)
            except shutil.Error:
                log_msg('Destination already exists?: \n\t' + fn, 3)

    else:
        try:
            shutil.move(mvfiles, destination)
        except IOError:
            log_msg('File to be moved does not exist: \n\t' + mvfiles, 3)


def add_period_to_date(indate, delta, lcal360=True):
    while len(indate) < 5:
        indate.append(0)
        msg = '`rose date` requires length=5 input date array - adding zero: '
        log_msg(msg + indate, 3)

    try:
        # Cylc6.0 ->
        cal = os.environ['CYLC_CYCLING_MODE']
        cylc6 = True
    except KeyError:
        # 'Pre Cylc6.0...'
        cylc6 = False

    if cylc6:
        # Cylc6.0 ->
        offset = 'P'
        for elem in delta:
            if elem > 0:
                offset += str(elem) + ['Y', 'M', 'D'][delta.index(elem)]

        dateinput = '{0:>4}{1:0>2}{2:0>2}T{3:0>2}{4:0>2}'.format(*indate)
        cmd = 'rose date {} --calendar {} --offset {} ' \
            '--print-format %Y,%m,%d,%H,%M'.format(dateinput, cal, offset)
        rcode, output = exec_subproc(cmd, verbose=False)

        if rcode == 0:
            outdate = map(int, output.split(','))
        else:
            log_msg('`rose date` command failed - ' + error, 3)
            outdate = None

    else:
        # 'Pre Cylc6.0...'
        outdate = [sum(x) for x in zip(indate, delta)]
        if lcal360:
            limits = {0: 999999, 1: 12, 2: 30, 3: 24, 4: 60, 5: 60, }
            for elem in reversed(sorted(limits)):
                try:
                    newval = outdate[elem] % limits[elem]
                    if outdate[elem] != newval:
                        outdate[elem-1] += outdate[elem]//limits[elem]
                        outdate[elem] = newval
                except IndexError:
                    pass

        else:  # Gregorian
            offset = 'P{}D'.format(delta[2])
            cmd = 'rose date {} --offset {} --print-format %Y,%m,%d,%H,*M'.\
                format(os.environ['CYLC_TASK_CYCLE_TIME'], offset)
            rcode, output = exec_subproc(cmd, verbose=False)
            if rcode == 0:
                outdate = map(int, output.split(','))
            else:
                log_msg('`rose date` command failed', 3)
                outdate = None

    return outdate


def log_msg(msg, level=1):
    output = {
        0: (sys.stdout, '[DEBUG] '),
        1: (sys.stdout, '[INFO] '),
        2: (sys.stdout, '[ OK ] '),
        3: (sys.stderr, '[WARN] '),
        4: (sys.stderr, '[ERROR] '),
        5: (sys.stderr, '[FAIL] '),
    }

    try:
        print >> output[level][0], output[level][1], msg
    except KeyError:
        level = 3
        print >> output[level][0], output[level][1], \
            'Unknown severity level for log message'

    if level == 5:
        sys.exit(100)
