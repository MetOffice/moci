#!/usr/bin/env python
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
    Driver for the XIOS component, called from link_drivers. Can cater for
    XIOS running in either attatched or detatched mode
'''

#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
import os
import sys
import error
import common

def _update_iodef(is_server_mode, is_coupled_mode, iodef_fname='iodef.xml'):
    '''
    Update the iodef.xml file for server/attatched mode and couplng mode.
    is_server_mode and is_coupled_mode are boolean. (true when each option
    is activated, false otherwise).
    iodef_fname is a string containing the filename for the iodef file, which
    defaults to 'iodef.xml'
    '''
    # Note we do not use python's xml module for this job, as the comment
    # line prevalent in the first line of the GO5 iodef.xml files renders
    # the file invalid as far as the xml module is concerned.
    swapfile_name = 'swap_iodef'
    iodef_file = common.open_text_file(iodef_fname, 'r')
    iodef_swap = common.open_text_file(swapfile_name, 'w')
    text_bool = ['false', 'true']
    for line in iodef_file.readlines():
        # Update the server_mode if the current setting is not what we want
        if '<!' not in line and 'using_server' in line:
            line = line.replace(text_bool[not is_server_mode], \
                                text_bool[is_server_mode])
        # Update the coupled mode if the current setting is not what we want
        elif '<!' not in line and 'using_oasis' in line:
            line = line.replace(text_bool[not is_coupled_mode], \
                                text_bool[is_coupled_mode])

        iodef_swap.write(line)

    iodef_file.close()
    iodef_swap.close()
    os.rename(swapfile_name, iodef_fname)

def _setup_executable(_):
    '''
    Setup the environment and any files required by the executable and/or
    by the iodef file update procedure.
    '''
    # Load the environment variables required
    xios_envar = common.LoadEnvar()
    if xios_envar.load_envar('XIOS_NPROC') != 0:
        sys.stderr.write('[FAIL] Environment variable XIOS_NPROC not set '
                         'Set to 0 to run xios in attatched mode, and to '
                         'a number greater than 0 for server mode\n')
        sys.exit(error.MISSING_EVAR_ERROR)

    if xios_envar['XIOS_NPROC'] == '0':
        # Running in attached mode
        using_server = False
    else:
        # Running in server (detatched) mode
        # The following environment variables are only relevant for this
        # mode
        using_server = True
        _ = xios_envar.load_envar('XIOS_LINK', 'xios.exe')
        if xios_envar.load_envar('ROSE_LAUNCHER_PREOPTS_XIOS') != 0:
            sys.stderr.write('[FAIL] Environment variable '
                             'ROSE_LAUNCHER_PREOPTS_XIOS not set\n')
            sys.exit(error.MISSING_EVAR_ERROR)
        if xios_envar.load_envar('XIOS_EXEC') != 0:
            sys.stderr.write('[FAIL] Environment variable XIOS_EXEC '
                             'not set\n')
            sys.exit(error.MISSING_EVAR_ERROR)
        common.remove_file(xios_envar['XIOS_LINK'])
        os.symlink(xios_envar['XIOS_EXEC'],
                   xios_envar['XIOS_LINK'])

    # Check our list of component drivers to see if MCT is active. If it is,
    # then this is a coupled model. Set the coupler flag accordingly.
    _ = xios_envar.load_envar('models')
    using_coupler = 'mct' in xios_envar['models']

    # Update the iodef file
    _update_iodef(using_server, using_coupler)

    return xios_envar


def _set_launcher_command(xios_envar):
    '''
    Setup the launcher command for the executable, bearing in mind that XIOS
    can run attached. If this is so, this function will return an empty
    string
    '''

    if xios_envar['XIOS_NPROC'] != '0':
        launch_cmd = '%s ./%s' % \
            (xios_envar['ROSE_LAUNCHER_PREOPTS_XIOS'], \
                 xios_envar['XIOS_LINK'])
        # Put in quotes to allow this environment variable to be exported as it
        # contains (or can contain) spaces
        xios_envar['ROSE_LAUNCHER_PREOPTS_XIOS'] = "'%s'" % \
            xios_envar['ROSE_LAUNCHER_PREOPTS_XIOS']
    else:
        launch_cmd = ''

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
