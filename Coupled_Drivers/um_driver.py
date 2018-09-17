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
    xhist_handle.close()
    return checkpoint_date


def _verify_fix_rst(xhistfile, cyclepoint, workdir, task_name):
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
                          'temp_hist' in f]
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
    _ = um_envar.load_envar('STASHMASTER', '')
    _ = um_envar.load_envar('STASHMSTR', '')
    _ = um_envar.load_envar('SHARED_FNAME', 'SHARED')
    _ = um_envar.load_envar('FLUME_IOS_NPROC', '0')

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
    # what is required
    save_um_state.save_state(common_envar, um_envar['CONTINUE'])

    # Create a link to the UM atmos exec in the work directory
    common.remove_file(um_envar['ATMOS_LINK'])
    os.symlink(um_envar['ATMOS_EXEC'],
               um_envar['ATMOS_LINK'])

    if um_envar['CONTINUE'] in ('', 'false'):
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
            _verify_fix_rst(um_envar['HISTORY'],
                            common_envar['CYLC_TASK_CYCLE_POINT'],
                            common_envar['CYLC_TASK_WORK_DIR'],
                            common_envar['CYLC_TASK_NAME'])
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
        sys.stdout.write('[INFO] Using default STASHmaster %s' %
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


def run_driver(common_envar, mode):
    '''
    Run the driver, and return an instance of common.LoadEnvar and as string
    containing the launcher command for the UM component
    '''
    if mode == 'run_driver':
        exe_envar = _setup_executable(common_envar)
        launch_cmd = _set_launcher_command(exe_envar)
    elif mode == 'finalize':
        _finalize_executable(common_envar)
        exe_envar = None
        launch_cmd = None
    return exe_envar, launch_cmd
