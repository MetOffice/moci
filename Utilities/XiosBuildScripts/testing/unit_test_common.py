#!/usr/bin/env python2.7
"""
 *****************************COPYRIGHT******************************
 (C) Crown copyright Met Office. All rights reserved.
 For further details please refer to the file COPYRIGHT.txt
 which you should have received as part of this distribution.
 *****************************COPYRIGHT******************************

 CODE OWNER
   Stephen Haddad

 NAME
   unit_test_common.py

 DESCRIPTION
    Provides functionality common to all the unit test classes.

"""
import os
import sys
import ConfigParser
import shutil
import unittest
import datetime
import string
import argparse

COMMON_CONF_FILENAME = 'common.conf'
SCRATCH_DIR_NAME = 'scratch_XBStest_'

# find parent directory directory containing this file so that source code
# can be imported

SCRIPT_DIR = os.path.abspath(os.path.join(os.path.realpath(__file__),
                                          os.pardir,
                                          os.pardir))
sys.path += [SCRIPT_DIR]

LIB_DIR = os.path.abspath(os.path.join(SCRIPT_DIR,
                                       'lib'))
sys.path += [LIB_DIR]

import common
import OasisBuildSystem

SYSTEM_NAME_MONSOON = 'Monsoon'
SYSTEM_NAME_EXTERNAL = 'external'

SYSTEM_NAME_OPTIONS = [OasisBuildSystem.OasisCrayBuildSystem.SYSTEM_NAME,
                       SYSTEM_NAME_MONSOON,
                       SYSTEM_NAME_EXTERNAL]

class CommandLineArguments(object):
    """
    Class to read the command line arguments for the unit test app.
    """
    def __init__(self):
        """
        """
        desc_msg = '''Run the XIOS/Oasis3-mct build script unit tests on the
specified platform

The platform is set using the --system-name command line argument.
The options are:
'''
        for name1 in SYSTEM_NAME_OPTIONS:
            desc_msg += '* {0}\n'.format(name1)

        desc_msg += '''

If you would like to retain the output from the unit tests, use the
--keep-output command line flag, and the temporary directory will
not be deleted.

Note that the command line options take precedence over the environment variables.
'''
        self.parser = argparse.ArgumentParser(description=desc_msg)

        help_msg = 'The name of the platform'
        self.parser.add_argument('--system-name',
                                 dest='system_name',
                                 help=help_msg,
                                 default=common.SYSTEM_NAME_EXTERNAL,
                                 choices=SYSTEM_NAME_OPTIONS)

        help_msg = 'working directory to use for temporary files'
        self.parser.add_argument('--working-dir',
                                 dest='working_dir',
                                 help=help_msg,
                                 default=os.getcwd())

        help_msg = 'If present the output directory will not be deleted.'
        self.parser.add_argument('--keep-output',
                                 help=help_msg,
                                 action='store_true',
                                 dest='keep_output')

        cmd_args = self.parser.parse_args()

        self.system_name = cmd_args.system_name
        self.working_dir = cmd_args.working_dir
        self.keep_output = cmd_args.keep_output


def run_tests(test_list_dict):
    """
    Top level function to run unit tests
    """
    cmd_args = CommandLineArguments()

    test_list = test_list_dict[cmd_args.system_name]


    # setting up working directory. A directory can be passed in as argument
    # or the default of the current directory will be used. The actual files
    # will be put in a subdirectory of the current or input directory
    date_time_str = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    working_dir = os.path.join(cmd_args.working_dir,
                               SCRATCH_DIR_NAME + '_' + date_time_str)
    print('working directory: {testDir}'.format(testDir=working_dir))
    if not (os.path.exists(working_dir) and os.path.isdir(working_dir)):
        print('creating working directory')
        os.mkdir(working_dir)
        if os.path.isdir(working_dir):
            print('working directory created')
    os.chdir(working_dir)
    print 'test files will be created in {testDir}'.format(testDir=os.getcwd())

    module_suites = []
    for test_class in test_list:
        module_suites += [
            unittest.TestLoader().loadTestsFromTestCase(test_class)]
    suites_to_run = unittest.TestSuite(module_suites)

    test_results = unittest.TextTestRunner(verbosity=2).run(suites_to_run)

    if not cmd_args.keep_output:
        #delete temporary test directory
        print 'tests complete, removing temp directory'
        shutil.rmtree(working_dir)

    if len(test_results.errors) > 0 or len(test_results.failures) > 0:
        exit(1)



def get_settings(config_list, settings_dir, system_name):
    """
    Get the settings for running the unit tests. If we are in a rose suite
    we will use the settings provided. If not in a rose suite, we can use
    the settings provided in .conf files in the local copy.
    """
    if os.environ.has_key('ROSE_SUITE_NAME'):
        settings_dict = os.environ
    else:
        settings_dict = get_settings_from_conf(config_list,
                                               settings_dir,
                                               system_name)
    return settings_dict


def get_settings_from_conf(config_list, settings_dir, system_name):
    """
    Get the settings for running unit tests from .conf files stored
    in $MOCI_ROOT/Utilities/XiosBuildScripts/testing/settings
    """
    settings_dict = {}

    path_common = os.path.join(settings_dir,
                               COMMON_CONF_FILENAME)

    settings_common = read_settings(path_common)
    settings_dict.update(settings_common['common'])
    for config1 in config_list:
        settings_dict.update(settings_common[config1])

    path_platform = os.path.join(settings_dir,
                                 system_name + '.conf')
    settings_platform = read_settings(path_platform)
    settings_dict.update(settings_platform['common'])
    for config1 in config_list:
        settings_dict.update(settings_platform[config1])

    settings_dict['WORKING_DIR'] = os.getcwd()

    for key1, value1 in settings_dict.iteritems():
        settings_dict[key1] = string.Template(value1).substitute(settings_dict)

    return settings_dict

def get_settings_dir():
    """
    Find the location of the settings directory
    """
    unit_test_dir = os.path.realpath(os.path.dirname(__file__))
    root_dir = os.path.abspath(os.path.join(unit_test_dir,
                                            os.pardir))
    settings_dir = os.path.join(root_dir, 'testing', 'settings')
    return settings_dir

def read_settings(config_filename):
    """
    Read the settings from a config file.
    """
    parser1 = ConfigParser.RawConfigParser()
    parser1.optionxform = str
    parser1.read(config_filename)

    settings_dict = {}
    for section1  in parser1.sections():
        section_dict = {}
        item_list = [s1[0] for s1 in parser1.items(section1)]
        for item1 in item_list:
            section_dict[item1] = parser1.get(section1, item1)
        settings_dict[section1] = section_dict

    return settings_dict
