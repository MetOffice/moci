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


globals()['debug_mode'] = None
globals()['debug_ok'] = True

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
                'FINALCYCLE_OVERRIDE': '',
                }
            if var in no_fail.keys():
                log_msg(no_fail[var], level='INFO')
            else:
                msg = 'LoadEnv: Unable to find environment variable: ' + var
                log_msg(msg, level='FAIL')

    return container


def cyclestring(specific_cycle=None):
    '''
    Create a representation of the current cycletime in string format.
    Return a list of strings: YYYY,MM,DD,mm,ss

    Optional argument: specific_cycle
        <type 'str'>, Format: '[YYYY][MM][DD]T[mm][hh]Z'
        Required when the cycle string required is for a date other than
        the current cycletime, for example the final cycle time.
    '''
    envars = loadEnv('CYCLEPOINT_OVERRIDE', 'CYLC_TASK_CYCLE_POINT')

    if specific_cycle:
        cyclepoint = specific_cycle
    else:
        # Default to current cycle point
        try:
            # An override is required for Single Cycle suites
            cyclepoint = envars.CYCLEPOINT_OVERRIDE
        except AttributeError:
            cyclepoint = envars.CYLC_TASK_CYCLE_POINT

    match = re.search(r'(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})Z', cyclepoint)
    if match:
        cyclestring = match.groups()
    else:
        log_msg('Unable to determine cycletime', level='FAIL')

    return cyclestring


def finalcycle():
    '''
    Determine whether this cycle is the final cycle for the running suite.
    Return True/False
    '''
    envars = loadEnv('ARCHIVE_FINAL',
                     'FINALCYCLE_OVERRIDE',
                     'CYLC_SUITE_FINAL_CYCLE_POINT')
    try:
        finalcycle = ('true' in envars.ARCHIVE_FINAL.lower())
    except AttributeError:
        try:
            finalpoint = envars.FINALCYCLE_OVERRIDE
        except AttributeError:
            finalpoint = envars.CYLC_SUITE_FINAL_CYCLE_POINT
        finalcycle = (cyclestring() == cyclestring(specific_cycle=finalpoint))

    return finalcycle


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


def ensure_list(value, listnone=True):
    '''
    Return a list for a given input.
      Optional argument: listnone - True=Return [''] or [None]
                                    False=Return '' or None
    '''
    if not isinstance(value, list) and (listnone or value):
        value = [value]
    return value


def add_path(files, path):
    ''' Add a given path to a file or list of files provided '''
    path = check_directory(path)
    files = ensure_list(files)

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
    delfiles = ensure_list(delfiles)

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
    mvfiles = ensure_list(mvfiles)

    for fname in mvfiles:
        try:
            shutil.move(fname, destination)
        except IOError:
            log_msg('move_files: File does not exist: ' + fname, level=msglevel)
        except shutil.Error:
            msg = 'move_files: Attempted to overwrite original file?: ' + fname
            log_msg(msg, level=msglevel)


def calendar():
    ''' Return the calendar based on the suite environment '''
    cal = os.environ['CYLC_CYCLING_MODE']
    if cal.lower() == 'integer':
        # Non-Cycling suites should export the CALENDAR environment
        # variable.  DEFAULT VALUE: 360day
        try:
            cal = os.environ['CALENDAR']
        except KeyError:
            cal = '360day'
    return cal

def add_period_to_date(indate, delta):
    '''
    Add a delta (list of integers) to a given date (list of integers).
        For 360day calendar, add period with simple arithmetic for speed
        For other calendars, call `rose date` with calendar argument -
      taken from environment variable CYLC_CYCLING_MODE.
        If no indate is provided ([0,0,0,0,0]) then delta is returned.
    '''
    if isinstance(delta, str):
        delta = get_frequency(delta, rtn_delta=True)

    if all(elem == 0 for elem in indate):
        outdate = delta
    else:
        cal = calendar()
        if cal == '360day':
            outdate = _mod_360day_calendar_date(indate, delta)
        else:
            outdate = _mod_all_calendars_date(indate, delta, cal)

    return outdate

@timer.run_timer
def _mod_all_calendars_date(indate, delta, cal):
    ''' Call `rose date` to return a date '''
    while len(indate) < 5:
        val = 1 if len(indate) in [1, 2] else 0
        indate.append(val)
        msg = '`rose date` requires length=5 input date array - adding {}: '
        log_msg(msg.format(val) + str(indate), level='WARN')

    offset = ('-' if any([d for d in delta if d < 0]) else '') + 'P'
    for elem in delta:
        if elem != 0:
            try:
                offset += str(abs(elem)) + ['Y', 'M', 'D'][delta.index(elem)]
            except IndexError:
                if 'T' not in offset:
                    offset += 'T'
                offset += str(abs(elem)) + ['M', 'H'][delta.index(elem)-4]

        dateinput = '{0:0>4}{1:0>2}{2:0>2}T{3:0>2}{4:0>2}'.format(*indate)
        if re.match(r'^\d{8}T\d{4}$', dateinput):
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

@timer.run_timer
def _mod_360day_calendar_date(indate, delta):
    '''
    Simple arithmetic calculation of new date for 360 day calendar.
    Use of `rose date`, while possible is inefficient.
    '''
    try:
        outdate = [int(x) for x in indate]
    except ValueError:
        log_msg('add_period_to_date: Invalid date representation: ' + 
                str(indate), level='FAIL')
    diff_hours = 0
    # multiplier to convert the delta list to a total number of hours
    multiplier = [360*24, 30*24, 24, 1, 1./60, 1./60/60] 
    for i, val in enumerate(delta):
        diff_hours += multiplier[i] * val
        if len(outdate) <= i:
            outdate.append(1 if i in [1, 2] else 0)

    for i, elem in enumerate(outdate):
        outdate[i] += diff_hours // multiplier[i]
        diff_hours = diff_hours % multiplier[i]

    if len(outdate) > 3:
        # Ensure hours are between 0 and 24
        while outdate[3] >= 24:
            outdate[3] -= 24
            outdate[2] += 1

    if len(outdate) > 2:
        # Ensure days are between 1 and 30
        if outdate[2] < 1:
            outdate[2] += 30
            outdate[1] -= 1
        while outdate[2] > 30:
            outdate[2] -= 30
            outdate[1] += 1

    # Ensure months are between 1 and 12
    if outdate[1] < 1:
        outdate[1] += 12
        outdate[0] -= 1
    while outdate[1] > 12:
        outdate[1] -= 12
        outdate[0] += 1
        
    return [int(x) for x in outdate]


def get_frequency(delta, rtn_delta=False):
    '''
    Extract the frequency and base period from a delta string in
    the form '\d+\w+'.

    Optional argument:
       rtn_delta = True - return a delta in the form of a list
                 = False - return the frequency and base period
    '''
    # all_targets dictionary: key=base period, val=date list index
    all_targets = {'h': 3, 'd': 2, 'm': 1, 's': 1, 'y': 0, 'a': 0, 'x': 0}
    regex = r'(-?\d+)([{}])'.format(''.join(all_targets.keys()))
    try:
        freq, base = re.match(regex, delta.lower()).groups()
        freq = int(freq)
    except AttributeError:
        freq = 1
        base = delta[0].lower()

    try:
        index = [all_targets[t] for t in all_targets if t == base][0]
    except IndexError:
        log_msg('get_frequency - Invalid target provided: ' + delta,
                level='FAIL')
 
    if rtn_delta:
        # Return delta in the form of an integer list
        rval = [0]*5
        if base == 's':
            freq = freq * 3
        elif base == 'x':
            freq = freq * 10
        rval[index] = freq
    else:
        # Return an integer frequency and string base
        rval = [freq, base]
    return rval


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
    globals()['debug_mode'] = debug
    globals()['debug_ok'] = True


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
    if get_debugmode():
        log_msg('Ignoring failed external command. Continuing...',
                level='DEBUG')
        globals()['debug_ok'] = False
    else:
        log_msg('Command Terminated', level='FAIL')
