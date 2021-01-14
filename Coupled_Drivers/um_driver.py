#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016-2021 Met Office. All rights reserved.

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
#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
import os
import sys
import shutil
import glob
import re
import stat
import common
import error
import save_um_state
import create_namcouple
try:
    import f90nml
except ImportError:
    pass

def _grab_xhist_date(xhistfile):
    '''
    Retrieve the checkpoint dump date from the variable CHECKPOINT_DUMP_IM
    in a Unified Model xhist file
    '''
    xhist_handle = common.open_text_file(xhistfile, 'r')
    for line in xhist_handle.readlines():
        match = re.search(r"CHECKPOINT_DUMP_IM\s*=\s*'\S*da(\d{8})", line)
        if match:
            checkpoint_date = match.group(1)
            break
    else:
        sys.stderr.write('Unable to find checkpoint date within XHIST file %s'
                         '\nPlease check the contents of this file and'
                         ' rerun. It is possible that this cycle of the'
                         '\nmodel has not been configured to produce a'
                         ' checkpoint restart, (in which case there will be no'
                         '\nvalue for CHECKPOINT_DUMP_IM), or there is a file'
                         ' system delay, especially on Lustre (the file will'
                         '\nbe zero length)' % xhistfile)
        sys.exit(error.CORRUPTED_MODEL_FILE_ERROR)

    xhist_handle.close()
    return checkpoint_date


def verify_fix_rst(xhistfile, cyclepoint, workdir, task_name, temp_hist_name):
    '''
    Verify that the restart dump the UM is attempting to pick up is for the
    start of the cycle. The cyclepoint variable has the form yyyymmddThhmmZ.
    If they don't match, attempt an automatic fix
    '''
    cycle_date_string = cyclepoint.split('T')[0]
    checkpoint_date = _grab_xhist_date(xhistfile)
    if checkpoint_date != cycle_date_string:
        # write the message to both standard out and standard error
        msg = '[WARN] The UM restart data does not match the ' \
            ' current cycle time\n.' \
            '   Cycle time is %s\n' \
            '   UM restart time is %s\n' % (cycle_date_string, checkpoint_date)
        sys.stdout.write(msg)
        #find the work directory for the previous cycle
        prev_work_dir = common.find_previous_workdir(cyclepoint, workdir,
                                                     task_name)
        old_hist_path = os.path.join(prev_work_dir, 'history_archive')
        old_hist_files = [f for f in os.listdir(old_hist_path) if
                          temp_hist_name in f]
        old_hist_files.sort(reverse=True)
        for o_h_f in old_hist_files:
            xhist_date = _grab_xhist_date(os.path.join(old_hist_path, o_h_f))
            if xhist_date == cycle_date_string:
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
    if um_envar.load_envar('UM_ATM_NPROCX') != 0:
        sys.stderr.write('[FAIL] Environment variable UM_ATM_NPROCX containing '
                         'the number of UM processors in the X direction '
                         'is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    if um_envar.load_envar('UM_ATM_NPROCY') != 0:
        sys.stderr.write('[FAIL] Environment variable UM_ATM_NPROCY containing '
                         'the number of UM processors in the Y direction '
                         'is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    if um_envar.load_envar('VN') != 0:
        sys.stderr.write('[FAIL] Environment variable VN containing the '
                         'UM version is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    if um_envar.load_envar('UMDIR') != 0:
        sys.stderr.write('[FAIL] Environment variable UMDIR is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    if um_envar.load_envar('ATMOS_EXEC') != 0:
        sys.stderr.write('[FAIL] Environment variable ATMOS_EXEC is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    if um_envar.load_envar('ROSE_LAUNCHER_PREOPTS_UM') != 0:
        sys.stderr.write('[FAIL] Environment variable '
                         'ROSE_LAUNCHER_PREOPTS_UM is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    _ = um_envar.load_envar('ATMOS_LINK', 'atmos.exe')
    _ = um_envar.load_envar('DR_HOOK', '0')
    _ = um_envar.load_envar('DR_HOOK_OPT', 'noself')
    _ = um_envar.load_envar('PRINT_STATUS', 'PrStatus_Normal')
    _ = um_envar.load_envar('UM_THREAD_LEVEL', 'MULTIPLE')
    _ = um_envar.load_envar('HISTORY', 'atmos.xhist')
    _ = um_envar.load_envar('CONTINUE', '')
    # ensure that CONTINUE is always lower case false, unless explicitly
    # set to true (in which case make sure it's lower case true).
    if 'T' in um_envar['CONTINUE'] or 't' in um_envar['CONTINUE']:
        um_envar['CONTINUE'] = 'true'
    else:
        um_envar['CONTINUE'] = 'false'
    _ = um_envar.load_envar('CONTINUE_FROM_FAIL', '')
    if 'T' in um_envar['CONTINUE_FROM_FAIL'] or \
      't' in um_envar['CONTINUE_FROM_FAIL']:
        um_envar['CONTINUE_FROM_FAIL'] = 'true'
        #If continue_from_fail is true then continue must also be true
        um_envar['CONTINUE'] = 'true'
    else:
        um_envar['CONTINUE_FROM_FAIL'] = 'false'
    _ = um_envar.load_envar('STASHMASTER', '')
    _ = um_envar.load_envar('STASHMSTR', '')
    _ = um_envar.load_envar('SHARED_FNAME', 'SHARED')
    _ = um_envar.load_envar('FLUME_IOS_NPROC', '0')
    _ = um_envar.load_envar('CPL_RIVER_COUNT', '0')

    load_shared_fname = um_envar.load_envar('SHARED_FNAME')
    if load_shared_fname == 0:
        um_envar.add('SHARED_NLIST',
                     um_envar['SHARED_FNAME'])
    else:
        um_envar.add('SHARED_NLIST', 'SHARED')

    load_atmos_stdout_file = um_envar.load_envar('ATMOS_STDOUT_FILE')
    if load_atmos_stdout_file == 0:
        um_envar.add('STDOUT_FILE',
                     um_envar['ATMOS_STDOUT_FILE'])
    else:
        um_envar.add('STDOUT_FILE', 'pe_output/atmos.fort6.pe')

    um_envar.add('HOUSEKEEP', 'hkfile')
    um_envar.add('STASHC', 'STASHC')
    um_envar.add('ATMOSCNTL', 'ATMOSCNTL')
    um_envar.add('IDEALISE', 'IDEALISE')
    um_envar.add('IOSCNTL', 'IOSCNTL')

    return um_envar


def _setup_executable(common_envar):
    '''
    Setup the environment and any files required by the executable
    '''
    # Create the environment variable container
    um_envar = common.LoadEnvar()
    # Load the environment variables required
    um_envar = _load_run_environment_variables(um_envar)

    # Save the state of the partial sum files, or restore state depending on
    # what is required. This doesnt currently make sense for integer cycling
    if common_envar['CYLC_CYCLING_MODE'] != 'integer':
        save_um_state.save_state(common_envar['RUNID'], common_envar,
                                 um_envar['CONTINUE'])

    # Create a link to the UM atmos exec in the work directory
    common.remove_file(um_envar['ATMOS_LINK'])
    os.symlink(um_envar['ATMOS_EXEC'],
               um_envar['ATMOS_LINK'])

    if um_envar['CONTINUE'] == 'false':
        sys.stdout.write('[INFO] This is an NRUN\n')
        common.remove_file(um_envar['HISTORY'])
    else:
        # check if file exists and is readable
        sys.stdout.write('[INFO] This is a CRUN\n')
        if not os.access(um_envar['HISTORY'], os.R_OK):
            sys.stderr.write('[FAIL] Can not read history file %s\n' %
                             um_envar['HISTORY'])
            sys.exit(error.MISSING_DRIVER_FILE_ERROR)
        if common_envar['DRIVERS_VERIFY_RST'] == 'True':
            verify_fix_rst(um_envar['HISTORY'],
                           common_envar['CYLC_TASK_CYCLE_POINT'],
                           common_envar['CYLC_TASK_WORK_DIR'],
                           common_envar['CYLC_TASK_NAME'],
                           'temp_hist')
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


def _set_launcher_command(um_envar):
    '''
    Setup the launcher command for the executable
    '''

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
    if not 'nlsizes' in sizes_nml:
        sys.stderr.write('[FAIL] nlsizes not found in %s\n' % \
                             um_resol_file)
        sys.exit(error.MISSING_ATM_RESOL_NML)
    if not 'global_row_length' in sizes_nml['nlsizes'] or \
            not 'global_rows' in sizes_nml['nlsizes']:
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
    if not 'model_levels' in sizes_nml['nlsizes']:
        sys.stderr.write('[FAIL] model_levels is missing from namelist '
                         'nlsizes in %s\n' % um_resol_file)
        sys.exit(error.MISSING_ATM_VERT_RESOL)

    # Store the vertical levels for atmosphere
    atmos_lev_name = um_name + '_model_levels'
    run_info[atmos_lev_name] = sizes_nml['nlsizes']['model_levels']

    return run_info

def get_jules_levels(jules_resol_file):
    '''
    Determine the number of levels in JULES.
    This function is only used when creating the namcouple at run time.
    '''

    # Check that resolution file exists
    if not os.path.isfile(jules_resol_file):
        sys.stderr.write('[FAIL] not found %s file.\n' % jules_resol_file)
        sys.exit(error.MISSING_FILE_SHARED)

    # Read the resolution file
    sizes_nml = f90nml.read(jules_resol_file)

    # Check that soil depths exist
    if not 'jules_soil' in sizes_nml:
        sys.stderr.write('[FAIL] jules_soil not found in %s\n' % \
                         jules_resol_file)
        sys.exit(error.MISSING_JULES_RESOL_NML)
    if not 'dzsoil_io' in sizes_nml['jules_soil']:
        sys.stderr.write('[FAIL] dzsoil_io is missing from namelist '
                         'jules_soil in %s\n' % jules_resol_file)
        sys.exit(error.MISSING_JULES_VERT_RESOL)

    # Return the vertical levels for soil
    return len(sizes_nml['jules_soil']['dzsoil_io'])

def _add_hybrid_cpl(n_cpl_freq, cpl_list, origin, dest, name_out_ident,
                    rmp_mapping, mapping_order, hybrid_weight):
    '''
    Write the hybrid coupling fields into hybrid_snd_list.
    This function is only used when creating the namcouple at run time.
    '''

    if cpl_list:
        hybrid_snd_list = []
        if isinstance(cpl_list, int):
            # Convert single integer to a list
            cpl_list = [cpl_list]

        # Loop across the fields to couple
        for stash_code in cpl_list:
            name_out = '{:05d}'.format(stash_code) + name_out_ident + '001'

            # Add entry
            hybrid_snd_list.append(
                create_namcouple.NamcoupleEntry(name_out,
                                                (100000 + stash_code),
                                                '?', origin, dest, -99, '?',
                                                rmp_mapping, mapping_order,
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

    # Determine if hybrid sending file is present
    if os.path.exists(hybrid_file_nml):
        # Determine if this Snr->Jnr or Jnr->Snr coupling
        if hybrid_file_nml == 'HYBRID_SNR2JNR':
            # These are Snr->Jnr fields
            origin = 'ATM'
            dest   = 'JNR'
            name_out_ident = 's'
        else:
            # These are Jnr->Snr fields
            origin = 'JNR'
            dest   = 'ATM'
            name_out_ident = 'j'

        # The default option
        mapping_order = -99

        # Check we have the data in oasis_nml which we need
        if not 'hybrid_weight' in oasis_nml['oasis_send_nml']:
            sys.stderr.write('[FAIL] entry hybrid_weight missing '
                             'from namelist oasis_send_nml.\n')
            sys.exit(error.MISSING_HYBRID_WEIGHT)
        else:
            hybrid_weight = oasis_nml['oasis_send_nml']['hybrid_weight']
        if not 'hybrid_rmp_mapping' in oasis_nml['oasis_send_nml']:
            sys.stderr.write('[FAIL] entry hybrid_rmp_mapping missing '
                             'from namelist oasis_send_nml.\n')
            sys.exit(error.MISSING_HYBRID_RMP_MAPPING)
        else:
            rmp_mapping = oasis_nml['oasis_send_nml']['hybrid_rmp_mapping']
            i_ext = rmp_mapping.find('_1st')
            if i_ext > 0:
                mapping_order = 1
                rmp_mapping = rmp_mapping[0:i_ext]
            else:
                i_ext = rmp_mapping.find('_2nd')
                if i_ext > 0:
                    mapping_order = 2
                    rmp_mapping = rmp_mapping[0:i_ext]

        # Read the hybrid namelist
        hybrid_nml = f90nml.read(hybrid_file_nml)

        # Check we have the expected information
        if not 'hybrid_cpl' in hybrid_nml:
            sys.stderr.write('[FAIL] namelist hybrid_cpl is missing '
                             'from %s.\n' % hybrid_nml)
            sys.exit(error.MISSING_HYBRID_NML)
        if not 'cpl_hybrid' in hybrid_nml['hybrid_cpl']:
            sys.stderr.write('[FAIL] entry cpl_hybrid is missing '
                             'from namelist hybrid_cpl in %s.\n' %
                             hybrid_nml)
            sys.exit(error.MISSING_HYBRID_SEND)

        # Check that we have some hybrid fields to send
        if hybrid_nml['hybrid_cpl']['cpl_hybrid']:
            hybrid_weight, hybrid_snd_list = \
                _add_hybrid_cpl(0, hybrid_nml['hybrid_cpl']['cpl_hybrid'],
                                origin, dest, name_out_ident, rmp_mapping,
                                mapping_order, hybrid_weight)

            # Are there any extra stats to send
            if 'l_hybrid_stats' in hybrid_nml['hybrid_cpl']:
                if hybrid_nml['hybrid_cpl']['l_hybrid_stats'] and \
                        'cpl_hybrid_stats' in hybrid_nml['hybrid_cpl']:
                    hybrid_weight, hybrid_snd_stat_list = _add_hybrid_cpl(
                        1, hybrid_nml['hybrid_cpl']['cpl_hybrid_stats'],
                        origin, dest, name_out_ident, rmp_mapping,
                        mapping_order, hybrid_weight)

                    if hybrid_snd_stat_list:
                        hybrid_snd_list.extend(hybrid_snd_stat_list)

                # Need to store value of l_hybrid_stats in case it's
                # true and any of the coupling frequencies need
                # modifying as a consequence.
                if hybrid_nml['hybrid_cpl']['l_hybrid_stats']:
                    flag_name = 'l_hyb_stats_' + origin + '2' + dest
                    run_info[flag_name] = True
        else:
            # No fields are being sent from this component
            hybrid_snd_list = None
    else:
        # File is missing, so no coupling field are being sent to the
        # other hybrid component.
        hybrid_snd_list = None

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
    if not 'exec_list' in run_info:
        run_info['exec_list'] = []
    run_info['exec_list'].append('toyatm')

    # Determine the atmosphere resolution
    run_info = get_atmos_resol('ATM', 'SIZES', run_info)

    # Determine the soil levels
    run_info['ATM_soil_levels'] = get_jules_levels('SHARED')

    # Read the namelist OASIS_ATM_SND (note that this must exist
    # or run_info['l_namecouple'] wouldn't be false and we wouldn't
    # be here)
    oasis_nml = f90nml.read('OASIS_ATM_SEND')

    # Check with have the expected namelist in this file
    if not 'oasis_send_nml' in oasis_nml:
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
            model_snd_list = create_namcouple.add_to_cpl_list(
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
    um_envar_fin = common.LoadEnvar()
    if um_envar_fin.load_envar('NPROC') != 0:
        sys.stderr.write('[FAIL] Environment variable NPROC is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    if um_envar_fin.load_envar('STDOUT_FILE') != 0:
        sys.stderr.write('[FAIL] Environment variable STDOUT_FILE containing '
                         'the path to the UM standard out is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)

    _ = um_envar_fin.load_envar('ATMOS_KEEP_MPP_STDOUT', 'false')

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


def run_driver(common_envar, mode, run_info):
    '''
    Run the driver, and return an instance of common.LoadEnvar and as string
    containing the launcher command for the UM component
    '''
    if mode == 'run_driver':
        exe_envar = _setup_executable(common_envar)
        launch_cmd = _set_launcher_command(exe_envar)
        if run_info['l_namcouple']:
            model_snd_list = None
        else:
            run_info, model_snd_list = _sent_coupling_fields(run_info)
            # We'll probably need the name of SHARED file later in
            # MCT driver and we'll need the STASHmaster directory
            run_info['SHARED_FILE'] = exe_envar['SHARED_NLIST']
            run_info['STASHMASTER'] = exe_envar['STASHMASTER']
            run_info['riv3'] = int(exe_envar['CPL_RIVER_COUNT'])
    elif mode == 'finalize':
        _finalize_executable(common_envar)
        exe_envar = None
        launch_cmd = None
        model_snd_list = None
    return exe_envar, launch_cmd, run_info, model_snd_list
