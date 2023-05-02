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
    jnr_def.py

DESCRIPTION
    Definition of the environment variables required for a Junior UM model
    run
'''
JNR_ENVIRONMENT_VARS_COMMON = {
    'ATMOS_STDOUT_FILE_JNR': {
        'default_val': 'pe_output_jnr/junio.fort6.pe'}}

JNR_ENVIRONMENT_VARS_INITIAL = {
    'UM_ATM_NPROCX_JNR': {},
    'UM_ATM_NPROCY_JNR': {},
    'ATMOS_EXEC_JNR': {},
    'ATMOS_LINK_JNR': {'default_val': 'atmos-jnr.exe'},
    'RUNID_JNR': {'default_val': 'junior'},
    'HISTORY_JNR': {'default_val': 'junio.xhist'},
    'FLUME_IOS_NPROC_JNR': {'default_val': '0'},
    'OCN_RES_ATM': {'default_val': ''},
    'ROSE_LAUNCHER_PREOPTS_JNR': {'default_val': 'unset',
                                  'triggers': [
                                      [lambda my_val: my_val == 'unset',
                                       ['JNR_NODES', 'OMPTHR_JNR',
                                        'HYPERTHREADS']]]},
    'JNR_NODES': {},
    'OMPTHR_JNR': {},
    'HYPERTHREADS': {}}
JNR_ENVIRONMENT_VARS_FINAL = {
    'NPROC_JNR': {},
    'STDOUT_FILE_JNR': {'desc': 'Path to the Jnr UM standard out file'},
    'ATMOS_KEEP_MPP_STDOUT': {'default_val': 'false'}}

JNR_ENVIRONMENT_VARS_INITIAL = {**JNR_ENVIRONMENT_VARS_COMMON,
                                **JNR_ENVIRONMENT_VARS_INITIAL}
JNR_ENVIRONMENT_VARS_FINAL = {**JNR_ENVIRONMENT_VARS_COMMON,
                              **JNR_ENVIRONMENT_VARS_FINAL}
