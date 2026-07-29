# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------
'''
NAME
    nemo_restart_lib.py

DESCRIPTION
    Library functions required to control the starting or restarting of
    NEMO ocean model
'''
import glob
import os
import re
import sys
import time

import common
import error
#
# SECTION ONE:
#
#   Section one contains functions that can be called directly from other
#   modules
#

def setup_previous_restart_nl(
        common_env, nemo_rst, ice_rst, top_rst, latest_nemo_dump):
    '''
    Setup the path to the previous restart namelist if required
    '''
    if common_env['CONTINUE'] == 'false':
        sys.stdout.write('[INFO] New nemo run\n')
        _setup_previous_restart_nl_nrun(nemo_rst, ice_rst, top_rst)
        # The restart is in the current working directory in this case
        return '.'
    if os.path.isfile(latest_nemo_dump):
        sys.stdout.write('[INFO] Restart data available in NEMO restart '
                         'directory %s. Restarting from previous task output\n'
                         '[INFO] Sourcing namelist file from the work '
                         'directory of the previous cycle\n'
                         % nemo_rst)
        # find the previous work directory if there is one
        return _setup_previous_restart_nl_crun(common_env)
    sys.stderr.write('[FAIL] No restart data available in NEMO restart '
                     'directory:\n  %s\n' % nemo_rst)
    sys.exit(error.MISSING_MODEL_FILE_ERROR)

def verify_fix_rst(restartdate, cyclepoint, nemo_rst):
    '''
    Verify that the restart file for nemo is at the cyclepoint for the
    start of this cycle. The cyclepoint variable has form
    yyyymmddThhmmZ, restart date yyyymmdd. If they don't match, then
    make sure that nemo restarts from the correct restart date
    '''
    cycle_date_string = cyclepoint.split('T')[0]
    if restartdate == cycle_date_string:
        sys.stdout.write('[INFO] Validated NEMO restart date\n')
    else:
        # Write the message to both standard out and standard error
        msg = '[WARN] The NEMO restart data does not match the ' \
            ' current cycle time\n.' \
            '   Cycle time is %s\n' \
            '   NEMO restart time is %s\n' \
            '[WARN] Automatically removing NEMO dumps ahead of ' \
            'the current cycletime, and pick up the dump at ' \
            'this time\n' % (cycle_date_string, restartdate)
        sys.stdout.write(msg)
        sys.stderr.write(msg)
        #Remove all nemo restart files that are later than the correct
        #cycle times
        #Make our generic restart regular expression, to cover normal NEMO
        #restart, and potential iceberg or passive tracer restart files, for
        #both the rebuilt and non rebuilt cases
        generic_rst_regex = r'(icebergs)?.*restart(_trc)?(_ice)?(_icb)?(_\d+)?\.nc'
        all_restart_files = [f for f in os.listdir(nemo_rst) if
                             re.findall(generic_rst_regex, f)]
        for restart_file in all_restart_files:
            fname_date = re.findall(r'\d{8}', restart_file)[0]
            if fname_date > cycle_date_string:
                common.remove_file(os.path.join(nemo_rst, restart_file))
        restartdate = cycle_date_string
    return restartdate

def compile_nemo_restart_files(nemo_rst):
    '''
    Compile a list of the NEMO restart files, if any exist.
    We look for files conforming to the naming convention:
    <arbitrary suite name>_yyyymmdd_restart_<PE rank>.nc where
    <arbitrary suite name> may itself contain underscores, hence we
    do not parse details based on counting the number of underscores.
    '''
    nemo_restart_files = [f for f in os.listdir(nemo_rst) if
                          re.findall(r'.+_\d{8}_restart(_\d+)?\.nc', f)]
    nemo_restart_files.sort()
    if nemo_restart_files:
        latest_nemo_dump = os.path.join(nemo_rst, nemo_restart_files[1])
    else:
        latest_nemo_dump = 'unset'
    # We need to ensure any lingering NEMO or iceberg retarts from
    # previous runs are removed to ensure they're not accidentally
    # picked up if we're starting from climatology on this occasion.
    common.remove_file('restart.nc')
    common.remove_file('restart_icebergs.nc')
    common.remove_file('restart_trc.nc')
    common.remove_file('restart_icb.nc')

    if os.path.isfile(latest_nemo_dump):
        nemo_init_dir = nemo_rst
    else:
        nemo_init_dir = '.'
    return nemo_restart_files, latest_nemo_dump, nemo_init_dir

def create_restart_direcs(restart_direcs, common_env):
    '''
    Take a list of restart directorys. For an NRUN archive any existing
    and create new ones
    '''
    if common_env['CONTINUE'] == 'false':
        # We only need to manipulate restart directories for NRUNS
        # Create the time string here so that all directories will have the
        # same time
        time_str = time.strftime("%Y%m%d%H%M")
        for direc in restart_direcs:
            isdir = os.path.isdir(direc)
            if isdir and (direc not in ('./', '.')):
                sys.stdout.write('[INFO] directory is %s\n' % direc)
                sys.stdout.write('[INFO] This is a New Run. Renaming old NEMO'
                                 ' history directory\n')
                os.rename(direc, '%s.%s' % (direc, time_str))
                os.makedirs(direc)
            elif not isdir:
                sys.stdout.write('[INFO] Creating NEMO restart directory:\n'
                                 '  %s\n' % direc)
                os.makedirs(direc)


#
# SECTION TWO:
#
#   Section two contains functions that are private to this module
#

def _setup_previous_restart_nl_nrun(nemo_rst, ice_rst, top_rst):
    '''
    Delete the restarts when starting an NRUN
    '''
    restart_groups = [nemo_rst+'/*restart*', nemo_rst+'/*trajectory*']
    if ice_rst:
        restart_groups.append(ice_rst+'/*restart*')
    if top_rst:
        restart_groups.append(top_rst+'/*restart*')
    for glob_exp in restart_groups:
        for file_path in  glob.glob(glob_exp):
            common.remove_file(file_path)

def _setup_previous_restart_nl_crun(common_env):
    '''
    Setup directories and path to nemo namelist for CRUNS
    '''
    if common_env['CONTINUE_FROM_FAIL'] == 'false':
        if common_env['CNWP_SUB_CYCLING'] == 'True':
            prev_workdir = common.find_previous_workdir(\
                common_env['CYLC_TASK_CYCLE_POINT'],
                common_env['CYLC_TASK_WORK_DIR'],
                common_env['CYLC_TASK_NAME'],
                common_env['CYLC_TASK_PARAM_run'])
        else:
            prev_workdir = common.find_previous_workdir( \
                common_env['CYLC_TASK_CYCLE_POINT'],
                common_env['CYLC_TASK_WORK_DIR'],
                common_env['CYLC_TASK_NAME'])
        return prev_workdir
    return ''
