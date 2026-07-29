#!/usr/bin/env python
# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------
'''
NAME
    update_nemo_nl.py

DESCRIPTION
    Update the NEMO namelists. Valid for NEMO 3.6 and NEMO 4.0. The interface
    function is update_nl
'''

import shutil
import common

def do_update_nl_files(namelist_filename, variables):
    '''
    Do the replacement of the variables in the namelist file and
    return the filename of the new file
    '''
    updated_nl_file = '%s.tmp' % namelist_filename
    _ = common.remove_file(updated_nl_file)
    with common.open_text_file(updated_nl_file, 'w') as new_fh:
        with common.open_text_file(namelist_filename, 'r') as old_fh:
            for line in old_fh.readlines():
                if '=' in line:
                    varname = line.split('=')[0]
                    if varname in variables.keys():
                        newline = '%s=%s,\n' % (varname, variables[varname])
                        new_fh.write(newline)
                    else:
                        new_fh.write(line)
                else:
                    new_fh.write(line)
    return updated_nl_file

def update_si3_nl(nemo_envar):
    '''
    Update the SI3 namelist
    '''
    variables = {'cn_icerst_indir': "'%s'" % nemo_envar['RST_LINK_DIR']}
    updated_nl_filename = do_update_nl_files(nemo_envar['SI3_NL'], variables)
    shutil.move(updated_nl_filename, nemo_envar['SI3_NL'])

def update_top_nl(nemo_envar, ln_restart, restart_ctl, ln_trcdta):
    '''
    Update the Top namelist
    '''
    variables = {'ln_rsttr': ln_restart,
                 'nn_rsttr': restart_ctl,
                 'ln_trcdta': ln_trcdta,
                 'cn_trcrst_indir': "'%s'" % nemo_envar['RST_LINK_DIR']}
    updated_nl_filename = do_update_nl_files(nemo_envar['TOP_NL'], variables)
    shutil.move(updated_nl_filename, nemo_envar['TOP_NL'])


def update_nl(common_envar, nemo_envar, ln_restart, restart_ctl, nemo_next_step,
              nemo_final_step, nemo_ndate0, nleapy):
    '''
    Update the NEMO namelist
    '''
    # variables to replace for NEMO3.6 and NEMO4.0
    # The run ID needs to appear in quotes in the namelist file and takes the
    # letter 'o' as a suffix (cn_exp)
    variables = {'cn_exp': "'%so'" % common_envar['RUNID'],
                 'ln_rstart': ln_restart,
                 'nn_rstctl': restart_ctl,
                 'nn_it000': nemo_next_step,
                 'nn_itend': nemo_final_step,
                 'nn_date0': nemo_ndate0,
                 'nn_leapy': nleapy,
                 'jpni': nemo_envar['NEMO_IPROC'],
                 'jpnj': nemo_envar['NEMO_JPROC'],
                 'nn_cpl_river': common_envar['CPL_RIVER_COUNT'],
                 'cn_ocerst_indir': "'%s'" % nemo_envar['RST_LINK_DIR']}
    # add nemo3.6 only variable
    if int(nemo_envar['NEMO_VERSION']) < 400:
        variables['jpnij'] = nemo_envar['NEMO_NPROC']

    updated_nl_filename = do_update_nl_files(nemo_envar['NEMO_NL'],
                                             variables)
    shutil.move(updated_nl_filename, nemo_envar['NEMO_NL'])
