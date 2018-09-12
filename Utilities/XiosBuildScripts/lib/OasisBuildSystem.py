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
   OasisBuildSystem
"""

import os
import sys
import abc
import subprocess
import shutil

import OasisModuleWriter
import common

EXTRACT_SCRIPT_FILE_NAME = 'oasisExtractScript01.sh'
BUILD_SCRIPT_FILENAME = 'oasisBuildScript01.sh'


class OasisBuildFailedException(Exception):

    """
    Exception raised if there is any problem found with building oasis.
    """
    pass


class OasisInvalidSourceCodeOptionError(Exception):

    """
    Exception raised if the there is an invalid option chosen for
    the source code location type.
    """
    pass


class OasisBuildSystem(common.XbsBuild):

    """
    Base class for building Oasis3-mct library on different platforms. Specific
    platforms will have a class that inherits from this to implement
    platform-specific build elements.
    """
    __metaclass__ = abc.ABCMeta

    SUB_DIRECTORY_LIST = ['lib',
                          'build']

    def __init__(self, settings_dict):
        """
        Constructor for base build class for Oasis.
        Arguments:
        settings_dict - A dictionary with settings object. This will often
                       be just the os.environ object, but doesn't need to be.
        """

        common.XbsBuild.__init__(self, settings_dict)

        self.do_build = settings_dict['BUILD_OASIS'] == 'true'

        self.library_name = settings_dict['OASIS3_MCT']
        self.build_platform_name = settings_dict['OASIS_PLATFORM_NAME']

        if self.do_build:
            # if we are building oasis, then get relevant repository settings

            self.make_config_file_name = settings_dict['OASIS_MAKE_FILE_NAME']

            self.source_code_location_type = \
                settings_dict['OASIS_SRC_LOCATION_TYPE']

            self.oasis_repository_url = settings_dict['OASIS_REPO_URL']
            self.oasis_revision_number = settings_dict['OASIS_REV_NO']
            if self.source_code_location_type == 'URL':
                pass
            elif self.source_code_location_type == 'local':
                self.oasis_src_code_dir = settings_dict['OASIS_SRC_CODE_DIR']
            else:
                raise OasisInvalidSourceCodeOptionError()

            self.oasis_src_dir = os.path.join(self.working_dir,
                                              self.library_name)
            try:
                self.oasis_output_dir = settings_dict['OASIS_OUTPUT_DIR']
            except KeyError:
                self.oasis_output_dir = None

        else:
            # if we are not building oasis, then we will be copying the output
            # to be used in a module.
            try:
                self.oasis_src_dir = settings_dict['OASIS_PREBUILD_DIR']
            except KeyError:
                msg1 = 'Variable OASIS_PREBUILD_DIR must be defined if '\
                       'not building Oasis library'
                raise common.MissingVariableError(msg1)

            try:
                self.oasis_repository_url = settings_dict['OASIS_REPO_URL']
                self.oasis_revision_number = settings_dict['OASIS_REV_NO']
            except KeyError:
                self.oasis_repository_url = 'unknown'
                self.oasis_revision_number = 'unknown'

        try:
            self.suite_url = settings_dict['ROSE_SUITE_URL']
            self.suite_revision_number = settings_dict['ROSE_SUITE_REV_NO']
        except KeyError:
            self.suite_url = ''
            self.suite_revision_number = ''

        # module writing related settings
        try:
            self.deploy_oasis_as_module = \
                settings_dict['DEPLOY_AS_MODULE'] == 'true'
            self.module_root_dir = settings_dict['MODULE_INSTALL_PATH']
            self.module_version = settings_dict['OASIS_MODULE_VERSION']
        except KeyError:
            common.formatted_write(
                sys.stdout,
                'Module related environment variables missing '
                'or invalid, default settings used.')
            self.deploy_oasis_as_module = False
            self.module_root_dir = ''
            self.module_version = ''

        try:
            self.build_tutorial = \
                settings_dict['OASIS_BUILD_TUTORIAL'] == 'true'
        except KeyError:
            common.formatted_write(
                sys.stdout,
                'OASIS_BUILD_TUTORIAL environment variable '
                'missing or invalid, default settings of false '
                'will be used.')
            self.build_tutorial = False

        self.separate_make_file = False
        if self.do_build:
            try:
                self.make_config_repo_url = \
                    settings_dict['OASIS_MAKE_REPO_URL']
                self.make_config_rev_no = \
                    settings_dict['OASIS_MAKE_REV_NO']

                self.separate_make_file = True
            except KeyError:
                self.make_config_repo_url = ''

        self.separate_tutorial_location = False
        if self.build_tutorial:
            if self.source_code_location_type == 'URL':
                try:
                    self.tutorial_repository_url = \
                        settings_dict['OASIS_TUTORIAL_REPO_URL']
                    self.tutorial_revision_number = \
                        settings_dict['OASIS_TUTORIAL_REV_NO']
                    self.separate_tutorial_location = True
                except KeyError:
                    self.tutorial_repository_url = ''
                    self.tutorial_revision_number = ''

            elif self.source_code_location_type == 'local':
                self.tutorial_repository_url = ''
                self.tutorial_revision_number = ''
            else:
                raise OasisInvalidSourceCodeOptionError()

    def __str__(self):
        ret_str_1 = ''
        if self.do_build:
            ret_str_1 += 'Building oasis3-mct library\n'
            if self.build_tutorial:
                ret_str_1 += 'Tutorial executables will be built\n'
            else:
                ret_str_1 += 'Tutorial will NOT be built\n'
            ret_str_1 += 'Source code to be retrieved from repository:\n'
            ret_str_1 += '{0}@{1}'.format(self.oasis_repository_url,
                                          self.oasis_revision_number)
        else:
            ret_str_1 += 'Library will not be built, module files will be \n'
            ret_str_1 += 'created at {0} \n'.format(self.module_root_dir)
            ret_str_1 += 'using library files copied from '
            ret_str_1 += '{0}\n'.format(self.oasis_src_dir)
        return ret_str_1

    def run_build(self):
        """
        Main build function. This function is typically called to run the
        build procedure.
        """
        if self.do_build:
            self.extract_source_code()
            self.write_include_file()

            build_command1 = self.create_build_command()
            self.execute_build_command(build_command1)

            if self.oasis_output_dir:
                self.copy_files(self.oasis_output_dir)

        if self.deploy_oasis_as_module:
            self.create_module()

    def extract_source_code(self):
        """
        Retreive source code from repository or directory
        """
        if self.source_code_location_type == 'URL':
            sys.stderr.write('extracting from source code repository\n\n')
            self.extract_from_repository()
        elif self.source_code_location_type == 'local':
            sys.stderr.write('extracting from local source code directory\n\n')
            self.extract_from_directory()
        else:
            raise OasisInvalidSourceCodeOptionError()

    def extract_from_repository(self):
        """
        Extract source code from the repository using FCM.
        """
       # if source code directory already exists, use update command
        # rather than checkout command
        if os.path.exists(self.oasis_src_dir):
            extract_string_1 = 'fcm update --non-interactive '\
                ' {oasis_src_dir} -r {oasis_revision_number}'
        else:
            extract_string_1 = \
                'fcm co {oasis_repository_url}@{oasis_revision_number} '\
                '{oasis_src_dir}\n'
            if self.separate_make_file:
                extract_string_1 += \
                    'fcm export {make_config_repo_url}'\
                    '/{make_config_file_name}@{make_config_rev_no}'\
                    ' {oasis_src_dir}/util/make_dir/'\
                    '{make_config_file_name}\n'
            if self.build_tutorial and self.separate_tutorial_location:
                extract_string_1 += \
                    'rm -rf {oasis_src_dir}/examples/tutorial/\n'
                extract_string_1 += \
                    'fcm export {tutorial_repository_url}@'\
                    '{tutorial_revision_number} '\
                    '{oasis_src_dir}/examples/tutorial/ \n'

        extract_string_1 = extract_string_1.format(**self.__dict__)

        if self.verbose:
            extract_script_path = os.path.join(self.working_dir,
                                               EXTRACT_SCRIPT_FILE_NAME)
            with open(extract_script_path, 'w') as extract_script:
                extract_script.write(extract_string_1)

        subprocess.call(extract_string_1, shell=True)

    def extract_from_directory(self):
        """
        Copy the Oasis3-mct source from a local directory.
        """
        # if source code directory already exists, delete to ensure correct
        # version of code is present.
        if os.path.exists(self.oasis_src_dir):
            os.rmdir(self.oasis_src_dir)

        print 'copying source code from {SRC} to {DEST}'.format(
            SRC=self.oasis_src_code_dir,
            DEST=self.oasis_src_dir)

        shutil.copytree(self.oasis_src_code_dir,
                        self.oasis_src_dir)

    def write_include_file(self):
        """
        Write the make.inc file to be used by the oasis3-mct build process.
        This tells the main makefile which architecture file to use.
        Usage:
        buildObject.write_include_file()
        """
        header_file_path = os.path.join(self.oasis_src_dir,
                                        'util',
                                        'make_dir',
                                        'make.inc')
        os.remove(header_file_path)

        header_file_str = """
PRISMHOME = {oasis_src_dir}
include $(PRISMHOME)/util/make_dir/{make_config_file_name}
"""
        header_file_str = header_file_str.format(**self.__dict__)

        with open(header_file_path, 'w') as header_file:
            header_file.write(header_file_str)

    @abc.abstractmethod
    def create_build_command(self):
        """
        Creates the series of commands to build the library (and tutorial
        files if required). The command is returned as a string and can then be
        executed using the subprocess module.

        Usage:
        buildCommandString = buildObject.create_build_command()

        Return value:
        A string with the command to be executed when building using subprocess
        module.
        """
        pass

    def execute_build_command(self, build_command):
        """
        Takes in a string containing the build commands and executes the
        commands using subprocess. If the commands fail, an exception
        is raised.

        Usage:
        self.execute_build_command(build_command)

        Arguments:
        build_command - string containing build commands.
        """
        result1 = subprocess.call(build_command, shell=True)
        if result1 != 0:
            raise OasisBuildFailedException()

    def copy_files(self, dest):
        """
        Copy the build output files to the specified directory. The directories
        copied will include the $ARCH/build and $ARCH/lib, where $ARCH is
        the name of the build directory created in the root oasis3-mct
        directory.
        If the build_tutorial member variable is True, the
        $OASIS_ROOT/examples/tutorial will also be copied to allow the
        tutorial example to be run.

        Usage:
        buildObject.CopyFile(dest)

        Arguments:
        dest - string containing path to destination directory of copied files.
        """
        src_dirs = []
        if self.do_build:
            for subdir1 in self.SUB_DIRECTORY_LIST:
                src_dirs += ['{0}/{1}/{2}'.format(self.oasis_src_dir,
                                                  self.build_platform_name,
                                                  subdir1)]

            if self.build_tutorial:
                src_dirs += [
                    '{0}/examples/tutorial'.format(self.oasis_src_dir)]

        else:
            for subdir1 in self.SUB_DIRECTORY_LIST:
                src_dirs += ['{0}/{1}'.format(self.oasis_src_dir,
                                              subdir1)]

        dest_dirs = []
        for subdir1 in self.SUB_DIRECTORY_LIST:
            dest_dirs += ['{0}/{1}'.format(dest,
                                           subdir1)]

        if self.build_tutorial:
            dest_dirs += ['{0}/examples/tutorial'.format(dest)]

        if os.path.exists(dest) and os.path.isdir(dest):
            sys.stdout.write('removing dir {0}\n'.format(dest))
            shutil.rmtree(dest)

        for src1, dest1 in zip(src_dirs, dest_dirs):
            shutil.copytree(src1, dest1)

    @abc.abstractmethod
    def create_module(self):
        """
        Creates environment modules for using the Oasis3-mct library in other
        applications.

        Usage:
        buildObject.create_module()
        """
        pass


class OasisCrayBuildSystem(OasisBuildSystem):

    """
    Class to build the Oasis3-mct libraries and tutorial on the Met Office
    Cray XC40 platform.
    """
    SYSTEM_NAME = 'UKMO_CRAY_XC40'

    def __init__(self, settings_dict):
        OasisBuildSystem.__init__(self, settings_dict)

    def __str__(self):
        ret_str_1 = OasisBuildSystem.__str__(self)
        ret_str_1 += '\nBuild is system is {0}.\n'.format(self.system_name)
        return ret_str_1

    def create_build_command(self):
        build_str_1 = '#!/bin/sh\n\n'
        build_str_1 += 'echo CURRENT MODULES:\n'
        build_str_1 += 'module list\n'
        for prereq_swap in self.prerequisite_swaps:
            build_str_1 += 'module swap {swap}\n'.format(swap=prereq_swap)

        for prereq_module in self.prerequisite_modules:
            build_str_1 += 'module load {0}\n'.format(prereq_module)

        build_str_1 += 'echo MODULES AFTER LOAD:\n'
        build_str_1 += 'module list\n'

        build_str_1 += '''
cd {oasis_src_dir}/util/make_dir
make -f TopMakefileOasis3
'''

        build_str_1 = build_str_1.format(**self.__dict__)
        if self.build_tutorial:
            tut_build_str_1 = '''
cd {oasis_src_dir}/examples/tutorial/
rm *.o
rm *.mod

rm model1.F90
mv model1_ukmo_cray_xc40.F90 model1.F90
rm model2.F90
mv model2_ukmo_cray_xc40.F90 model2.F90
rm data_oasis3/namcouple
mv data_oasis3/namcouple_TP data_oasis3/namcouple
make model1
make model2
'''
            build_str_1 += \
                tut_build_str_1.format(oasis_src_dir=self.oasis_src_dir)

        if self.verbose:
            build_script_path_1 = '{0}/{1}'.format(self.working_dir,
                                                   BUILD_SCRIPT_FILENAME)
            with open(build_script_path_1, 'w') as build_script_1:
                build_script_1.write(build_str_1)

        return build_str_1

    def create_module(self):
        """
        Function to create a module for the Oasis3-mct library.
        """
        module_writer_1 = OasisModuleWriter.OasisCrayModuleWriter(
            version=self.module_version,
            modulePath=self.module_root_dir,
            srcUrl=self.oasis_repository_url,
            revNo=self.oasis_revision_number,
            externalUrl=self.oasis_repository_url,
            externalRevNo=self.oasis_revision_number,
            suiteUrl=self.suite_url,
            suite_rev_num=self.suite_revision_number,
            moduleName=self.library_name,
            platform=self.SYSTEM_NAME,
            prerequisites=self.all_prerequisites,
        )

        module_writer_1.write_module()

        temp_str1 = '{mod_root}/packages/{rel_path}'
        rel_path = module_writer_1.module_relative_path
        module_package_directory = \
            temp_str1.format(mod_root=self.module_root_dir,
                             rel_path=rel_path)
        self.copy_files(module_package_directory)

        remote_writer_1 = OasisModuleWriter.OasisCrayRemoteModuleWriter(
            version=self.module_version,
            modulePath=self.module_root_dir,
            srcUrl=self.oasis_repository_url,
            revNo=self.oasis_revision_number,
            externalUrl=self.oasis_repository_url,
            externalRevNo=self.oasis_revision_number,
            suiteUrl=self.suite_url,
            suite_rev_num=self.suite_revision_number,
            moduleName=self.library_name,
            platform=self.system_name)
        remote_writer_1.write_module()


def create_build_system(system_name, settings_dict):
    """
    Factory method to construct oasis3-mct build object for the correct
    platform.

    Usage:
    buildObject = createBuildSystem(system_name)

    Arguments:
    system_name - A string containing the name of the platform for the build.

    Return:
    An object derived from OasisBuildSystem which has the correct build
    settings for the specified platform.
    """
    build_system_1 = None
    if system_name == OasisCrayBuildSystem.SYSTEM_NAME:
        build_system_1 = OasisCrayBuildSystem(settings_dict)
    return build_system_1
