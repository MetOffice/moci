#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2022 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************

 Purpose:
    Assess the data on disk to determine whether further data should
    be retrieved from an archive system

 Requirements:
    Iris Python module

 Model Environment:
    DATAM           - Link to the UM DATAM directory (full path).
                      For information only
    OZONE_SHARE     - Full path to the ozone apps shared directory
    OZONE_ANCIL     - Full path and filename of ozone ancillary to be created
    RUNID           - Prefix string to model output
    SOURCE_STREAM   - 2 character stream identifier
    UMTASK          - Name of the UM task

 Cylc Environment:
    CYLC_TASK_CYCLE_POINT
    CYLC_SUITE_INITIAL_CYCLE_POINT
    CYLC_SUITE_NAME

 Optional Environment:
    RETRIEVE_ARCHIVE_SCRIPT - Site specific archive retrival script
    PRIMARY_ARCHIVE         - Archive path for this suite
    SECONDARY_ARCHIVE       - Secondary archive for data before Nrun
    STASHCODES              - STASHcodes to process. Default=253,40453
'''
import sys
import os
import re
import subprocess
import shlex
import iris

print('Using Python version ' + sys.version)
print('Using Iris version ' + iris.__version__)

RVAL_OK = 0
# PT_REGEX to match a Cylc Cyclepoint '<YYYY><MM><DD>T0000Z'
# The resulting match.groups() attribute will contain (year, month, day)
PT_REGEX = re.compile(r'^(\d{4})(\d{2})(\d{2})T0000Z$')


class OzoneEnvironmentError(Exception):
    ''' Exception for missing required environment variables '''


class OzoneSourceNotFoundError(Exception):
    ''' Exception for missing source data files '''


class OzoneMissingDataError(Exception):
    ''' Exception for missing data time points in source files '''


class OzoneArchiveRetrievalError(Exception):
    ''' Exception for problems relating to retrieving data from archive '''

try:
    # Python 3+
    SymlinkExistsError = FileExistsError
except NameError:
    SymlinkExistsError = OSError

if int(iris.__version__.split('.')[0]) < 2:
    # For operations with cube time coordinates -
    iris.FUTURE.cell_datetime_objects = True

class OneYear(object):
    '''
    Object containing imformation regarging one year's worth of data
    '''
    def __init__(self, year, load=True):
        self.year = year
        self._months = [False] * 12
        self._fields = [stash_fmt(sc.strip())
                        for sc in ENV.GET_STASH.split(',')]
        if load:
            self.load_data()

    @property
    def missing_months(self):
        ''' Return a list of months missing from the most recent load '''
        return [i + 1 for i in range(12) if self._months[i] is False]

    @property
    def complete_year(self):
        ''' Return True if 12 monthly data points are present '''
        return len(self.missing_months) == 0

    def check_time_coords(self, cube):
        '''
        Check the data time points available on the cube <type iris.Cube>.
        Compare available months with previously stored list from other cubes.
        '''
        months = [False] * 12
        for time_pt in cube.coord('time').cells():
            if self.year == time_pt.point.year:
                months[time_pt.point.month - 1] = True
            else:
                raise OzoneMissingDataError(
                    '\n[ERROR] Data found on cube for incorrect year'
                )

        print('[INFO] {} time points available for curent STASH item {}'.
              format(months.count(True), cube.name()))
        if months != self._months and any(self._months):
            print('[WARN] {} time points available for previous item(s)'.
                  format(self._months.count(True)))
            raise OzoneMissingDataError(
                '\n[ERROR] Mismatch in data points found on different cubes'
            )
        self._months = months

    def load_data(self):
        '''
        Load cubes for STASHcodes stored in self._fields.
        '''
        sourcedata = os.path.join(ENV.OZONE_SHARE,
                                  '*a.??{}*.pp'.format(self.year))

        constraints = [iris.AttributeConstraint(time=lambda cell:
                                                cell.point.year == self.year)]
        for stashcode in self._fields:
            constraints.append(iris.AttributeConstraint(STASH=stashcode))

        try:
            cubes = iris.load(sourcedata, constraints=constraints)
        except OSError:
            raise OzoneSourceNotFoundError(
                '\n[ERROR] No files found matching "{}"'.format(sourcedata)
            )
        for cube in cubes:
            self.check_time_coords(cube)


class Environment(object):
    '''
    Containter for environment variables, accessible as attributes
    to the container object.
    '''
    def __init__(self):
        self.__dict__ = {}

    def add_var(self, varname, varval=None, required=True, default=None):
        ''' Add variable to Envrionment object '''
        if varval is None:
            varval = os.getenv(varname, default=default)

        if required and varval is None:
            raise OzoneEnvironmentError(
                '\n[ERROR] Required variable {}'.format(varname)
                + ' is not available in the environment'
            )
        self.__dict__[varname] = varval


ENV = Environment()


def setup_environment():
    ''' Define the required environment '''
    ENV.add_var('CYLC_TASK_CYCLE_POINT')
    ENV.add_var('CYLC_SUITE_INITIAL_CYCLE_POINT')
    ENV.add_var('DATAM')
    ENV.add_var('OZONE_SHARE')
    ENV.add_var('RUNID')
    ENV.add_var('SOURCE_STREAM')
    ENV.add_var('GET_STASH', default=os.environ.get('STASHCODES', '253, 30453'))

    ENV.add_var('RETRIEVE_ARCHIVE_SCRIPT', default='')
    ENV.add_var('PRIMARY_ARCHIVE', required=False)
    ENV.add_var('SECONDARY_ARCHIVE', required=False)

    # Required for skipping ozone redistribution
    ENV.add_var('CYLC_SUITE_NAME')
    ENV.add_var('UMTASK')
    ENV.add_var('OZONE_ANCIL')


def task_info():
    ''' Pretty print the data retrieval information '''
    task_cycle = ENV.CYLC_TASK_CYCLE_POINT
    task_year = cyclepoint(task_cycle)[0]
    first_cycle = ENV.CYLC_SUITE_INITIAL_CYCLE_POINT
    first_year, first_month = cyclepoint(first_cycle)[:2]

    simulation_year = task_year - first_year
    if simulation_year > 2:
        y1_on_disk = y2_on_disk = 'Yes'
    elif simulation_year == 0:
        # Ozone must always run on 1st Jan.  No data available on disk
        y1_on_disk = y2_on_disk = 'No'
    elif simulation_year == 1:
        y1_on_disk = 'No'
        y2_on_disk = 'Partial' if first_month > 0 else 'Yes'
    elif simulation_year == 2:
        y1_on_disk = 'Partial' if first_month > 0 else 'Yes'
        y2_on_disk = 'Yes'

    yrs = [task_year - 2, task_year - 1]
    source_file = r'{r}a.{s}[{y1}|{y2}]*.pp'.format(r=ENV.RUNID,
                                                    s=ENV.SOURCE_STREAM,
                                                    y1=yrs[0], y2=yrs[1])
    print('[INFO] ' + '*' * 73)
    print('[INFO]')
    print('[INFO] Troposphere data to be retrieved from files matching "{}"'.
          format(source_file))
    print('[INFO]')
    print('[INFO] Ozone redistribution shared task directory:')
    print('\t\t{}'.format(ENV.OZONE_SHARE))
    print('[INFO]')
    print('[INFO] Initial cycle point: {}'.format(first_cycle))
    print('[INFO] Current cycle point: {}'.format(task_cycle))
    print('[INFO]')
    print('[INFO] Availability on disk expected from model run:')
    print('\t\t{y1}={a1}, {y2}={a2}'.format(y1=yrs[0], y2=yrs[1],
                                            a1=y1_on_disk, a2=y2_on_disk))
    if any(y != 'Yes' for y in [y1_on_disk, y2_on_disk]):
        print('[INFO] Primary archive source:')
        print('\t\t{}'.format(ENV.PRIMARY_ARCHIVE))
        print('[INFO] Secondary archive source:')
        print('\t\t{}'.format(ENV.SECONDARY_ARCHIVE))
    print('[INFO]')
    print('[INFO] ' + '*' * 73)


def cyclepoint(cycle):
    ''' Return an integer list representation of the Cylc cyclepoint '''
    try:
        date = PT_REGEX.match(cycle).groups()
    except AttributeError:
        raise OzoneEnvironmentError(
            '\n[ERROR] Cannot parse the cycle point: ' + cycle
            )
    return [int(x) for x in date]


def stash_fmt(stashcode):
    ''' Return a formatted string in the style "m<MM>s<SS>i<III>" '''
    return 'm01s{}i{}'.format(str(stashcode).zfill(5)[:2],
                              str(stashcode).zfill(5)[2:])


def link_sourcefiles(year, first_cycle):
    '''
    Create soft links in $OZONE_SHARE to source files in the
    model data directory
    '''
    data_on_disk = False
    model_data = os.path.join(ENV.OZONE_SHARE, 'model_data')
    if not os.path.exists(os.readlink(model_data)):
        if first_cycle:
            # model_data link does not yet exist
            return data_on_disk
        raise OzoneSourceNotFoundError(
            '\n[ERROR] Unable to access link to model data ($DATAM)'
        )

    source_regex = r'{}a\.{}{}.*\.pp'.format(ENV.RUNID,
                                             ENV.SOURCE_STREAM,
                                             year)

    for sfile in [f for f in os.listdir(model_data)
                  if re.match(source_regex, f)]:
        new_link = os.path.join(ENV.OZONE_SHARE, sfile)
        try:
            os.symlink(os.path.join(model_data, sfile), new_link)
        except SymlinkExistsError:
            os.unlink(new_link)
            os.symlink(os.path.join(model_data, sfile), new_link)
        data_on_disk = True

    return data_on_disk


def get_archived_data(year_data, archive_path, output_num):
    '''
    Retrieve months missing from year_data <type OneYear>
    from archive_path <type str>  if available.

    output_num <type int> is appended to the output filename.

    Return updated year_data.

    Shell command to site specific retrieval script takes
    the following format:
       <SCRIPT>
       Required Arguments:
         -a <ARCHIVE PATH>
         -y <YEAR>
         -f <FRST MONTH>
         -l <LAST MONTH>
         -s <COMMA SEP. LIST OF STASH CODES>
         -o <OUTPUT FILE PATH>
    '''
    if year_data.complete_year:
        # No data retrieval required
        pass
    elif archive_path:
        script = ENV.RETRIEVE_ARCHIVE_SCRIPT
        if not os.path.isfile(script):
            raise OzoneArchiveRetrievalError(
                '\n[ERROR] Specified archive retrieval script '
                'does not exist: ' + script
            )

        m_first = year_data.missing_months[0]
        m_last = year_data.missing_months[-1]
        print('[INFO] Checking {} archive for {}, months between {} and {}.'.
              format(archive_path, year_data.year, m_first, m_last))

        output = '{}a.{}{}_arch{}.pp'.format(
            ENV.RUNID, ENV.SOURCE_STREAM, year_data.year, output_num
        )
        cmd = '{} -a {} -y {} -f {} -l {} -s {} -o {}'.format(
            script, archive_path,
            year_data.year, m_first, m_last,
            ENV.GET_STASH.replace(' ', ''), output
        )

        if shell_cmd(cmd) == RVAL_OK:
            if os.path.isfile(output):
                year_data.load_data()
                print('[INFO] Missing data found in ' + archive_path)
        else:
            raise OzoneArchiveRetrievalError(
                '\n[ERROR] Failed in archive retrieval script: ' + script
            )

    return year_data


def shell_cmd(cmd):
    '''
    Execute given shell command `cmd` <type str>
    '''
    # Use shlex.split to cope with arguments that contain whitespace
    cmd_array = shlex.split(cmd)
    try:
        output = subprocess.check_output(cmd_array,
                                         stderr=subprocess.STDOUT,
                                         universal_newlines=True,
                                         cwd=os.getcwd())
    except subprocess.CalledProcessError as exc:
        output = exc.output
        rcode = exc.returncode
    except OSError as exc:
        output = exc.strerror
        rcode = exc.errno
    else:
        rcode = 0
    finally:
        print('[SUBPROCESS] ' + str(output))

    return rcode


def skip_redistribution():
    '''
    Shell out to `cylc broadcast` to:
      * Nullify further ozone tasks in the current cycle
      * Redefine the ozone ancillary file to be used by UM tasks in the
        current cycle year to be the initial ozone ancillary file
    '''
    print('\n[WARN] No data is available for ozone redistribution '
          'due to proximity to NRun')

    broadcast = 'cylc broadcast ' + ENV.CYLC_SUITE_NAME

    # Cancel redistribution for this cycle
    cmd = broadcast + ' -n {}_ozone'
    cmd += ' -p ' + ENV.CYLC_TASK_CYCLE_POINT
    cmd += ' -s script="echo [INFO] No redistribution required in the ' \
           + 'first year of simulation"'
    cmd += ' -s post-script=""'

    for task in ['redistribute', 'rose_arch']:
        _ = shell_cmd(cmd.format(task))

    # Change target ozone ancillary for the next 12 months
    thisyear = ENV.CYLC_TASK_CYCLE_POINT[:4]
    startyear = ENV.CYLC_SUITE_INITIAL_CYCLE_POINT[:4]
    cyclepts = []
    for month in range(1, 13):
        for day in [1, 11, 21]:
            cyclepts.append('-p {}{:02}{:02}T0000Z'.
                            format(thisyear, month, day))
    ozone_ancil = ENV.OZONE_ANCIL.replace(thisyear, startyear)
    cmd = '{} -n {} '.format(broadcast, ENV.UMTASK)
    cmd += ' '.join(cyclepts)
    cmd += ' -s [environment]OZONE_ANCIL={}'.format(ozone_ancil)
    print('\n[INFO] UM ozone ancillary for the next 12 months is '
          + ozone_ancil)
    _ = shell_cmd(cmd)


def main():
    ''' Main function '''
    setup_environment()
    task_info()

    current_cycle = cyclepoint(ENV.CYLC_TASK_CYCLE_POINT)
    initial_cycle = cyclepoint(ENV.CYLC_SUITE_INITIAL_CYCLE_POINT)

    acceptable_missing_data = {
        'nrun_year': list(range(1, initial_cycle[1])),
        'before_nrun': list(range(1, 13)),
        'after_nrun': []
        }

    available_months = 0
    for year in [current_cycle[0] - y for y in [1, 2]]:
        if year < initial_cycle[0]:
            this_year = 'before_nrun'
        elif year > initial_cycle[0]:
            this_year = 'after_nrun'
        else:
            this_year = 'nrun_year'
        if link_sourcefiles(year, current_cycle == initial_cycle):
            year_data = OneYear(year)
            missing_since_nrun = ','.join(
                [str(i) for i in year_data.missing_months
                 if i not in acceptable_missing_data[this_year]]
            )
            if missing_since_nrun:
                raise OzoneMissingDataError(
                    '\n[ERROR] Required data since NRun not found on disk: '
                    'Year: {} Months: {}'.format(year, missing_since_nrun)
                )
        else:
            year_data = OneYear(year, load=False)

        if len(year_data.missing_months) > 0:
            for i, archive in enumerate([ENV.PRIMARY_ARCHIVE,
                                         ENV.SECONDARY_ARCHIVE]):
                year_data = get_archived_data(year_data, archive, i + 1)

        available_months += 12 - len(year_data.missing_months)

    if available_months < 12:
        # Minimum of 12 months data required for redistribution
        print('\n[INFO] Start of simulation - no redistribution required')
        skip_redistribution()
    else:
        print('\n[INFO] Proceeding to redistribution with {} months of data'.
              format(available_months))


if __name__ == '__main__':
    main()
