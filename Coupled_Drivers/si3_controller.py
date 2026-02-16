#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021-2026 Met Office. All rights reserved.
 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    si3_controller.py

DESCRIPTION
'''


import re
import os
import sys
import glob
import common
import error
import dr_env_lib.ocn_cont_def
import dr_env_lib.env_lib

def _check_si3nl_envar(envar_container):
    '''
    Get the si3 namelist file exists
    '''

    #Information will be retrieved from this file during the running of the
    #controller, so check it exists.

    if not os.path.isfile(envar_container['SI3_NL']):
        sys.stderr.write('[FAIL] si3_controller: Can not find the SI3 namelist '
                         'file %s\n' % envar_container['SI3_NL'])
        sys.exit(error.MISSING_CONTROLLER_FILE_ERROR)
    return 0

def _get_si3rst(si3_nl_file):
    '''
    Retrieve the SI3 restart directory from the nemo namelist file
    '''
    si3rst_rcode, si3rst_val = common.exec_subproc([ \
            'grep', 'cn_icerst_outdir', si3_nl_file])
    if si3rst_rcode == 0:
        si3_rst = re.findall('[\"\'](.*?)[\"\']', si3rst_val)[0]
        if si3_rst[-1] == '/':
            si3_rst = si3_rst[:-1]
        return si3_rst
    return None


def _verify_si3_rst(cyclepointstr, nemo_nproc, si3_restart_files):
    '''
    Verify that the SI3 restart files match what we expect from the number
    of NEMO processors.
    '''
    si3_rst_regex = r'%s_restart_ice(_\d+)?\.nc' % cyclepointstr
    current_rst_files = [f for f in si3_restart_files if
                         re.findall(si3_rst_regex, f)]

    if len(current_rst_files) not in (1, nemo_nproc, nemo_nproc+1):
        sys.stderr.write('[FAIL] Unable to find SI3 restart files for'
                         ' this cycle. Must either have one rebuilt file,'
                         ' as many as there are nemo processors (%i) or'
                         ' both rebuilt and processor files.'
                         '[FAIL] Found %i SI3 restart files\n'
                         % (nemo_nproc, len(current_rst_files)))
        sys.exit(error.MISSING_MODEL_FILE_ERROR)


def _load_environment_variables(si3_envar):
    '''
    Load the SI3 environment variables required for the model run
    into the si3_envar container
    '''

    si3_envar = dr_env_lib.env_lib.load_envar_from_definition(
        si3_envar, dr_env_lib.ocn_cont_def.SI3_ENVIRONMENT_VARS_INITIAL)

    return si3_envar

def _setup_si3_controller(common_env,
                          restart_ctl,
                          nemo_nproc,
                          runid,
                          verify_restart,
                          nemo_dump_time):
    '''
    Setup the environment and any files required by the executable
    '''
    # Create the environment variable container
    si3_envar = dr_env_lib.env_lib.LoadEnvar()

    # Load the environment variables required
    si3_envar = _load_environment_variables(si3_envar)
    _ = _check_si3nl_envar(si3_envar)

    # SI3 hasn't been set up to use CONTINUE_FROM_FAIL yet
    # Raise an error if it's set to prevent unexpected behaviour in future
    if common_env['CONTINUE_FROM_FAIL'] == 'true':
        sys.stderr.write('[FAIL] si3_controller is not coded to work with'
                         'CONTINUE_FROM_FAIL=true')
        sys.exit(error.INVALID_EVAR_ERROR)

    restart_direcs = []
    si3_rst = _get_si3rst(si3_envar['SI3_NL'])
    if si3_rst:
        restart_direcs.append(si3_rst)

    ###########################################################
    # If it is a continuation run get the restart info from
    # wherever it was written by the previous task.
    ###########################################################

    # Identify any relevant SI3 restart files in the suite data directory.
    # These should conform to the format:
    # <some arbitrary name>_yyyymmdd_restart_ice<PE rank>.nc" or
    # <some arbitrary name>_yyyymmdd_restart_ice.nc" in the case
    # of the restart file having been rebuilt.
    si3_restart_files = [f for f in os.listdir(si3_rst) if
                         re.findall(r'.+_\d{8}_restart_ice', f)]
    si3_restart_files.sort()

    # Default position is that we're starting from a restart file and
    # that the value of restart_ctl is simply whatever is provided
    # by the NEMO driver, without modification.

    if si3_restart_files:
        # Set up full path to restart files
        latest_si3_dump = os.path.join(si3_rst, si3_restart_files[-1])

    else:
        # If we didn't find any restart files in the suite data directory,
        # check the SI3_START env var.
        if common_env['CONTINUE'] == 'false':
            latest_si3_dump = si3_envar['SI3_START']
        else:
            # We don't have a restart file, which implies we must be
            # starting from climatology.
            latest_si3_dump = 'unset'

    # If we have a link to restart_ice.nc left over from a previous run,
    # remove it for both NRUNs and CRUNs
    common.remove_file('restart_ice.nc')

    # Is this a CRUN or an NRUN?
    if common_env['CONTINUE'] == 'false':

        # This is definitely a new run
        sys.stdout.write('[INFO] si3_controller: New SI3 run\n\n')

        if os.path.isfile(latest_si3_dump):
            sys.stdout.write('[INFO] si3_controller: Removing old SI3 '
                             'restart data\n\n')
            # For NRUNS, get rid of any existing restart files from
            # previous runs.
            for file_path in glob.glob(si3_rst+'/*restart_ice*'):
                # os.path.isfile will return true for symbolic links as well
                # as physical files.
                common.remove_file(file_path)

        # If we do have a SI3 start dump.
        if si3_envar['SI3_START'] != '':
            if os.path.isfile(si3_envar['SI3_START']):
                os.symlink(si3_envar['SI3_START'], 'restart_ice.nc')
            elif os.path.isfile('%s_0000.nc' %
                                si3_envar['SI3_START']):
                for fname in glob.glob('%s_????.nc' %
                                       si3_envar['SI3_START']):
                    proc_number = fname.split('.')[-2][-4:]
                    common.remove_file('restart_ice_%s.nc' % proc_number)
                    os.symlink(fname, 'restart_ice_%s.nc' % proc_number)
            elif os.path.isfile('%s_0000.nc' %
                                si3_envar['SI3_START'][:-3]):
                for fname in glob.glob('%s_????.nc' %
                                       si3_envar['SI3_START'][:-3]):
                    proc_number = fname.split('.')[-2][-4:]

                    # We need to make sure there isn't already
                    # a restart file link set up, and if there is, get
                    # rid of it because symlink wont work otherwise!
                    common.remove_file('restart_ice_%s.nc' % proc_number)

                    os.symlink(fname, 'restart_ice_%s.nc' % proc_number)
            else:
                sys.stderr.write('[FAIL] file %s not found\n' %
                                 si3_envar['SI3_START'])
                sys.exit(error.MISSING_MODEL_FILE_ERROR)
        else:
            # If there's no SI3 restart we must be starting from climatology.
            sys.stdout.write('[INFO] si3_controller: SI3 is starting from'
                             ' climatology.\n\n')


    elif os.path.isfile(latest_si3_dump):
        # We have a valid restart file so we're not starting from climatology
        # This could be a new run or a continutaion run.
        si3_dump_time = re.findall(r'_(\d*)_restart_ice', latest_si3_dump)[0]

        if verify_restart == 'True':
            _verify_si3_rst(nemo_dump_time, nemo_nproc, si3_restart_files)
        if si3_dump_time != nemo_dump_time:
            sys.stderr.write('[FAIL] si3_controller: Mismatch in SI3 restart '
                             'file date %s and NEMO restart file date %s\n'
                             % (si3_dump_time, nemo_dump_time))
            sys.exit(error.MISMATCH_RESTART_DATE_ERROR)


        # This could be a new run (the first NRUN of a cycle) or
        # a CRUN.
        sys.stdout.write('[INFO] si3_controller: Restart data avaliable in '
                         'SI3 restart directory %s. Restarting from previous '
                         'task output\n\n'
                         % si3_rst)

        # For each PE, set up a link to the appropriate sub-domain
        # restart file.
        si3_restart_count = 0

        for i_proc in range(nemo_nproc):
            tag = str(i_proc).zfill(4)
            si3_rst_source = '%s/%so_%s_restart_ice_%s.nc' % \
                (si3_rst, runid, si3_dump_time, tag)
            si3_rst_link = 'restart_ice_%s.nc' % tag
            common.remove_file(si3_rst_link)
            if os.path.isfile(si3_rst_source):
                os.symlink(si3_rst_source, si3_rst_link)
                si3_restart_count += 1

        if si3_restart_count < 1:
            sys.stdout.write('[INFO] No SI3 sub-PE restarts found\n')
            # We found no passive tracer restart sub-domain files let's
            # look for a full domain file.
            si3_rst_source = '%s/%so_%s_restart_ice.nc' % \
                (si3_rst, runid, si3_dump_time)

            if os.path.isfile(si3_rst_source):
                sys.stdout.write('[INFO] Using rebuilt SI3 restart '\
                     'file: %s\n' % si3_rst_source)
                si3_rst_link = 'restart_ice.nc'
                common.remove_file(si3_rst_link)
                os.symlink(si3_rst_source, si3_rst_link)

        # We don't issue an error if we don't find any restart file
        # because it can be legitimate to want to start from
        # climatology although the likelihood of wanting to do that
        # during a CRUN seems pretty slim.

    else:
        sys.stderr.write('[FAIL] si3_controller: No restart data avaliable in '
                         'SI3 restart directory:\n  %s\n' % si3_rst)
        sys.exit(error.MISSING_MODEL_FILE_ERROR)



    return si3_envar

def _set_launcher_command(_):
    '''
    Setup the launcher command for the executable
    '''
    sys.stdout.write('[INFO] si3_controller: SI3 uses the same launch '
                     'command as NEMO\n\n')
    launch_cmd = ''
    return launch_cmd

def _finalize_si3_controller():
    '''
    Finalize the passive SI3 setup
    '''

def run_controller(common_env,
                   restart_ctl,
                   nemo_nproc,
                   runid,
                   verify_restart,
                   nemo_dump_time,
                   mode):
    '''
    Run the passive tracer controller.
    '''
    if mode == 'run_controller':
        exe_envar = _setup_si3_controller(common_env,
                                          restart_ctl,
                                          nemo_nproc,
                                          runid,
                                          verify_restart,
                                          nemo_dump_time)

        launch_cmd = _set_launcher_command(exe_envar)
    elif mode == 'finalize':
        _finalize_si3_controller()
        exe_envar = None
        launch_cmd = None

    return exe_envar, launch_cmd
