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
import collections
import importlib
import os
import re
import shutil
import sys

import common
import error
import nemo_lib
import nemo_restart_lib
import nemo_runtime_namcouple
import ocn_lib
import update_nemo_nl

# Define errors for the NEMO driver only
SERIAL_MODE_ERROR = 99

def _verify_fix_rst(restartdate, nemo_rst, model_basis_time, time_step,
                    num_steps, calendar):
    '''
    Verify that the restart file for nemo corresponds to the model
    time reached within a given model run. If they don't match, then
    make sure that nemo restarts from the correct restart date

    :arg: string restartdate        : NEMO dump file date
    :arg: string nemo_rst           : Path to NEMO restart files
    :arg: string model_basis_time   : Model basis time
    :arg: int time_step             : Ocean time-step (in seconds)
    :arg: int num_steps             : Num. of time-steps covered
    :arg: string calendar           : Calendar used in model

    '''
    # Calculate the model restart time based on the start date of the
    # last calculated model step, the time-step and the number of
    # steps. Then convert the date format.
    model_basis_datetime = datetime.datetime.strptime(
        model_basis_time, "%Y%m%d")

    model_restart_date = _calc_current_model_date(
        model_basis_datetime, time_step, num_steps, calendar)

    model_restart_date = model_restart_date.strftime('%Y%m%d')

    if restartdate == model_restart_date:
        sys.stdout.write('[INFO] Validated NEMO restart date\n')
    else:
        # Write the message to both standard out and standard error
        msg = '[WARN] The NEMO restart data does not match the ' \
            ' current model time\n.' \
            '   Current model date is %s\n' \
            '   NEMO restart time is %s\n' \
            '[WARN] Automatically removing NEMO dumps ahead of ' \
            'the current model date, and pick up the dump at ' \
            'this time\n' % (model_restart_date, restartdate)
        sys.stdout.write(msg)
        sys.stderr.write(msg)
        #Remove all nemo restart files that are later than the correct
        #cycle times
        #Make our generic restart regular expression, to cover normal NEMO
        #restart, and potential iceberg, SI3 or passive tracer restart files,
        #for both the rebuilt and non rebuilt cases
        generic_rst_regex = r'(icebergs)?.*restart(_trc)?(_ice)?(_icb)?(_\d+)?\.nc'
        all_restart_files = [f for f in os.listdir(nemo_rst) if
                             re.findall(generic_rst_regex, f)]
        for restart_file in all_restart_files:
            fname_date = re.findall(r'\d{8}', restart_file)[0]
            if fname_date > model_restart_date:
                common.remove_file(os.path.join(nemo_rst, restart_file))
        restartdate = model_restart_date

    return restartdate

def _calc_current_model_date(model_basis_time, time_step, num_steps,
                             calendar):
    '''
    Calculate the current model date using the basis time,
    and the number of time-steps covered in a given model run.

    :arg: datetime model_basis_time : Model basis time
    :arg: int time_step             : Ocean model timestep (in seconds)
    :arg: int num_steps             : Num. timesteps covered in this
                                      model run
    :arg: string calendar           : Calendar used in the model run

    '''
    ref_date_format = 'seconds since %Y-%m-%d %H:%M:%S'

    # modify the calendar names for compatability with cf_units module
    if calendar == "360day":
        calendar = "360_day"
    if calendar == "365day":
        calendar = "365_day"

    # Provide a reference time for the timestep incrementation.
    ref_time = model_basis_time.strftime(ref_date_format)

    model_progress_secs = cf_units.date2num(
        model_basis_time, ref_time, calendar=calendar) + (time_step * num_steps)

    current_model_date = cf_units.num2date(
        model_progress_secs, ref_time, calendar=calendar)

    return current_model_date

def _nemo_driver_assertions(nemo_envar):
    '''
    Assertions prior to the running of the drivers, to ensure that we are
    running in a parallel configuration, and the NEMO version is 3.6 or later
    '''
    assert int(nemo_envar['NEMO_VERSION']) >= 306, \
        '[FAIL] The python drivers are only valid for NEMO versions' \
        ' 3.6 and later.\n'

    assert int(nemo_envar['NEMO_NPROC']) > 1, \
        '[FAIL] Nemo driver does not support the running of NEMO' \
        ' in serial mode\n'


def _run_submodel_custom(common_env, nemo_envar, ln_restart, restart_ctl):
    '''
    If the submodels have unique requirements we run those here
    '''
    if 'top' in common_env['models']:
        # ln_trcdta appears to always be the opposite of ln_restart, so we
        # set it on that basis, though if this is correct it would seem to
        # be redundant which should be addressed in the NEMO base code.
        # These settings are based purely on the logic employed by the
        # forerunner to this code in the MEDUSA-adapted UM10.6 GC3-coupled
        # control script.
        if ln_restart == ".true.":
            ln_trcdta = ".false."
        elif ln_restart == ".false.":
            ln_trcdta = ".true."
        else:
            sys.stderr.write('[FAIL] TOP: invalid ln_restart value:'
                             ' %s\n' % ln_restart)
            sys.exit(error.INVALID_LOCAL_ERROR)
        # Update the TOP namelist
        update_nemo_nl.update_top_nl(nemo_envar, ln_restart, restart_ctl,
                                     ln_trcdta)

    if 'si3' in common_env['models']:
        update_nemo_nl.update_si3_nl(nemo_envar)

def _run_submodel_controllers(nemo_envar, common_env, restart_ctl,
                              nemo_dump_time, controller_mode):
    '''
    Import and run the TOP/SI3 controllers if required
    '''
    submodels = []
    # We check for the presence of lower case t, as in a lowered (TRUE, True,
    # or true)
    if 't' in nemo_envar['L_OCN_PASS_TRC'].lower():
        submodels.append('top')
        sys.stdout.write('[INFO] nemo_driver: Passive tracer code is '
                         'active.\n')
    else:
        sys.stdout.write('[INFO] nemo_driver: '
                         'Passive tracer code not active.\n')
    for submodel in submodels:
        controller_name = '%s_controller' % submodel
        sys.stdout.write('[INFO] Calling %s in %s mode\n' %
                         (controller_name, controller_mode))
        controller_mod = importlib.import_module(controller_name)
        controller_mod.run_controller(common_env,
                                      restart_ctl,
                                      int(nemo_envar['NEMO_NPROC']),
                                      common_env['RUNID'],
                                      common_env['DRIVERS_VERIFY_RST'],
                                      nemo_dump_time,
                                      controller_mode)

def _processor_restart_files_nrun(nemo_envar, common_env, nemo_init_dir):
    '''
    Set up links to processor restart files for NRUN and return ln_restart
    '''
    nemo_warn = 'NEMO_START not set\nNEMO will use climatology\n'
    ln_restart = ocn_lib.setup_nrun(nemo_envar['NEMO_START'],
                                    nemo_envar['RST_LINK_DIR'],
                                    'restart', nemo_init_dir,
                                    nemo_warn)

    # Set up Icebergs NRUN
    icebergs_warn = 'NEMO_ICEBERGS_START not set or file(s)' \
                    ' not found. Icebergs (if switched on) will start' \
                    ' from a state of zero icebergs\n'
    _ = ocn_lib.setup_nrun(nemo_envar['NEMO_ICEBERGS_START'],
                           nemo_envar['RST_LINK_DIR'],
                           'restart_icebergs', nemo_init_dir,
                           icebergs_warn)

    # Set up SI3 NRUN
    if 'si3' in common_env['models']:
        si3_warn = 'New SI3 run\n'
        _ = ocn_lib.setup_nrun(nemo_envar['SI3_START'],
                               nemo_envar['RST_LINK_DIR'],
                               'restart_ice', nemo_init_dir, si3_warn)

    # Set up TOP NRUN
    if 'top' in common_env['models']:
        top_warn = 'New TOP run\n'
        _ = ocn_lib.setup_nrun(nemo_envar['TOP_START'],
                               nemo_envar['RST_LINK_DIR'],
                               'restart_trc', nemo_init_dir, top_warn)
    return ln_restart

def _processor_restart_files_crun(nemo_init_dir, restart_link_dir,
                                  nemo_nproc, nemo_dump_time, runid):
    '''
    Compile a list of relevant restart files for CRUNs
    '''
    Restarts = collections.namedtuple(
        'Restarts', 'model file_label rst_label')
    # Create a list of the various Restarts
    restart_types = [
        Restarts('NEMO', '%so_%s_restart', 'restart'),
        Restarts('SI3', '%so_%s_restart_ice', 'restart_ice'),
        Restarts('Icebergs', '%so_icebergs_%s_restart', 'restart_icebergs'),
        Restarts('TOP', '%so_%s_restart_trc', 'restart_trc')]
    for i_restart in restart_types:
        # Create links for restart files - either rebuilt or processor restarts
        file_label = i_restart.file_label % (runid, nemo_dump_time)
        ocn_lib.setup_restart(nemo_init_dir, restart_link_dir,
                              file_label, i_restart.rst_label, nemo_nproc,
                              i_restart.model)

def _crun_timesteps(nemo_rst_date_bool, nemo_dump_time, nemo_step_int,
                    nemo_last_step, common_env):
    '''Set up the timesteps for a CRUN'''
    if not nemo_rst_date_bool:
        # Nemo dump time is relative to the start of a model run and is an
        # integer
        nemo_dump_time = int(nemo_dump_time)
        completed_days = nemo_dump_time * (nemo_step_int / 86400)
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
    return ln_restart, restart_ctl, nemo_next_step


def _nrun_timesteps(nemo_first_step):
    '''Set up the timesteps for an NRUN'''
    restart_ctl = 0
    nemo_next_step = nemo_first_step
    nemo_last_step = nemo_first_step - 1
    return restart_ctl, nemo_next_step, nemo_last_step


def _verify_restart(common_env, nemo_envar, nemo_dump_time, nemo_rst):
    '''
    Verify the dump time against cycle time if appropriate, do the
    automatic fix, and check all other restart files match
    '''
    if common_env['DRIVERS_VERIFY_RST'] == 'True':
        nemo_dump_time = nemo_restart_lib.verify_fix_rst(
            nemo_dump_time,
            common_env['CYLC_TASK_CYCLE_POINT'], nemo_rst)
    return nemo_dump_time

def _setup_executable(common_env):
    '''
    Set up the environment and any files required by the executable
    '''

    # Load the environment variables required
    nemo_envar, models = nemo_lib.load_environment_variables(
        'setup', common_env['models'])
    common_env['models'] = models

    #Link the ocean executable
    common.remove_file(nemo_envar['OCEAN_LINK'])
    os.symlink(nemo_envar['OCEAN_EXEC'],
               nemo_envar['OCEAN_LINK'])

    # Set up date variables
    nleapy, model_basis, run_start, \
        run_length, run_days = nemo_lib.setup_dates(common_env)

    # Make the required assertions
    _nemo_driver_assertions(nemo_envar)

    # Read restart from current nemo namelists
    nemo_rst, is_icebergs, ice_rst, top_rst = nemo_lib.read_current_cycle_nl(
        common_env, nemo_envar)

    # we dont want any duplicates
    restart_direcs = list(
        collections.OrderedDict.fromkeys(
            [direc for direc in [nemo_rst, ice_rst, top_rst] if direc]))

    nemo_restart_lib.create_restart_direcs(restart_direcs, common_env)

    nemo_restart_files, latest_nemo_dump, nemo_init_dir \
        = nemo_restart_lib.compile_nemo_restart_files(nemo_rst)

    restart_nl_path = nemo_restart_lib.setup_previous_restart_nl(
        common_env, nemo_rst, ice_rst, top_rst, latest_nemo_dump)

    history_nemo_nl = os.path.join(restart_nl_path, nemo_envar['NEMO_NL'])

    nemo_first_step, nemo_last_step, nemo_step_int, nemo_rst_date_bool \
        = nemo_lib.read_history_nl(history_nemo_nl)

    # The initial date of the model run (YYYYMMDD)
    nemo_ndate0 = '%04d%02d%02d' % tuple(model_basis[:3])

    nemo_dump_time = "00000000"

    if os.path.isfile(latest_nemo_dump):
        nemo_dump_time = re.findall(r'_(\d*)_restart', latest_nemo_dump)[0]
        nemo_dump_time = _verify_restart(
            common_env, nemo_envar, nemo_dump_time, nemo_rst)
        # link restart files no that the last output one becomes next input one
        common.remove_file('restart.nc')
        common.remove_file('restart_ice.nc')
        common.remove_file('restart_trc.nc')

        # Sort out the processor restart files
        _processor_restart_files_crun(
            nemo_init_dir, nemo_envar['RST_LINK_DIR'],
            int(nemo_envar['NEMO_NPROC']), nemo_dump_time, common_env['RUNID'])

        ln_restart, restart_ctl, nemo_next_step \
            = _crun_timesteps(nemo_rst_date_bool, nemo_dump_time, nemo_step_int,
                              nemo_last_step, common_env)
    else:
        # This is an NRUN
        # Set up NEMO Nrun and ln_restart
        ln_restart = _processor_restart_files_nrun(nemo_envar, common_env,
                                                   nemo_init_dir)
        restart_ctl, nemo_next_step, nemo_last_step \
            = _nrun_timesteps(nemo_first_step)

    nemo_final_step = nemo_lib.setup_nemo_runlen(
        common_env, run_start, model_basis, nemo_step_int, run_days,
        run_length, nemo_next_step, nemo_last_step)


    # Update the NEMO namelist
    update_nemo_nl.update_nl(common_env, nemo_envar, ln_restart, restart_ctl,
                             nemo_next_step, nemo_final_step, nemo_ndate0,
                             nleapy)

    # Deal with submodels that have unique requirements
    _run_submodel_custom(common_env, nemo_envar, ln_restart, restart_ctl)

    return nemo_envar


def _set_launcher_command(launcher, nemo_envar):
    '''
    Set up the launcher command for the executable
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


def _write_output_file_to_stdout(out_file_path, error_count=0):
    '''
    Write ocean output file to standard out, and append the number of errors
    to error_count (if present), or count and return number of errors in this
    file if not present. The output files have unicode encoding, and
    writing to standard out can't handle this, so we filter out any non ascii
    characters from the line
    '''
    sys.stdout.write('[INFO] Ocean output from file %s\n' % out_file_path)
    with open(out_file_path, 'r', encoding='utf8') as n_out:
        for line in n_out:
            # remove all non ascii characters
            line = ''.join(i for i in line if ord(i) < 128)
            sys.stdout.write(line)
            if 'E R R O R' in line:
                error_count += 1
    return error_count


def _write_ocean_out_to_stdout():
    '''
    Write the contents of ocean.output to standard out, and determine if
    there was an error in this run
    '''
    error_count = 0
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
            error_count = _write_output_file_to_stdout(
                nemo_output_file, error_count)
        else:
            sys.stdout.write('[INFO] Nemo output file %s not avaliable\n'
                             % nemo_output_file)
    return error_count

def _copy_nl_end_of_run(nemo_envar_fin, nemo_rst, top_rst):
    '''
    Copy namelist files at the end of run so next cycle can find them. We assume
    nemo_rst will always exist
    '''
    if os.path.isdir(nemo_rst):
        shutil.copy(nemo_envar_fin['NEMO_NL'], nemo_rst)
    if top_rst:
        if os.path.isdir(top_rst):
            shutil.copy(nemo_envar_fin['TOP_NL'], top_rst)

def _finalize_executable(common_env):
    '''
    Finalize the NEMO run, copy the nemo namelist to the restart directory
    for the next cycle, update standard out, and ensure that no errors
    have been found in the NEMO execution.
    '''
    sys.stdout.write('[INFO] finalizing NEMO\n')
    sys.stdout.write('[INFO] running finalize in %s\n' % os.getcwd())

    error_count = _write_ocean_out_to_stdout()

    if int(error_count) >= 1:
        sys.stderr.write('[FAIL] An error has been found with the NEMO run.'
                         ' Please investigate the ocean.output file for more'
                         ' details\n')
        sys.exit(error.COMPONENT_MODEL_ERROR)

    # move the nemo namelist to the restart directory to allow the next cycle
    # to pick it up
    nemo_envar_fin, models = nemo_lib.load_environment_variables(
        'final', common_env['models'])
    common_env['models'] = models
    nemo_rst, _, _, top_rst = nemo_lib.read_current_cycle_nl(
        common_env, nemo_envar_fin)
    _copy_nl_end_of_run(nemo_envar_fin, nemo_rst, top_rst)

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
                nemo_runtime_namcouple.sent_coupling_fields(
                    exe_envar, run_info)
    elif mode == 'finalize':
        _finalize_executable(common_env)
        exe_envar = None
        launch_cmd = None
        model_snd_list = None
    elif mode == 'failure':
        # subset of operations of the model fails
        _write_ocean_out_to_stdout()
        exe_envar = None
        launch_cmd = None
        model_snd_list = None
    return exe_envar, launch_cmd, run_info, model_snd_list
