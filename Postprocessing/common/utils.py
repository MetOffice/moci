#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2018 Met Office. All rights reserved.

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


def load_env(varname, default_value=None, required=False):
    '''
    Load requested environment variable
    Arguments:
        varname       - <type str> Name of environment variable
    Optional Arguments:
        default_value - Default value set if the variable is not found
                        in the environment
        required      - <type bool>  Default=False
                        Exit with system failure if True and no
                        default_value is specified.
    '''
    try:
        envar = os.environ[varname]
    except KeyError:
        envar = default_value
        if required is True and default_value is None:
            msg = 'REQUIRED variable not found in the environment: '
            log_msg(msg + varname, level='FAIL')

    return envar


class CylcCycle(object):
    ''' Object representing the current Cylc cycle point '''
    def __init__(self, cyclepoint=None):
        '''
        Optional argument:
           cyclepoint - ISOformat datestring OR list/tuple of digits
        '''
        if cyclepoint is None:
            # Load optional cycle point override environment
            cyclepoint = load_env('CYCLEPOINT_OVERRIDE')
            if cyclepoint is None:
                cyclepoint = load_env('CYLC_TASK_CYCLE_POINT', required=True)
        self.startcycle = self._cyclepoint(cyclepoint)

        cycleperiod = load_env('CYCLEPERIOD', required=True)
        try:
            # Split period into list of integers if possible
            cycleperiod = [int(x) for x in cycleperiod.split(',')]
        except ValueError:
            # Period provided is intended as a string
            pass
        enddate = add_period_to_date(self.startcycle['intlist'],
                                     cycleperiod)
        self.endcycle = self._cyclepoint(enddate)

    @staticmethod
    def isoformat(cpoint):
        ''' Return cycle point as ISO format datestring '''
        if isinstance(cpoint, (list, tuple)):
            cyclepoint = list(cpoint)
            while len(cyclepoint) < 5:
                cyclepoint.append(0)
            cpoint = '{:0>4}{:0>2}{:0>2}T{:0>2}{:0>2}Z'.format(*cyclepoint)

        if re.match(r'\d{8}T\d{4}Z', cpoint):
            return cpoint
        else:
            msg = 'Unable to determine cycle point in ISO format: '
            log_msg(msg + str(cpoint), level='FAIL')

    def _cyclepoint(self, cpoint):
        '''
        Return a dictionary representing a cycle point in 3 formats:
           iso     = ISO format datestring
           intlist = List of 5 <type int> values: [Y,M,D,hh,mm]
           strlist = List of 5 <type str> values: ['Y','M','D','hh','mm']
        '''
        cycle_repr = {'iso': self.isoformat(cpoint)}
        cycle_repr['strlist'] = list(re.match(
            r'(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})Z', cycle_repr['iso']
            ).groups())
        cycle_repr['intlist'] = [int(x) for x in cycle_repr['strlist']]

        return cycle_repr


def finalcycle():
    '''
    Determine whether this cycle is the final cycle for the running suite.
    Return True/False
    '''
    arch_final = load_env('ARCHIVE_FINAL')
    if arch_final is None:
        finalpoint = load_env('FINALCYCLE_OVERRIDE')
        if finalpoint is None:
            finalpoint = load_env('CYLC_SUITE_FINAL_CYCLE_POINT', required=True)

        # The end point of final cycle will always be beyond the "final point"
        # as defined by either $CYLC_SUITE_FINAL_CYCLE_POINT (calendar cycling
        # suites) or $FINAL_CYCLE_OVERRIDE (for integer cycling suites), since
        # Cylc will not trigger further cycles beyond this point.
        # Set fcycle=True in this instance.
        fcycle = (CylcCycle().endcycle['intlist'] >
                  CylcCycle(cyclepoint=finalpoint).startcycle['intlist'])

    else:
        # Set final cycle according to value of ARCHIVE_FINAL
        fcycle = ('true' in arch_final.lower())

    return fcycle


@timer.run_timer
def exec_subproc(cmd, verbose=True, cwd=os.getcwd()):
    '''
    Execute given shell command.
    'cmd' input should be in the form of either a:
      string        - "cd DIR; command arg1 arg2"
      list of words - ["command", "arg1", "arg2"]
    Optional arguments:
      verbose = False: only reproduce the command std.out upon
                failure of the command
                True: reproduce std.out regardless of outcome
      cwd     = Directory in which to execute the command
    '''
    import subprocess
    import shlex

    cmd_array = [cmd]
    if not isinstance(cmd, list):
        cmd_array = cmd.split(';')
        for i, cmd in enumerate(cmd_array):
            # Use shlex.split to cope with arguments that contain whitespace
            cmd_array[i] = shlex.split(cmd)

    # Initialise rcode, in the event there is no command
    rcode = 99
    output = 'No command provided'

    for cmd in cmd_array:
        try:
            output = subprocess.check_output(cmd,
                                             stderr=subprocess.STDOUT,
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


def ensure_list(value, listnone=False):
    '''
    Return a list for a given input.
      Optional argument: listnone - True=Return [''] or [None]
                                    False=Return []
    '''
    if value or listnone:
        if not isinstance(value, (list, tuple)):
            value = [value]
    else:
        value = []

    return value


def add_path(files, path):
    ''' Add a given path to a file or list of files provided '''
    path = check_directory(path)
    files = ensure_list(files)

    return [os.path.join(path, str(f)) for f in files]


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
def copy_files(cpfiles, destination=None, tmp_ext='.tmp'):
    '''
    Copy file(s).
    Optional arguments:
        destination  - Where provided destination must be a writable
                       directory location
                     - Default behaviour: If not present, file(s) will be
                       copied to the  original directory
                       (os.path.dirname(filename)) with a "tmp_ext" extension
        tmp_ext      - Extension used when copying to the same directory
    '''
    if destination:
        destination = check_directory(destination)

    cpfiles = ensure_list(cpfiles)
    outputfiles = []
    for srcfile in cpfiles:
        if destination:
            output = os.path.join(destination, os.path.basename(srcfile))
        else:
            output = srcfile + tmp_ext

        try:
            src = open(srcfile, 'rb')
        except IOError as exc:
            msg = 'copy_files: Failed to read from source file: ' + srcfile
            log_msg(' - '.join([msg, exc.strerror]), level='ERROR')

        try:
            out = open(output, 'wb')
        except IOError as exc:
            msg = 'copy_files: Failed to write to target file: ' + output
            log_msg(' - '.join([msg, exc.strerror]), level='ERROR')

        shutil.copyfileobj(src, out)
        src.close()
        out.close()
        outputfiles.append(output)

    return outputfiles

@timer.run_timer
def remove_files(delfiles, path=None, ignore_non_exist=False):
    '''
    Delete files.
    Optional arguments:
      path             - if not provided full path is assumed to have been
                         provided in the filename.
      ignore_non_exist - flag to allow a non-existent file to be ignored.
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
            if not ignore_non_exist:
                log_msg('remove_files: File does not exist: ' + fname,
                        level='WARN')


@timer.run_timer
def move_files(mvfiles, destination, originpath=None, fail_on_err=False):
    '''
    Move a single file or list of files to a given directory.
    Optionally a directory of origin may be specified.
    Arguments:
      mvfiles     - filename or list of filenames to be moved
      destination - Path to move the file(s) to
    Optional Arguments:
      originpath  - Current location of the file.
                    Default=os.path.basename(<filename>)
      fail_on_err - Failure to move the file results in app failure.
                    Primary cause of failure is a non-existent target file.
                    Default=False
    '''
    msglevel = 'ERROR' if fail_on_err else 'WARN'
    destination = check_directory(destination)

    if originpath:
        mvfiles = add_path(mvfiles, originpath)
    mvfiles = ensure_list(mvfiles)

    for fname in mvfiles:
        try:
            shutil.move(fname, destination)
        except shutil.Error:
            if os.path.dirname(fname) == destination:
                msg = 'move_files: Attempted to overwrite original file: '
                log_msg(msg + fname, level=msglevel)
            else:
                dest_file = os.path.join(destination, os.path.basename(fname))
                remove_files(dest_file)
                msg = 'move_files: Deleted pre-existing file with same name ' \
                    'prior to move: ' + dest_file
                log_msg(msg, level='WARN')
                shutil.move(fname, destination)
        except IOError:
            # Exception changes in Python 3:
            #   IOError has been merged into OSError
            #   shutil.Error is now a child of IOError, therefore exception
            #   order is important here for compatibility with both 2.7 and 3+
            log_msg('move_files: File does not exist: ' + fname, level=msglevel)


def calendar():
    ''' Return the calendar based on the suite environment '''
    cal = load_env('CYLC_CYCLING_MODE', default_value='360day')
    if cal.lower() == 'integer':
        # Non-Cycling suites should export the CALENDAR environment
        # variable.  DEFAULT VALUE: 360day
        cal = load_env('CALENDAR', default_value='360day')

    return cal


def monthlength(month, year):
    '''Returns length of given month in days - calendar dependent'''
    days_per_month = {
        # Days list runs from Dec -> Nov
        '360day': [30]*12,
        '365day': [31, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30],
        'gregorian': [31, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30],
        }
    year = int(year) + (int(month) // 12)
    month = int(month) % 12

    if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        days_per_month['gregorian'][2] = 29

    return days_per_month[calendar()][month % 12]


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
    outdate = [int(d) for d in indate]
    while len(outdate) < 5:
        val = 1 if len(outdate) in [1, 2] else 0
        outdate.append(val)
        msg = '`rose date` requires length=5 input date array - adding {}: '
        log_msg(msg.format(val) + str(outdate), level='WARN')

    for elem in delta:
        if elem != 0:
            offset = ('-' if elem < 0 else '') + 'P'
            try:
                offset += str(abs(elem)) + ['Y', 'M', 'D'][delta.index(elem)]
            except IndexError:
                if 'T' not in offset:
                    offset += 'T'
                offset += str(abs(elem)) + ['M', 'H'][delta.index(elem)-4]

            dateinput = '{0:0>4}{1:0>2}{2:0>2}T{3:0>2}{4:0>2}'.format(*outdate)
            if re.match(r'^\d{8}T\d{4}$', dateinput):
                cmd = 'rose date {} --calendar {} --offset {} --print-format ' \
                    '%Y,%m,%d,%H,%M'.format(dateinput, cal, offset)

                rcode, output = exec_subproc(cmd, verbose=False)
            else:
                log_msg('add_period_to_date: Invalid date for conversion to '
                        'ISO 8601 date representation: ' + str(outdate),
                        level='ERROR')

            if rcode == 0:
                outdate = [int(x) for x in output.split(',')]
            else:
                if 'SyntaxError: invalid syntax' in output:
                    # Rose not currently compatible with Python3
                    # due to "print" statements
                    log_msg('add_period_to_date: `rose date` command is '
                            'incompatible with Python 3 libraries. '
                            'Use of `rose date` is required for Gregorian '
                            'calendar.\n Please resolve before continuing.',
                            level='ERROR')
                else:
                    log_msg('`rose date` command failed:\n' + output,
                            level='ERROR')
                outdate = None
                break

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

    for i, _ in enumerate(outdate):
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
    r'''
    Extract the frequency and base period from a delta string in
    the form '\d+\w+' or an ISO period e.g. P1Y2M

    Optional argument:
       rtn_delta = True - return a delta in the form of a list
                 = False - return the frequency and base period
    '''
    # all_targets dictionary: key=base period, val=date list index
    all_targets = {'h': 3, 'd': 2, 'm': 1, 's': 1, 'y': 0, 'a': 0, 'x': 0}
    regex = r'(-?\d+)([{}])'.format(''.join(all_targets.keys()))
    rval = [0]*5

    preserve_neg = None
    while delta:
        neg, iso, subdaily, delta = re.match(r'(-?)(p?)(t?)([\w\-]*)',
                                             delta.lower()).groups()
        if subdaily:
            # Redefine "m" to "minutes" (date index 4)
            all_targets['m'] = 4
        if iso:
            # `delta` prefix is [-]P indicating an ISO period.
            # Any negative should be preserved such that it is applied
            # to each frequency in the whole string.  Examples:
            #   -P1Y3M is "-1 year and -1 month"
            #   PT1H30M is "+1 hour and +30 minutes"
            preserve_neg = (neg == '-')
        multiplier = -1 if (preserve_neg or neg) else 1

        try:
            freq, base = re.match(regex, delta).groups()
            freq = int(freq) * multiplier
        except AttributeError:
            freq = 1 * multiplier
            base = delta[0]

        try:
            index = [all_targets[t] for t in all_targets if t == base][0]
        except IndexError:
            concatdelta = ''.join([neg, subdaily, delta])
            log_msg('get_frequency - Invalid target provided: ' + concatdelta,
                    level='FAIL')

        if rtn_delta:
            # Strip freq/base from the start of the delta string for next pass
            delta = delta.lstrip(str(freq))
            delta = delta.lstrip(base)
            if not re.search(r'\d+', delta):
                # Remaining delta string cannot be a period - pass complete
                delta = ''

            # Return delta in the form of an integer list
            if base == 's':
                freq = freq * 3
            elif base == 'x':
                freq = freq * 10
            rval[index] = freq
        else:
            # Return an integer frequency and string base
            rval = [freq, base]
            delta = ''

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
    return globals()['debug_mode']


def get_debugok():
    '''Get method for the debug_ok global variable'''
    return globals()['debug_ok']


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
