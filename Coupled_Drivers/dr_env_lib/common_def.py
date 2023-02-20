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
    common_def.py

DESCRIPTION
    Definition of the environment variables required for all model runs
'''

COMMON_ENVIRONMENT_VARS_INIT_FIN = {
    'models': {'desc': ('A space separated list of all the components in this'
                        ' run'),
               'trigger': [[lambda my_val: 'cice' in my_val or 'nemo' in my_val,
                            ['CALENDAR', 'MODELBASIS', 'TASKSTART',
                             'LAST_DUMP_HOURS']],
                           [lambda my_val: 'cice' in my_val \
                            or 'nemo' in my_val or 'cpmip' in 'my_val',
                            ['TASKLENGTH']],
                           [lambda my_val: 'um' in my_val or 'nemo' in my_val,
                            ['CPL_RIVER_COUNT']]]},
    'RUNID': {},
    'DATAM': {},
    'ROSE_LAUNCHER': {},
    'CYLC_TASK_WORK_DIR': {},
    'CYLC_TASK_NAME': {},
    'CUSTOM_LAUNCH_COMMAND': {'default_val': ''},
    # the following two variables are used for Coupled NWP to allow resubmission
    # within the same cylc cycle as coupled_run1, couled_run2
    'CNWP_SUB_CYCLING': {'default_val': 'False'},
    'CYLC_TASK_PARAM_run': {'default_val': False},
    'CONTINUE': {'default_val': 'false'},
    'CONTINUE_FROM_FAIL': {'default_val': 'false'},
    # The following variable is associated with running seasonal forecasts.
    # If true, it allows us to handle the fact that multiple CRUNS are
    # run within the same cycle, thereby allowing us to fnd appropriate
    # running directories. CYLC_TASK_TRY_NUMBER will also allow us to
    # monitor the number of model attempts.
    'SEASONAL': {'default_val': 'False'},
    'CYLC_TASK_TRY_NUMBER': {},
    # if DRIVERS_VERIFY_RST 'False', then automatic restart mode disabled
    'DRIVERS_VERIFY_RST': {'default_val': 'True'},
    'HYBRID_COMPONENT': {'default_val': 'none'},
    'CYLC_CYCLING_MODE': {'default_val': 'unset',
                          'triggers': [[lambda my_val: my_val in ('360day',
                                                                  '365day',
                                                                  'gregorian'),
                                        ['CYLC_TASK_CYCLE_POINT']]]},
    'CYLC_TASK_CYCLE_POINT': {},
    # The following variables are common to the NEMO and CICE models
    'CALENDAR': {},
    'MODELBASIS': {},
    'TASKSTART': {},
    'LAST_DUMP_HOURS': {'default_val': '0'},
    # Task length is required by NEMO, CICE, and CPMIP
    'TASKLENGTH': {},
    # CPL_RIVER_COUNT is required by UM and NEMO
    'CPL_RIVER_COUNT': {'default_val': '0'}}
