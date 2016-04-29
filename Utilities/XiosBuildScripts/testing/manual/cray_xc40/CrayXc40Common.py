#!/usr/bin/env python2.7
"""
*****************************COPYRIGHT******************************
 (C) Crown copyright Met Office. All rights reserved.
 For further details please refer to the file COPYRIGHT.txt
 which you should have received as part of this distribution.
*****************************COPYRIGHT******************************

Settings for running build scripts manual on the UKMO Cray XC40.
"""
import os
import sys

def setup_path_to_scripts():
    """
    Get the path to the scripts to be tested, which should be 3 levels up
    """

    run_script_dir_path = os.path.realpath(os.path.dirname(__file__))
    root_dir = os.path.abspath(os.path.join(run_script_dir_path,
                                            os.pardir,
                                            os.pardir,
                                            os.pardir))
    script_dir = os.path.abspath(os.path.join(root_dir,
                                              'bin'))
    lib_dir = os.path.abspath(os.path.join(root_dir,
                                           'lib'))
    sys.path += [script_dir]
    sys.path += [lib_dir]
    script_env = os.environ
    script_env['PATH'] += ':{0}'.format(script_dir)

    try:
        script_env['PYTHONPATH'] += ':{0}'.format(lib_dir)
    except KeyError:
        script_env['PYTHONPATH'] = lib_dir

    return [script_dir, lib_dir, script_env]


class CrayXc40CommonSettings(object):
    """
    Class to hold the settings common to all the manual test setup classes.
    """
    def __init__(self):
        """
        Constructor for settings container.
        """
        self.SYSTEM_NAME = 'UKMO_CRAY_XC40'

        self.DEPLOY_AS_MODULE = 'true'
        self.MODULE_INSTALL_PATH = os.getcwd() + '/modules'

        self.ROSE_SUITE_URL = 'undefined'
        self.ROSE_SUITE_REV_NO = 'undefined'

        self.XBS_PREREQ_MODULES = \
            'cray-hdf5-parallel/1.8.13,cray-netcdf-hdf5parallel/4.3.2'
