#!/usr/bin/env python2.7
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
    xxxx_driver.py

DESCRIPTION
    Template driver code
'''

import common


def _setup_executable(common_envar):
    '''
    Setup the environment and any files required by the executable
    '''
    # Load the environment variables required
    xxx_envar = common.LoadEnvar()

    return xxx_envar


def _set_launcher_command(xxxx_envar):
    '''
    Setup the launcher command for the executable
    '''
    launch_cmd = ''
    return launch_cmd


def _finalize_executable(common_envar):
    '''
    Perform any tasks required after completion of model run
    '''


def run_driver(common_envar, mode):
    '''
    Run the driver, and return an instance of common.LoadEnvar and as string
    containing the launcher command for the XIOS component
    '''
    if mode == 'run_driver':
        exe_envar = _setup_executable(common_envar)
        launch_cmd = _set_launcher_command(exe_envar)
    elif mode == 'finalize':
        _finalize_executable(common_envar)
        exe_envar = None
        launch_cmd = None
    return exe_envar, launch_cmd
