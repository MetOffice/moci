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
    utils.py

DESCRIPTION
    Common utilities for post-processing methods

'''
import sys
import re
import os
import shutil
import timer


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
            no_fail = {
                'ARCHIVE_FINAL': 'ARCHIVE_FINAL=False',
                'CYCLEPOINT_OVERRIDE': '',
                }
            if var in no_fail.keys():
                msg = no_fail[var]
                level = 1
            else:
                msg = 'LoadEnv: Unable to find environment variable: ' + var
                level = 5
            log_msg(msg, level=level)

    return container


@timer.run_timer
def exec_subproc(cmd, verbose=True, cwd=os.environ['PWD']):
    '''
    Execute given shell command.
    'cmd' input should be in the form of either a:
      string        - "cd DIR; command arg1 arg2"
      list of words - ["command", "arg1", "arg2"]
    Optional arguments:
      verbose = False: only reproduce the command std.out upon
                failure of the command
                True: reprodude std.out regardless of outcome
      cwd     = Directory in which to execute the command
    '''
    import subprocess
    cmd_array = [cmd]
    if not isinstance(cmd, list):
        cmd_array = cmd.split(';')
        for i, cmd in enumerate(cmd_array):
            cmd_array[i] = cmd.split()

    for cmd in cmd_array:
        if 'cd' in cmd:
            cwd = cmd[1]
            continue
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                             universal_newlines=True, cwd=cwd)
            rcode = 0
            if verbose:
                log_msg('[SUBPROCESS]: ' + str(output))
        except subprocess.CalledProcessError as exc:
            output = exc.output
            rcode = exc.returncode
        except OSError as exc:
            output = exc.strerror
            rcode = exc.errno
        if rcode != 0:
            log_msg('[SUBPROCESS]: Command: {}'.format(' '.join(cmd)), 4)
            log_msg('[SUBPROCESS]: Error = {}:\n\t{}'.format(rcode, output), 4)
            break
    return rcode, output


def catch_failure(ignore=False):
    if ignore:
        log_msg('Ignoring failed external command. Continuing...', 0)
    else:
        log_msg('Command Terminated', 5)


def get_subset(datadir, pattern):
    '''Returns a list of files matching a given regex'''
    datadir = check_directory(datadir)
    try:
        patt = re.compile(pattern)
    except TypeError:
        log_msg('get_subset: Incompatible pattern supplied.', 4)
        files = []
    else:
        files = [fn for fn in sorted(os.listdir(datadir)) if patt.search(fn)]
    return files


def check_directory(datadir):
    try:
        datadir = os.path.expandvars(datadir)
    except TypeError:
        log_msg('check_directory: Exiting - No directory provided', 5)

    if not os.path.isdir(datadir):
        log_msg('check_directory: Exiting - Directory does not exist: '
                + str(datadir), 5)
    return datadir


def add_path(files, path):
    path = check_directory(path)
    if type(files) != list:
        files = [files]

    return map(lambda f: os.path.join(path, f), files)


@timer.run_timer
def remove_files(delfiles, path=None, ignoreNonExist=False):
    if path:
        path = check_directory(path)
        delfiles = add_path(delfiles, path)

    if type(delfiles) != list:
        delfiles = [delfiles]

    for fn in delfiles:
        try:
            os.remove(fn)
        except OSError:
            if not ignoreNonExist:
                log_msg('remove_files: File does not exist: ' + fn, 3)


@timer.run_timer
def move_files(mvfiles, destination, originpath=None, fail_on_err=False):
    '''
    Move a single file or list of files to a given directory.
    Optionally a directory of origin may be specified.
    '''
    msglevel = 5 if fail_on_err else 3
    destination = check_directory(destination)

    if originpath:
        mvfiles = add_path(mvfiles, originpath)

    if not isinstance(mvfiles, list):
        mvfiles = [mvfiles]

    for fname in mvfiles:
        try:
            shutil.move(fname, destination)
        except IOError:
            log_msg('move_files: File does not exist: ' + fname, msglevel)
        except shutil.Error:
            msg = 'move_files: Attempted to overwrite original file?: ' + fname
            log_msg(msg, msglevel)


def add_period_to_date(indate, delta):
    '''
    Add a delta (list of integers) to a given date (list of integers).
        Call `rose date` with calendar argument -
      taken from environment variable CYLC_CYCLING_MODE.
        If no indate is provided ([0,0,0,0,0}) then delta is returned.
    '''

    while len(indate) < 5:
        indate.append(0)
        msg = '`rose date` requires length=5 input date array - adding zero: '
        log_msg(msg + str(indate), level=3)

    offset = 'P'
    for elem in delta:
        if elem > 0:
            try:
                offset += str(elem) + ['Y', 'M', 'D'][delta.index(elem)]
            except IndexError:
                if 'T' not in offset:
                    offset += 'T'
                offset += str(elem) + ['M', 'H'][delta.index(elem)-4]

    if all(elem == 0 for elem in indate):
        output = '{0:0>4},{1:0>2},{2:0>2},{3:0>2},{4:0>2}'.format(*delta)
        rcode = 0
    else:
        dateinput = '{0:0>4}{1:0>2}{2:0>2}T{3:0>2}{4:0>2}'.format(*indate)

        if re.match(r'^\d{8}T\d{4}$', dateinput):
            cal = os.environ['CYLC_CYCLING_MODE']
            if cal.lower() == 'integer':
                # Non-Cycling suites should export the CALENDAR environment
                # variable.  DEFAULT VALUE: 360day
                try:
                    cal = os.environ['CALENDAR']
                except KeyError:
                    cal = '360day'
            cmd = 'rose date {} --calendar {} --offset {} --print-format ' \
            '%Y,%m,%d,%H,%M'.format(dateinput, cal, offset)
            rcode, output = exec_subproc(cmd, verbose=False)
        else:
            log_msg('add_period_to_date: Invalid date for conversion to '
                    'ISO 8601 date representation: ' + str(indate), level=5)



    if rcode == 0:
        outdate = map(int, output.split(','))
    else:
        log_msg('`rose date` command failed:\n' + output, level=3)
        outdate = None

    return outdate


def log_msg(msg, level=1):
    out = sys.stdout
    err = sys.stderr

    output = {
        0: (out, '[DEBUG] '),
        1: (out, '[INFO] '),
        2: (out, '[ OK ] '),
        3: (err, '[WARN] '),
        4: (err, '[ERROR] '),
        5: (err, '[FAIL] '),
    }

    try:
        output[level][0].write('{} {}\n'.format(output[level][1], msg))
    except KeyError:
        level = 3
        msg = 'log_msg: Unknown severity level for log message.'
        output[level][0].write('{} {}\n'.format(output[level][1], msg))

    if level == 5:
        sys.exit(output[level][1] + 'Terminating PostProc...')
