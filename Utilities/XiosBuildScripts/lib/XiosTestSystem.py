#!/usr/bin/env python
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office 2019. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""
 CODE OWNER
   Stephen Haddad

 NAME
   XiosModuleWriter.py

 DESCRIPTION
    Creates Environment Module files for both the XIOS library and
    to set up the programming environment (PrgEnv).
"""

import os
import shutil
import subprocess
import abc

import common


class XiosTestSystem(common.XbsBase):

    """
    Abstract base class for running XIOS test case.
    """
    SYSTEM_NAME = 'Base'

    OUTPUT_FILE_LIST = ['output_atmosphere_0.nc',
                        'output_atmosphere_zoom_0.nc',
                        'output_surface_6h_2.nc',
                        'output_atmosphere_1.nc',
                        'output_surface_1d.nc',
                        'output_surface_6h_3.nc',
                        'output_atmosphere_2.nc',
                        'output_surface_6h_0.nc',
                        'output_atmosphere_3.nc',
                        'output_surface_6h_1.nc']

    def __init__(self, settings_dict):
        """
        Constructor for abstract base class for running XIOS test case.
        """
        common.XbsBase.__init__(self, settings_dict)

        self.test_dir = os.path.join(self.working_dir, 'xiosTestComplete')
        if os.path.exists(self.test_dir):
            if os.path.isdir(self.test_dir):
                shutil.rmtree(self.test_dir)
            else:
                os.remove(self.test_dir)
        os.mkdir(self.test_dir)

        self.suite_mode = 'ROSE_DATA' in settings_dict
        self.xios_root_dir = settings_dict['XIOS_PATH']
        self.xios_server_location = settings_dict['XIOS_EXEC']
        self.xios_server_link_name = 'xios_server.exe'
        self.xios_test_exec_name = 'test_complete.exe'
        self.test_client_location = os.path.join(self.xios_root_dir,
                                                 'bin',
                                                 self.xios_test_exec_name)
        if not os.path.exists(self.xios_server_location):
            err_msg1 = 'Xios server executable not found: {0}'
            err_msg1 = err_msg1.format(self.xios_server_location)
            raise common.MissingTestFileError(err_msg1)
        if not os.path.exists(self.test_client_location):
            err_msg1 = 'Xios testclient executable not found: {0}'
            err_msg1 = err_msg1.format(self.test_client_location)
            raise common.MissingTestFileError(err_msg1)

        # copy XML def files
        xms_file_base1 = os.path.join(self.xios_root_dir,
                                      'inputs',
                                      'COMPLETE')
        xms_file_name_list1 = ['context_atmosphere.xml',
                               'context_surface.xml',
                               'iodef.xml']

        for fname1 in xms_file_name_list1:
            shutil.copy(os.path.join(xms_file_base1, fname1),
                        self.test_dir)

        # link to executables
        self.server_link_path = os.path.join(self.test_dir,
                                             self.xios_server_link_name)
        if os.path.islink(self.server_link_path):
            os.remove(self.server_link_path)
        os.symlink(self.xios_server_location, self.server_link_path)

        self.client_link_path = os.path.join(self.test_dir,
                                             self.xios_test_exec_name)
        if os.path.islink(self.client_link_path):
            os.remove(self.client_link_path)
        os.symlink(self.test_client_location, self.client_link_path)

        self.test_script_file_name = os.path.join(self.working_dir,
                                                  'testScript.sh')
        try:
            self.result_dest_dir = settings_dict['XIOS_RESULT_DIR']
            self.do_result_copy = True
        except KeyError:
            self.result_dest_dir = ''
            self.do_result_copy = False

    @abc.abstractmethod
    def __str__(self):
        pass

    def run_test(self):
        """
        Main function for running test.
        """
        self.write_test_file()
        self.execute_test_script()
        self.copy_output()

    @abc.abstractmethod
    def write_test_file(self):
        """
        Write out script to run the XIOS test case. The script will then be
        executed or submitted to the queue as required.
        """
        pass

    @abc.abstractmethod
    def execute_test_script(self):
        """
        Execute test script either directly or by submitting to the queue.
        """
        pass

    def copy_output(self):
        """
        Copy the test output to the directory specified by
        self.result_dest_dir.
        """
        if not self.do_result_copy:
            print('output not being copied')
            return

        if not os.path.exists(self.result_dest_dir):
            os.makedirs(self.result_dest_dir)

        for file_name1 in self.OUTPUT_FILE_LIST:
            path1 = os.path.join(self.test_dir,
                                 file_name1)
            msg1 = 'copying from {src} to {dest}/'
            msg1 = msg1.format(src=path1,
                               dest=self.result_dest_dir)
            print(msg1)
            cmd1 = 'cp {src} {dest}/'.format(src=path1,
                                             dest=self.result_dest_dir)
            subprocess.call(cmd1,
                            shell=True)


class XiosCrayXC40TestSystem(XiosTestSystem):

    """
    Class for running XIOS complete test case on Met Office Cray XC40
    supercomputer.
    """
    SYSTEM_NAME = 'UKMO_CRAY_XC40'

    def __init__(self, settings_dict):
        XiosTestSystem.__init__(self, settings_dict)

    def __str__(self):
        return 'Class to run XIOS complete test on UKMO Cray XC-40 HPC'

    def write_test_file(self):
        """
        Write out script to run the XIOS test case. The script will then be
        executed or submitted to the queue as required.
        """
        exec_str1 = ''
        if not self.suite_mode:
            exec_str1 += '''
#!/bin/bash --login
#PBS -N XIOScomplete
#PBS -l select=2
#PBS -l walltime=00:15:00
#PBS -j oe
'''
        else:
            exec_str1 += '#!/bin/bash\n'

        exec_str1 += '''
cd {test_dir}
echo current dir is $(pwd)
rm -rf *.csv *.nc

aprun -n 28 ./{xios_test_exec_name} : -n 4 ./{xios_server_link_name}
'''.format(**self.__dict__)

        if os.path.exists(self.test_script_file_name):
            os.remove(self.test_script_file_name)

        with open(self.test_script_file_name, 'w') as script_file1:
            script_file1.write(exec_str1)
        os.chmod(self.test_script_file_name, 477)

    def execute_test_script(self):
        """
        Execute test script either directly or by submitting to the queue.
        """
        print('\nExecuting xios test configuration')
        if self.suite_mode:
            result1 = subprocess.call(self.test_script_file_name)
        else:
            result1 = subprocess.call(['qsub',
                                       self.test_script_file_name])
        if result1 != 0:
            raise common.TestError('Error executing XIOS test')


class XiosLinuxIntelTestSystem(XiosTestSystem):

    """
    Class for running XIOS complete test case on Met Office Linux platform
    using Intel compiler.

    WARNING!  Linux/Intel platform version of these build and
    test scripts is not currently working but should be fixed soon.
    """
    SYSTEM_NAME = 'UKMO_LINUX_INTEL'

    def __init__(self, settings_dict):
        """
        """
        XiosTestSystem.__init__(self, settings_dict)

    def __str__(self):
        return 'Class to run XIOS complete test on UKMO Linux Desktop with '\
               'Intel compiler environment'

    def write_test_file(self):
        """
        Write out script to run the XIOS test case. The script will then be
        executed or submitted to the queue as required.
        """
        test_cmd1 = '''#!/bin/bash

cd {test_dir}
echo current dir is $(pwd)
rm -rf *.csv *.nc

mpirun -n 3 ./{xios_test_exec_name} : -n 1 ./{xios_server_link_name}

'''.format(**self.__dict__)

        if os.path.exists(self.test_script_file_name):
            os.remove(self.test_script_file_name)

        with open(self.test_script_file_name, 'w') as script_file1:
            script_file1.write(test_cmd1)

        os.chmod(self.test_script_file_name, 477)

    def execute_test_script(self):
        """
        Execute test script either directly or by submitting to the queue.
        """
        print('\nExecuting xios test configuration')
        result1 = subprocess.call(self.test_script_file_name)
        if result1 != 0:
            raise common.TestError('Error executing XIOS test')


class XiosCrayXC30TestSystem(XiosCrayXC40TestSystem):

    """
    Class for running XIOS complete test case on the ARCHER Cray XC30
    supercomputer.
    """
    SYSTEM_NAME = 'NCAS_CRAY_XC30'

    def __str__(self):
        return 'Class to run XIOS complete test on Archer HPC (Cray XC30)'

    def write_test_file(self):
        """
        Write out script to run the XIOS test case. The script will then be
        executed or submitted to the queue as required.
        """
        exec_str1 = ''
        if not self.suite_mode:
            exec_str1 += '''
#!/bin/bash --login
#PBS -N XIOScomplete
#PBS -l select=2
#PBS -l walltime=00:20:00
#PBS -j oe
#PBS -q short
#PBS -A n02-cms
'''
        else:
            exec_str1 += '#!/bin/bash\n'

        exec_str1 += '''
cd {test_dir}
echo current dir is $(pwd)
rm -rf *.csv *.nc

aprun -n 24 ./{xios_test_exec_name} : -n 4 ./{xios_server_link_name}
'''.format(**self.__dict__)

        if os.path.exists(self.test_script_file_name):
            os.remove(self.test_script_file_name)

        with open(self.test_script_file_name, 'w') as script_file1:
            script_file1.write(exec_str1)
        os.chmod(self.test_script_file_name, 477)


def create_test_system(system_name, settings_dict):
    """
    Factory method for constructing XIOS test object.
    """
    test_system1 = None
    if system_name == XiosCrayXC40TestSystem.SYSTEM_NAME:
        test_system1 = XiosCrayXC40TestSystem(settings_dict)
    elif system_name == XiosLinuxIntelTestSystem.SYSTEM_NAME:
        test_system1 = XiosLinuxIntelTestSystem(settings_dict)
    elif system_name == XiosCrayXC30TestSystem.SYSTEM_NAME:
        test_system1 = XiosCrayXC30TestSystem(settings_dict)
    else:
        raise common.ConfigError('Invalid system name for test system')
    return test_system1
