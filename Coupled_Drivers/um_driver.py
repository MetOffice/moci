#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2023 Met Office. All rights reserved.
 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    um_driver.py

DESCRIPTION
    Driver for the UM component, called from link_drivers
'''
import datetime
import os
import sys
import shutil
import glob
import re
import stat

try:
    import cf_units
except ImportError:
    IMPORT_ERROR_MSG = ('Unable to import cf_units. Ensure scitools module '
                        'has been loaded first.')
    sys.exit(IMPORT_ERROR_MSG)

import common
import error
import save_um_state
import dr_env_lib.um_def
import dr_env_lib.env_lib
try:
    import f90nml
except ImportError:
    pass


def _expand_fortran_namelist(nl_text):
    """
    In fortran namelists there is the opportunity to collapse N repeated
    values (v) into the form N*V. This can cause problems if you try
    to parse the data. This function expands these entries.

    """
    # Define the pattern in order to search for instances in the namelist
    # of the string N*v, where the value optionally has a decimal point.
    pattern = r"(\d+)\*([\d\.]+)"
    while re.search(pattern, nl_text):
        match = re.search(pattern, nl_text)
        repeats = int(match.group(1))
        value = match.group(2)
        value_list = [value]*repeats
        values_str = ", ".join(value_list)
        # The matched pattern needs to have the "*" escaped
        # or it treats it as a matching extension
        nl_text = re.sub(match.group(0).replace('*', r'\*'),
                         values_str, nl_text)

    return nl_text


def _grab_file_info(infile, pattern):
    '''
    Retrieve the required information from a text file, as specified
    by the Regex argument.
    '''
    file_handle = common.open_text_file(infile, 'r')
    for line in file_handle.readlines():
        # Expand any N repeating namelist values V of the form N*V
        line = _expand_fortran_namelist(line)
        match = re.search(pattern, line)
        if match:
            file_info = match.group(1)
            break
    file_handle.close()

    if match is None:
        msg = "Pattern %s not found in file %s" % (pattern, infile)
        sys.stderr.write(msg)
        sys.exit(error.IOERROR)

    return file_info


def _grab_xhist_date(xhistfile):
    '''
    Retrieve the checkpoint dump date from the variable CHECKPOINT_DUMP_IM
    in a Unified Model xhist file
    '''
    # Pattern that defines the CHECKPOINT_DUMP_IM variable, which
    # specifies the location of the UM restart dump. The dump file
    # name from climate suites has the format *daYYYYmmdd.
    checkpoint_pattern = r"CHECKPOINT_DUMP_IM\s*=\s*'\S*da(\d{8})"
    checkpoint_date = _grab_file_info(xhistfile, checkpoint_pattern)

    return checkpoint_date


def _grab_xhist_start_date(xhistfile):
    '''
    Get the model basis time from MODEL_DATA_TIME in a Unified Model
    xhist file.
    '''
    # Pattern that defines the MODEL_DATA_TIME entry that specifies
    # the model basis time, which has the format YYYY,mm,dd,HH,MM,SS.
    start_date_pattern = r"MODEL_DATA_TIME\s*=\s*([\d\s,]+),"
    start_date = _grab_file_info(xhistfile, start_date_pattern)
    start_date = datetime.datetime.strptime(
        start_date.replace(" ", ""), "%Y,%m,%d,%H,%M,%S")

    return start_date


def _grab_xhist_completed_steps(xhistfile):
    '''
    Get the number of completed model steps from the H_STEPIM
    variable in the Unified Model xhist file.
    '''
    # Pattern that defines the H_STEPIM entry that defines the number of
    # model time-steps.
    steps_pattern = r"H_STEPIM\s*=\s*(\d+),"
    n_steps = _grab_file_info(xhistfile, steps_pattern)

    return int(n_steps)


def _grab_atmos_timestep_info(atmos_cntl_file):
    '''
    Get the number of seconds per period and the number of steps per
    period from the Unified Model's ATMOSCNTL file.
    '''
    # Define patterns that respectively specify the number of steps per
    # time period, and the number of seconds per period.
    n_steps_pattern = r"steps_per_periodim\s*=\s*(\d+),"
    n_secs_pattern = r"secs_per_periodim\s*=\s*(\d+),"

    n_steps_per_period = _grab_file_info(
        atmos_cntl_file, n_steps_pattern)
    n_secs_per_period = _grab_file_info(
        atmos_cntl_file, n_secs_pattern)

    return float(n_steps_per_period), float(n_secs_per_period)


def _calc_current_model_date(xhistfile, calendar, prev_work_dir):
    '''
    Calculates the current model date based on the model start date
    for the previous model step, and the number of completed
    timesteps.
    '''
    ref_date_format = 'seconds since %Y-%m-%d %H:%M:%S'

    # modify the calendar names for compatability with cf_units module
    if calendar == "360day":
        calendar = "360_day"
    if calendar == "365day":
        calendar = "365_day"

    # Retrieve the model start date for this model run, and
    # the number of completed steps from the UM history file.
    model_start_date = _grab_xhist_start_date(xhistfile)
    n_completed_steps = _grab_xhist_completed_steps(xhistfile)

    # Get the number of time steps per period and the number of
    # seconds per period from the UM namelist.
    n_steps_per_period, n_secs_per_period = _grab_atmos_timestep_info(
        os.path.join(prev_work_dir, 'ATMOSCNTL'))

    timestep_seconds = n_secs_per_period / n_steps_per_period
    progress_seconds = n_completed_steps * timestep_seconds

    # Provide a reference time for the timestep incrementation.
    ref_time = model_start_date.strftime(ref_date_format)
    model_date_num_secs = cf_units.date2num(
        model_start_date, ref_time, calendar=calendar) + progress_seconds

    current_model_date = cf_units.num2date(
        model_date_num_secs, ref_time, calendar=calendar)

    return current_model_date


def verify_fix_rst(xhistfile, cyclepoint, workdir, task_name, temp_hist_name,
                   calendar, task_param_run=None):
    '''
    Verify that the date associated with the restart dump the UM is
    attempting to pick up is consistent with the start date of the
    current CRUN. If they don't match, attempt an automatic
    fix. Alternatively, look within the user-defined path defined by
    the environment variable PREV_MODEL_WORKDIR if so specified. The
    cyclepoint variable has the form yyyymmddThhmmZ.
    '''
    # Compare the checkpoint date from the history file with the
    # current model date. This is calculated using the number of
    # completed timesteps completed thus far, and the model basis
    # time. The two should be consistent.
    checkpoint_date = _grab_xhist_date(xhistfile)

    #find the work directory for the previous cycle
    prev_work_dir = common.find_previous_workdir(
        cyclepoint, workdir, task_name, task_param_run)

    current_model_date = _calc_current_model_date(
        xhistfile, calendar, prev_work_dir)

    current_model_date = current_model_date.strftime('%Y%m%d')

    # If we are running a seasonal forecast, the NRUN and CRUNS are
    # done during the same cycle, unlike other climate suites. For the
    # former, we can compare the UM dump restart date with the
    # expected model progress.
    if checkpoint_date != current_model_date:
        # write the message to both standard out and standard error
        msg = '[WARN] The UM restart data does not match the ' \
            ' current model time\n.' \
            ' Current model date is %s\n' \
            ' UM restart time is %s\n' % (current_model_date, checkpoint_date)
        sys.stdout.write(msg)

        old_hist_path = os.path.join(prev_work_dir, 'history_archive')
        old_hist_files = [f for f in os.listdir(old_hist_path) if
                          temp_hist_name in f]
        old_hist_files.sort(reverse=True)
        for o_h_f in old_hist_files:
            xhist_date = _grab_xhist_date(os.path.join(old_hist_path, o_h_f))
            if xhist_date == current_model_date:
                shutil.copy(os.path.join(old_hist_path, o_h_f),
                            xhistfile)
                sys.stdout.write('%s\n' % ('*'*42,))
                sys.stdout.write('[WARN] Automatically attempting to fix UM'
                                 ' restart data, by using the xhist file:\n'
                                 '    %s\n from the previous cycle\n' %
                                 (os.path.join(old_hist_path, o_h_f)))
                sys.stdout.write('%s\n' % ('*'*42,))
                break
    else:
        sys.stdout.write('[INFO] Validated UM restart date\n')


def _load_run_environment_variables(um_envar):
    '''
    Load the UM environment variables required for the model run into the
    um_envar container
    '''
    um_envar = dr_env_lib.env_lib.load_envar_from_definition(
        um_envar, dr_env_lib.um_def.UM_ENVIRONMENT_VARS_INITIAL)

    # copy a couple of variables to different names
    um_envar.add('STDOUT_FILE', um_envar['ATMOS_STDOUT_FILE'])

    return um_envar


def _setup_executable(common_env):
    '''
    Setup the environment and any files required by the executable
    '''
    # Create the environment variable container
    um_envar = dr_env_lib.env_lib.LoadEnvar()
    # Load the environment variables required
    um_envar = _load_run_environment_variables(um_envar)

    # Save the state of the partial sum files, or restore state depending on
    # what is required. This doesnt currently make sense for integer cycling
    if common_env['CYLC_CYCLING_MODE'] != 'integer':
        save_um_state.save_state(common_env['RUNID'], common_env)

    # Create a link to the UM atmos exec in the work directory
    common.remove_file(um_envar['ATMOS_LINK'])
    os.symlink(um_envar['ATMOS_EXEC'],
               um_envar['ATMOS_LINK'])

    if common_env['CONTINUE'] == 'false':
        sys.stdout.write('[INFO] This is an NRUN\n')
        common.remove_file(um_envar['HISTORY'])
    else:
        # check if file exists and is readable
        sys.stdout.write('[INFO] This is a CRUN\n')
        if not os.access(um_envar['HISTORY'], os.R_OK):
            sys.stderr.write('[FAIL] Can not read history file %s\n' %
                             um_envar['HISTORY'])
            sys.exit(error.MISSING_DRIVER_FILE_ERROR)
        if common_env['DRIVERS_VERIFY_RST'] == 'True':

            # In seasonal forecasting, model runs are split into NRUNs and
            # CRUNs within the same cycle. Use the CYLC_TASK_PARAM_run
            # variable to access the previous model step work directory.
            if common_env['SEASONAL'] == 'True':
                verify_fix_rst(um_envar['HISTORY'],
                               common_env['CYLC_TASK_CYCLE_POINT'],
                               common_env['CYLC_TASK_WORK_DIR'],
                               common_env['CYLC_TASK_NAME'],
                               'temp_hist',
                               common_env['CALENDAR'],
                               common_env['CYLC_TASK_PARAM_run'])
            else:
                verify_fix_rst(um_envar['HISTORY'],
                               common_env['CYLC_TASK_CYCLE_POINT'],
                               common_env['CYLC_TASK_WORK_DIR'],
                               common_env['CYLC_TASK_NAME'],
                               'temp_hist',
                               common_env['CALENDAR'])
    um_envar.add('HISTORY_TEMP', 'thist')

    # Calculate total number of processes
    um_npes = int(um_envar['UM_ATM_NPROCX']) * \
        int(um_envar['UM_ATM_NPROCY'])
    nproc = um_npes + int(um_envar['FLUME_IOS_NPROC'])

    um_envar.add('UM_NPES', str(um_npes))
    um_envar.add('NPROC', str(nproc))

    # Set the stashmaster default. Note that the environment variable STASHMSTR
    # takes precedence if set. STASHMSTR is a legacy version of STASHMASTER
    # for compatibility with bin/um-recon in the UM source.
    if um_envar['STASHMASTER'] == '':
        stashmaster = os.path.join(um_envar['UMDIR'],
                                   'vn%s' % (um_envar['VN']),
                                   'ctldata', 'STASHmaster')
        sys.stdout.write('[INFO] Using default STASHmaster %s\n' %
                         stashmaster)
        um_envar['STASHMASTER'] = stashmaster
    if um_envar['STASHMSTR'] == '':
        if not os.path.isdir(um_envar['STASHMASTER']):
            sys.stderr.write('STASHMaster directory %s doesn\'t exist\n' %
                             um_envar['STASHMASTER'])

            sys.exit(error.MISSING_MODEL_FILE_ERROR)
    else:
        um_envar['STASHMASTER'] = um_envar['STASHMSTR']
    try:
        os.makedirs(os.path.dirname(um_envar['STDOUT_FILE']))
    except OSError:
        # If the stdout file is not within a subdirectory nothing else needs
        # doing, as is the case if the directory already exists
        pass
    # Delete any previous stdout files
    for stdout_file in glob.glob('%s*' % um_envar['STDOUT_FILE']):
        common.remove_file(stdout_file)

    return um_envar


def _set_launcher_command(launcher, um_envar):
    '''
    Setup the launcher command for the executable
    '''
    if um_envar['ROSE_LAUNCHER_PREOPTS_UM'] == 'unset':
        ss = False
        um_envar['ROSE_LAUNCHER_PREOPTS_UM'] = \
            common.set_aprun_options(um_envar['NPROC'], \
                um_envar['ATMOS_NODES'], um_envar['OMPTHR_ATM'], \
                    um_envar['HYPERTHREADS'], ss) \
                        if launcher == 'aprun' else ''

    launch_cmd = '%s ./%s' % \
        (um_envar['ROSE_LAUNCHER_PREOPTS_UM'], \
             um_envar['ATMOS_LINK'])

    # Put in quotes to allow this environment variable to be exported as it
    # contains (or can contain) spaces
    um_envar['ROSE_LAUNCHER_PREOPTS_UM'] = "'%s'" % \
        um_envar['ROSE_LAUNCHER_PREOPTS_UM']

    return launch_cmd

def get_atmos_resol(um_name, um_resol_file, run_info):
    '''
    Determine the atmosphere resolution.
    This function is only used when creating the namcouple at run time.
    '''

    # Check that resolution file exists
    if not os.path.isfile(um_resol_file):
        sys.stderr.write('[FAIL] not found %s file.\n' % um_resol_file)
        sys.exit(error.MISSING_FILE_SIZES)

    # Read the resolution file
    sizes_nml = f90nml.read(um_resol_file)

    # Check the horizontal resolution variables exist
    if 'nlsizes' not in sizes_nml:
        sys.stderr.write('[FAIL] nlsizes not found in %s\n' % \
                             um_resol_file)
        sys.exit(error.MISSING_ATM_RESOL_NML)
    if 'global_row_length' not in sizes_nml['nlsizes'] or \
            'global_rows' not in sizes_nml['nlsizes']:
        sys.stderr.write('[FAIL] global_row_length or global_rows are '
                         'missing from namelist nlsizes in %s\n' % \
                             um_resol_file)
        sys.exit(error.MISSING_ATM_HORIZ_RESOL)

    # Store the grid
    atmos_resol = int(sizes_nml['nlsizes']['global_row_length'] / 2)
    atmos_grid_name = um_name + '_grid'
    if um_name == 'JNR':
        run_info[atmos_grid_name] = 'n' + str(atmos_resol) + 'j'
    else:
        run_info[atmos_grid_name] = 'n' + str(atmos_resol)

    # Store the resolution
    atmos_resol_name = um_name + '_resol'
    run_info[atmos_resol_name] = [sizes_nml['nlsizes']['global_row_length'],
                                  sizes_nml['nlsizes']['global_rows']]

    # Check that vertical resolution exists
    if 'model_levels' not in sizes_nml['nlsizes']:
        sys.stderr.write('[FAIL] model_levels is missing from namelist '
                         'nlsizes in %s\n' % um_resol_file)
        sys.exit(error.MISSING_ATM_VERT_RESOL)

    # Store the vertical levels for atmosphere
    atmos_lev_name = um_name + '_model_levels'
    run_info[atmos_lev_name] = sizes_nml['nlsizes']['model_levels']

    return run_info

def get_jules_levels(jules_resol_file):
    '''
    Determine the number of soil levels, vegetation tiles and
    non-vegetation tiles.
    This function is only used when creating the namcouple at run time.
    '''

    # Check that resolution file exists
    if not os.path.isfile(jules_resol_file):
        sys.stderr.write('[FAIL] not found %s file.\n' % jules_resol_file)
        sys.exit(error.MISSING_FILE_SHARED)

    # Read the resolution file
    sizes_nml = f90nml.read(jules_resol_file)

    # Check that soil depth, which is given by the number of elements in
    # in dzsoil_io, exists
    if 'jules_soil' not in sizes_nml:
        sys.stderr.write('[FAIL] jules_soil not found in %s\n' % \
                         jules_resol_file)
        sys.exit(error.MISSING_JULES_RESOL_NML)
    if 'dzsoil_io' not in sizes_nml['jules_soil']:
        sys.stderr.write('[FAIL] dzsoil_io is missing from namelist '
                         'jules_soil in %s\n' % jules_resol_file)
        sys.exit(error.MISSING_JULES_VERT_RESOL)

    # Store the soil levels
    n_soil_levs = len(sizes_nml['jules_soil']['dzsoil_io'])

    # Check that tile information exists
    if 'jules_surface_types' not in sizes_nml:
        sys.stderr.write('[FAIL] jules_surface_types not found in %s\n' % \
                         jules_resol_file)
        sys.exit(error.MISSING_JULES_RESOL_NML)
    # 'npft' is the number of plant functional or vegetation tiles, and
    # 'nnvg' is the number of non-vegetation tiles.
    if 'npft' not in sizes_nml['jules_surface_types'] or \
       'nnvg' not in sizes_nml['jules_surface_types']:
        sys.stderr.write('[FAIL] npft or nnvg is missing from namelist '
                         'jules_surface_types in %s\n' % jules_resol_file)
        sys.exit(error.MISSING_JULES_TILE_INFO)

    # Return soil levels, number of plant function tiles (npft) and
    # number of non-vegetation tiles (nnvg).
    return n_soil_levs, sizes_nml['jules_surface_types']['npft'], \
        sizes_nml['jules_surface_types']['nnvg']

def _determine_rmp_mapping(rmp_mapping):
    '''
    Determine the rmp mapping from the string rmp_mapping
    '''

    remap = {}
    # Separate by the number of rmp mappings
    for remap_str in rmp_mapping.split(';'):

        # The default mapping type
        mapping_type = -99

        # Determine the stash fields which this remapping applies to.
        i_colon = remap_str.find(':')
        if i_colon > 0:
            stash_list = []
            for stash_code in remap_str[i_colon+1:].split(','):
                stash_list.append(int(stash_code))
            remap_str = remap_str[:i_colon]
        else:
            stash_list = ['default']

        # Determine the mapping type
        if remap_str.find('BICUBIC') > -1:
            mapping_type = 3
        else:
            i_ext = remap_str.find('_1st')
            if i_ext > 0:
                mapping_type = 1
                remap_str = remap_str[0:i_ext]
            else:
                i_ext = remap_str.find('_2nd')
                if i_ext > 0:
                    mapping_type = 2
                    remap_str = remap_str[0:i_ext]

        # Store remapping and the mapping type
        for stash_name in stash_list:
            if stash_name != 'default':
                stash_name = '{:05d}'.format(stash_name)
            remap[stash_name] = {'mapping': remap_str, 'map_type': mapping_type}

    # Return remapping information
    return remap

def _add_hybrid_cpl(n_cpl_freq, cpl_list, origin, dest, name_out_ident,
                    rmp_mapping, hybrid_weight):
    '''
    Write the hybrid coupling fields into hybrid_snd_list.
    This function is only used when creating the namcouple at run time.
    '''

    if cpl_list:

        # Determine the remapping
        remap = _determine_rmp_mapping(rmp_mapping)

        # Ensure we have a list
        if isinstance(cpl_list, int):
            # Convert single integer to a list
            cpl_list = [cpl_list]

        # Loop across the fields to couple
        hybrid_snd_list = []
        for stash_code in cpl_list:
            stash_name = '{:05d}'.format(stash_code)
            name_out = stash_name + name_out_ident + '001s'

            if stash_name in remap:
                remapping = remap[stash_name]['mapping']
                mapping_type = remap[stash_name]['map_type']
            else:
                if 'default' in remap:
                    remapping = remap['default']['mapping']
                    mapping_type = remap['default']['map_type']
                else:
                    sys.stderr.write('[FAIL] Require a default remapping '
                                     'in hybrid_rmp_mapping.\n')
                    sys.exit(error.MISSING_DEFAULT_RMP)

            # Add entry
            import write_namcouple
            hybrid_snd_list.append(
                write_namcouple.NamcoupleEntry(name_out,
                                               (100000 + stash_code),
                                               '?', origin, dest, -99, '?',
                                               remapping, mapping_type,
                                               hybrid_weight, True,
                                               n_cpl_freq))

            # Move to next entry
            hybrid_weight += 1
    else:
        # There's no extra coupling fields
        hybrid_snd_list = None

    return hybrid_weight, hybrid_snd_list

def read_hybrid_coupling(hybrid_file_nml, run_info, oasis_nml):
    '''
    Read the hybrid coupling namelist and store the hybrid coupling
    fields.
    This function is only used when creating the namcouple at run time.
    '''

    # Default option is to send no fields
    hybrid_snd_list = None

    # Determine if hybrid sending file is present
    if os.path.exists(hybrid_file_nml):
        # Determine if this Snr->Jnr or Jnr->Snr coupling
        if hybrid_file_nml == 'HYBRID_SNR2JNR':
            # These are Snr->Jnr fields
            origin = 'ATM'
            dest = 'JNR'
            name_out_ident = 's'
        else:
            # These are Jnr->Snr fields
            origin = 'JNR'
            dest = 'ATM'
            name_out_ident = 'j'

        # Check we have the data in oasis_nml which we need
        if 'hybrid_weight' not in oasis_nml['oasis_send_nml']:
            sys.stderr.write('[FAIL] entry hybrid_weight missing '
                             'from namelist oasis_send_nml.\n')
            sys.exit(error.MISSING_HYBRID_WEIGHT)
        else:
            hybrid_weight = oasis_nml['oasis_send_nml']['hybrid_weight']
        if 'hybrid_rmp_mapping' not in oasis_nml['oasis_send_nml']:
            sys.stderr.write('[FAIL] entry hybrid_rmp_mapping missing '
                             'from namelist oasis_send_nml.\n')
            sys.exit(error.MISSING_HYBRID_RMP_MAPPING)
        else:
            rmp_mapping = oasis_nml['oasis_send_nml']['hybrid_rmp_mapping']

        # Read the hybrid namelist
        hybrid_nml = f90nml.read(hybrid_file_nml)

        # Check we have the expected information
        if 'hybrid_cpl' not in hybrid_nml:
            sys.stderr.write('[FAIL] namelist hybrid_cpl is missing '
                             'from %s.\n' % hybrid_nml)
            sys.exit(error.MISSING_HYBRID_NML)
        if 'cpl_hybrid' not in hybrid_nml['hybrid_cpl']:
            sys.stderr.write('[FAIL] entry cpl_hybrid is missing '
                             'from namelist hybrid_cpl in %s.\n' %
                             hybrid_nml)
            sys.exit(error.MISSING_HYBRID_SEND)

        # Default option is to have no stats
        if 'l_hybrid_stats' not in hybrid_nml['hybrid_cpl']:
            hybrid_nml['hybrid_cpl']['l_hybrid_stats'] = False

        # Check that we have some hybrid fields to send
        if hybrid_nml['hybrid_cpl']['cpl_hybrid']:
            if hybrid_nml['hybrid_cpl']['l_hybrid_overw'] or \
               hybrid_nml['hybrid_cpl']['l_hybrid_stats']:
                hybrid_weight, hybrid_snd_list \
                    = _add_hybrid_cpl(0, hybrid_nml['hybrid_cpl']['cpl_hybrid'],
                                      origin, dest, name_out_ident,
                                      rmp_mapping, hybrid_weight)

                # Are there any extra stats to send
                if hybrid_nml['hybrid_cpl']['l_hybrid_stats'] and \
                        'cpl_hybrid_stats' in hybrid_nml['hybrid_cpl']:
                    hybrid_weight, hybrid_snd_stat_list = _add_hybrid_cpl(
                        1, hybrid_nml['hybrid_cpl']['cpl_hybrid_stats'],
                        origin, dest, name_out_ident, rmp_mapping,
                        hybrid_weight)

                    if hybrid_snd_stat_list:
                        hybrid_snd_list.extend(hybrid_snd_stat_list)

                # Need to store value of l_hybrid_stats in case it's
                # true and any of the coupling frequencies need
                # modifying as a consequence.
                if hybrid_nml['hybrid_cpl']['l_hybrid_stats']:
                    flag_name = 'l_hyb_stats_' + origin + '2' + dest
                    run_info[flag_name] = True

    return run_info, hybrid_snd_list

def _sent_coupling_fields(run_info):
    '''
    Write the coupling fields sent from UM into model_snd_list.
    This function is only used when creating the namcouple at run time.
    '''
    # Check that file specifying the coupling fields sent from
    # UM is present
    if not os.path.exists('OASIS_ATM_SEND'):
        sys.stderr.write('[FAIL] OASIS_ATM_SEND is missing.\n')
        sys.exit(error.MISSING_OASIS_ATM_SEND)

    # Add toyatm to our list of executables
    if 'exec_list' not in run_info:
        run_info['exec_list'] = []
    run_info['exec_list'].append('toyatm')

    # Determine the atmosphere resolution
    run_info = get_atmos_resol('ATM', 'SIZES', run_info)

    # Determine the soil levels
    run_info['ATM_soil_levels'], run_info['ATM_veg_tiles'], \
        run_info['ATM_non_veg_tiles'] = get_jules_levels('SHARED')

    # Read the namelist OASIS_ATM_SND (note that this must exist
    # or run_info['l_namecouple'] wouldn't be false and we wouldn't
    # be here)
    oasis_nml = f90nml.read('OASIS_ATM_SEND')

    # Check with have the expected namelist in this file
    if 'oasis_send_nml' not in oasis_nml:
        sys.stderr.write('[FAIL] namelist oasis_send_nml is '
                         'missing from OASIS_ATM_SEND.\n')
        sys.exit(error.MISSING_OASIS_SEND_NML_ATM)

    # Store core namcouple options
    # The namcoupled debug value
    if 'nlogprt' in oasis_nml['oasis_send_nml']:
        run_info['nlogprt'] = oasis_nml['oasis_send_nml']['nlogprt']
        if isinstance(run_info['nlogprt'], int):
            # Convert single integer to a list
            run_info['nlogprt'] = [run_info['nlogprt']]
    else:
        run_info['nlogprt'] = 0
    # Determine if any namcouple coupling should use EXPOUT
    if 'expout' in oasis_nml['oasis_send_nml']:
        if isinstance(oasis_nml['oasis_send_nml']['expout'], list):
            run_info['expout'] = oasis_nml['oasis_send_nml']['expout']
        else:
            run_info['expout'] = [oasis_nml['oasis_send_nml']['expout']]
    # Determine if any remapping file need to be created by OASIS-mct
    if 'rmp_create' in oasis_nml['oasis_send_nml']:
        if isinstance(oasis_nml['oasis_send_nml']['rmp_create'], list):
            run_info['rmp_create'] = \
                oasis_nml['oasis_send_nml']['rmp_create']
        else:
            run_info['rmp_create'] = \
                [oasis_nml['oasis_send_nml']['rmp_create']]

    # Create a list of fields sent from ATM
    model_snd_list = None
    if 'oasis_atm_send' in oasis_nml['oasis_send_nml']:
        # Check that we have some fields in here
        if oasis_nml['oasis_send_nml']['oasis_atm_send']:
            import write_namcouple
            model_snd_list = write_namcouple.add_to_cpl_list(
                'ATM', False, 0,
                oasis_nml['oasis_send_nml']['oasis_atm_send'])

    # Add any hybrid coupling fields
    run_info, hybrid_snd_list = read_hybrid_coupling('HYBRID_SNR2JNR',
                                                     run_info, oasis_nml)
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
    um_envar_fin = dr_env_lib.env_lib.LoadEnvar()
    um_envar_fin = dr_env_lib.env_lib.load_envar_from_definition(
        um_envar_fin, dr_env_lib.um_def.UM_ENVIRONMENT_VARS_FINAL)

    pe0_suffix = '0'*(len(str(int(um_envar_fin['NPROC'])-1)))
    um_pe0_stdout_file = '%s%s' % (um_envar_fin['STDOUT_FILE'],
                                   pe0_suffix)
    if not os.path.isfile(um_pe0_stdout_file):
        sys.stderr.write('Could not find PE0 output file %s\n' %
                         um_pe0_stdout_file)
        sys.exit(error.MISSING_DRIVER_FILE_ERROR)
    elif not common.is_non_zero_file(um_pe0_stdout_file):
        sys.stderr.write('PE0 file %s exists but has zero size\n' %
                         um_pe0_stdout_file)
        sys.exit(error.MISSING_DRIVER_FILE_ERROR)
    else:
        # append the pe0 output to standard out
        sys.stdout.write('[INFO] UM Output from file %s\n' % um_pe0_stdout_file)
        sys.stdout.write('%PE0 OUTPUT%\n')
        # use an iterator to avoid loading the pe0 file into memory
        with open(um_pe0_stdout_file, 'r') as f_pe0:
            for line in f_pe0:
                sys.stdout.write(line)

    # Remove output from other PEs unless requested otherwise
    if um_envar_fin['ATMOS_KEEP_MPP_STDOUT'] == 'false':
        for stdout_file in glob.glob('%s*' %
                                     um_envar_fin['STDOUT_FILE']):
            common.remove_file(stdout_file)

    # Rose-ana expects fixed filenames so we link to .pe0 as otherwise the
    # filename depends on the processor decomposition
    if os.path.isfile(um_pe0_stdout_file):
        if um_pe0_stdout_file != '%s0' % um_envar_fin['STDOUT_FILE']:
            lnk_src = '%s%s' % \
                (os.path.basename(um_envar_fin['STDOUT_FILE']),
                 pe0_suffix)
            lnk_dst = '%s0' % um_envar_fin['STDOUT_FILE']
            common.remove_file(lnk_dst)
            os.symlink(lnk_src, lnk_dst)

    # Make any core dump files world-readable to assist in debugging problems
    for corefile in glob.glob('*core*'):
        if os.path.isfile(corefile):
            current_st = os.stat(corefile)
            # Update, so in addition to current permissions the file is
            # readable by user, group, and others
            os.chmod(corefile, current_st.st_mode | stat.S_IRUSR |
                     stat.S_IRGRP | stat.S_IROTH)


def run_driver(common_env, mode, run_info):
    '''
    Run the driver, and return an instance of LoadEnvar and as string
    containing the launcher command for the UM component
    '''
    if mode == 'run_driver':
        exe_envar = _setup_executable(common_env)
        launch_cmd = _set_launcher_command(common_env['ROSE_LAUNCHER'],
                                           exe_envar)
        if run_info['l_namcouple']:
            model_snd_list = None
        else:
            run_info, model_snd_list = _sent_coupling_fields(run_info)
            # We'll probably need the name of SHARED file later in
            # MCT driver and we'll need the STASHmaster directory
            run_info['SHARED_FILE'] = exe_envar['SHARED_NLIST']
            run_info['STASHMASTER'] = exe_envar['STASHMASTER']
            run_info['riv3'] = int(common_env['CPL_RIVER_COUNT'])
    elif mode == 'finalize' or mode == 'failure':
        _finalize_executable(common_env)
        exe_envar = None
        launch_cmd = None
        model_snd_list = None

    return exe_envar, launch_cmd, run_info, model_snd_list
