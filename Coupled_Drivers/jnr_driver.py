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
    jnr_driver.py

DESCRIPTION
    Driver for the Jnr hybrid UM component, called from link_drivers
    This is only used when creating the namcouple at run time.
'''
import os
import sys
import glob
import common
import error
import save_um_state
import um_driver
import write_namcouple
import dr_env_lib.jnr_def
import dr_env_lib.env_lib
try:
    import f90nml
except ImportError:
    pass

# UM control file for Jnr UM
CNTL_NAMELIST_FILE_JNR='ATMOSCNTL_JNR'

def _load_run_environment_variables(jnr_envar):
    '''
    Load the UM environment variables required for the model run into the
    jnr_envar container
    '''
    jnr_envar = dr_env_lib.env_lib.load_envar_from_definition(
        jnr_envar, dr_env_lib.jnr_def.JNR_ENVIRONMENT_VARS_INITIAL)

    jnr_envar.add('STDOUT_FILE_JNR', jnr_envar['ATMOS_STDOUT_FILE_JNR'])

    return jnr_envar


def _setup_executable(common_env):
    '''
    Setup the environment and any files required by the executable
    '''
    # Create the environment variable container
    jnr_envar = dr_env_lib.env_lib.LoadEnvar()
    # Load the environment variables required
    jnr_envar = _load_run_environment_variables(jnr_envar)

    # Save the state of the partial sum files, or restore state depending on
    # what is required
    if common_env['CYLC_CYCLING_MODE'] != 'integer':
        save_um_state.save_state(jnr_envar['RUNID_JNR'], common_env)

    # Create a link to the UM atmos exec in the work directory
    common.remove_file(jnr_envar['ATMOS_LINK_JNR'])
    os.symlink(jnr_envar['ATMOS_EXEC_JNR'],
               jnr_envar['ATMOS_LINK_JNR'])

    if common_env['CONTINUE'] == 'false':
        sys.stdout.write('[INFO] This is an NRUN for Jnr\n')
        common.remove_file(jnr_envar['HISTORY_JNR'])
    else:
        # check if file exists and is readable
        sys.stdout.write('[INFO] This is a CRUN for Jnr\n')
        if not os.access(jnr_envar['HISTORY_JNR'], os.R_OK):
            sys.stderr.write("[FAIL] Can not read Jnr's history file %s\n" %
                             jnr_envar['HISTORY_JNR'])
            sys.exit(error.MISSING_DRIVER_FILE_ERROR)
        if common_env['DRIVERS_VERIFY_RST'] == 'True':

            # In seasonal forecasting, model runs are split into NRUNs and
            # CRUNs within the same cycle. Use the CYLC_TASK_PARAM_run
            # variable to access the previous model step work directory.
            if common_env['SEASONAL'] == 'True':
                um_driver.verify_fix_rst(jnr_envar['HISTORY_JNR'],
                                         common_env['CYLC_TASK_CYCLE_POINT'],
                                         common_env['CYLC_TASK_WORK_DIR'],
                                         common_env['CYLC_TASK_NAME'],
                                         'temp_jnr_hist',
                                         common_env['CALENDAR'],
                                         CNTL_NAMELIST_FILE_JNR,
                                         common_env['CYLC_TASK_PARAM_run'])
            else:
                um_driver.verify_fix_rst(jnr_envar['HISTORY_JNR'],
                                         common_env['CYLC_TASK_CYCLE_POINT'],
                                         common_env['CYLC_TASK_WORK_DIR'],
                                         common_env['CYLC_TASK_NAME'],
                                         'temp_jnr_hist',
                                         common_env['CALENDAR'],
                                         CNTL_NAMELIST_FILE_JNR)

    jnr_envar.add('HISTORY_TEMP_JNR', 'thist_jnr')

    # Calculate total number of processes
    jnr_npes = int(jnr_envar['UM_ATM_NPROCX_JNR']) * \
        int(jnr_envar['UM_ATM_NPROCY_JNR'])
    nproc_jnr = jnr_npes + int(jnr_envar['FLUME_IOS_NPROC_JNR'])

    jnr_envar.add('UM_NPES_JNR', str(jnr_npes))
    jnr_envar.add('NPROC_JNR', str(nproc_jnr))

    # Create the output directory for files coming from Jnr
    try:
        os.makedirs(os.path.dirname(jnr_envar['STDOUT_FILE_JNR']))
        sys.stdout.write("[INFO] created output directory for Jnr\n")
    except OSError:
        # If the stdout file is not within a subdirectory nothing else needs
        # doing, as is the case if the directory already exists
        pass
    # Delete any previous stdout files
    for stdout_file in glob.glob('%s*' % jnr_envar['STDOUT_FILE_JNR']):
        common.remove_file(stdout_file)

    return jnr_envar

def _set_launcher_command(launcher, jnr_envar):
    '''
    Setup the launcher command for the executable
    '''
    if jnr_envar['ROSE_LAUNCHER_PREOPTS_JNR'] == 'unset':
        ss = False
        jnr_envar['ROSE_LAUNCHER_PREOPTS_JNR'] = \
            common.set_aprun_options(jnr_envar['NPROC_JNR'], \
                jnr_envar['JNR_NODES'], jnr_envar['OMPTHR_JNR'], \
                    jnr_envar['HYPERTHREADS'], ss) \
                        if launcher == 'aprun' else ''

    launch_cmd = '%s ./%s' % \
        (jnr_envar['ROSE_LAUNCHER_PREOPTS_JNR'], \
             jnr_envar['ATMOS_LINK_JNR'])

    # Put in quotes to allow this environment variable to be exported as it
    # contains (or can contain) spaces
    jnr_envar['ROSE_LAUNCHER_PREOPTS_JNR'] = "'%s'" % \
        jnr_envar['ROSE_LAUNCHER_PREOPTS_JNR']

    return launch_cmd

def _sent_coupling_fields(run_info):
    '''
    Write the coupling fields sent from JNR into model_snd_list
    '''
    # Check that file specifying the coupling fields sent from
    # UM is present
    if not os.path.exists('OASIS_JNR_SEND'):
        sys.stderr.write('[FAIL] OASIS_JNR_SEND is missing.\n')
        sys.exit(error.MISSING_OASIS_JNR_SEND)

    # Add toyatm to our list of executables
    if 'exec_list' not in run_info:
        run_info['exec_list'] = []
    run_info['exec_list'].append('junior')

    # Determine the atmosphere resolution
    run_info = um_driver.get_atmos_resol('JNR', 'SIZES_JNR', run_info)

    # Determine the number of tile types
    run_info['JNR_veg_tiles'], run_info['JNR_non_veg_tiles'] \
        = um_driver.get_jules_levels('SHARED_JNR')

    # Read the OASIS sending namelist
    oasis_nml = f90nml.read('OASIS_JNR_SEND')

    # Check we have the expected information
    if 'oasis_send_nml' not in oasis_nml:
        sys.stderr.write('[FAIL] namelist oasis_send_nml is '
                         'missing from OASIS_JNR_SEND.\n')
        sys.exit(error.MISSING_OASIS_SEND_NML_JNR)
    if 'oasis_jnr_send' not in oasis_nml['oasis_send_nml']:
        sys.stderr.write('[FAIL] entry oasis_jnr_send is missing '
                         'from namelist oasis_send_nml in '
                         'OASIS_JNR_SEND.\n')
        sys.exit(error.MISSING_OASIS_JNR_SEND)

    # Create a list of fields sent from JNR
    model_snd_list = None
    # Check that we have some fields in here
    if oasis_nml['oasis_send_nml']['oasis_jnr_send']:
        model_snd_list = \
            write_namcouple.add_to_cpl_list( \
            'JNR', False, 0,
            oasis_nml['oasis_send_nml']['oasis_jnr_send'])

    # Add any hybrid coupling fields
    run_info, hybrid_snd_list = um_driver.read_hybrid_coupling(
        'HYBRID_JNR2SNR', run_info, oasis_nml)
    if hybrid_snd_list:
        if model_snd_list:
            model_snd_list.extend(hybrid_snd_list)
        else:
            model_snd_list = hybrid_snd_list

    return run_info, model_snd_list

def _finalize_executable(_):
    '''
    Perform any tasks required after completion of model run
    '''
    jnr_envar_fin = dr_env_lib.env_lib.LoadEnvar()
    jnr_envar_fin = dr_env_lib.env_lib.load_envar_from_definition(
        jnr_envar_fin, dr_env_lib.jnr_def.JNR_ENVIRONMENT_VARS_FINAL)

    pe0_suffix = '0'*(len(str(int(jnr_envar_fin['NPROC_JNR'])-1)))
    jnr_pe0_stdout_file = '%s%s' % (jnr_envar_fin['STDOUT_FILE_JNR'],
                                    pe0_suffix)
    if not os.path.isfile(jnr_pe0_stdout_file):
        sys.stderr.write('Could not find PE0 output file %s\n' %
                         jnr_pe0_stdout_file)
        sys.exit(error.MISSING_DRIVER_FILE_ERROR)
    elif not common.is_non_zero_file(jnr_pe0_stdout_file):
        sys.stderr.write('PE0 file %s exists but has zero size\n' %
                         jnr_pe0_stdout_file)
        sys.exit(error.MISSING_DRIVER_FILE_ERROR)
    else:
        # append the pe0 output to standard out
        sys.stdout.write('%JNR PE0 OUTPUT%\n')
        # use an iterator to avoid loading the pe0 file into memory
        with open(jnr_pe0_stdout_file, 'r') as f_pe0:
            for line in f_pe0:
                sys.stdout.write(line)

    # Remove output from other PEs unless requested otherwise
    if jnr_envar_fin['ATMOS_KEEP_MPP_STDOUT'] == 'false':
        for stdout_file in glob.glob('%s*' %
                                     jnr_envar_fin['STDOUT_FILE_JNR']):
            common.remove_file(stdout_file)

    # Rose-ana expects fixed filenames so we link to .pe0 as otherwise the
    # filename depends on the processor decomposition
    if os.path.isfile(jnr_pe0_stdout_file):
        if jnr_pe0_stdout_file != '%s0' % jnr_envar_fin['STDOUT_FILE_JNR']:
            lnk_src = '%s%s' % \
                (os.path.basename(jnr_envar_fin['STDOUT_FILE_JNR']),
                 pe0_suffix)
            lnk_dst = '%s0' % jnr_envar_fin['STDOUT_FILE_JNR']
            common.remove_file(lnk_dst)
            os.symlink(lnk_src, lnk_dst)

def run_driver(common_env, mode, run_info):
    '''
    Run the driver, and return an instance of LoadEnvar and as string
    containing the launcher command for the UM component
    '''
    if mode == 'run_driver':
        exe_envar = _setup_executable(common_env)
        if exe_envar['OCN_RES_ATM'] and 'OCN_grid' not in run_info:
            # If coupling two atmospheres without an ocean, they will
            # still need to aware of the ocean grid used in their ancils.
            run_info['OCN_grid'] = exe_envar['OCN_RES_ATM']
        launch_cmd = _set_launcher_command(common_env['ROSE_LAUNCHER'],
                                           exe_envar)
        if run_info['l_namcouple']:
            model_snd_list = None
        else:
            run_info, model_snd_list = _sent_coupling_fields(run_info)
    elif mode == 'finalize':
        _finalize_executable(common_env)
        exe_envar = None
        launch_cmd = None
        model_snd_list = None
    return exe_envar, launch_cmd, run_info, model_snd_list
