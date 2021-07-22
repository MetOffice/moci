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
    cpmip_um.py

DESCRIPTION
    CPMIP functions for UM
'''
import os
import re
import sys
import common
import error

try:
    # Mule is not part of the standard Python package
    import mule
except ImportError:
    sys.stdout.write('[WARN] Mule utility is unavaliable, unable to calculate'
                     ' complexity for UM\n')

def _is_mule():
    '''
    Check if mule is avaliable to the configuration
    '''
    return 'mule' in sys.modules

def update_input_for_metrics_um(cpmip_envar, nml_shared, nml_ioscntl):
    '''
    Update the UM namelists to ensure that the timers are set
    to be running
    '''
    try:
        num_version = float(cpmip_envar['VN'])
    except ValueError:
        sys.stderr.write('Expecting a numerical value for UM Version in'
                         ' environment variable VN. Instead got %s\n' %
                         cpmip_envar['VN'])
        sys.exit(error.INVALID_EVAR_ERROR)
    # For versions of UM prior to 10.7 the oasis timers can not be run
    # independently from the general UM timers
    mod_shared_nl = common.ModNamelist(nml_shared)
    if num_version < 10.7:
        mod_shared_nl.var_val('ltimer', '.true.')
    else:
        mod_shared_nl.var_val('ltimer', '.false.')
        mod_shared_nl.var_val('l_oasis_timers', '.true.')

    #If required update the namelist for IO timing.
    if cpmip_envar['IO_COST'] in ('true', 'True'):
        mod_shared_nl.var_val('lstashdumptimer', '.true.')
        nn_timing_val = 2
    else:
        nn_timing_val = 1

    mod_shared_nl.replace()
    # Let the UM only write out on the first task (rank 0) to attempt to
    # avoid too much skewing of load balancing information. prnt_writers
    # takes integer values: 1 - all tasks, 2 - rank 0, 3 - rank 0 and head
    # IO servers
    mod_ioscntl_nl = common.ModNamelist(nml_ioscntl)
    mod_ioscntl_nl.var_val('prnt_writers', 2)
    mod_ioscntl_nl.replace()

    # Ocean needs to know about nn_timing_val
    return nn_timing_val


def time_resources_um(cpmip_envar, mpi_tasks_total, stdout_file_str):
    '''
    Finalize code for UM
    '''
    # Determine the name of the UM pe0 output file.
    pe0_suffix = '0'*(len(str(mpi_tasks_total - 1)))
    um_pe0_stdout_file = '%s%s' % (cpmip_envar[stdout_file_str],
                                   pe0_suffix)

    # UM time is for one processor
    um_time, um_coupling_time, um_put_time = get_um_info(um_pe0_stdout_file)

    return um_time, um_coupling_time, um_put_time, um_pe0_stdout_file


def get_um_info(pe0_output):
    '''
    Grab the UM output. Returns the UM CPU time (sans coupling), and the time
    spent in the UMs coupling routines
    '''
    get_times = False

    # Zero times in case they're not in output
    geto2a_time = 0
    puta2o_time = 0
    inita2o_time = 0
    get_hyb_time = 0
    put_hyb_time = 0
    init_hyb_time = 0

    geto2a_regex = re.compile(r"\d+\s*oasis3_geto2a\s*(\d+.\d+)")
    puta2o_regex = re.compile(r"\d+\s*oasis3_puta2o\s*(\d+.\d+)")
    inita2o_regex = re.compile(r"\d+\s*oasis3_inita2o\s*(\d+.\d+)")
    get_hyb_regex = re.compile(r"\d+\s*oasis3_get_hybrid\s*(\d+.\d+)")
    put_hyb_regex = re.compile(r"\d+\s*oasis3_put_hybrid\s*(\d+.\d+)")
    init_hyb_regex = re.compile(r"\d+\s*oasis_init_hybrid\s*(\d+.\d+)")
    um_shell_regex = re.compile(r"\d+\s*UM_SHELL\s*(\d+.\d+)")
    with open(pe0_output, 'r') as f_pe0:
        for line in f_pe0:
            if 'MPP : Non Inclusive timer summary' in line:
                get_times = True
            if 'CPU TIMES (sorted by wallclock times)' in line:
                get_times = False
            # Pull out the average times for the coupling routines
            if get_times:
                geto2a_match = geto2a_regex.search(line)
                puta2o_match = puta2o_regex.search(line)
                inita2o_match = inita2o_regex.search(line)
                get_hyb_match = get_hyb_regex.search(line)
                put_hyb_match = put_hyb_regex.search(line)
                init_hyb_match = init_hyb_regex.search(line)
                um_shell_match = um_shell_regex.search(line)
                if geto2a_match:
                    geto2a_time = float(geto2a_match.group(1))
                if puta2o_match:
                    puta2o_time = float(puta2o_match.group(1))
                if inita2o_match:
                    inita2o_time = float(inita2o_match.group(1))
                if get_hyb_match:
                    get_hyb_time = float(get_hyb_match.group(1))
                if put_hyb_match:
                    put_hyb_time = float(put_hyb_match.group(1))
                if init_hyb_match:
                    init_hyb_time = float(init_hyb_match.group(1))
                if um_shell_match:
                    um_shell_time = float(um_shell_match.group(1))
    try:
        model_time = um_shell_time
        put_time = puta2o_time + put_hyb_time
        coupling_time = put_time + geto2a_time + inita2o_time + \
            get_hyb_time + init_hyb_time
    except NameError:
        sys.stderr.write('[FAIL] Unable to determine Oasis timings from'
                         ' the UM standard output\n')
        sys.exit(error.MISSING_CONTROLLER_FILE_ERROR)
    return model_time, coupling_time, put_time


def get_um_io(pe0_output):
    '''
    Grab the UM timing information for IO routines if avaliable. These
    routines are AS STASH, DUMPCTL, MEANCTL, IOS_Shutdown,
    IOS_stash_client_fini
    Note that not all these routines may be avaliable in a given
    Run
    '''
    get_times = False
    possible_routines = ['AS STASH', 'DUMPCTL', 'MEANCTL',
                         'IOS_Shutdown', 'IOS_stash_client_fini']
    present = []
    times = []
    with open(pe0_output, 'r') as f_pe0:
        for line in f_pe0:
            if 'MPP : Inclusive timer summary' in line:
                get_times = True
            if 'CPU TIMES (sorted by wallclock times)' in line:
                get_times = False
            if get_times:
                for routine in possible_routines:
                    routine_regex = re.compile(
                        r"\d+\s*%s\s*(\d+.\d+)" % routine)
                    routine_match = routine_regex.search(line)
                    if routine_match:
                        present.append(routine)
                        cpu_time = float(routine_match.group(1))
                        times.append(cpu_time)
    missing = set(possible_routines) - set(present)
    missing = list(missing)
    if missing:
        for missing_routine in missing:
            sys.stdout.write('[INFO] IO timings running, routine %s'
                             ' unavaliable in this configuration\n' %
                             (missing_routine,))
    total_io_times = sum(times)
    return total_io_times


def get_complexity_um(model_name, runid, datam_dir, cycle_date,
                      msg, total_complexity):
    '''
    Calculate the UM complexity
    '''
    dump_name = '%sa.da%s_00' % (runid, cycle_date)
    dump_path = os.path.join(datam_dir, dump_name)

    # Get the fraction of fields within the model that are prognostic
    if _is_mule() and os.path.isfile(dump_path):
        umfile = mule.UMFile.from_file(dump_path,
                                       remove_empty_lookups=True)
        # What number of our fields are prognostics?
        prog_fields = umfile.fixed_length_header.raw[153]
        # How many levels are in the model (p_levels)
        number_p_levels = umfile.integer_constants.raw[8]
        # What is the resolution of the model?
        um_res = umfile.integer_constants.raw[6] * \
            umfile.integer_constants.raw[7] * number_p_levels
        um_complexity = float(prog_fields) / float(number_p_levels)
        msg += 'The %s complexity is %i, and total resolution %i\n' % \
            (model_name, um_complexity, um_res)
        total_complexity += um_complexity
    else:
        msg += 'Unable to calculate %s complexity and %s resolution\n' % \
            (model_name, model_name)

    return msg, total_complexity
