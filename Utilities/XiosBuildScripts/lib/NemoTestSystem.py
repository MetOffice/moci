#!/usr/bin/env python2.7
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""
 CODE OWNER
   Stephen Haddad

 NAME
   NemoTestSystem
"""

import os
import sys
import subprocess
from abc import ABCMeta, abstractmethod

import common

#######################################################################


class NemoTestSystem(common.XbsBase):

    """
    Base class to run the NEMO Gyre test configuration.
    """
    # factory method
    SYSTEM_NAME = 'BASE_NEMO_TEST_SYSTEM'
    __metaclass__ = ABCMeta

    OUTPUT_FILE_LIST = ['GYRE_5d_00010101_00011230_grid_T.nc',
                        'GYRE_5d_00010101_00011230_grid_V.nc',
                        'GYRE_5d_00010101_00011230_grid_U.nc',
                        'GYRE_5d_00010101_00011230_grid_W.nc']

    def __init__(self, settings_dict):
        """
        Constructor for base class to run the NEMO Gyre test configuration.
        """
        common.XbsBase.__init__(self, settings_dict)
        self.script_name = ''
        self.script_path = ''

        self.xios_path = settings_dict['XIOS_PATH']
        self.nemo_dir_name = settings_dict['NEMO']
        self.build_path_dir = settings_dict['BUILD_PATH']
        self.nemo_tasks_jpi = int(settings_dict['NEMO_TASKS_JPI'])
        self.nemo_tasks_jpj = int(settings_dict['NEMO_TASKS_JPJ'])
        self.xios_tasks = int(settings_dict['XIOS_TASKS'])
        self.jpcfg = int(settings_dict['JP_CFG'])
        self.nemo_experiment_rel_path = settings_dict['NEMO_EXP_REL_PATH']
        self.launch_directory = os.getcwd()
        self.suite_mode = settings_dict.has_key('ROSE_DATA')
        self.tasks_per_node = int(settings_dict['TASKS_PER_NODE'])
        self.xios_tasks_per_node = int(settings_dict['XIOS_TASKS_PER_NODE'])
        self.xios_server_link_name = 'xios_server.exe'
        self.nemo_exec_name = 'opa'
        self.xios_server_exec = settings_dict['XIOS_EXEC']
        try:
            self.result_dest_dir = settings_dict['NEMO_RESULT_DIR']
            self.do_result_copy = True
        except KeyError:
            self.result_dest_dir = ''
            self.do_result_copy = False

        # Number of NEMO tasks
        self.nemo_tasks = self.nemo_tasks_jpi * self.nemo_tasks_jpj
        # Total Number of tasks

        self.path_to_nemo_experiment = \
            os.path.join(self.build_path_dir,
                         self.nemo_dir_name,
                         self.nemo_experiment_rel_path,
                         'GYRE_{0}'.format(str(self.jpcfg)),
                         'EXP00')
        if not os.path.isdir(self.path_to_nemo_experiment):
            except_msg1 = 'NEMO experiment directory not found {0:s}'
            except_msg1 = except_msg1.format(self.path_to_nemo_experiment)
            raise common.TestError(except_msg1)

    def edit_iodef_xml_file(self):
        '''
        Edit iodef.xml
        'one_file' replaced by 'multiple_file'
        '''
        namein = os.path.join(self.path_to_nemo_experiment,
                              'iodef.xml')
        nameout = '{0}~'.format(namein)
        with open(namein, 'r') as fpin, open(nameout, 'w') as fpout:
            for line in fpin:
                if 'multiple_file' in line:
                    line = line.replace('multiple_file',
                                        'one_file')

                if ('using_server' in line) and ('false' in line):
                    line = line.replace('false', 'true')
                fpout.write(line)
        os.rename(nameout, namein)

    def run_test(self):
        """
        Main function to run NEMO test.
        """
        # Change Directory
        os.chdir(self.path_to_nemo_experiment)
        print 'launch directory is {0}'.format(self.launch_directory)
        print 'current directory is {0}'.format(os.getcwd())

        # Create symbolic link to IO server
        xios_binary_link = os.path.join(self.path_to_nemo_experiment,
                                        self.xios_server_link_name)
        msg_1 = '''creating symbolic link to XIOS server:
target: {0}
link: {1}'''.format(self.xios_server_exec, xios_binary_link)
        print msg_1

        if os.path.islink(xios_binary_link):
            os.remove(xios_binary_link)
        os.symlink(self.xios_server_exec,
                   xios_binary_link)

        print 'writing test script'
        self.write_script()
        print 'running test script'
        self.run_test_script()

        self.copy_output()

    @abstractmethod
    def write_script(self):
        """
        Create the test script to run. The script is written to disk as it may
        need to be submitted to the queue.
        """
        pass

    @abstractmethod
    def run_test_script(self):
        """
        Run the test script. This may be submitted to queue or
        executed directly.
        """
        pass

    def copy_output(self):
        """
        Copy the NEMO test output files to the destination directory specified
        by self.result_dest_dir. These files can then be used to validate
        the NEMO test results.
        """
        if not self.do_result_copy:
            print 'output not being copied'
            return

        if not os.path.exists(self.result_dest_dir):
            os.makedirs(self.result_dest_dir)

        for file_name1 in self.OUTPUT_FILE_LIST:
            path1 = os.path.join(self.path_to_nemo_experiment,
                                 file_name1)
            print 'copying {src} to {dest}/'.format(src=path1,
                                                    dest=self.result_dest_dir)
            copy_cmd1 = 'cp {src} {dest}/'.format(src=path1,
                                                  dest=self.result_dest_dir)
            subprocess.call(copy_cmd1,
                            shell=True)


class NemoCrayXc40TestSystem(NemoTestSystem):

    """
    Class to run nemo test on Cray XC40 system
    """
    SYSTEM_NAME = 'UKMO_CRAY_XC40'

    def __init__(self, settings_dict):
        """
        Constructor for class to run the NEMO Gyre test configuration on
        the UK Met Office Cray XC40 platform.
        """
        print 'creating Cray XC40 test system'
        NemoTestSystem.__init__(self, settings_dict)
        self.script_name = 'opa.pbs'
        self.script_path = '{0}/{1}'.format(self.path_to_nemo_experiment,
                                            self.script_name)

        self.total_tasks = self.nemo_tasks + self.xios_tasks

        self.nnodes = ((self.nemo_tasks // self.tasks_per_node) +
                       (self.xios_tasks // self.xios_tasks_per_node))
        if self.nemo_tasks % self.tasks_per_node != 0:
            self.nnodes += 1
        if self.xios_tasks % self.xios_tasks_per_node != 0:
            self.nnodes += 1

        self.edit_iodef_xml_file()

    def __str__(self):
        return 'System for testing NEMO on MO Cray XC40 environment'

    def write_script(self):
        """
        Create the test script to run. The script is written to disk as it may
        need to be submitted to the queue.
        """
        test_cmd1 = ''
        if not self.suite_mode:
            test_cmd1 += '#!/bin/bash --login\n'
            test_cmd1 += '#PBS -N test_nemo_gyre\n'
            test_cmd1 += '#PBS -l select={nnodes:d}\n'
            test_cmd1 += '#PBS -l walltime=00:15:00\n'
            test_cmd1 += '#PBS -j oe\n'
            test_cmd1 += '#PBS -q parallel\n'
            test_cmd1 += '#PBS -P climate\n'
        else:
            test_cmd1 += '#!/bin/bash\n'
        test_cmd1 += 'cd {0}'.format(self.path_to_nemo_experiment)
        test_cmd1 += '\n'
#        for mod_1 in self.prerequisite_modules:
#            test_cmd1 += 'module load {0}\n'.format(mod_1)
        test_cmd1 += '\n'
        aprun_cmd = 'aprun '\
            '-n {xios_tasks:d} -N {xios_tasks_per_node:d} '\
            './{xios_server_link_name} : '\
            '-n {nemo_tasks:d} -N {tasks_per_node:d} ./{nemo_exec_name}\n'

        test_cmd1 += aprun_cmd
        test_cmd1 += '\n'

        test_cmd1 = test_cmd1.format(**self.__dict__)

        if os.path.exists(self.script_path):
            os.remove(self.script_path)

        with open(self.script_path, 'w') as script_file:
            script_file.write(test_cmd1)

        os.chmod(self.script_path, 477)

        return test_cmd1

    def run_test_script(self):
        """
        Run the test script. This may be submitted to queue or
        executed directly.
        """
        print 'running test script at location {0}'.format(self.script_path)
        if not os.path.exists(self.script_path) \
                or not os.path.isfile(self.script_path):
            print 'ERROR: test script not found    !'
            sys.stderr.write('Test script creation failed, aborting test.')
            err_msg1 = 'Test script creation failed, aborting test.'
            raise common.TestError(err_msg1)
        if self.suite_mode:
            result1 = subprocess.call(self.script_path)
        else:
            result1 = subprocess.call(['qsub', self.script_path])
        if result1 != 0:
            err_msg1 = 'Error executing NEMO test - error code: {0:d}'
            err_msg1 = err_msg1.format(result1)
            raise common.TestError(err_msg1)


class NemoLinuxIntelTestSystem(NemoTestSystem):

    '''
    Class to run nemo test on Linux Desktop system with Intel
    Compiler environment

    WARNING!  Linux/Intel platform version of these build and
    test scripts is not currently working but should be fixed soon.
    '''

    SYSTEM_NAME = 'UKMO_LINUX_INTEL'

    def __init__(self, settings_dict):
        """
        Constructor for class to run the NEMO Gyre test configuration on
        the UK Met OfficeLinux Desktop system with Intel Compiler environment.
        """
        print 'creating Linux Intel test system'
        NemoTestSystem.__init__(self, settings_dict)
        self.script_name = 'opa.sh'
        self.script_path = '{0}/{1}'.format(self.path_to_nemo_experiment,
                                            self.script_name)

        self.total_tasks = self.nemo_tasks + self.xios_tasks

        self.nnodes = 1
        self.edit_iodef_xml_file()

    def __str__(self):
        return 'System for testing NEMO on MO Linux desktop with Intel '\
               'Compiler environment'

    def write_script(self):
        """
        Create the test script to run. The script is written to disk as it may
        need to be submitted to the queue.
        """
        if os.path.exists(self.script_path):
            os.remove(self.script_path)

        with open(self.script_path, 'w') as script_file:
            script_file.write('#!/bin/bash\n')
            script_file.write('cd {0}'.format(self.path_to_nemo_experiment))
            script_file.write('\n')
            script_file.write('source /data/cr1/mhambley/modules/setup\n')
            script_file.write(
                'module load environment/dynamo/compiler/intelfortran/15.0.0\n')
            script_file.write('\n')
            mpirun_cmd = 'mpirun '\
                         '-np {xios_tasks:d} ./{xios_server_exec} : '\
                         '-np {nemo_tasks:d} ./{nemo_exec_name}\n'
            mpirun_cmd = mpirun_cmd.format(**self.__dict__)
            script_file.write(mpirun_cmd)
            script_file.write('\n')

        os.chmod(self.script_path, 477)

    def run_test_script(self):
        """
        Run the test script. This may be submitted to queue or
        executed directly.
        """
        print 'running test script at location {0}'.format(self.script_path)
        if not os.path.exists(self.script_path) \
           or not os.path.isfile(self.script_path):
            print 'ERROR: test script not found    !'
            err_msg1 = 'Test script creation failed, aborting test.'
            sys.stderr.write(err_msg1)
            raise common.TestError(err_msg1)

        result1 = subprocess.call(self.script_path)
        if result1 != 0:
            err_msg1 = \
                'Error executing NEMO test - error code: {0:d}'.format(result1)
            raise common.TestError(err_msg1)


def build_test_system(system_name, settings_dict):
    """
    Factory method to construct the test runner class.
    """
    test_system = None
    if system_name == NemoCrayXc40TestSystem.SYSTEM_NAME:
        test_system = NemoCrayXc40TestSystem(settings_dict)
    elif system_name == NemoLinuxIntelTestSystem.SYSTEM_NAME:
        test_system = NemoLinuxIntelTestSystem(settings_dict)
    return test_system
