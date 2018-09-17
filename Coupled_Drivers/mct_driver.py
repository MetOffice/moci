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
    mct_driver.py

DESCRIPTION
    Driver for OASIS3-MCT
'''

#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
import os
import sys
import glob
import common
import error
import update_namcouple

import cpmip_controller


def _multiglob(*args):
    '''
    Takes in a list of globbable strings, and returns a single list of
    filenames matching those strings
    '''
    filenames = []
    for arg in args:
        filenames += glob.glob(arg)
    return filenames

def _setup_nemo_cpld(common_envar, mct_envar):
    '''
    Setup NEMO for coupled configurations
    '''
    nemo_cpld_envar = common.LoadEnvar()
    _ = nemo_cpld_envar.load_envar('OCEAN_LINK', 'ocean.exe')
    nemo_debug_files = glob.glob('*%s*.nc' % nemo_cpld_envar['OCEAN_LINK'])
    for nemo_debug_file in nemo_debug_files:
        common.remove_file(nemo_debug_file)


def _setup_um_cpld(common_envar, mct_envar):
    '''
    Setup UM for coupled configurations
    '''
    # Remove potential UM debug netcdf files. If this isn't done MCT will
    # just append details to existing files
    um_cpld_envar = common.LoadEnvar()
    _ = um_cpld_envar.load_envar('ATMOS_LINK', 'atmos.exe')
    um_debug_files = glob.glob('*%s*.nc' % um_cpld_envar['ATMOS_LINK'])
    for um_debug_file in um_debug_files:
        common.remove_file(um_debug_file)



def _setup_executable(common_envar):
    '''
    Setup the environment and any files required by the executable
    '''
    # Load the environment variables required
    mct_envar = common.LoadEnvar()

    if mct_envar.load_envar('COUPLING_COMPONENTS') != 0:
        sys.stderr.write('[FAIL] Environment variable COUPLING_COMPONENTS'
                         ' containing a list of components to be coupled is'
                         ' not set, however the MCT driver has been run\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    if mct_envar.load_envar('RMP_DIR') != 0:
        sys.stderr.write('[FAIL] Environment variable RMP_DIR containing'
                         ' remapping weights files not defined in the'
                         ' environment\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    _ = mct_envar.load_envar('CPMIP_ANALYSIS', 'False')

    # Does the namcouple file exist
    if not os.path.exists('namcouple'):
        sys.stderr.write('[FAIL] Could not find a namcouple file in the'
                         ' working directory. This file should originate'
                         ' in the Rose app\'s file directory\n')
        sys.exit(error.MISSING_MODEL_FILE_ERROR)

    # Tidyup our OASIS files before the setup process is started
    files_to_tidy = _multiglob('nout.*', 'debug.*root.*', 'debug.??.*',
                               'debug.???.*', '*fort*', 'rmp_*')
    for f_to_tidy in files_to_tidy:
        common.remove_file(f_to_tidy)

    # Organise the remapping files
    remap_files = glob.glob('%s/rmp_*' % mct_envar['RMP_DIR'])
    for remap_file in remap_files:
        linkname = os.path.split(remap_file)[-1]
        os.symlink(remap_file, linkname)

    # Create transient field namelist
    _, _ = common.exec_subproc('./OASIS_fields')


    for component in mct_envar['COUPLING_COMPONENTS'].split():
        if not component in common_envar['models']:
            sys.stderr.write('[FAIL] Attempting to couple component %s,'
                             ' however this component is not being run in'
                             ' this configuration\n' % component)
            sys.exit(999)
        if not component in list(SUPPORTED_MODELS.keys()):
            sys.stderr.write('[FAIL] The component %s is not supported by the'
                             ' mct driver\n' % component)
            sys.exit(999)
        # Setup coupling for individual component
        sys.stdout.write('[INFO] MCT driver setting up %s component\n' %
                         component)
        SUPPORTED_MODELS[component](common_envar, mct_envar)

    # Update the general, non-component specific namcouple details 
    update_namcouple.update('mct')

    # Run the CPMIP controller if appropriate
    # Check for the presence of t (as in TRUE, True, or true) in the
    # CPMIP_ANALYSIS value
    if mct_envar['CPMIP_ANALYSIS'].lower().startswith('t'):
        controller_mode = "run_controller"
        sys.stdout.write('[INFO] mct_driver: CPMIP analyis will be performed\n')
        cpmip_controller.run_controller(controller_mode, common_envar)

    return mct_envar


def _set_launcher_command(_):
    '''
    Setup the launcher command for the executable. MCT does not require a
    call to the launcher as it runs as a library
    '''
    launch_cmd = ''
    return launch_cmd


def _finalize_executable(common_envar):
    '''
    Perform any tasks required after completion of model run
    '''
    # Load the environment variables required
    mct_envar = common.LoadEnvar()
    _ = mct_envar.load_envar('CPMIP_ANALYSIS', 'False')
    # run the cpmip controller if appropriate
    # check for the presence of t (as in TRUE, True, or true) in the
    # CPMIP_ANALYSIS value
    if mct_envar['CPMIP_ANALYSIS'].lower().startswith('t'):
        controller_mode = "finalize"
        sys.stdout.write(
            '[INFO] mct_driver: CPMIP analyis is being performed\n')
        cpmip_controller.run_controller(controller_mode, common_envar)


def run_driver(common_envar, mode):
    '''
    Run the driver, and return an instance of common.LoadEnvar and as string
    containing the launcher command for the MCT component
    '''
    if mode == 'run_driver':
        exe_envar = _setup_executable(common_envar)
        launch_cmd = _set_launcher_command(exe_envar)
    elif mode == 'finalize':
        _finalize_executable(common_envar)
        exe_envar = None
        launch_cmd = None
    return exe_envar, launch_cmd


# Dictionary containing the supported models and their assosicated setup
# function within the driver
SUPPORTED_MODELS = {'nemo': _setup_nemo_cpld,
                    'um': _setup_um_cpld}
