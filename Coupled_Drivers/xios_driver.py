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
    xios_driver.py

DESCRIPTION
    Driver for the XIOS component. Can cater for XIOS running in either
    attatched or detatched mode
'''


import error
import common
import os
import sys

def _setup_executable(_):
    '''
    Setup the environment and any files required by the executable
    '''
    # Load the environment variables required
    xios_envar = common.LoadEnvar()
    _ = xios_envar.load_envar('XIOS_EXEC', 'unset')
    _ = xios_envar.load_envar('XIOS_LINK', 'xios.exe')
    _ = xios_envar.load_envar('XIOS_NPROC', 'unset')

    if xios_envar['XIOS_NPROC'] not in ('0', 'unset'):
        if xios_envar.load_envar('ROSE_LAUNCHER_PREOPTS_XIOS') != 0:
            sys.stderr.write('[FAIL] Environment variable '
                             'ROSE_LAUNCHER_PREOPTS_XIOS not set\n')
            sys.exit(error.MISSING_EVAR_ERROR)

    if xios_envar['XIOS_EXEC'] != 'unset':
        if os.path.isfile(xios_envar['XIOS_LINK']):
            os.remove(xios_envar['XIOS_LINK'])
        os.symlink(xios_envar['XIOS_EXEC'],
                   xios_envar['XIOS_LINK'])

    return xios_envar

def _set_launcher_command(xios_envar):
    '''
    Setup the launcher command for the executable, bearing in mind that XIOS
    can run attachted. If this is so, this function will return an empty
    string
    '''
    if xios_envar['XIOS_NPROC'] not in ('0', 'unset'):
        launch_cmd = '%s ./%s' % \
            (xios_envar['ROSE_LAUNCHER_PREOPTS_XIOS'], \
                 xios_envar['XIOS_LINK'])
    else:
        launch_cmd = ''

    # Put in quotes to allow this environment variable to be exported as it
    # contains (or can contain) spaces
    xios_envar['ROSE_LAUNCHER_PREOPTS_XIOS'] = "'%s'" % \
        xios_envar['ROSE_LAUNCHER_PREOPTS_XIOS']

    return launch_cmd

def _finalize_executable(_):
    '''
    There is no finalization required for XIOS
    '''
    pass


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
