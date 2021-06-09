#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    nemo_driver.py

DESCRIPTION
    Driver for the NEMO 3.6 model, called from link_drivers. Note that this
    does not cater for any earlier versions of NEMO
'''
import re
import os
import time
import datetime
import sys
import glob
import shutil
import inc_days
import common
import error
import dr_env_lib.nemo_def
import dr_env_lib.env_lib
import write_namcouple
try:
    import f90nml
except ImportError:
    pass

# Here, "top" refers to the NEMO TOP passive tracer system. It does not
# imply anything to do with being in overall control or at the head of
# any form of control heirarchy.
import top_controller

import si3_controller

# Define errors for the NEMO driver only
SERIAL_MODE_ERROR = 99

def _check_nemonl(envar_container):
    '''
    As the environment variable NEMO_NL is required by both the setup
    and finalise functions, this will be encapsulated here
    '''
    # Information will be retrieved from this file during the running of the
    # driver, so check it exists
    if not os.path.isfile(envar_container['NEMO_NL']):
        sys.stderr.write('[FAIL] Can not find the nemo namelist file %s\n' %
                         envar_container['NEMO_NL'])
        sys.exit(error.MISSING_DRIVER_FILE_ERROR)
    else:
        return 0

def _get_nemorst(nemo_nl_file):
    '''
    Retrieve the nemo restart directory from the nemo namelist file
    '''
    ocerst_rcode, ocerst_val = common.exec_subproc([ \
            'grep', 'cn_ocerst_outdir', nemo_nl_file])
    if ocerst_rcode == 0:
        nemo_rst = re.findall(r'[\"\'](.*?)[\"\']', ocerst_val)[0]
        if nemo_rst[-1] == '/':
            nemo_rst = nemo_rst[:-1]
        return nemo_rst
    return None

def _get_ln_icebergs(nemo_nl_file):
    '''
    Interrogate the nemo namelist to see if we are running with icebergs,
    Returns boolean, True if icebergs are used, False if not
    '''
    icb_rcode, icb_val = common.exec_subproc([ \
            'grep', 'ln_icebergs', nemo_nl_file])
    if icb_rcode != 0:
        sys.stderr.write('Unable to read ln_icebergs in &namberg namelist'
                         ' in the NEMO namelist file %s\n'
                         % nemo_nl_file)
        sys.exit(error.SUBPROC_ERROR)
    else:
        if 'true' in icb_val.lower():
            return True
        return False


def _verify_nemo_rst(cyclepointstr, nemo_rst, nemo_nl, nemo_nproc):
    '''
    Verify that the full set of nemo restart files match. Currently this
    is limited to the icebergs restart file. We require either a single
    restart file, or a number of restart files equal to the number of
    nemo processors.
    '''
    restart_files = [f for f in os.listdir(nemo_rst) if
                     'restart' in f]
    if _get_ln_icebergs(nemo_nl):
        nemo_icb_regex = r'_icebergs_%s_restart(_\d+)?\.nc' % cyclepointstr
        icb_restart_files = [f for f in restart_files if
                             re.findall(nemo_icb_regex, f)]
        # we can have a single rebuilt file, number of files equal to
        # number of nemo processors, or rebuilt file and processor files.
        if len(icb_restart_files) not in (1, nemo_nproc, nemo_nproc+1):
            sys.stderr.write('[FAIL] Unable to find iceberg restart files for'
                             ' this cycle. Must either have one rebuilt file,'
                             ' as many as there are nemo processors (%i) or'
                             ' both rebuilt and processor files.'
                             '[FAIL] Found %i iceberg restart files\n'
                             % (nemo_nproc, len(icb_restart_files)))
            sys.exit(error.MISSING_MODEL_FILE_ERROR)


def _verify_fix_rst(restartdate, cyclepoint, nemo_rst):
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
        generic_rst_regex = r'(icebergs)?.*restart(_trc)?(_\d+)?\.nc'
        all_restart_files = [f for f in os.listdir(nemo_rst) if
                             re.findall(generic_rst_regex, f)]
        for restart_file in all_restart_files:
            fname_date = re.findall(r'\d{8}', restart_file)[0]
            if fname_date > cycle_date_string:
                common.remove_file(os.path.join(nemo_rst, restart_file))
        restartdate = cycle_date_string
    return restartdate


def _load_environment_variables(nemo_envar):
    '''
    Load the NEMO environment variables required for the model run into the
    nemo_envar container
    '''
    # Load the nemo namelist environment variable
    nemo_envar = dr_env_lib.env_lib.load_envar_from_definition(
        nemo_envar, dr_env_lib.nemo_def.NEMO_ENVIRONMENT_VARS_INITIAL)
    _ = _check_nemonl(nemo_envar)

    return nemo_envar


def _setup_dates(common_env):
    '''
    Setup the dates for the NEMO model run
    '''
    calendar = common_env['CALENDAR']
    if calendar == '360day':
        calendar = '360'
        nleapy = 30
    elif calendar == '365day':
        calendar = '365'
        nleapy = 0
    elif calendar == 'gregorian':
        nleapy = 1
    else:
        sys.stderr.write('[FAIL] Calendar type %s not recognised\n' %
                         calendar)
        sys.exit(error.INVALID_EVAR_ERROR)

    #turn our times into lists of integers
    model_basis = [int(i) for i in common_env['MODELBASIS'].split(',')]
    run_start = [int(i) for i in common_env['TASKSTART'].split(',')]
    run_length = [int(i) for i in common_env['TASKLENGTH'].split(',')]

    run_days = inc_days.inc_days(run_start[0], run_start[1], run_start[2],
                                 run_length[0], run_length[1], run_length[2],
                                 calendar)
    return nleapy, model_basis, run_start, run_length, run_days



def _setup_executable(common_env):
    '''
    Setup the environment and any files required by the executable
    '''
    # Create the environment variable container
    nemo_envar = dr_env_lib.env_lib.LoadEnvar()
    # Load the environment variables required
    nemo_envar = _load_environment_variables(nemo_envar)


    #Link the ocean executable
    common.remove_file(nemo_envar['OCEAN_LINK'])
    os.symlink(nemo_envar['OCEAN_EXEC'],
               nemo_envar['OCEAN_LINK'])

    # Setup date variables
    nleapy, model_basis, run_start, \
        run_length, run_days = _setup_dates(common_env)

    # NEMO model setup
    if int(nemo_envar['NEMO_VERSION']) < 306:
        sys.stderr.write('[FAIL] The python drivers are only valid for nemo'
                         ' versions greater than 3.6')
        sys.exit(error.INVALID_COMPONENT_VER_ERROR)

    # Read restart from nemo namelist
    restart_direcs = []
    nemo_rst = _get_nemorst(nemo_envar['NEMO_NL'])
    if nemo_rst:
        restart_direcs.append(nemo_rst)
    icerst_rcode, icerst_val = common.exec_subproc([ \
            'grep', 'cn_icerst_dir', nemo_envar['NEMO_NL']])
    if icerst_rcode == 0:
        ice_rst = re.findall(r'[\"\'](.*?)[\"\']', icerst_val)[0]
        if ice_rst[-1] == '/':
            ice_rst = ice_rst[:-1]
        restart_direcs.append(ice_rst)

    for direc in restart_direcs:
        # Strip white space
        direc = direc.strip()

        # Check for trailing slashes in directory names and strip them
        # out if they're present.
        if direc.endswith('/'):
            direc = direc.rstrip('/')

        if os.path.isdir(direc) and (direc not in ('./', '.')) and \
                common_env['CONTINUE'] == 'false':
            sys.stdout.write('[INFO] directory is %s\n' % direc)
            sys.stdout.write('[INFO] This is a New Run. Renaming old NEMO'
                             ' history directory\n')
            os.rename(direc, '%s.%s' % (direc, time.strftime("%Y%m%d%H%M")))
            os.makedirs(direc)
        elif not os.path.isdir(direc):
            sys.stdout.write('[INFO] Creating NEMO restart directory:\n  %s' %
                             direc)
            os.makedirs(direc)

    # Compile a list of the NEMO restart files, if any exist.
    # We look for files conforming to the naming convention:
    # <arbitrary suite name>_yyyymmdd_restart_<PE rank>.nc where
    # <arbitrary suite name> may itself contain underscores, hence we
    # do not parse details based on counting the number of underscores.
    nemo_restart_files = [f for f in os.listdir(nemo_rst) if
                          re.findall(r'.+_\d{8}_restart(_\d+)?\.nc', f)]
    nemo_restart_files.sort()
    if nemo_restart_files:
        latest_nemo_dump = nemo_rst + '/' + nemo_restart_files[-1]
    else:
        latest_nemo_dump = 'unset'

    nemo_init_dir = '.'

    # We need to ensure any lingering NEMO or iceberg retarts from
    # previous runs are removed to ensure they're not accidentally
    # picked up if we're starting from climatology on this occasion.
    common.remove_file('restart.nc')
    common.remove_file('restart_icebergs.nc')

    if common_env['CONTINUE'] == 'false':
        # This is a new run
        sys.stdout.write('[INFO] New nemo run\n')
        if os.path.isfile(latest_nemo_dump):
            #os.path.isfile will return true for symbolic links aswell
            sys.stdout.write('[INFO] Removing old NEMO restart data\n')
            for file_path in glob.glob(nemo_rst+'/*restart*'):
                common.remove_file(file_path)
            for file_path in glob.glob(ice_rst+'/*restart*'):
                common.remove_file(file_path)
            for file_path in glob.glob(nemo_rst+'/*trajectory*'):
                common.remove_file(file_path)
        # source our history namelist file from the current directory in case
        # of first cycle
        history_nemo_nl = os.path.join(nemo_init_dir, nemo_envar['NEMO_NL'])
    elif os.path.isfile(latest_nemo_dump):
        sys.stdout.write('[INFO] Restart data available in NEMO restart '
                         'directory %s. Restarting from previous task output\n'
                         % nemo_rst)
        sys.stdout.write('[INFO] Sourcing namelist file from the work '
                         'directory of the previous cycle\n')
        # find the previous work directory if there is one
        if common_env['CONTINUE_FROM_FAIL'] == 'false':
            if common_env['CNWP_SUB_CYCLING'] == 'True':
                prev_workdir = common.find_previous_workdir( \
                    common_env['CYLC_TASK_CYCLE_POINT'],
                    common_env['CYLC_TASK_WORK_DIR'],
                    common_env['CYLC_TASK_NAME'],
                    common_env['CYLC_TASK_PARAM_run'])
            else:
                prev_workdir = common.find_previous_workdir( \
                    common_env['CYLC_TASK_CYCLE_POINT'],
                    common_env['CYLC_TASK_WORK_DIR'],
                    common_env['CYLC_TASK_NAME'])
            history_nemo_nl = os.path.join(prev_workdir, nemo_envar['NEMO_NL'])
        else:
            history_nemo_nl = nemo_envar['NEMO_NL']
        nemo_init_dir = nemo_rst
    else:
        sys.stderr.write('[FAIL] No restart data available in NEMO restart '
                         'directory:\n  %s\n' % nemo_rst)
        sys.exit(error.MISSING_MODEL_FILE_ERROR)

    #any variables containing things that can be globbed will start with gl_
    gl_first_step_match = 'nn_it000='
    gl_last_step_match = 'nn_itend='
    gl_step_int_match = 'rn_rdt='
    gl_nemo_restart_date_match = 'ln_rstdate'

    # Read values from the nemo namelist file used by the previous cycle
    # (if appropriate), or the configuration namelist if this is the initial
    # cycle.

    # First timestep of the previous cycle
    _, first_step_val = common.exec_subproc(['grep', gl_first_step_match,
                                             history_nemo_nl])

    nemo_first_step = int(re.findall(r'.+=(.+),', first_step_val)[0])

    # Last timestep of the previous cycle
    _, last_step_val = common.exec_subproc(['grep', gl_last_step_match,
                                            history_nemo_nl])
    nemo_last_step = re.findall(r'.+=(.+),', last_step_val)[0]

    # The string in the nemo time step field might have any one of
    # a number of variants. e.g. "set_by_rose", "set_by_system",
    # "set_by_um", etc. Hence we just check for the presence of
    # purely numeric characters to see if we start from zero or not.
    if nemo_last_step.isdigit():
        nemo_last_step = int(nemo_last_step)
    else:
        nemo_last_step = 0

    # Determine (as an integer) the number of seconds per model timestep
    _, nemo_step_int_val = common.exec_subproc(['grep', gl_step_int_match,
                                                nemo_envar['NEMO_NL']])
    nemo_step_int = int(re.findall(r'.+=(\d*)', nemo_step_int_val)[0])

    # If the value for nemo_rst_date_value is true then the model uses
    # absolute date convention, otherwise the dump times are relative to the
    # start of the model run and have an integer representation
    _, nemo_rst_date_value = common.exec_subproc([ \
            'grep', gl_nemo_restart_date_match, history_nemo_nl])
    if 'true' in nemo_rst_date_value:
        nemo_rst_date_bool = True
    else:
        nemo_rst_date_bool = False

    # The initial date of the model run (YYYYMMDD)
    nemo_ndate0 = '%04d%02d%02d' % tuple(model_basis[:3])

    nemo_dump_time = "00000000"

    if os.path.isfile(latest_nemo_dump):
        nemo_dump_time = re.findall(r'_(\d*)_restart', latest_nemo_dump)[0]
        # Verify the dump time against cycle time if appropriate, do the
        # automatic fix, and check all other restart files match
        if common_env['DRIVERS_VERIFY_RST'] == 'True':
            nemo_dump_time = _verify_fix_rst( \
                nemo_dump_time,
                common_env['CYLC_TASK_CYCLE_POINT'], nemo_rst)
            _verify_nemo_rst(nemo_dump_time, nemo_rst, nemo_envar['NEMO_NL'],
                             int(nemo_envar['NEMO_NPROC']))
        # link restart files no that the last output one becomes next input one
        common.remove_file('restart.nc')

        common.remove_file('restart_ice_in.nc')

        # Sort out the processor restart files
        if int(nemo_envar['NEMO_NPROC']) == 1:
            sys.stderr.write('[FAIL] NEMO driver does not support the running'
                             ' of NEMO in serial mode\n')
            sys.exit(SERIAL_MODE_ERROR)
        else:

            nemo_restart_count = 0
            ice_restart_count = 0
            iceberg_restart_count = 0

            # Nemo has multiple processors
            for i_proc in range(int(nemo_envar['NEMO_NPROC'])):
                tag = str(i_proc).zfill(4)
                nemo_rst_source = '%s/%so_%s_restart_%s.nc' % \
                    (nemo_init_dir, common_env['RUNID'], \
                         nemo_dump_time, tag)
                nemo_rst_link = 'restart_%s.nc' % tag
                common.remove_file(nemo_rst_link)

                if os.path.isfile(nemo_rst_source):
                    os.symlink(nemo_rst_source, nemo_rst_link)
                    nemo_restart_count += 1

                ice_rst_source = '%s/%so_%s_restart_ice_%s.nc' % \
                    (nemo_init_dir, common_env['RUNID'], \
                         nemo_dump_time, tag)
                if os.path.isfile(ice_rst_source):
                    ice_rst_link = 'restart_ice_in_%s.nc' % tag
                    common.remove_file(ice_rst_link)
                    os.symlink(ice_rst_source, ice_rst_link)
                    ice_restart_count += 1

                iceberg_rst_source = '%s/%so_icebergs_%s_restart_%s.nc' % \
                    (nemo_init_dir, common_env['RUNID'], \
                         nemo_dump_time, tag)
                if os.path.isfile(iceberg_rst_source):
                    iceberg_rst_link = 'restart_icebergs_%s.nc' % tag
                    common.remove_file(iceberg_rst_link)
                    os.symlink(iceberg_rst_source, iceberg_rst_link)
                    iceberg_restart_count += 1
            #endfor

            if nemo_restart_count < 1:
                sys.stdout.write('[INFO] No NEMO sub-PE restarts found\n')
                # We found no nemo restart sub-domain files let's
                # look for a global file.
                nemo_rst_source = '%s/%so_%s_restart.nc' % \
                    (nemo_init_dir, common_env['RUNID'], \
                         nemo_dump_time)
                if os.path.isfile(nemo_rst_source):
                    sys.stdout.write('[INFO] Using rebuilt NEMO restart '\
                         'file: %s\n' % nemo_rst_source)
                    nemo_rst_link = 'restart.nc'
                    common.remove_file(nemo_rst_link)
                    os.symlink(nemo_rst_source, nemo_rst_link)

            if ice_restart_count < 1:
                sys.stdout.write('[INFO] No ice sub-PE restarts found\n')
                # We found no ice restart sub-domain files let's
                # look for a global file.
                ice_rst_source = '%s/%so_%s_restart_ice.nc' % \
                                    (nemo_init_dir, common_env['RUNID'], \
                         nemo_dump_time)
                if os.path.isfile(ice_rst_source):
                    sys.stdout.write('[INFO] Using rebuilt ice restart '\
                        'file: %s\n' % ice_rst_source)
                    ice_rst_link = 'restart_ice_in.nc'
                    common.remove_file(ice_rst_link)
                    os.symlink(ice_rst_source, ice_rst_link)

            if iceberg_restart_count < 1:
                sys.stdout.write('[INFO] No iceberg sub-PE restarts found\n')
                # We found no iceberg restart sub-domain files let's
                # look for a global file.
                iceberg_rst_source = '%s/%so_icebergs_%s_restart.nc' % \
                    (nemo_init_dir, common_env['RUNID'], \
                         nemo_dump_time)
                if os.path.isfile(iceberg_rst_source):
                    sys.stdout.write('[INFO] Using rebuilt iceberg restart'\
                        'file: %s\n' % iceberg_rst_source)
                    iceberg_rst_link = 'restart_icebergs.nc'
                    common.remove_file(iceberg_rst_link)
                    os.symlink(iceberg_rst_source, iceberg_rst_link)

        #endif (nemo_envar(NEMO_NPROC) == 1)
        if nemo_rst_date_bool:
            #Then nemo_dump_time has the form YYYYMMDD
            pass
        else:
            #nemo_dump_time is relative to start of model run and is an
            #integer
            nemo_dump_time = int(nemo_dump_time)
            completed_days = nemo_dump_time * (nemo_step_int // 86400)
            sys.stdout.write('[INFO] Nemo has previously completed %i days\n' %
                             completed_days)
        ln_restart = ".true."
        restart_ctl = 2
        if common_env['CONTINUE_FROM_FAIL'] == 'true':
            # This is only used for coupled NWP where we don't have dates in
            # NEMO restart file names
            nemo_next_step = int(nemo_dump_time)+1
        else:
            nemo_next_step = nemo_last_step + 1
    else:
        # This is an NRUN
        if nemo_envar['NEMO_START'] != '':
            if os.path.isfile(nemo_envar['NEMO_START']):

                os.symlink(nemo_envar['NEMO_START'], 'restart.nc')
                ln_restart = ".true."

            elif os.path.isfile('%s_0000.nc' %
                                nemo_envar['NEMO_START']):
                for fname in glob.glob('%s_????.nc' %
                                       nemo_envar['NEMO_START']):
                    proc_number = fname.split('.')[-2][-4:]

                    # We need to make sure there isn't already
                    # a restart file link set up, and if there is, get
                    # rid of it because symlink wont work otherwise!
                    common.remove_file('restart_%s.nc' % proc_number)

                    os.symlink(fname, 'restart_%s.nc' % proc_number)
                ln_restart = ".true."
            elif os.path.isfile('%s_0000.nc' %
                                nemo_envar['NEMO_START'][:-3]):
                for fname in glob.glob('%s_????.nc' %
                                       nemo_envar['NEMO_START'][:-3]):
                    proc_number = fname.split('.')[-2][-4:]

                    # We need to make sure there isn't already
                    # a restart file link set up, and if there is, get
                    # rid of it because symlink wont work otherwise!
                    common.remove_file('restart_%s.nc' % proc_number)

                    os.symlink(fname, 'restart_%s.nc' % proc_number)
                ln_restart = ".true."
            else:
                sys.stderr.write('[FAIL] file %s not found\n' %
                                 nemo_envar['NEMO_START'])
                sys.exit(error.MISSING_MODEL_FILE_ERROR)
        else:
            #NEMO_START is unset
            sys.stdout.write('[WARN] NEMO_START not set\n'
                             'NEMO will use climatology\n')
            ln_restart = ".false."

        if nemo_envar['NEMO_ICEBERGS_START'] != '':
            if os.path.isfile(nemo_envar['NEMO_ICEBERGS_START']):

                # We need to make sure there isn't already
                # an iceberg restart file link set up, and if there is, get
                # rid of it because symlink wont work otherwise!
                common.remove_file('restart_icebergs.nc')
                os.symlink(nemo_envar['NEMO_ICEBERGS_START'],
                           'restart_icebergs.nc')
            elif os.path.isfile('%s_0000.nc' %
                                nemo_envar['NEMO_ICEBERGS_START']):
                for fname in glob.glob('%s_????.nc' %
                                       nemo_envar['NEMO_ICEBERGS_START']):
                    proc_number = fname.split('.')[-2][-4:]

                    # We need to make sure there isn't already
                    # an iceberg restart file link set up, and if there is, get
                    # rid of it because symlink wont work otherwise!
                    common.remove_file('restart_icebergs_%s.nc' % proc_number)

                    os.symlink(fname, 'restart_icebergs_%s.nc' % proc_number)
            elif os.path.isfile('%s_0000.nc' %
                                nemo_envar['NEMO_ICEBERGS_START'][:-3]):
                for fname in glob.glob('%s_????.nc' %
                                       nemo_envar['NEMO_ICEBERGS_START'][:-3]):
                    proc_number = fname.split('.')[-2][-4:]

                    # We need to make sure there isn't already
                    # an iceberg restart file link set up, and if there is, get
                    # rid of it because symlink wont work otherwise!
                    common.remove_file('restart_icebergs_%s.nc' % proc_number)

                    os.symlink(fname, 'restart_icebergs_%s.nc' % proc_number)
            else:
                sys.stderr.write('[FAIL] file %s not found\n' %
                                 nemo_envar['NEMO_ICEBERGS_START'])
                sys.exit(error.MISSING_MODEL_FILE_ERROR)
        else:
            #NEMO_ICEBERGS_START unset
            sys.stdout.write('[WARN] NEMO_ICEBERGS_START not set or file(s)'
                             ' not found. Icebergs (if switched on) will start'
                             ' from a state of zero icebergs\n')
        restart_ctl = 0
        nemo_next_step = nemo_first_step
        nemo_last_step = nemo_first_step - 1

    if common_env['CONTINUE_FROM_FAIL'] == 'true':
        #Check that the length of run is correct
        #(it won't be if this is the wrong restart file)
        run_start_dt = datetime.datetime(run_start[0], run_start[1],
                                         run_start[2], run_start[3])
        model_basis_dt = datetime.datetime(model_basis[0], model_basis[1],
                                           model_basis[2], model_basis[3])
        nemo_init_step = (run_start_dt-model_basis_dt).total_seconds() \
                           /nemo_step_int
        tot_runlen_sec = run_days * 86400 + run_length[3]*3600 \
                       + run_length[4]*60 + run_length[5]
        nemo_final_step = int((tot_runlen_sec//nemo_step_int) + nemo_init_step)
        # Check that nemo_next_step is the correct number of hours to
        # match LAST_DUMP_HOURS variable
        steps_per_hour = 3600./nemo_step_int
        last_dump_hrs = int(common_env['LAST_DUMP_HOURS'])
        last_dump_step = int(nemo_init_step + last_dump_hrs*steps_per_hour)
        if nemo_next_step-1 != last_dump_step:
            sys.stderr.write('[FAIL] Last NEMO restarts not at correct time')
            sys.exit(error.RESTART_FILE_ERROR)
    else:
        tot_runlen_sec = run_days * 86400 + run_length[3]*3600 \
            + run_length[4]*60 + run_length[5]
        nemo_final_step = (tot_runlen_sec // nemo_step_int) + nemo_last_step


    #Make our call to update the nemo namelist. First generate the list
    #of commands
    if int(nemo_envar['NEMO_VERSION']) >= 400:
        # from NEMO 4.0 onwards we don't have jpnij in the namelist
        update_nl_cmd = '--file %s --runid %so --restart %s --restart_ctl %s' \
            ' --next_step %i --final_step %s --start_date %s --leapyear %i' \
            ' --iproc %s --jproc %s  --cpl_river_count %s --verbose' % \
            (nemo_envar['NEMO_NL'], \
                 common_env['RUNID'], \
                 ln_restart, \
                 restart_ctl, \
                 nemo_next_step, \
                 nemo_final_step, \
                 nemo_ndate0, \
                 nleapy, \
                 nemo_envar['NEMO_IPROC'], \
                 nemo_envar['NEMO_JPROC'], \
                 common_env['CPL_RIVER_COUNT'])
    else:
        update_nl_cmd = '--file %s --runid %so --restart %s --restart_ctl %s' \
                        ' --next_step %i --final_step %s --start_date %s' \
                        ' --leapyear %i --iproc %s --jproc %s --ijproc %s' \
                        ' --cpl_river_count %s --verbose' % \
                        (nemo_envar['NEMO_NL'], \
                         common_env['RUNID'], \
                         ln_restart, \
                         restart_ctl, \
                         nemo_next_step, \
                         nemo_final_step, \
                         nemo_ndate0, \
                         nleapy, \
                         nemo_envar['NEMO_IPROC'], \
                         nemo_envar['NEMO_JPROC'], \
                         nemo_envar['NEMO_NPROC'], \
                         common_env['CPL_RIVER_COUNT'])

    update_nl_cmd = './update_nemo_nl %s' % update_nl_cmd

    # REFACTOR TO USE THE SAFE EXEC SUBPROC
    update_nl_rcode, _ = common.__exec_subproc_true_shell([ \
            update_nl_cmd])
    if update_nl_rcode != 0:
        sys.stderr.write('[FAIL] Error updating nemo namelist\n')
        sys.exit(error.SUBPROC_ERROR)

    # We just check for the presence of T or t (as in TRUE, True or true)
    # in the L_OCN_PASS_TRC value.
    if ('T' in nemo_envar['L_OCN_PASS_TRC']) or \
       ('t' in nemo_envar['L_OCN_PASS_TRC']):

        sys.stdout.write('[INFO] nemo_driver: Passive tracer code is '
                         'active.\n')

        controller_mode = "run_controller"

        top_controller.run_controller(common_env,
                                      restart_ctl,
                                      int(nemo_envar['NEMO_NPROC']),
                                      common_env['RUNID'],
                                      common_env['DRIVERS_VERIFY_RST'],
                                      nemo_dump_time,
                                      controller_mode)
    else:
        sys.stdout.write('[INFO] nemo_driver: '
                         'Passive tracer code not active\n.')

    use_si3 = 'si3' in common_env['models']
    if use_si3:
        sys.stdout.write('[INFO] nemo_driver: SI3 code is active.\n')
        controller_mode = "run_controller"
        si3_controller.run_controller(common_env,
                                      restart_ctl,
                                      int(nemo_envar['NEMO_NPROC']),
                                      common_env['RUNID'],
                                      common_env['DRIVERS_VERIFY_RST'],
                                      nemo_dump_time,
                                      controller_mode)

    return nemo_envar


def _set_launcher_command(launcher, nemo_envar):
    '''
    Setup the launcher command for the executable
    '''
    if nemo_envar['ROSE_LAUNCHER_PREOPTS_NEMO'] == 'unset':
        ss = False
        nemo_envar['ROSE_LAUNCHER_PREOPTS_NEMO'] = \
            common.set_aprun_options(nemo_envar['NEMO_NPROC'], \
                nemo_envar['OCEAN_NODES'], nemo_envar['OMPTHR_OCN'], \
                    nemo_envar['OHYPERTHREADS'], ss) \
                        if launcher == 'aprun' else ''

    launch_cmd = '%s ./%s' % \
        (nemo_envar['ROSE_LAUNCHER_PREOPTS_NEMO'], \
             nemo_envar['OCEAN_LINK'])

    # Put in quotes to allow this environment variable to be exported as it
    # contains (or can contain) spaces
    nemo_envar['ROSE_LAUNCHER_PREOPTS_NEMO'] = "'%s'" % \
        nemo_envar['ROSE_LAUNCHER_PREOPTS_NEMO']
    return launch_cmd

def get_ocean_resol(nemo_nl_file, run_info):
    '''
    Determine the ocean resolution.
    This function is only used when creating the namcouple at run time.
    '''

    # Read in the resolution of ocean (existent of namelist_cfg has
    # already been checked)
    ocean_nml = f90nml.read(nemo_nl_file)

    # Check the required entries exist
    if 'namcfg' not in ocean_nml:
        sys.stderr.write('[FAIL] namcfg not found in namelist_cfg\n')
        sys.exit(error.MISSING_OCN_RESOL_NML)
    if 'jpiglo' not in ocean_nml['namcfg'] or \
       'jpjglo' not in ocean_nml['namcfg'] or \
       'cp_cfg' not in ocean_nml['namcfg'] or \
       'jp_cfg' not in ocean_nml['namcfg']:
        sys.stderr.write('[FAIL] cp_cfg, jp_cfg, jpiglo or jpjglo are '
                         'missing from namelist namcf in namelist_cfg\n')
        sys.exit(error.MISSING_OCN_RESOL)

    # Check it is on orca grid
    if ocean_nml['namcfg']['cp_cfg'] != 'orca':
        sys.stderr.write('[FAIL] we can currently only handle the '
                         'ORCA grid\n')
        sys.exit(error.NOT_ORCA_GRID)

    # Check this is a grid we recognise
    if ocean_nml['namcfg']['jp_cfg'] == 25:
        run_info['OCN_grid'] = 'orca025'
    else:
        run_info['OCN_grid'] = 'orca' + str(ocean_nml['namcfg']['jp_cfg'])

    # Store the ocean resolution
    run_info['OCN_resol'] = [ocean_nml['namcfg']['jpiglo'],
                             ocean_nml['namcfg']['jpjglo']]

    return run_info

def _sent_coupling_fields(nemo_envar, run_info):
    '''
    Write the coupling fields sent from NEMO into model_snd_list.
    This function is only used when creating the namcouple at run time.
    '''
    # Check that file specifying the coupling fields sent from
    # NEMO is present
    if not os.path.exists('OASIS_OCN_SEND'):
        sys.stderr.write('[FAIL] OASIS_OCN_SEND is missing.\n')
        sys.exit(error.MISSING_OASIS_OCN_SEND)

    # Add toyatm to our list of executables
    if not 'exec_list' in run_info:
        run_info['exec_list'] = []
    run_info['exec_list'].append('toyoce')

    # Determine the ocean resolution
    run_info = get_ocean_resol(nemo_envar['NEMO_NL'], run_info)

    # If using the default coupling option, we'll need to read the
    # NEMO namelist later
    run_info['nemo_nl'] = nemo_envar['NEMO_NL']

    # Read the namelist
    oasis_nml = f90nml.read('OASIS_OCN_SEND')

    # Check we have the expected information
    if 'oasis_ocn_send_nml' not in oasis_nml:
        sys.stderr.write('[FAIL] namelist oasis_ocn_send_nml is '
                         'missing from OASIS_OCN_SEND.\n')
        sys.exit(error.MISSING_OASIS_OCN_SEND_NML)
    if 'oasis_ocn_send' not in oasis_nml['oasis_ocn_send_nml']:
        sys.stderr.write('[FAIL] entry oasis_ocn_send is missing '
                         'from namelist oasis_ocn_send_nml in '
                         'OASIS_OCN_SEND.\n')
        sys.exit(error.MISSING_OASIS_OCN_SEND)

    # Create a list of fields sent from OCN
    model_snd_list = \
        write_namcouple.add_to_cpl_list( \
        'OCN', False, 0,
        oasis_nml['oasis_ocn_send_nml']['oasis_ocn_send'])

    return run_info, model_snd_list

def write_ocean_out_to_stdout():
    '''
    Write the contents of ocean.output to stnadard out
    '''
    # append the ocean output and solver stat file to standard out. Use an
    # iterator to read the files, incase they are too large to fit into
    # memory. Try to find both the NEMO 3.6 and NEMO 4.0 solver files for
    # compatiblilty reasons
    nemo_stdout_file = 'ocean.output'
    nemo36_solver_file = 'solver.stat'
    nemo40_solver_file = 'run.stat'
    icebergs_stat_file = 'icebergs.stat'
    for nemo_output_file in (nemo_stdout_file,
                             nemo36_solver_file, nemo40_solver_file,
                             icebergs_stat_file):
        # The output file from NEMO4.0 has some suspect utf8 encoding,
        # this try/except will handle it
        if os.path.isfile(nemo_output_file):
            sys.stdout.write('[INFO] Ocean output from file %s\n' %
                             nemo_output_file)
            with open(nemo_output_file, 'r', encoding='utf-8') as n_out:
                for line in n_out:
                    try:
                        sys.stdout.write(line)
                    except UnicodeEncodeError:
                        pass
        else:
            sys.stdout.write('[INFO] Nemo output file %s not avaliable\n'
                             % nemo_output_file)

def _finalize_executable(common_env):
    '''
    Finalize the NEMO run, copy the nemo namelist to the restart directory
    for the next cycle, update standard out, and ensure that no errors
    have been found in the NEMO execution.
    '''
    sys.stdout.write('[INFO] finalizing NEMO\n')
    sys.stdout.write('[INFO] running finalize in %s\n' % os.getcwd())

    write_ocean_out_to_stdout()

    _, error_count = common.__exec_subproc_true_shell([ \
            'grep "E R R O R" ocean.output | wc -l'])
    if int(error_count) >= 1:
        sys.stderr.write('[FAIL] An error has been found with the NEMO run.'
                         ' Please investigate the ocean.output file for more'
                         ' details\n')
        sys.exit(error.COMPONENT_MODEL_ERROR)

    # move the nemo namelist to the restart directory to allow the next cycle
    # to pick it up
    nemo_envar_fin = dr_env_lib.env_lib.LoadEnvar()
    nemo_envar_fin = dr_env_lib.env_lib.load_envar_from_definition(
        nemo_envar_fin, dr_env_lib.nemo_def.NEMO_ENVIRONMENT_VARS_FINAL)
    nemo_rst = _get_nemorst(nemo_envar_fin['NEMO_NL'])
    if os.path.isdir(nemo_rst) and \
            os.path.isfile(nemo_envar_fin['NEMO_NL']):
        shutil.copy(nemo_envar_fin['NEMO_NL'], nemo_rst)

    # The only way to check if TOP is active is by checking the
    # passive tracer env var.

    # Check whether we need to finalize the TOP controller
    if ('T' in nemo_envar_fin['L_OCN_PASS_TRC']) or \
       ('t' in nemo_envar_fin['L_OCN_PASS_TRC']):

        sys.stdout.write('[INFO] nemo_driver: Finalize TOP controller.')

        controller_mode = "finalize"
        top_controller.run_controller([], [], [], [], [], [], controller_mode)

    use_si3 = 'si3' in common_env['models']
    if use_si3:
        sys.stdout.write('[INFO] nemo_driver: Finalise SI3 controller\n')
        controller_mode = "finalize"
        si3_controller.run_controller([], [], [], [], [], [], controller_mode)

def run_driver(common_env, mode, run_info):
    '''
    Run the driver, and return an instance of LoadEnvar and as string
    containing the launcher command for the NEMO model
    '''
    if mode == 'run_driver':
        exe_envar = _setup_executable(common_env)
        launch_cmd = _set_launcher_command(common_env['ROSE_LAUNCHER'], exe_envar)
        if run_info['l_namcouple']:
            model_snd_list = None
        else:
            run_info, model_snd_list = \
                _sent_coupling_fields(exe_envar, run_info)
    elif mode == 'finalize':
        _finalize_executable(common_env)
        exe_envar = None
        launch_cmd = None
        model_snd_list = None
    elif mode == 'failure':
        # subset of operations of the model fails
        write_ocean_out_to_stdout()
        exe_envar = None
        launch_cmd = None
        model_snd_list = None
    return exe_envar, launch_cmd, run_info, model_snd_list
