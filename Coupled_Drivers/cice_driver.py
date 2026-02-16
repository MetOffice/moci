#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2023-2026 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    cice_driver.py

DESCRIPTION
    Driver for the CICE model, called from link_drivers. Currently this does
    not cater for stand alone CICE and therefore must be run in conjuction
    with the NEMO driver
'''


import os
import sys
import re
import datetime
import time
import time2days
import inc_days
import common
import error
import dr_env_lib.cice_def
import dr_env_lib.env_lib


def __expand_array(short_array):
    '''
    Expand a shortened array containing n*m entries into a full list
    '''
    long_array = ''
    for group in short_array.split(','):
        if '*' not in group:
            long_array += '%s,' % group
        else:
            multiplier = int(group.split('*')[0])
            value = group.split('*')[1]
            long_array += ('%s,' % value) * multiplier
    if long_array[-1] == ',':
        long_array = long_array[:-1]
    return long_array

def _verify_fix_rst(pointerfile, task_start):
    '''
    Verify the restart file for cice is at the time associated with
    the TASKSTART variable. The pointerfile contains a string of the
    path to the restart file. If the dates dont match, fix the date in
    the pointerfile.

    '''
    # Convert the format of the task start time. Seasonal forecasting
    # uses a date format that includes seconds, so account for this in
    # the choice of date formatting.
    try:
        task_start_datetime = datetime.datetime.strptime(
            task_start, "%Y,%m,%d,%H,%M,%S")
    except ValueError:
        task_start_datetime = datetime.datetime.strptime(
            task_start, "%Y,%m,%d,%H,%M")
    task_start = task_start_datetime.strftime('%Y%m%d')

    # deal with the pointer file
    with common.open_text_file(pointerfile, 'r') as pointer_handle:
        restart_path = pointer_handle.readlines()[0].strip()
    if not os.path.isfile(restart_path):
        sys.stderr.write('[INFO] The CICE restart file %s can not be found\n' %
                         restart_path)
        sys.exit(error.MISSING_MODEL_FILE_ERROR)
    #grab the date from the restart file name. It has form yyyy-mm-dd, to
    #match cyclepoint strip the -'s.
    restartmatch = re.search(r'\d{4}-\d{2}-\d{2}',
                             os.path.basename(restart_path))
    restartdate = restartmatch.group(0).replace('-', '')

    if restartdate != task_start:
        # write the message to both standard out and standard error
        msg = '[WARN ]The CICE restart data does not match the ' \
            ' current task start time\n.' \
            '   Task start time is %s\n' \
            '   CICE restart time is %s\n' % (task_start, restartdate)
        sys.stdout.write(msg)
        sys.stderr.write(msg)
        #Turn the task_start variable into form yyyy-mm-dd
        fixed_restart_date = '%s-%s-%s' % (task_start[:4],
                                           task_start[4:6],
                                           task_start[6:8])
        #Swap the date in the restart path
        restart_path_fixed = restart_path.replace(restartmatch.group(0),
                                                  fixed_restart_date)
        new_pointerfile = '%s.tmp' % (pointerfile)
        with common.open_text_file(new_pointerfile, 'w') as new_pointer_handle:
            #The restart path line should be padded to 256 characters
            new_pointer_handle.write("{:<256}".format(restart_path_fixed))
        os.rename(new_pointerfile, pointerfile)
        sys.stdout.write('%s\n' % ('*'*42,))
        sys.stdout.write('[WARN] Automatically fixing CICE restart\n')
        sys.stdout.write('[WARN] Update pointer file %s to replace \n'
                         '[WARN] restart file %s\n'
                         '[WARN] with\n'
                         '[WARN] restart file %s\n' %
                         (pointerfile, restart_path, restart_path_fixed))
        sys.stdout.write('%s\n' % ('*'*42,))
    else:
        sys.stdout.write('[INFO] Validated CICE restart date\n')


def _load_environment_variables(cice_envar):
    '''
    Load the CICE environment variables required for the model run into the
    cice_envar container
    '''
    cice_envar = dr_env_lib.env_lib.load_envar_from_definition(
        cice_envar, dr_env_lib.cice_def.CICE_ENVIRONMENT_VARS_INITIAL)

    cice_envar['ATM_DATA_DIR'] = '%s:%s' % \
        (cice_envar['ATM_DATA_DIR'], cice_envar['CICE_ATMOS_DATA'])
    cice_envar['OCN_DATA_DIR'] = '%s:%s' % \
        (cice_envar['OCN_DATA_DIR'], cice_envar['CICE_OCEAN_DATA'])

    return cice_envar


def _setup_executable(common_env):
    '''
    Setup the environment and any files required by the executable
    '''
    # Create the environment variable container
    cice_envar = dr_env_lib.env_lib.LoadEnvar()
    # Load the ice namelist path. Information will be retrieved from this file
    # druing the running of the driver, so check if it exists.
    _ = cice_envar.load_envar('CICE_IN', 'ice_in')
    cice_nl = cice_envar['CICE_IN']
    if not os.path.isfile(cice_nl):
        sys.stderr.write('[FAIL] Can not find the cice namelist file %s\n' %
                         cice_nl)
        sys.exit(error.MISSING_DRIVER_FILE_ERROR)

    # load the remaining environment variables
    cice_envar = _load_environment_variables(cice_envar)

    calendar = common_env['CALENDAR']
    if calendar == '360day':
        calendar = '360'
        caldays = 360
        cice_leap_years = ".false."
    elif calendar == '365day':
        calendar = '365'
        caldays = 365
        cice_leap_years = ".false."
    else:
        caldays = 365
        cice_leap_years = ".true."

    #turn our times into lists of integers
    model_basis = [int(i) for i in common_env['MODELBASIS'].split(',')]
    run_start = [int(i) for i in common_env['TASKSTART'].split(',')]
    run_length = [int(i) for i in common_env['TASKLENGTH'].split(',')]

    run_days = inc_days.inc_days(run_start[0], run_start[1], run_start[2],
                                 run_length[0], run_length[1], run_length[2],
                                 calendar)
    days_to_start = time2days.time2days(run_start[0], run_start[1],
                                        run_start[2], calendar)

    tot_runlen_sec = run_days * 86400 + run_length[3]*3600 + run_length[4]*60 \
        + run_length[5]

    # These variables default to zero except in operational NWP suite where
    # a run can be restarted part way through after a failure.
    # In this case CONTINUE_FROM_FAIL should also be true
    last_dump_hours = int(common_env['LAST_DUMP_HOURS'])
    last_dump_seconds = last_dump_hours*3600

    #any variables containing things that can be globbed will start with gl_
    gl_step_int_match = '^dt='
    _, step_int_val = common.exec_subproc(['grep', gl_step_int_match,
                                           cice_nl])
    cice_step_int = int(re.findall(r'^dt=(\d*)\.?', step_int_val)[0])
    cice_steps = (tot_runlen_sec - last_dump_seconds) // cice_step_int

    _, cice_histfreq_val = common.exec_subproc(['grep', 'histfreq', cice_nl])
    cice_histfreq_val = re.findall(r'histfreq\s*=\s*(.*)', cice_histfreq_val)[0]
    cice_histfreq = __expand_array(cice_histfreq_val)[1]

    _, cice_histfreq_n_val = common.exec_subproc([ \
            'grep', 'histfreq_n', cice_nl])
    cice_histfreq_n_val = re.findall(r'histfreq_n\s*=\s*(.*)',
                                     cice_histfreq_n_val)[0]
    cice_histfreq_n = __expand_array(cice_histfreq_n_val)
    cice_histfreq_n = int(cice_histfreq_n.split(',')[0])

    _, cice_age_rest_val = common.exec_subproc([ \
            'grep', '^restart_age', cice_nl])
    cice_age_rest = re.findall(r'restart_age\s*=\s*(.*)',
                               cice_age_rest_val)[0]

    # If the variables MODELBASIS, TASKSTART, TASKLENGTH are unset from the
    # environment then read from the shared namelist file
    if False in (common_env['MODELBASIS'],
                 common_env['TASKSTART'],
                 common_env['TASKLENGTH']):
        # at least one variable has to be read from the shared namelist file
        if not os.path.ispath(cice_envar['SHARED_FNAME']):
            sys.stderr.write('[FAIL] Can not find shared namelist file %s\n' %
                             cice_envar['SHARED_FNAME'])
            sys.exit(error.MISSING_DRIVER_FILE_ERROR)
        if not common_env['MODELBASIS']:
            _, modelbasis_val = common.exec_subproc('grep', 'model_basis_time',
                                                    cice_envar['SHARED_FNAME'])
            modelbasis_val = re.findall(r'model_basis_time\s*=\s*(.*)',
                                        modelbasis_val)
            modelbasis = [int(i) for i in __expand_array(modelbasis_val)]
            common_env.add('MODELBASIS', modelbasis)
        if not common_env['TASKSTART']:
            common_env.add('TASKSTART', common_env['MODELBASIS'])
        if not common_env['TASKLENGTH']:
            _, tasklength_val = common.exec_subproc('grep', 'run_target_end',
                                                    cice_envar['SHARED_FNAME'])
            tasklength_val = re.findall(r'run_target_end\s*=\s*(.*)',
                                        tasklength_val)
            tasklength = [int(i) for i in __expand_array(tasklength_val)]
            common_env.add('TASKLENGTH', tasklength)

    if cice_envar['TASK_START_TIME'] == 'unavaliable':
        # This is probably a climate suite
        days_to_year_init = time2days.time2days(model_basis[0], 1, 1, calendar)
        days_to_start = time2days.time2days(run_start[0], run_start[1],
                                            run_start[2], calendar)
        cice_istep0 = (days_to_start - days_to_year_init) * 86400 \
                      // cice_step_int
    else:
        # This is probably a coupled NWP suite
        cmd = ['rose', 'date', str(run_start[0])+'0101T0000Z',
               cice_envar['TASK_START_TIME']]
        _, time_since_year_start = common.exec_subproc(cmd)
        #The next command works because rose date assumes
        # 19700101T0000Z is second 0
        cmd = ['rose', 'date', '--print-format=%s', '19700101T00Z',
               '--offset='+time_since_year_start]
        # Account for restarting from a failure in next line
        # common.exec_subproc returns a tuple containing (return_code, output)
        seconds_since_year_start = int(common.exec_subproc(cmd)[1]) \
                                     + last_dump_seconds
        cice_istep0 = seconds_since_year_start/cice_step_int

    _, cice_rst_val = common.exec_subproc(['grep', 'restart_dir', cice_nl])
    cice_rst = re.findall(r'restart_dir\s*=\s*\'(.*)\',', cice_rst_val)[0]
    if cice_rst[-1] == '/':
        cice_rst = cice_rst[:-1]

    if cice_rst in (os.getcwd(), '.'):
        cice_restart = os.path.join(common_env['DATAM'],
                                    cice_envar['CICE_RESTART'])
    else:
        cice_restart = os.path.join(cice_rst,
                                    cice_envar['CICE_RESTART'])

    _, cice_hist_val = common.exec_subproc(['grep', 'history_dir', cice_nl])
    cice_hist = re.findall(r'history_dir\s*=\s*\'(.*)\',', cice_hist_val)[0]
    _, cice_incond_val = common.exec_subproc(['grep', 'incond_dir', cice_nl])
    cice_incond = re.findall(r'incond_dir\s*=\s*\'(.*)\',', cice_incond_val)[0]

    for direc in (cice_rst, cice_hist, cice_incond):
        # Strip white space
        direc = direc.strip()

        # Check for trailing slashes in directory names and strip them
        # out if they're present.
        if direc.endswith('/'):
            direc = direc.rstrip('/')

        if os.path.isdir(direc) and (direc not in ('./', '.')) and \
                common_env['CONTINUE'] == 'false':
            sys.stdout.write('[INFO] directory is %s\n' % direc)
            sys.stdout.write('[INFO] This is a New Run. Renaming old CICE'
                             ' history directory\n')

            # In seasonal forecasting, we automatically apply
            # short-stepping to re-try the model. Before re-attempting
            # it, remove the associated CICE history directory.
            old_hist_dir = "%s.%s" % (direc, time.strftime("%Y%m%d%H%M"))

            if (common_env['SEASONAL'] == 'True' and
                    int(common_env['CYLC_TASK_TRY_NUMBER']) > 1):
                common.remove_latest_hist_dir(old_hist_dir)

            os.rename(direc, old_hist_dir)
            os.makedirs(direc)
        elif not os.path.isdir(direc):
            sys.stdout.write('[INFO] Creating CICE output directory %s\n' %
                             direc)
            os.makedirs(direc)

    cice_restart_files = [f for f in os.listdir(cice_rst) if
                          re.findall(r'.*i\.restart\..*', f)]
    if not cice_restart_files:
        cice_restart_files = ['nofile']

    if not os.path.isfile(os.path.join(cice_rst, cice_restart_files[-1])):
        if cice_envar['CICE_START']:
            if cice_age_rest == 'true':
                cice_runtype = 'continue'
                ice_ic = 'set in pointer file'
                _, _ = common.exec_subproc([cice_envar['CICE_START'],
                                            '>', cice_restart])
                sys.stdout.write('[INFO] %s > %s' %
                                 (cice_envar['CICE_START'],
                                  cice_restart))
            else:
                cice_runtype = 'initial'
                ice_ic = cice_envar['CICE_START']
            restart = '.true.'
        else:
            ice_ic = 'default'
            cice_runtype = 'initial'
            restart = '.false.'
    else:
        cice_runtype = 'continue'
        restart = '.true.'
        if cice_envar['CICE_START']:
            ice_ic = 'set_in_pointer_file'
        else:
            ice_ic = 'default'

    # if this is a continuation verify the restart file date
    if cice_runtype == 'continue' and \
            common_env['DRIVERS_VERIFY_RST'] == 'True':
        _verify_fix_rst(cice_restart, common_env['TASKSTART'])

    # if this is a continuation from a failed NWP job we check that the last
    # CICE dump matches the time of LAST_DUMP_HOURS
    if common_env['CONTINUE_FROM_FAIL'] == 'true':
        #Read the filename from pointer file
        with open(cice_restart) as fid:
            rst_file = fid.readline()
        rst_file = rst_file.rstrip('\n').strip()
        rst_file = os.path.basename(rst_file)
        ymds = [int(f) for f in rst_file[-19:-3].split('-')]
        since_start = datetime.datetime(ymds[0], ymds[1], ymds[2], \
                                        ymds[3]//3600, (ymds[3]%3600)//60, \
                                        (ymds[3]%3600)%60) \
             - datetime.datetime(run_start[0], run_start[1], run_start[2],
                                 run_start[3], run_start[4])
        if int(since_start.total_seconds()) != last_dump_seconds:
            sys.stderr.write('[FAIL] Last CICE restart not at correct time')
            sys.stderr.write('since_start='+since_start.total_seconds())
            sys.stderr.write('last_dump_seconds='+last_dump_seconds)
            sys.exit(error.RESTART_FILE_ERROR)

    #block of code to modify the main CICE namelist
    mod_cicenl = common.ModNamelist(cice_nl)
    mod_cicenl.var_val('days_per_year', caldays)
    mod_cicenl.var_val('history_file', '%si.%i%s' %
                       (common_env['RUNID'],
                        cice_histfreq_n,
                        cice_histfreq))
    mod_cicenl.var_val('ice_ic', ice_ic)
    mod_cicenl.var_val('incond_file', '%si_ic' % common_env['RUNID'])
    mod_cicenl.var_val('istep0', int(cice_istep0))
    mod_cicenl.var_val('npt', int(cice_steps))
    mod_cicenl.var_val('pointer_file', cice_restart)
    mod_cicenl.var_val('restart', restart)
    mod_cicenl.var_val('restart_file', '%si.restart' %
                       common_env['RUNID'])
    mod_cicenl.var_val('runtype', cice_runtype)
    mod_cicenl.var_val('use_leap_years', cice_leap_years)
    mod_cicenl.var_val('year_init', int(model_basis[0]))
    mod_cicenl.var_val('grid_file', cice_envar['CICE_GRID'])
    mod_cicenl.var_val('kmt_file', cice_envar['CICE_KMT'])
    mod_cicenl.var_val('nprocs', int(cice_envar['CICE_NPROC']))
    mod_cicenl.var_val('atm_data_dir', cice_envar['ATM_DATA_DIR'])
    mod_cicenl.var_val('ocn_data_dir', cice_envar['OCN_DATA_DIR'])
    mod_cicenl.replace()


    return cice_envar


def _set_launcher_command(_):
    '''
    Setup the launcher command for the executable
    '''
    sys.stdout.write('[INFO] CICE uses the same launch command as NEMO\n')
    launch_cmd = ''
    return launch_cmd

def _finalize_executable(_):
    '''
    Write the Ice output to stdout
    '''
    ice_out_file = 'ice_diag.d'
    if os.path.isfile(ice_out_file):
        sys.stdout.write('[INFO] CICE output from file %s\n' % ice_out_file)
        with open(ice_out_file, 'r') as i_out:
            for line in i_out:
                sys.stdout.write(line)
    else:
        sys.stdout.write('[INFO] CICE output file %s not avaliable\n'
                         % ice_out_file)


def run_driver(common_env, mode, run_info):
    '''
    Run the driver, and return an instance of dr_env_lib.env_lib.LoadEnvar and as string
    containing the launcher command for the CICE model
    '''
    if mode == 'run_driver':
        exe_envar = _setup_executable(common_env)
        launch_cmd = _set_launcher_command(exe_envar)
        model_snd_list = None
    elif mode == 'finalize' or 'failure':
        _finalize_executable(common_env)
        exe_envar = None
        launch_cmd = None
        model_snd_list = None
    return exe_envar, launch_cmd, run_info, model_snd_list
