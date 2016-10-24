#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2016 Met Office. All rights reserved.

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
import errno
import shutil
import timer

debug_mode = False
debug_ok = True


class Variables(object):
    '''Object to hold a group of variables'''
    def __init__(self):
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
                'INITCYCLE_OVERRIDE': '',
                }
            if var in no_fail.keys():
                log_msg(no_fail[var], level='INFO')
            else:
                msg = 'LoadEnv: Unable to find environment variable: ' + var
                log_msg(msg, level='FAIL')

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
            msg = '[SUBPROCESS]: Command: {}\n[SUBPROCESS]: Error = {}:\n\t{}'
            log_msg(msg.format(' '.join(cmd), rcode, output), level='WARN')
            break

    return rcode, output


def get_subset(datadir, pattern):
    '''Returns a list of files matching a given regex'''
    datadir = check_directory(datadir)
    try:
        patt = re.compile(pattern)
    except TypeError:
        log_msg('get_subset: Incompatible pattern supplied.', level='WARN')
        files = []
    else:
        files = [fn for fn in sorted(os.listdir(datadir)) if patt.search(fn)]
    return files


def check_directory(datadir):
    '''
    Ensure that a given directory actually exists.
    Program will exit with an error if the test is unsuccessful.
    '''
    try:
        datadir = os.path.expandvars(datadir)
    except TypeError:
        log_msg('check_directory: Exiting - No directory provided',
                level='FAIL')

    if not os.path.isdir(datadir):
        msg = 'check_directory: Exiting - Directory does not exist: '
        log_msg(msg + str(datadir), level='FAIL')
    return datadir


def add_path(files, path):
    ''' Add a given path to a file or list of files provided '''
    path = check_directory(path)
    if not isinstance(files, list):
        files = [files]

    return [os.path.join(path, f) for f in files]


def create_dir(dirname, path=None):
    ''' Create a directory '''
    if path:
        dirname = os.path.join(path, dirname)
    try:
        os.makedirs(dirname)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(dirname):
            pass
        else:
            log_msg('create_dir: Unable to create directory: ' + dirname,
                    level='FAIL')


@timer.run_timer
def remove_files(delfiles, path=None, ignoreNonExist=False):
    '''
    Delete files.
    Optional arguments:
      path           - if not provided full path is assumed to have been
                       provided in the filename.
      ignoreNonExist - flag to allow a non-existent file to be ignored.
                       Default behaviour is to provide a warning and continue.
    '''
    if path:
        path = check_directory(path)
        delfiles = add_path(delfiles, path)

    if not isinstance(delfiles, list):
        delfiles = [delfiles]

    for fname in delfiles:
        try:
            os.remove(fname)
        except OSError:
            if not ignoreNonExist:
                log_msg('remove_files: File does not exist: ' + fname,
                        level='WARN')


@timer.run_timer
def move_files(mvfiles, destination, originpath=None, fail_on_err=False):
    '''
    Move a single file or list of files to a given directory.
    Optionally a directory of origin may be specified.
    '''
    msglevel = 'ERROR' if fail_on_err else 'WARN'
    destination = check_directory(destination)

    if originpath:
        mvfiles = add_path(mvfiles, originpath)

    if not isinstance(mvfiles, list):
        mvfiles = [mvfiles]

    for fname in mvfiles:
        try:
            shutil.move(fname, destination)
        except IOError:
            log_msg('move_files: File does not exist: ' + fname, level=msglevel)
        except shutil.Error:
            msg = 'move_files: Attempted to overwrite original file?: ' + fname
            log_msg(msg, level=msglevel)


def add_period_to_date(indate, delta):
    '''
    Add a delta (list of integers) to a given date (list of integers).
        Call `rose date` with calendar argument -
      taken from environment variable CYLC_CYCLING_MODE.
        If no indate is provided ([0,0,0,0,0]) then delta is returned.
    '''

    while len(indate) < 5:
        indate.append(0)
        msg = '`rose date` requires length=5 input date array - adding zero: '
        log_msg(msg + str(indate), level='WARN')

    if isinstance(delta, str):
        all_targets = {'h': 3, 'd': 2, 'm': 1, 's': 1, 'y': 0, 'a': 0}
        digits = re.match(r'(-?\d+)([{}])'.format(''.join(all_targets.keys())),
                          delta.lower())
        if digits:
            base, target = digits.groups()
        else:
            base = 1
            target = delta[0].lower()
        delta = [0]*5
        try:
            index = [all_targets[t] for t in all_targets if
                     t == target][0]
            delta[index] = int(base) * (3 if target == 's' else 1)
        except IndexError:
            msg = 'add_period_to_date - Unknown target period: '
            log_msg(msg + target, level='FAIL')

    offset = ('-' if any([d for d in delta if d < 0]) else '') + 'P'
    for elem in delta:
        if elem != 0:
            try:
                offset += str(abs(elem)) + ['Y', 'M', 'D'][delta.index(elem)]
            except IndexError:
                if 'T' not in offset:
                    offset += 'T'
                offset += str(abs(elem)) + ['M', 'H'][delta.index(elem)-4]

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
            log_msg('add_period_to_date: Invalid date for conversion to ISO '
                    '8601 date representation: ' + str(indate), level='FAIL')

    if rcode == 0:
        outdate = map(int, output.split(','))
    else:
        log_msg('`rose date` command failed:\n' + output, level='WARN')
        outdate = None

    return outdate


def log_msg(msg, level='INFO'):
    '''
    Produce a message to the appropriate output stream.
    Messages tagged with 'ERROR' and 'FAIL' will result in the program exiting,
    unless model is running in debug_mode, in which case only 'FAIL' will exit.
    '''
    out = sys.stdout
    err = sys.stderr
    level = str(level).upper()

    output = {
        'DEBUG': (err, '[DEBUG] '),
        'INFO': (out, '[INFO] '),
        'OK': (out, '[ OK ] '),
        'WARN': (err, '[WARN] '),
        'ERROR': (err, '[ERROR] '),
        'FAIL': (err, '[FAIL] '),
    }

    try:
        output[level][0].write('{} {}\n'.format(output[level][1], msg))
    except KeyError:
        level = 'WARN'
        msg = 'log_msg: Unknown severity level for log message.'
        output[level][0].write('{} {}\n'.format(output[level][1], msg))

    if level == 'ERROR':
        # If in debug mode, terminate at the end of the task.
        # Otherwise terminate now.
        catch_failure()
    elif level == 'FAIL':
        sys.exit(output[level][1] + 'Terminating PostProc...')


def set_debugmode(debug):
    '''Set method for the debug_mode global variable'''
    global debug_mode
    global debug_ok

    debug_mode = debug
    debug_ok = True


def get_debugmode():
    '''Get method for the debug_mode global variable'''
    return debug_mode


def get_debugok():
    '''Get method for the debug_ok global variable'''
    return debug_ok


def catch_failure():
    '''
    Ignore errors in external subprocess commands or other failures,
    allowing the task to continue to completion.
    Ultimately causes the task to fail due to the global debug_ok setting.
    '''
    global debug_ok

    if debug_mode:
        log_msg('Ignoring failed external command. Continuing...',
                level='DEBUG')
        debug_ok = False
    else:
        log_msg('Command Terminated', level='FAIL')
