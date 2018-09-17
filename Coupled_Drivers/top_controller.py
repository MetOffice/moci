#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    top_controller.py

DESCRIPTION
    Controller for the generic NEMO TOP passive tracer code.

    This is written specifically with MEDUSA in mind but should be applicable,
    with minimal alterations to other biological and chemical models if
    required.

    It is assumed that TOP/MEDUSA, when employed, is simply run from within
    the NEMO executable - i.e. TOP/MEDUSA is not run as a stand-alone entity
    or as a separate component in a coupled system.

    This program is referred to as a "controller" rather than a driver since
    it is run, if required, as a subordinate task from the nemo driver.

    TOP requires the TOP namelist file: namelist_top_cfg to drive the NEMO
    passive tracer code.

    MEDUSA requires the namelist file: namelist_medusa_cfg to drive the
    MEDUSA specific science.

    There are other potentially relevant namelist files e.g.:
    namelist_cfc_cfg
    namelist_idtra_cfg
    namelist_age_cfg
    Although these are commonly used when MEDUSA is run, their presence is
    not exclusively dependent on MEDUSA, hence their management belongs
    elsewhere (if they need to be managed at all) and is not considered here.

    Only the TOP namelist file is updated dynamically with run-specific details.
    Other files mentioned remain static from run to run.

    We detect whether TOP (or MEDUSA) is active during a run by looking for
    the L_OCN_PASS_TRC environment variable. This variable is actually used
    by the NEMO driver as a trigger for whether or not to call this module.

    Note the very fundamental assumption that TOP restarts conform to a
    "restart_trc" naming convention analagous to the Nemo "restart" convention.
    i.e. this is hard coded in all processing, in line with equiavalent
    NEMO processing. While unsatisfactory in terms of flexibility and in terms
    of allowing for the ability to set alternative input and output restart
    names in the namelists, this practise is so ingrained in existing
    procedures that to attempt to change it would require a major rewrite of
    all pre- and post-proccessing code.

    Version compatibility: NEMO vn3.6
'''

#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
import re
import os
import sys
import glob
import shutil
import common
import error

# Define errors for the TOP controller only
SERIAL_MODE_ERROR = 99

def _get_topnl_envar(envar_container):
    '''
    As the environment variable TOP_NL is required by both the setup
    and finalize functions, this will be encapsulated here.
    '''

    envar_container.load_envar('TOP_NL', 'namelist_top_cfg')

    #Information will be retrieved from this file during the running of the
    #controller, so check it exists.

    if not os.path.isfile(envar_container['TOP_NL']):
        sys.stderr.write('[FAIL] top_controller: Can not find the TOP namelist '
                         'file %s\n' % envar_container['TOP_NL'])
        sys.exit(error.MISSING_CONTROLLER_FILE_ERROR)
    else:
        return envar_container

def _get_toprst_dir(top_nl_file):
    '''
    Retrieve the restart directory from the TOP namelist file.
    Currently TOP/MEDUSA uses the same restart directory as the
    main NEMO component so we could in principle get this from
    the NEMO namelist. However, for complete flexibility we
    interrogate the TOP namelist in case this is ever defined as
    something different.
    '''

    toprst_rcode, toprst_val = common.exec_subproc([ \
            'grep', 'cn_trcrst_outdir', top_nl_file])

    if toprst_rcode == 0:
        top_rst_dir = re.findall('[\"\'](.*?)[\"\']', toprst_val)[0]
        if top_rst_dir[-1] == '/':
            top_rst_dir = top_rst_dir[:-1]
        return top_rst_dir

def _verify_top_rst(cyclepointstr, nemo_nproc, top_restart_files):
    '''
    Verify that the top restart files match what we expect from the number
    of NEMO processors.
    '''
    top_rst_regex = r'%s_restart_trc(_\d+)?\.nc' % cyclepointstr
    current_rst_files = [f for f in top_restart_files if
                         re.findall(top_rst_regex, f)]
    if len(current_rst_files) not in (1, nemo_nproc, nemo_nproc+1):
        sys.stderr.write('[FAIL] Unable to find top restart files for'
                         ' this cycle. Must either have one rebuilt file,'
                         ' as many as there are nemo processors (%i) or'
                         ' both rebuilt and processor files.'
                         '[FAIL] Found %i top restart files\n'
                         % (nemo_nproc, len(current_rst_files)))
        sys.exit(error.MISSING_MODEL_FILE_ERROR)
    

def _load_environment_variables(top_envar):
    '''
    Load the TOP environment variables required for the model run
    into the top_envar container
    '''
    top_envar = _get_topnl_envar(top_envar)

    # Load the TOP namelist from an environment variable
    # otherwise use default name.
    _ = top_envar.load_envar('TOP_NL', 'namelist_top_cfg')

    # Load the initial TOP restart file name, if there is
    # one, from an environment variable
    _ = top_envar.load_envar('TOP_START', '')

    # Is this a cycling run? Note: CONTINUE does NOT
    # indicate that this is a continuation run. It indicates
    # that it is a cycle within a set of runs which MAY be a
    # CRUN but may also be the first NRUN in the sequence!
    _ = top_envar.load_envar('CONTINUE', '')

    return top_envar

def _setup_top_controller(restart_ctl,
                          nemo_nproc,
                          runid,
                          verify_restart,
                          nemo_dump_time):
    '''
    Setup the environment and any files required by the executable
    '''
    # Create the environment variable container
    top_envar = common.LoadEnvar()

    # Load the environment variables required
    top_envar = _load_environment_variables(top_envar)

    # Read restart from TOP namelist
    restart_direcs = []

    # Find the TOP restart location
    top_rst = _get_toprst_dir(top_envar['TOP_NL'])

    if top_rst:
        restart_direcs.append(top_rst)

    ###########################################################
    # If it is a continuation run get the restart info from
    # wherever it was written by the previous task.
    ###########################################################

    # Identify any relevant TOP restart files in the suite data directory.
    # These should conform to the format:
    # <some arbitrary name>_yyyymmdd_restart_trc_<PE rank>.nc" or
    # <some arbitrary name>_yyyymmdd_restart_trc.nc" in the case
    # of the restart file having been rebuilt.
    top_restart_files = [f for f in os.listdir(top_rst) if
                         re.findall(r'.+_\d{8}_restart_trc', f)]
    top_restart_files.sort()

    # Default position is that we're starting from a restart file and
    # that the value of restart_ctl is simply whatever is provided
    # by the NEMO driver, without modification.
    ln_restart = ".true."

    if top_restart_files:
        # Set up full path to restart files
        latest_top_dump = os.path.join(top_rst, top_restart_files[-1])
    else:
        # If we didn't find any restart files in the suite data directory,
        # check the TOP_START env var.
        if top_envar['CONTINUE'] == '':
            latest_top_dump = top_envar['TOP_START']
        else:
            # We don't have a restart file, which implies we must be
            # starting from climatology.
            latest_top_dump = 'unset'

    top_init_dir = '.'

    # If we have a link to restart_trc.nc left over from a previous run,
    # remove it for both NRUNs and CRUNs
    common.remove_file('restart_trc.nc')

    # Is this a CRUN or an NRUN?
    if top_envar['CONTINUE'] == '':

        # This is definitely a new run
        sys.stdout.write('[INFO] top_controller: New TOP/MEDUSA run\n\n')

        if os.path.isfile(latest_top_dump):
            sys.stdout.write('[INFO] top_controller: Removing old TOP '
                             'restart data\n\n')
            # For NRUNS, get rid of any existing restart files from
            # previous runs.
            for file_path in glob.glob(top_rst+'/*restart_trc*'):
                # os.path.isfile will return true for symbolic links as well
                # as physical files.
                common.remove_file(file_path)

        # If we do have a passive tracer start dump.
        if top_envar['TOP_START'] != '':
            if os.path.isfile(top_envar['TOP_START']):
                os.symlink(top_envar['TOP_START'], 'restart_trc.nc')
            elif os.path.isfile('%s_0000.nc' %
                                top_envar['TOP_START']):
                for fname in glob.glob('%s_????.nc' %
                                       top_envar['TOP_START']):
                    proc_number = fname.split('.')[-2][-4:]
                    common.remove_file('restart_trc_%s.nc' % proc_number)
                    os.symlink(fname, 'restart_trc_%s.nc' % proc_number)
        else:
            # If there's no TOP restart we must be starting from climatology.
            sys.stdout.write('[INFO] top_controller: TOP is starting from'
                             ' climatology.\n\n')
            # Set the restart flag accordingly
            ln_restart = ".false."

        # Don't check restart time-step consistency.
        # This may or may not be a good thing depending on whether
        # we want to ensure NRUNs start from consistently dated restarts
        # in all components.
        restart_ctl = 0


    elif os.path.isfile(latest_top_dump):
        # We have a valid restart file so we're not starting from climatology
        # This could be a new run or a continutaion run.
        top_dump_time = re.findall(r'_(\d*)_restart_trc', latest_top_dump)[0]

        if verify_restart == 'True':
            _verify_top_rst(nemo_dump_time, nemo_nproc, top_restart_files)
        if top_dump_time != nemo_dump_time:
            sys.stderr.write('[FAIL] top_controller: Mismatch in TOP restart '
                             'file date %s and NEMO restart file date %s\n'
                             % (top_dump_time, nemo_dump_time))
            sys.exit(error.MISMATCH_RESTART_DATE_ERROR)


        # This could be a new run (the first NRUN of a cycle) or
        # a CRUN.
        sys.stdout.write('[INFO] top_controller: Restart data avaliable in '
                         'TOP restart directory %s. Restarting from previous '
                         'task output\n\n'
                         % top_rst)
        top_init_dir = top_rst

        # For each PE, set up a link to the appropriate sub-domain
        # restart file.
        top_restart_count = 0

        for i_proc in range(nemo_nproc):
            tag = str(i_proc).zfill(4)
            top_rst_source = '%s/%so_%s_restart_trc_%s.nc' % \
                (top_init_dir, runid, top_dump_time, tag)
            top_rst_link = 'restart_trc_%s.nc' % tag
            common.remove_file(top_rst_link)
            if os.path.isfile(top_rst_source):
                os.symlink(top_rst_source, top_rst_link)
                top_restart_count += 1

        if top_restart_count < 1:
            sys.stdout.write('[INFO] No TOP sub-PE restarts found\n')
            # We found no passive tracer restart sub-domain files let's
            # look for a full domain file.
            top_rst_source = '%s/%so_%s_restart_trc.nc' % \
                (top_init_dir, runid, top_dump_time)

            if os.path.isfile(top_rst_source):
                sys.stdout.write('[INFO] Using rebuilt TOP restart '\
                     'file: %s\n' % top_rst_source)
                top_rst_link = 'restart_trc.nc'
                common.remove_file(top_rst_link)
                os.symlink(top_rst_source, top_rst_link)

        # We don't issue an error if we don't find any restart file
        # because it can be legitimate to want to start from
        # climatology although the likelihood of wanting to do that
        # during a CRUN seems pretty slim.

    else:
        sys.stderr.write('[FAIL] top_controller: No restart data avaliable in '
                         'TOP restart directory:\n  %s\n' % top_rst)
        sys.exit(error.MISSING_MODEL_FILE_ERROR)

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
        sys.stderr.write('[FAIL] top_controller: invalid ln_restart value: '
                         '%s\n' % ln_restart)
        sys.exit(error.INVALID_LOCAL_ERROR)

    # Update the TOP namelist.
    mod_topnl = common.ModNamelist(top_envar['TOP_NL'])
    mod_topnl.var_val('ln_rsttr', ln_restart)
    mod_topnl.var_val('nn_rsttr', restart_ctl)
    mod_topnl.var_val('ln_trcdta', ln_trcdta)
    mod_topnl.replace()

    # Write details of our namelist settings
    sys.stdout.write('[INFO] top_controller: Start of TOP namelist settings:\n')
    sys.stdout.write('[INFO]     Namelist file: %s \n' % top_envar['TOP_NL'])
    sys.stdout.write('[INFO]     ln_rsttr = %s \n' % ln_restart)
    sys.stdout.write('[INFO]     nn_rsttr = %d \n' % restart_ctl)
    sys.stdout.write('[INFO]     ln_trcdta = %s \n' % ln_trcdta)
    sys.stdout.write('[INFO] top_controller: End of TOP namelist settings\n\n')

    return top_envar

def _set_launcher_command(_):
    '''
    Setup the launcher command for the executable
    '''
    sys.stdout.write('[INFO] top_controller: MEDUSA/TOP uses the same launch '
                     'command as NEMO\n\n')
    launch_cmd = ''
    return launch_cmd

def _finalize_top_controller():
    '''
    Finalize the passive tracer set-up, copy the TOP namelist to the
    restart directory for the next cycle.
    '''
    sys.stdout.write('[INFO] finalizing Ocean Passive Tracers \n')
    sys.stdout.write('[INFO] running finalize in %s \n' % os.getcwd())

    # Move the TOP namelist to the restart directory to allow the next cycle
    # to pick it up
    top_envar_fin = common.LoadEnvar()
    top_envar_fin = _get_topnl_envar(top_envar_fin)
    top_rst = _get_toprst_dir(top_envar_fin['TOP_NL'])
    if os.path.isdir(top_rst) and \
            os.path.isfile(top_envar_fin['TOP_NL']):
        shutil.copy(top_envar_fin['TOP_NL'], top_rst)


def run_controller(restart_ctl,
                   nemo_nproc,
                   runid,
                   verify_restart,
                   nemo_dump_time, mode):
    '''
    Run the passive tracer controller.
    '''
    if mode == 'run_controller':
        exe_envar = _setup_top_controller(restart_ctl,
                                          nemo_nproc,
                                          runid,
                                          verify_restart,
                                          nemo_dump_time)

        launch_cmd = _set_launcher_command(exe_envar)
    elif mode == 'finalize':
        _finalize_top_controller()
        exe_envar = None
        launch_cmd = None

    return exe_envar, launch_cmd
