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
    nemo_def.py

DESCRIPTION
    Definition of the environment variables required for a NEMO model
    run
'''

# Variables required for both initalise and finalise
NEMO_ENVIRONMENT_VARS_COMMON = {
    'NEMO_NL': {'default_val': 'namelist_cfg'},
    'L_OCN_PASS_TRC': {'default_val': 'false'}
    }

NEMO_ENVIRONMENT_VARS_INITIAL = {
    'OCEAN_EXEC': {'desc': ('Ocean executable (OCEAN_EXEC=<full path to'
                            ' exec>)')},
    'NEMO_NPROC': {'desc': 'Number of NEMO processors'},
    'NEMO_IPROC': {'desc': 'Number of NEMO processors in the i direction'},
    'NEMO_JPROC': {'desc': 'Number of NEMO processors in the j direction'},
    'NEMO_VERSION': {},
    'OCEAN_LINK': {'default_val': 'ocean.exe'},
    'OCN_RES': {'default_val': ''},
    'NEMO_NL': {'default_val': 'namelist_cfg'},
    'NEMO_START': {'default_val': ''},
    'NEMO_ICEBERGS_START': {'default_val': ''},
    'ROSE_LAUNCHER_PREOPTS_NEMO': {'default_val': 'unset',
                                   'triggers': [
                                       [lambda my_val: my_val == 'unset',
                                        ['OCEAN_NODES', 'OMPTHR_OCN',
                                         'OHYPERTHREADS']]]},
    'OCEAN_NODES': {},
    'OMPTHR_OCN': {},
    'OHYPERTHREADS': {}
    }


NEMO_ENVIRONMENT_VARS_FINAL = {}
# Merge inital and final with common
NEMO_ENVIRONMENT_VARS_INITIAL = {**NEMO_ENVIRONMENT_VARS_COMMON,
                                 **NEMO_ENVIRONMENT_VARS_INITIAL}
NEMO_ENVIRONMENT_VARS_FINAL = {**NEMO_ENVIRONMENT_VARS_COMMON,
                               **NEMO_ENVIRONMENT_VARS_FINAL}
