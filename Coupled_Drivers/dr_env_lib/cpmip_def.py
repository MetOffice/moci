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
    cpmip_def.py

DESCRIPTION
    Definition of the environment variables required for running the CPMIP
    analysis in a coupled model run
'''

CPMIP_ENVIRONMENT_VARS_INITIAL = {
    'VN': {},
    'models': {'desc': ('A space separated list of all the components in this'
                        ' run'),
               'triggers': [[lambda my_val: 'nemo' in my_val, ['NEMO_NL']],
                            [lambda my_val: 'jnr' in my_val, ['RUNID_JNR']]]},
    'RUNID_JNR': {},
    'NEMO_NL': {'default_val': 'namelist_cfg'},
    'IO_COST': {'default_val': 'False'},
    'DATA_INTENSITY': {'default_val': 'False'},
    'PPN': {'default_val': '0'}}

CPMIP_ENVIRONMENT_VARS_FINAL = {
    'COUPLED_PLATFORM': {'default_val': 'exz'},
    'DATAM': {},
    'CYLC_TASK_CYCLE_POINT': {},
    'CYCLE': {},
    'RESUB': {},
    'models': {'desc': ('A space separated list of all the components in this'
                        ' run'),
               'triggers': [[lambda my_val: 'um' in my_val,
                             ['UM_ATM_NPROCX', 'UM_ATM_NPROCY',
                              'ROSE_LAUNCHER_PREOPTS_UM', 'STDOUT_FILE',
                              'FLUME_IOS_NPROC']],
                            [lambda my_val: 'jnr' in my_val,
                             ['RUNID_JNR', 'UM_ATM_NPROCX_JNR',
                              'UM_ATM_NPROCY_JNR', 'ROSE_LAUNCHER_PREOPTS_JNR',
                              'STDOUT_FILE_JNR', 'FLUME_IOS_NPROC_JNR']],
                            [lambda my_val: 'nemo' in my_val,
                             ['NEMO_NPROC', 'ROSE_LAUNCHER_PREOPTS_NEMO',
                              'ROSE_LAUNCHER_PREOPTS_XIOS', 'XIOS_NPROC',
                              'NEMO_NL', 'CICE_ROW', 'CICE_COL']]]},
    #UM related variables
    'UM_ATM_NPROCX': {},
    'UM_ATM_NPROCY': {},
    'ROSE_LAUNCHER_PREOPTS_UM': {},
    'STDOUT_FILE': {},
    'FLUME_IOS_NPROC': {'default_val': '0'},
    #Junior Related Variables
    'RUNID_JNR': {},
    'UM_ATM_NPROCX_JNR': {},
    'UM_ATM_NPROCY_JNR': {},
    'ROSE_LAUNCHER_PREOPTS_JNR': {},
    'STDOUT_FILE_JNR': {},
    'FLUME_IOS_NPROC_JNR': {'default_val': '0'},
    #Nemo related variables
    'NEMO_NL': {'default_val': 'namelist_cfg'},
    'NEMO_NPROC': {'desc': 'Number of NEMO processors'},
    'ROSE_LAUNCHER_PREOPTS_NEMO': {},
    'ROSE_LAUNCHER_PREOPTS_XIOS': {},
    'XIOS_NPROC': {'default_val': '0'},
    'CICE_ROW': {'default_val': '0'},
    'CICE_COL': {'default_val': '0'},
    #Metric related variables
    'time_in_launcher': {},
    'TASKLENGTH': {},
    'CYLC_TASK_LOG_ROOT': {},
    'PPN': {'default_val': '0'},
    'COMPLEXITY': {'default_val': 'False'},
    'IO_COST': {'default_val': 'False'},
    'DATA_INTENSITY': {'default_val': 'False'},
    'TOTAL_POWER_CONSUMPTION': {'default_val': ''},
    'NODES_IN_HPC': {'default_val': ''}}
