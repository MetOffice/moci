#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2023-2026 Met Office. All rights reserved.

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



import os
import shutil
import common
import dr_env_lib.xios_def
import dr_env_lib.env_lib

def _copy_iodef_custom(xios_evar):
    '''
    If a custom iodef file exists, copy this to the required input filename
    '''
    if xios_evar['IODEF_CUSTOM']:
        shutil.copy(xios_evar['IODEF_CUSTOM'], xios_evar['IODEF_FILENAME'])

def _update_iodef(
        is_server_mode, is_coupled_mode, oasis_components, iodef_fname):
    '''
    Update the iodef.xml file for server/attatched mode and couplng mode.
    is_server_mode and is_coupled_mode are boolean. (true when each option
    is activated, false otherwise).
    '''

    # Work-around in lieu of viable multi component iodef.xml handling
    _, _ = common.exec_subproc(['cp', 'mydef.xml', iodef_fname])

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
        # Update the list of coupled components
        elif '<!' not in line and 'oasis_codes_id' in line:
            if oasis_components.strip():
                line = '<variable id="oasis_codes_id"   type="string" >' \
                   + oasis_components+'</variable>'
            else:
                line =  '<!-- oasis_codes_id not required -->'

        iodef_swap.write(line)

    iodef_file.close()
    iodef_swap.close()
    os.rename(swapfile_name, iodef_fname)


def _setup_coupling_components(xios_envar):
    '''
    Set up the coupling components for the iodef file. This is less
    straightforward than you might imagine, since the names of the componenets
    are hard coded in the component source code. Nemo becomes toyoce and
    lfric is lfric. These become a comma separated string.
    We use the COUPLING_COMPONENTS environment variable to determine this,
    however it is borrowed from MCT, do we must delete it from the xios_envar
    container after use
    '''
    oasis_components = []
    if 'lfric' in xios_envar['COUPLING_COMPONENTS']:
        oasis_components.append('lfric')
    if 'nemo' in xios_envar['COUPLING_COMPONENTS']:
        oasis_components.append('toyoce')
    xios_envar.remove('COUPLING_COMPONENTS')
    oasis_components = ','.join(oasis_components)
    return oasis_components, xios_envar


def _setup_executable(common_env):
    '''
    Setup the environment and any files required by the executable and/or
    by the iodef file update procedure.
    '''
    # Load the environment variables required
    xios_envar = dr_env_lib.env_lib.LoadEnvar()
    xios_envar = dr_env_lib.env_lib.load_envar_from_definition(
        xios_envar, dr_env_lib.xios_def.XIOS_ENVIRONMENT_VARS_INITIAL)

    if xios_envar['XIOS_NPROC'] == '0':
        # Running in attached mode
        using_server = False
    else:
        # Running in server (detached) mode
        # The following environment variables are only relevant for this
        # mode
        using_server = True
        common.remove_file(xios_envar['XIOS_LINK'])
        os.symlink(xios_envar['XIOS_EXEC'],
                   xios_envar['XIOS_LINK'])

    # Check our list of component drivers to see if MCT is active. If it is,
    # then this is a coupled model. Set the coupler flag accordingly.
    using_coupler = 'mct' in common_env['models']

    # Copy the custom IO file if required
    _copy_iodef_custom(xios_envar)

    # Get the list of coupled componenets
    oasis_components, xios_envar = _setup_coupling_components(xios_envar)
    # Update the iodef file
    _update_iodef(using_server, using_coupler, oasis_components,
                  xios_envar['IODEF_FILENAME'])

    return xios_envar


def _set_launcher_command(launcher, xios_envar):
    '''
    Setup the launcher command for the executable, bearing in mind that XIOS
    can run attached. If this is so, this function will return an empty
    string
    '''
    if xios_envar['XIOS_NPROC'] != '0':
        if xios_envar['ROSE_LAUNCHER_PREOPTS_XIOS'] == 'unset':
            ompthr = 1
            hyperthreads = 1
            ss = True
            xios_envar['ROSE_LAUNCHER_PREOPTS_XIOS'] = \
                common.set_aprun_options(xios_envar['XIOS_NPROC'], \
                    xios_envar['XIOS_NODES'], ompthr, \
                        hyperthreads, ss) \
                            if launcher == 'aprun' else ''

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

def _sent_coupling_fields(run_info):
    '''
    Add XIOS executable to list of executables.
    This function is only used when creating the namcouple at run time.
    '''

    # Add xios to our list of executables
    if not 'exec_list' in run_info:
        run_info['exec_list'] = []
    run_info['exec_list'].append('xios.x')

    return run_info

def _finalize_executable(_):
    '''
    There is no finalization required for XIOS
    '''
    pass


def run_driver(common_env, mode, run_info):
    '''
    Run the driver, and return an instance of LoadEnvar and as string
    containing the launcher command for the XIOS component
    '''
    if mode == 'run_driver':
        exe_envar = _setup_executable(common_env)
        launch_cmd = _set_launcher_command(common_env['ROSE_LAUNCHER'],
                                           exe_envar)
        model_snd_list = None
        if not run_info['l_namcouple']:
            run_info = _sent_coupling_fields(run_info)
    elif mode == 'finalize':
        _finalize_executable(common_env)
        exe_envar = None
        launch_cmd = None
        model_snd_list = None
    return exe_envar, launch_cmd, run_info, model_snd_list
