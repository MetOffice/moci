# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------
'''
NAME
    nemo_lib.py

DESCRIPTION
    Library functions required for the NEMO driver
'''
import datetime
import os
import sys

import common
import dr_env_lib.env_lib
import dr_env_lib.nemo_def
import dr_env_lib.ocn_cont_def
import error
import inc_days
import ocn_lib

#
# SECTION ONE:
#
#   Section one contains functions that can be called directly from other
#   modules
#

def read_current_cycle_nl(common_env, nemo_envar):
    '''
    Read the current cycle namelist for each item in turn, NEMO, SI3 and TOP
    '''
    nemo_rst, ln_icebergs, ice_rst, top_rst = None, None, None, None
    if 'nemo' in common_env['models']:
        nemo_rst, ln_icebergs = _read_current_cycle_nl_nemo(
            nemo_envar['NEMO_NL'])
    if 'si3' in common_env['models']:
        ice_rst = _read_current_cycle_nl_si3(nemo_envar['SI3_NL'])
    if 'top' in common_env['models']:
        top_rst = _read_current_cycle_nl_top(nemo_envar['TOP_NL'])
    return nemo_rst, ln_icebergs, ice_rst, top_rst



def setup_dates(common_env):
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

def read_history_nl(history_nemo_nl):
    '''
    Read and process the desired variables from the history nemo namelist
    '''
    namelist = ocn_lib.ReadOcnNamelist(history_nemo_nl)
    nemo_first_step, nemo_last_step, nemo_step_int, nemo_rst_date \
        = namelist.read_variables(
            'nemo_first_step', 'nemo_last_step', 'nemo_step_int',
            'nemo_rst_date')
    return (int(nemo_first_step), _check_nemo_last_step(nemo_last_step),
            int(nemo_step_int), string_to_boolean(nemo_rst_date))

def load_environment_variables(mode, models):
    '''
    Load the environment variables for NEMO and SI3 into a single
    container
    '''
    nemo_envar = dr_env_lib.env_lib.LoadEnvar()
    # The functions to check the namelists for each model
    checks = {'nemo': _check_nemonl,
              'si3': _check_si3nl,
              'top': _check_topnl}
    if mode == 'setup':
        defs = {
            'nemo': dr_env_lib.nemo_def.NEMO_ENVIRONMENT_VARS_INITIAL,
            'si3': dr_env_lib.ocn_cont_def.SI3_ENVIRONMENT_VARS_INITIAL,
            'top': dr_env_lib.ocn_cont_def.TOP_ENVIRONMENT_VARS_INITIAL}
    elif mode == 'final':
        defs = {
            'nemo': dr_env_lib.nemo_def.NEMO_ENVIRONMENT_VARS_FINAL,
            'si3': dr_env_lib.ocn_cont_def.SI3_ENVIRONMENT_VARS_FINAL,
            'top': dr_env_lib.ocn_cont_def.TOP_ENVIRONMENT_VARS_FINAL}
    for imodel in models.split(' '):
        if imodel in defs.keys():
            nemo_envar = dr_env_lib.env_lib.load_envar_from_definition(
                nemo_envar, defs[imodel])
            checks[imodel](nemo_envar)
    # TOP is controlled by the environment variable 'L_OCN_PASS_TRC' rather
    # than in the models list, we must add the environment variables
    if 't' in nemo_envar['L_OCN_PASS_TRC'].lower():
        models = models + ' top'
        nemo_envar = dr_env_lib.env_lib.load_envar_from_definition(
            nemo_envar, defs['top'])
        checks['top'](nemo_envar)
    return nemo_envar, models

def string_to_boolean(nemo_rst_date):
    '''
    If a string contains a string containg upper or lower case true
    (or some permeatation thereof), return python boolean True. Otherwise
    return False
    '''
    if 'true' in nemo_rst_date.lower():
        return True
    return False


def setup_nemo_runlen(common_env, run_start, model_basis, nemo_step_int,
                      run_days, run_length, nemo_next_step, nemo_last_step):
    '''
    Setup the nemo runlength for coupled NWP models with subcycle restarts
    '''
    if common_env['CONTINUE_FROM_FAIL'] == 'true':
        # Check the length of the run is correct
        # (it won't be if this is the wrong restart file)
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
            sys.stderr.write('[FAIL] Last NEMO restarts not at correct time\n'
                             ' Last completed timestep %d\n'
                             ' Expected next step %d\n'
                             ' Actual next step %d\n'
                             % (last_dump_step, last_dump_step+1,
                                nemo_next_step))
            sys.exit(error.RESTART_FILE_ERROR)
    else:
        tot_runlen_sec = run_days * 86400 + run_length[3]*3600 \
            + run_length[4]*60 + run_length[5]
        nemo_final_step = (tot_runlen_sec // nemo_step_int) + nemo_last_step
    return nemo_final_step


#
# SECTION TWO:
#
#   Section two contains functions that are private to this module
#

def _check_nemo_last_step(nemo_last_step):
    '''
    The string in the nemo time step field might have any one of
    a number of variants. e.g. "set_by_rose", "set_by_system",
    "set_by_um", etc. Hence we just check for the presence of
    purely numeric characters to see if we start from zero or not.
    '''
    if nemo_last_step.isdigit():
        return int(nemo_last_step)
    return 0

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

def _check_si3nl(envar_container):
    '''
    Check the si3 namelist file exists as information will be retrieved from
    this file during the running of the driver
    '''
    if not os.path.isfile(envar_container['SI3_NL']):
        sys.stderr.write('[FAIL] Can not find the SI3 namelist '
                         'file %s\n' % envar_container['SI3_NL'])
        sys.exit(error.MISSING_DRIVER_FILE_ERROR)

def _check_topnl(envar_container):
    '''
    Check the TOP namelist file exists as information will be retrieved from
    this file during the running of the driver'''
    if not os.path.isfile(envar_container['TOP_NL']):
        sys.stderr.write('[FAIL] Can not find the TOP namelist '
                         'file %s\n' % envar_container['TOP_NL'])
        sys.exit(error.MISSING_DRIVER_FILE_ERROR)


def _read_current_cycle_nl_nemo(namelist_path):
    '''
    Read the variables required from the current cycle namelist and
    modify as required for NEMO
    '''
    current_nl = ocn_lib.ReadOcnNamelist(namelist_path)
    nemo_rst, ln_icebergs = current_nl.read_variables(
        'nemo_rst', 'ln_icebergs')
    if nemo_rst:
        nemo_rst = common.remove_trailing_slash(nemo_rst)
    return nemo_rst, string_to_boolean(ln_icebergs)

def _read_current_cycle_nl_si3(namelist_path):
    '''
    Read the variables required from the current cycle namelist and
    modify as required for SI3
    '''
    current_nl = ocn_lib.ReadOcnNamelist(namelist_path)
    ice_rst = current_nl.read_variables('ice_rst')
    if ice_rst:
        ice_rst = common.remove_trailing_slash(ice_rst)
    sys.stdout.write('[INFO] NEMO running with SI3 submodel\n')
    return ice_rst

def _read_current_cycle_nl_top(namelist_path):
    '''
    Read the variables required from the current cycle namelist and
    modify as required for TOP
    '''
    current_nl = ocn_lib.ReadOcnNamelist(namelist_path)
    top_rst = current_nl.read_variables('top_rst')
    if top_rst:
        top_rst = common.remove_trailing_slash(top_rst)
    sys.stdout.write('[INFO] NEMO running with TOP submodel\n')
    return top_rst
