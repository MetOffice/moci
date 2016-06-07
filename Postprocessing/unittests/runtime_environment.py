#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''

import os

def setup_env():
    '''Set up the runtime environment required to run the postproc unittests'''

    # Standard Cylc Environment
    os.environ['CYLC_SUITE_REG_NAME'] = 'suiteID'
    os.environ['CYLC_SUITE_NAME'] = os.environ['CYLC_SUITE_REG_NAME']
    os.environ['CYLC_CYCLING_MODE'] = '360day'
    os.environ['CYLC_SUITE_SHARE_DIR'] = os.environ['PWD']
    os.environ['CYLC_TASK_WORK_DIR'] = os.environ['PWD']
    os.environ['CYLC_TASK_LOG_ROOT'] = os.environ['PWD'] + '/job'
    os.environ['CYLC_SUITE_INITIAL_CYCLE_POINT'] = '19950821T0000Z'
    os.environ['CYLC_TASK_CYCLE_POINT'] = '20000121T0000Z'

    # Standard UM Setup Environment
    os.environ['RUNID'] = 'testp'
    os.environ['DATAM'] = os.environ['CYLC_TASK_WORK_DIR']
