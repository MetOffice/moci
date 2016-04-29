#!/usr/bin/env python2.7
#
#*****************************COPYRIGHT******************************
#(C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
#*****************************COPYRIGHT******************************
"""
 CODE OWNER
   Stephen Haddad

 NAME
   OasisTestSystem
"""

import os
import sys
import subprocess
import shutil
import abc

import common


class OasisTestFailedException(Exception):

    """
    Raised when the execution of the oasis3-mct test command fails.
    """
    pass


class MissingTestOutputException(Exception):

    """
    Raised when an expected test output is missing after the test
    has been run.
    """
    pass


class OasisTestSystem(common.XbsBase):

    """
    Class to test basic functionality of the Oasis3-MCT library.
    """
    __metaclass__ = abc.ABCMeta
    # Class (static) variable definitions
    SYSTEM_NAME = "BASE_CLASS"
    TEST_SCRIPT_FILENAME = 'oasisRunTutorialScript.sh'

    OUTPUT_FILE_NAMES = ['FRECVATM_model2_01.nc',
                         'FRECVOCN_model1_03.nc',
                         'FSENDATM_model2_03.nc',
                         'FSENDOCN_model1_01.nc',
                         'FSENDOCN_model1_02.nc']

    TUTORIAL_DATA_FILE_LIST = ['my_remapping_file_bilinear.nc',
                               'fdocn.nc',
                               'grid_model2.nc',
                               'fdatm.nc',
                               'grid_model1.nc']

    def __init__(self, settings_dict):
        """
        Constructor
        """
        common.XbsBase.__init__(self, settings_dict)
        self.library_name = settings_dict['OASIS3_MCT']
        self.oasis_root_dir = settings_dict['OASIS_ROOT']
        self.build_platform_name = settings_dict['OASIS_PLATFORM_NAME']
        self.asis_tutorial_data_dir = settings_dict['OASIS_DATA_DIRECTORY']
        self.oasis_module_version = settings_dict['OASIS_MODULE_VERSION']

        self.oasis_build_output_dir = settings_dict['OASIS_OUTPUT_DIR']
        self.tutorial_src_dir = os.path.join(self.oasis_build_output_dir,
                                             'examples',
                                             'tutorial')
        try:
            self.test_name = settings_dict['OASIS_TEST_NAME']
        except KeyError:
            self.test_name = 'oasis3mct_tutorial'
        self.tutorial_working_dir = os.path.join(self.working_dir,
                                                 self.test_name)
        self.tutorial_output_dir = os.path.join(self.tutorial_working_dir,
                                                'runDir')
        self.suite_mode = settings_dict.has_key('ROSE_DATA')
        if self.suite_mode:
            self.run_tut_cmd = 'run_tutorial_ukmo_cray_xc40_rose'
        else:
            self.run_tut_cmd = 'run_tutorial_ukmo_cray_xc40'

        try:
            self.result_dest_dir = settings_dict['OASIS_RESULT_DIR']
            self.do_result_copy = True
        except KeyError:
            self.result_dest_dir = ''
            self.do_result_copy = False

        # create a fresh working dir for test
        if os.path.exists(self.tutorial_working_dir):
            shutil.rmtree(self.tutorial_working_dir)

        shutil.copytree(self.tutorial_src_dir, self.tutorial_working_dir)
        # copy data files
        for file_name1 in self.TUTORIAL_DATA_FILE_LIST:
            src_path = os.path.join(self.asis_tutorial_data_dir,
                                    file_name1)
            dest_path = os.path.join(self.tutorial_working_dir,
                                     'data_oasis3',
                                     file_name1)
            shutil.copyfile(src_path, dest_path)

    def run_test(self):
        """
        Main umbrella method which runs all methods that are part of the
        oasis3-mct test.
        """
        run_cmd_string = self.create_test_command()
        if self.verbose:
            run_test_script_path = os.path.join(self.working_dir,
                                                self.TEST_SCRIPT_FILENAME)
            with open(run_test_script_path, 'w') as test_script1:
                test_script1.write(run_cmd_string + '\n')

        self.execute_test_cmd(run_cmd_string)

        if self.suite_mode:
            self.copy_results()

    def execute_test_cmd(self, run_cmd):
        """
        Execute the given test command in a subprocess. The command is given
        in shell script. It will usually have been create by
        create_test_command.

        testObject.execute_test_cmd(run_cmd)

        Arguments:
        run_cmd - A string containing shell commands to execute the test.

        Exceptions:
        OasisTestFailedException - If the execution fails i.e. the subprocess
                                   has non zero return value.
        """
        result1 = subprocess.call(run_cmd, shell=True)
        if result1 != 0:
            raise OasisTestFailedException()

    @abc.abstractmethod
    def create_test_command(self):
        """
        Create command to run oasis3-mct test.

        commadString = testObj.create_test_command()

        Return:
        A string with shell commands to execute the oasis3-mct test.
        """
        pass

    def copy_results(self):
        """
        Copies the contents of the result directory to destination specified
        by the result_dest_dir object member variable.
        """
        if not self.do_result_copy:
            sys.stderr.write('output not being copied')
            return

        if not os.path.exists(self.result_dest_dir):
            os.makedirs(self.result_dest_dir)

        for file_name1 in self.OUTPUT_FILE_NAMES:
            path1 = os.path.join(self.tutorial_output_dir, file_name1)
            msg1 = 'copying from {src} to {dest} \n'
            msg1 = msg1.format(src=path1,
                               dest=self.result_dest_dir)
            print msg1
            result_dest_file_name = os.path.join(self.result_dest_dir,
                                                 file_name1)
            shutil.copyfile(path1,
                            result_dest_file_name)


class OasisCrayTestSystem(OasisTestSystem):

    """
    Class to run the Oasis3-mct test on the Met Office Cray XC40.
    """
    SYSTEM_NAME = 'UKMO_CRAY_XC40'

    def __init__(self, settings_dict):
        """
        Constructor for class to run the Oasis3-mct test on the Met
        Office Cray XC40.
        """
        OasisTestSystem.__init__(self, settings_dict)

    def __str__(self):
        ret_val = 'Class to test Oasis 3-MCT library on the '
        ret_val += 'Met Office Cray XC40 architecture'
        return ret_val

    def create_test_command(self):
        """
        Create command to run oasis3-mct test on Met Office Cray XC40 platform
        with Cray compiler environment.

        commadString = testObj.create_test_command()

        Return:
        A string with shell commands to execute the oasis3-mct test.
        """
        test_cmd1 = '''#!/bin/sh

cd {tutorial_working_dir}
./{run_tut_cmd}
'''
        test_cmd1 = test_cmd1.format(**self.__dict__)
        return test_cmd1


class OasisLinuxIntelTestSystem(OasisTestSystem):

    """
    Class to run the Oasis3-mct test on the Met Office Linux Desktop
    with Intel Compiler.
    """
    SYSTEM_NAME = 'UKMO_LINUX_INTEL'

    def __init__(self, settings_dict):
        """
        Constructor for class to run the Oasis3-mct test on the Met Office
        Linux Desktop with Intel Compiler.
        """
        OasisTestSystem.__init__(self, settings_dict)

    def __str__(self):
        ret_val = 'Class to test Oasis 3-MCT library on the Met '\
            'Office Linux Desktop architecture'
        return ret_val

    def create_test_command(self):
        """
        Create command to run oasis3-mct test on Met Office Linix Desktop
        platform with Intel compiler environment.

        commadString = testObj.create_test_command()

        Return:
        A string with shell commands to execute the oasis3-mct test.
        """
        pass


def create_test_system(system_name, settings_dict):
    """
    Factory method to create a class to run the tests.

    Usage:
    testObject = createTestSystem(system_name)

    Arguments:
    system_name - A string containing the name of the platform for the test.

    Return:
    An object derived from OasisBuildSystem which has the correct test
    settings for the specified platform.
    """
    test_system1 = None
    if system_name == OasisCrayTestSystem.SYSTEM_NAME:
        test_system1 = OasisCrayTestSystem(settings_dict)
    elif system_name == common.SYSTEM_NAME_MONSOON:
        test_system1 = OasisCrayTestSystem(settings_dict)
    elif system_name == OasisLinuxIntelTestSystem.SYSTEM_NAME:
        test_system1 = OasisLinuxIntelTestSystem(settings_dict)
    return test_system1
