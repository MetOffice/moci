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
    nemo_runtime_namcouple.py

DESCRIPTION
    Library of function required for the creation of the NEMO namcouple
    components at runtime
'''
import os
import sys
import write_namcouple
import error
try:
    import f90nml
except ImportError:
    pass

def get_ocean_resol(nemo_nl_file, run_info):
    '''
    Determine the ocean resolution.
    This function is only used when creating the namcouple at run time.
    '''

    # Read in the resolution of ocean (existent of namelist_cfg has
    # already been checked)
    ocean_nml = f90nml.read(nemo_nl_file)

    # Check the required entries exist
    if 'namcfg' not in ocean_nml:
        sys.stderr.write('[FAIL] namcfg not found in namelist_cfg\n')
        sys.exit(error.MISSING_OCN_RESOL_NML)
    if 'jpiglo' not in ocean_nml['namcfg'] or \
       'jpjglo' not in ocean_nml['namcfg'] or \
       'cp_cfg' not in ocean_nml['namcfg'] or \
       'jp_cfg' not in ocean_nml['namcfg']:
        sys.stderr.write('[FAIL] cp_cfg, jp_cfg, jpiglo or jpjglo are '
                         'missing from namelist namcf in namelist_cfg\n')
        sys.exit(error.MISSING_OCN_RESOL)

    # Check it is on orca grid
    if ocean_nml['namcfg']['cp_cfg'] != 'orca':
        sys.stderr.write('[FAIL] we can currently only handle the '
                         'ORCA grid\n')
        sys.exit(error.NOT_ORCA_GRID)

    # Check this is a grid we recognise
    if ocean_nml['namcfg']['jp_cfg'] == 25:
        run_info['OCN_grid'] = 'orca025'
    else:
        run_info['OCN_grid'] = 'orca' + str(ocean_nml['namcfg']['jp_cfg'])

    # Store the ocean resolution
    run_info['OCN_resol'] = [ocean_nml['namcfg']['jpiglo'],
                             ocean_nml['namcfg']['jpjglo']]

    return run_info

def sent_coupling_fields(nemo_envar, run_info):
    '''
    Write the coupling fields sent from NEMO into model_snd_list.
    This function is only used when creating the namcouple at run time.
    '''
    # Check that file specifying the coupling fields sent from
    # NEMO is present
    if not os.path.exists('OASIS_OCN_SEND'):
        sys.stderr.write('[FAIL] OASIS_OCN_SEND is missing.\n')
        sys.exit(error.MISSING_OASIS_OCN_SEND)

    # Add toyatm to our list of executables
    if not 'exec_list' in run_info:
        run_info['exec_list'] = []
    run_info['exec_list'].append('toyoce')

    # Determine the ocean resolution
    run_info = get_ocean_resol(nemo_envar['NEMO_NL'], run_info)

    # If using the default coupling option, we'll need to read the
    # NEMO namelist later
    run_info['nemo_nl'] = nemo_envar['NEMO_NL']

    # Read the namelist
    oasis_nml = f90nml.read('OASIS_OCN_SEND')

    # Check we have the expected information
    if 'oasis_ocn_send_nml' not in oasis_nml:
        sys.stderr.write('[FAIL] namelist oasis_ocn_send_nml is '
                         'missing from OASIS_OCN_SEND.\n')
        sys.exit(error.MISSING_OASIS_OCN_SEND_NML)
    if 'oasis_ocn_send' not in oasis_nml['oasis_ocn_send_nml']:
        sys.stderr.write('[FAIL] entry oasis_ocn_send is missing '
                         'from namelist oasis_ocn_send_nml in '
                         'OASIS_OCN_SEND.\n')
        sys.exit(error.MISSING_OASIS_OCN_SEND)

    # Create a list of fields sent from OCN
    model_snd_list = \
        write_namcouple.add_to_cpl_list( \
        'OCN', False, 0,
        oasis_nml['oasis_ocn_send_nml']['oasis_ocn_send'])

    return run_info, model_snd_list
