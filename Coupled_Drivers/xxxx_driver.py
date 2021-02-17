#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2019 Met Office. All rights reserved.

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

#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
import common


def _setup_executable(common_envar, run_info):
    '''
    Setup the environment and any files required by the executable
    '''
    # Load the environment variables required
    xxx_envar = common.LoadEnvar()

    return xxx_envar


def _set_launcher_command(launcher, exe_envar):
    '''
    Setup the launcher command for the executable
    '''
    rose_launcher_preopts = common.set_aprun_options(exe_envar['NPROC'], exe_envar['NODES'], exe_envar['OMPTHR'], exe_envar['HYPERTHREADS'], False) if launcher == 'aprun' else ''
    launch_cmd = '%s' % (rose_launcher_preopts)
    return launch_cmd


def _sent_coupling_fields(exe_envar, run_info):
    '''
    Add the coupling fields sent from this executable.
    This function is only used when creating the namcouple at run time.
    '''
    model_snd_list = None
    return run_info, model_snd_list


def _finalize_executable(common_envar):
    '''
    Perform any tasks required after completion of model run
    '''


def run_driver(common_envar, mode, run_info):
    '''
    Run the driver, and return an instance of common.LoadEnvar and as string
    containing the launcher command for the XIOS component
    '''
    if mode == 'run_driver':
        exe_envar = _setup_executable(common_envar, run_info)
        launch_cmd = _set_launcher_command(common_envar['ROSE_LAUNCHER'], exe_envar)
        model_snd_list = None
        if not run_info['l_namcouple']:
            run_info, model_snd_list \
                = _sent_coupling_fields(exe_envar, run_info)
    elif mode == 'finalize':
        _finalize_executable(common_envar)
        exe_envar = None
        launch_cmd = None
        model_snd_list = None
    return exe_envar, launch_cmd, run_info, model_snd_list
