#!/usr/bin/env python2.7
""" *****************************COPYRIGHT******************************
 (C) Crown copyright Met Office. All rights reserved.
 For further details please refer to the file COPYRIGHT.txt
 which you should have received as part of this distribution.
 *****************************COPYRIGHT******************************

 CODE OWNER
   Stephen Haddad

 NAME
   XiosModuleWriter.py

 DESCRIPTION
    Creates Environment Module files for both the XIOS library and
    to set up the programming environment (PrgEnv).

 CODE OWNER
   Stephen Haddad

 NAME
   XiosBuildSystem.py

 DESCRIPTION
    Creates Environment Module files for both the XIOS library and
    to set up the programming environment (PrgEnv).
"""
import os
import subprocess
import shutil
import sys
import ConfigParser
import abc

import common
import OasisModuleWriter
import XiosModuleWriter


REPOSITORY_SECTION_TITLE = 'Repository'
DEPENDENCIES_SECTION_TITLE = 'Dependencies'

BUILD_SCRIPT_FILENAME = 'xiosBuildScript01.sh'
EXTRACT_SCRIPT_FILENAME = 'xiosExtractScript01.sh'


class XiosInvalidSourceCodeOptionError(Exception):

    """
    Exception raised if the there is an invalid option chosen for
    the source code location type.
    """
    pass


class XiosBuildSystem(common.XbsBase):

    """
    Base class containing functionality to build xios. For a particular
    system, e.g. linux desktop or Cray XC-40, the subclasses will implement
    system specific functions.
    """
    __metaclass__ = abc.ABCMeta
    SYSTEM_NAME = 'XIOS_BASE_SYSTEM'
    XiosSubDirList = ['bin', 'inc', 'lib', 'inputs']

    def __init__(self, settings_dict):
        """
        Class constructor for XiosBuildSystem base class.
        """
        common.XbsBase.__init__(self, settings_dict)
        self.build_required = False
        self.pre_build_clean = False
        self.update_required = False
        self.tar_command = 'tar'

        try:
            self.compiler_module = settings_dict['XBS_COMPILER_PRGENV']
            self.load_compiler_module = True
        except KeyError:
            self.compiler_module = None
            self.load_compiler_module = False

        self.build_path = settings_dict['BUILD_PATH']

        try:
            self.specify_compiler = \
                settings_dict['XBS_SPECIFY_COMPILER_PRGENV'] == 'true'
            self.compiler_version = \
                settings_dict['XBS_COMPILER_PRGENV']
        except KeyError:
            self.specify_compiler = False
            self.compiler_version = None

        prereq_module_str = settings_dict['XBS_PREREQ_MODULES']
        prereq_module_str = \
            ''.join([s1 for s1 in prereq_module_str if "'[] ".count(s1) == 0])
        self.prerequisite_modules = prereq_module_str.split(',')

        self.library_name = settings_dict['XIOS']
        self.source_code_location_type = settings_dict[
            'XIOS_SRC_LOCATION_TYPE']

        self.xios_repository_url = settings_dict['XIOS_REPO_URL']
        self.xios_revision_number = settings_dict['XIOS_REV']
        if self.source_code_location_type == 'URL':
            pass
        elif self.source_code_location_type == 'local':
            self.xios_source_code_dir = settings_dict['XIOS_SRC_CODE_DIR']
            # repository URL and revision only used for info purposes
            # as the source code is actually retrieved from disk
        else:
            raise XiosInvalidSourceCodeOptionError()

        try:
            self.number_of_build_tasks = int(settings_dict['XIOS_NUM_CORES'])
        except KeyError:
            self.number_of_build_tasks = 8

        try:
            self.copy_prebuild = \
                settings_dict['XIOS_USE_PREBUILT_LIB'] == 'true'
            if self.copy_prebuild:
                self.prebuild_directory = settings_dict['XIOS_PREBUILT_DIR']
        except KeyError:
            self.copy_prebuild = False
            self.prebuild_directory = ''

        if self.copy_prebuild:
            self.library_dir = self.prebuild_directory
        else:
            self.library_dir = os.path.join(self.working_dir,
                                            self.library_name)

        try:
            self.use_oasis = settings_dict['USE_OASIS'] == 'true'
        except KeyError:
            self.use_oasis = False
        if self.use_oasis:
            if settings_dict.has_key('OASIS_ROOT'):
                self.oasis_root = settings_dict['OASIS_ROOT']
                print 'OASIS found at {0}'.format(self.oasis_root)
            else:
                print 'OASIS not found'
                raise common.ConfigError('OASIS not found')
        else:
            self.oasis_root = ''

        self.post_build_cleanup = settings_dict[
            'XIOS_POST_BUILD_CLEANUP'] == 'true'
        self.do_clean_build = settings_dict['XIOS_DO_CLEAN_BUILD'] == 'true'

        try:
            self.xios_external_url = settings_dict['XIOS_EXTERNAL_REPO_URL']
        except KeyError:
            self.xios_external_url = ''

        try:
            self.suite_url = settings_dict['ROSE_SUITE_URL']
            self.suite_revision_number = settings_dict['ROSE_SUITE_REV_NO']
        except KeyError:
            self.suite_url = ''
            self.suite_revision_number = ''

        try:
            self.deploy_xios_as_module = settings_dict[
                'DEPLOY_AS_MODULE'] == 'true'
            self.module_root_dir = settings_dict['MODULE_INSTALL_PATH']
            self.module_version = settings_dict['XIOS_MODULE_VERSION']
            self.prg_env_version = settings_dict['XIOS_PRGENV_VERSION']
            if self.use_oasis:
                self.oasis_module_name = settings_dict['OASIS3_MCT']
                self.oasis_module_version = \
                    settings_dict['OASIS_MODULE_VERSION']
                self.oasis_revision_number = settings_dict['OASIS_REV_NO']
            else:
                self.oasis_module_name = ''
                self.oasis_module_version = ''
                self.oasis_revision_number = ''
        except KeyError:
            self.deploy_xios_as_module = False
            self.module_root_dir = ''
            self.module_version = ''
            self.prg_env_version = ''
            self.oasis_module_name = ''
            self.oasis_module_version = ''
            self.oasis_revision_number = ''

        self.file_name_base = 'default_base'

    def run_build(self):
        """
        Main function to call to
        Usage:
        system.run_build()
        """
        print "working directory is {0}".format(self.working_dir)
        if self.copy_prebuild:
            self.setup_prebuild()
            return

        self.check_build_required()
        if self.build_required:
            self.get_source_code()
        if self.pre_build_clean:
            self.setup_arch_files()

        build_cmd = self.create_build_command()
        self.execute_build_command(build_cmd)

        self.check_xios_build()
        self.copy_files()
        if self.deploy_xios_as_module:
            self.create_module()
        self.clean_up()

    def setup_prebuild(self):
        """
        When using prebuild configm this functions performs required setup.
        """
        source_base = self.prebuild_directory
        dest_base = os.path.join(self.build_path, self.library_name)
        self.copy_xios_files_from_source_to_dest(source_base, dest_base)

        if self.deploy_xios_as_module:
            self.create_module()

    def write_build_conf(self):
        """
        Writes out a file that describes the build config used. When next a
        build is executed the old conf can be comapred with the new one
        to determine if a build is requried.
        """
        conf1 = ConfigParser.RawConfigParser()
        conf1.add_section(REPOSITORY_SECTION_TITLE)
        conf1.set(REPOSITORY_SECTION_TITLE, 'URL', self.xios_repository_url)
        conf1.set(REPOSITORY_SECTION_TITLE,
                  'revision',
                  self.xios_revision_number)

        conf1.add_section(DEPENDENCIES_SECTION_TITLE)

        conf1.set(DEPENDENCIES_SECTION_TITLE, 'useOasis', self.use_oasis)
        conf1.set(DEPENDENCIES_SECTION_TITLE, 'oasisRoot', self.oasis_root)

        build_path_root = os.path.join(self.build_path, self.library_name)
        conf_file_name1 = os.path.join(build_path_root, 'build.conf')
        if os.path.exists(conf_file_name1):
            os.remove(conf_file_name1)

        with open(conf_file_name1, 'w') as conf_file1:
            conf1.write(conf_file1)

    def check_build_required(self):
        """
        check if build output and working folders exist and match. Updates
        the member variables  build_required, pre_build_clean and
        update_required as required.
        """

        if self.do_clean_build:
            self.build_required = True
            self.pre_build_clean = True
            return

        build_path_root = os.path.join(self.build_path, self.library_name)
        if not os.path.exists(build_path_root) or\
                not os.path.isdir(build_path_root):
            self.build_required = True
            self.pre_build_clean = True

        file_name_list = ['bin/xios_server.exe', 'lib/libxios.a']
        for ref_file_name1 in file_name_list:
            if not os.path.exists(os.path.join(build_path_root,
                                               ref_file_name1)):
                # an important build file is missing, rebuild required.
                self.build_required = True

        # read in build settings from build folder
        conf_file_name1 = build_path_root + '/build.conf'
        if not os.path.exists(conf_file_name1):
            self.build_required = True
            # if we don't know what build settings were used, build from
            # scratch
            self.pre_build_clean = True

        conf1 = ConfigParser.RawConfigParser()
        conf1.read(conf_file_name1)

        # compare with current settings
        try:
            old_repository_url = conf1.get(REPOSITORY_SECTION_TITLE, 'URL')
            new_repository_url = self.xios_repository_url
            if old_repository_url != new_repository_url:
                self.build_required = True
                self.pre_build_clean = True

            old_revision_number = conf1.get(
                REPOSITORY_SECTION_TITLE, 'revision')
            new_revision_number = self.xios_revision_number
            if old_revision_number != new_revision_number:
                self.build_required = True
                try:
                    old_rev_num = int(old_revision_number)
                    new_rev_num = int(new_revision_number)
                    if new_rev_num != old_rev_num:
                        self.update_required = True
                except ValueError:
                    # there will be an exception if the revision is head, in
                    # which we will do an update
                    self.update_required = True

            old_use_oasis = conf1.get(DEPENDENCIES_SECTION_TITLE, 'useOasis')
            new_use_oasis = self.use_oasis
            if old_use_oasis != new_use_oasis:
                self.build_required = True
                self.pre_build_clean = True

            old_oasis_root = conf1.get(DEPENDENCIES_SECTION_TITLE, 'oasisRoot')
            new_oasis_root = self.oasis_root
            if old_oasis_root != new_oasis_root:
                self.build_required = True
                self.pre_build_clean = True

        except (ConfigParser.NoOptionError,
                ConfigParser.MissingSectionHeaderError,
                ConfigParser.NoSectionError):
            # an exception will generated if any of the settings are missing
            # from the conf file, in which case rebuild
            sys.stderr.write('Error reading conf file, triggering clean build')
            self.build_required = True
            self.pre_build_clean = True

    def get_source_code(self):
        """
        Retrieve the XIOS source code either from a repository or a directory.
        """
        if self.source_code_location_type == 'URL':
            self.extract_from_repository()
        elif self.source_code_location_type == 'local':
            self.extract_from_directory()
        else:
            raise XiosInvalidSourceCodeOptionError()

    def extract_from_repository(self):
        """
        Update the XIOS source code from a repository.
        """
        destination_dir = os.path.join(self.working_dir,
                                       self.library_name)

        if (not os.path.exists(destination_dir) or
                not os.path.isdir(destination_dir) or
                self.do_clean_build):
            self.extract_xios_source_code()
            return

        if not self.update_required:
            return

        extract_cmd = '''
cd {destination_dir}
fcm update --non-interactive -r {rev_no}
'''.format(destination_dir=destination_dir,
           rev_no=self.xios_revision_number)

        if self.verbose:
            script_file_name = os.path.join(self.working_dir,
                                            EXTRACT_SCRIPT_FILENAME)
            if (os.path.exists(script_file_name) and
                    os.path.isfile(script_file_name)):
                os.remove(script_file_name)
            with open(script_file_name, 'w') as extract_script:
                extract_script.write('#!/bin/sh')
                extract_script.write(extract_cmd)

            os.chmod(script_file_name, 477)

        print '\nExecuting fcm update command\n'
        result1 = subprocess.call(extract_cmd, shell=True)
        if result1 != 0:
            err_msg1 = 'Error updating XIOS source code'
            raise common.SourceCodeExtractionError(err_msg1)

    def extract_xios_source_code(self):
        """
        Checkout the XIOS source code from a repository.
        """
        destination_dir = os.path.join(self.working_dir,
                                       self.library_name)

        if os.path.exists(destination_dir) and os.path.isdir(destination_dir):
            shutil.rmtree(destination_dir)

        extract_cmd = '''
fcm co {repo_url}@{rev_number} {dest_dir}
cd {dest_dir}
for i in tools/archive/*.tar.gz; do  {tar_cmd} -xzf $i; done
'''.format(repo_url=self.xios_repository_url,
           rev_number=self.xios_revision_number,
           dest_dir=destination_dir,
           tar_cmd=self.tar_command)

        if self.verbose:
            script_file_name = os.path.join(self.working_dir,
                                            EXTRACT_SCRIPT_FILENAME)
            if (os.path.exists(script_file_name) and
                    os.path.isfile(script_file_name)):
                os.remove(script_file_name)
            with open(script_file_name, 'w') as extract_script:
                extract_script.write('#!/bin/sh')
                extract_script.write(extract_cmd)

        print '\nexecuting fcm check-out command\n'
        result1 = subprocess.call(extract_cmd, shell=True)
        if result1 != 0:
            err_msg1 = 'Error extracting XIOS source code'
            raise common.SourceCodeExtractionError(err_msg1)

    def extract_from_directory(self):
        """
        Retrieve the XIOS source codefrom a directory.
        """
        destination_dir = os.path.join(self.working_dir, self. library_name)
        # if source code directory already exists, delete to ensure correct
        # version of code is present.
        if os.path.exists(destination_dir):
            os.rmdir(destination_dir)

        print 'copying source code from {SRC} to {DEST}'.format(
            SRC=self.xios_source_code_dir,
            DEST=destination_dir)

        shutil.copytree(self.xios_source_code_dir,
                        destination_dir)

    def check_xios_build(self):
        """
        Check that the XIOS build has completed sucessfully. This is
        done by checking that expected output is present.
        """
        source_base = os.path.join(self.working_dir,
                                   self.library_name)
        xios_lib_path = os.path.join(source_base, 'lib', 'libxios.a')
        if not os.path.exists(xios_lib_path):
            err_msg1 = 'XIOS lib file not found at {0}, '\
                'build failed!'.format(xios_lib_path)
            raise common.BuildError(err_msg1)
        xios_server_exe = '{0}/bin/xios_server.exe'.format(source_base)
        if not os.path.exists(xios_server_exe):
            err_msg1 = 'XIOS server binary file not found at {0}, '\
                'build failed!'.format(xios_server_exe)
            raise common.BuildError(err_msg1)

    def copy_files(self):
        """
        Copy XIOS build output file from the build directory
        to the destination specified by the BUILD_PATH environment variable.
        """
        dest_base = os.path.join(self.build_path, self.library_name)
        self.copy_files_to_dir(dest_base)

    def copy_files_to_dir(self, dest_base):
        """
        Copy XIOS build output files from the build directory
        to the destination specified by the dest_base argument.
        """
        source_base = os.path.join(self.working_dir, self.library_dir)
        self.copy_xios_files_from_source_to_dest(source_base,
                                                 dest_base)
        self.write_build_conf()

    def copy_xios_files_from_source_to_dest(self, source_base, dest_base):
        """
        Copy XIOS build output files from source_base to dest_base.
        """
        print '''
copying XIOS output files:
working directory: {work_dir}
source directory: {source_base}
destination directory: {dest_base}
'''.format(source_base=source_base,
           dest_base=dest_base,
           work_dir=self.working_dir)

        sub_dir_list = self.XiosSubDirList
        source_dirs = [os.path.join(source_base,
                                    dir1) for dir1 in sub_dir_list]
        print 'copying output files'
        if os.path.exists(dest_base) and os.path.isdir(dest_base):
            print 'removing dir {0}'.format(dest_base)
            shutil.rmtree(dest_base)
        destination_dirs = \
            [os.path.join(dest_base, dir1) for dir1 in sub_dir_list]
        for source_dir, dest_dir in zip(source_dirs, destination_dirs):
            print 'copying directory from  {0} to {1}'.format(source_dir,
                                                              dest_dir)
            shutil.copytree(source_dir, dest_dir)

    def clean_up(self):
        """
        Remove the build file from the working directory.
        """
        if self.post_build_cleanup:
            src_dir = os.path.join(self.working_dir, self.library_name)
            print 'removing build working directory {0}'.format(src_dir)
            shutil.rmtree(src_dir)

    def setup_arch_files(self):
        """
        Setup the arch files to be used by the make_xios build script
        Inputs:
        arch_path: full path where the arch files should be written
        file_name_base: the base name for the files (based on
                      the build architecture)
        oasis_root_path: The full path to the root of the OASIS directory if
                         used for this build. empty string
        """

        arch_path = os.path.join(self.working_dir,
                                 self.library_name,
                                 'arch')
        try:
            oasis_root_path = self.oasis_root
        except AttributeError:
            oasis_root_path = None

        file_name_env = arch_path + '/' + self.file_name_base + '.env'
        if os.path.isfile(file_name_env):
            os.remove(file_name_env)
        self.setup_arch_env_file(file_name_env, oasis_root_path)
        print 'writing out arch file {0}'.format(file_name_env)

        file_name_path = os.path.join(arch_path,
                                      self.file_name_base + '.path')
        if os.path.isfile(file_name_path):
            os.remove(file_name_path)
        self.setup_arch_path_file(file_name_path)
        print 'writing out arch file {0}'.format(file_name_path)

        file_name_fcm = os.path.join(arch_path, self.file_name_base + '.fcm')
        if os.path.isfile(file_name_fcm):
            os.remove(file_name_fcm)
        self.setup_arch_fcm_file(file_name_fcm)
        print 'writing out arch file {0}'.format(file_name_fcm)

    @abc.abstractmethod
    def setup_arch_fcm_file(self, file_name_fcm):
        """
        Sets up the arch.fcm file used in the build.
        """
        pass

    @abc.abstractmethod
    def setup_arch_env_file(self, file_name, oasis_root_path):
        """
        Sets up the arch.env file used in the build.
        """
        pass

    @abc.abstractmethod
    def setup_arch_path_file(self, file_name):
        """
        Sets up the arch.path file used in the build.
        """
        pass

    @abc.abstractmethod
    def create_build_command(self):
        """
        Write out the build script to a file (verbose mode only).
        """
        pass

    def execute_build_command(self, build_cmd):
        """
        Execute the build command.
        """
        print 'executing build command'
        return_code = subprocess.call(build_cmd, shell=True)
        if return_code != 0:
            raise common.BuildError('Error compiling XIOS: build failed!')

    @abc.abstractmethod
    def create_module(self):
        """
        Create a module file and associated package files for XIOS.
        """
        pass


class XiosCrayBuildSystem(XiosBuildSystem):

    """
    Subclass of XiosBuildSystem that implements Xios build
    on Cray XC-40 system.
    """
    SYSTEM_NAME = 'UKMO_CRAY_XC40'

    def __init__(self, settings_dict):
        """
        Class constructor for XiosCrayBuildSystem.

        Usage:
        system1 = XiosCrayyBuildSystem(settings)

        Inputs:
        settings_dict - A dictionary with the required settings (usually based
                       on os.environ).
        """
        XiosBuildSystem.__init__(self, settings_dict)

        self.file_name_base = 'arch-XC30_Cray'

    def create_build_command(self):
        """
        Write out the build script to a file (verbose mode only).
        """
        build_cmd1 = ''

        if self.load_compiler_module:
            build_cmd1 += 'module swap {0}\n'.format(self.compiler_module)
        for mod_1 in self.prerequisite_modules:
            build_cmd1 += 'module load {0}\n'.format(mod_1)

        build_cmd1 += '\n'
        xios_src_dir = os.path.join(self.working_dir, self.library_name)
        build_cmd1 += 'cd {0}\n'.format(xios_src_dir)

        # main build command
        build_cmd1 += './make_xios --arch XC30_Cray'
        if self.do_clean_build:
            build_cmd1 += ' --full '
        if self.use_oasis:
            build_cmd1 += ' --use_oasis oasis3_mct '
        build_cmd1 += ' --job {0}'.format(self.number_of_build_tasks)
        build_cmd1 += '\n'

        if self.verbose:
            build_script_file_name = os.path.join(self.working_dir,
                                                  BUILD_SCRIPT_FILENAME)
            if os.path.exists(build_script_file_name) and \
                    os.path.isfile(build_script_file_name):
                os.remove(build_script_file_name)

            with open(build_script_file_name, 'w') as build_script:
                build_script.write('#!/bin/sh\n\n')
                build_script.write(build_cmd1)

        return build_cmd1

    def setup_arch_fcm_file(self, file_name):
        """
        Sets up the arch.fcm file used in the build.
        """
        with open(file_name, 'w') as fcm_file:
            fcm_file.write('''
%CCOMPILER      CC
%FCOMPILER      ftn
%LINKER         CC

%BASE_CFLAGS    -em -DMPICH_SKIP_MPICXX -h msglevel_4 -h zero -h gnu
%PROD_CFLAGS    -O1 -DBOOST_DISABLE_ASSERTS
%DEV_CFLAGS     -O2
%DEBUG_CFLAGS   -g

%BASE_FFLAGS    -em -m 4 -e0 -eZ
%PROD_FFLAGS    -O3
%DEV_FFLAGS     -G2
%DEBUG_FFLAGS   -g

%BASE_INC       -D__NONE__
%BASE_LD        -D__NONE__

%CPP            cpp
%FPP            cpp -P -CC
%MAKE           gmake
''')

    def setup_arch_path_file(self, file_name):
        """
        Sets up the arch.path file used in the build.
        """
        arch_path_string = '''
NETCDF_INCDIR=""
NETCDF_LIBDIR=""
NETCDF_LIB=""

MPI_INCDIR=""
MPI_LIBDIR=""
MPI_LIB=""

HDF5_INCDIR=""
HDF5_LIBDIR=""
HDF5_LIB=""
'''
        if self.use_oasis:
            arch_path_string += '''
OASIS_INCDIR="-I{oasis_root}/build/lib/psmile.MPI1"
OASIS_LIBDIR="-L{oasis_root}/lib"
OASIS_LIB="-lpsmile.MPI1 -lscrip -lmct -lmpeu"
'''
        else:
            arch_path_string += '''
OASIS_INCDIR=""
OASIS_LIBDIR=""
OASIS_LIB=""
'''
        arch_path_string = arch_path_string.format(**self.__dict__)

        with open(file_name, 'w') as path_file:
            path_file.write(arch_path_string)

    def setup_arch_env_file(self, file_name, oasis_root_path):
        """
        Sets up the arch.env file used in the build.
        """
        arch_env_str = '''
export HDF5_INC_DIR=""
export HDF5_LIB_DIR=""

export NETCDF_INC_DIR=""
export NETCDF_LIB_DIR=""

'''
        with open(file_name, 'w') as env_file:
            env_file.write(arch_env_str)

    def create_module(self):
        """
        Create a module file and associated package files for XIOS.
        """
        print 'creating modules with root {0}'.format(self.module_root_dir)
        if not os.path.exists(self.module_root_dir):
            os.makedirs(self.module_root_dir)
        elif not os.path.isdir(self.module_root_dir):
            err_msg1 = 'Module install directory {0} not found, module not '\
                'deployed.\n'.format(self.module_root_dir)
            raise common.ModuleCreationError(err_msg1)

        self.create_local_module_files()

        self.create_remote_module_files()

    def get_oasis_module_path(self, remote):
        """
        Use the oasis module writer to calculate the relative path to
        the oasis module.
        """
        # Create a dummy version  of the oasis module writer to get the
        # relative path to the oasis modules for use in the PrgEnv module. This
        # ensure that if the path changes, the PrgEnv will remain consistent.
        if remote:
            omw1 = OasisModuleWriter.OasisCrayRemoteModuleWriter(
                version=self.oasis_module_version,
                modulePath=self.module_root_dir,
                srcUrl='',
                revNo=self.oasis_revision_number,
                externalUrl='',
                externalRevNo='',
                suiteUrl=self.suite_url,
                suite_rev_num=self.suite_revision_number,
                moduleName=self.oasis_module_name,
                platform=self.system_name)
        else:
            omw1 = OasisModuleWriter.OasisCrayModuleWriter(
                version=self.oasis_module_version,
                modulePath=self.module_root_dir,
                srcUrl='',
                revNo=self.oasis_revision_number,
                externalUrl='',
                externalRevNo='',
                suiteUrl=self.suite_url,
                suite_rev_num=self.suite_revision_number,
                moduleName=self.oasis_module_name,
                platform=self.system_name,
                prerequisites=[])
        omw1.setup_file_path()
        return omw1.module_relative_path

    def create_local_module_files(self):
        """
        Create the module files that will be used on this platform.
        """
        print 'Creating XIOS module'
        mod_writer1 = \
            XiosModuleWriter.XiosCrayModuleWriter(self.module_version,
                                                  self.module_root_dir,
                                                  self.xios_repository_url,
                                                  self.xios_revision_number,
                                                  self.xios_external_url,
                                                  self.suite_url,
                                                  self.suite_revision_number,
                                                  self.system_name,
                                                  self.prerequisite_modules)
        mod_writer1.write_module()

        module_package_directory = \
            os.path.join(self.module_root_dir,
                         'packages',
                         mod_writer1.module_relative_path)

        print 'Copying files {0}'.format(module_package_directory)
        self.copy_files_to_dir(module_package_directory)

        # XIOS Prg-Env module
        modules_to_load = []
        if self.use_oasis:
            modules_to_load += [self.get_oasis_module_path(False)]
        modules_to_load += [mod_writer1.module_relative_path]

        prg_env_writer1 = \
            XiosModuleWriter.XiosCrayPrgEnvWriter(
                version=self.prg_env_version,
                modulePath=self.module_root_dir,
                module_list=modules_to_load,
                platform=self.system_name,
                suiteUrl=self.suite_url,
                suite_revision_number=self.suite_revision_number,
                prerequisites=self.prerequisite_modules,
                compiler_module=self.compiler_version)
        # Create the PrgEnv module with 2 names, first XIOS-PrgEnv and then
        # GC3-PrgEnv
        prg_env_writer1.write_module()

        prg_env_writer1.module_name = \
            XiosModuleWriter.XiosPrgEnvWriter.GC3_PRGENV_NAME
        prg_env_writer1.write_module()

    def create_remote_module_files(self):
        """
        Create the module files that will be used on other platforms.
        """
        remote_mod_writer1 = \
            XiosModuleWriter.XiosCrayRemoteModuleWriter(
                self.module_version,
                self.module_root_dir,
                self.xios_repository_url,
                self.xios_revision_number,
                self.xios_external_url,
                self.suite_url,
                self.suite_revision_number,
                self.system_name)
        remote_mod_writer1.write_module()

        modules_to_load = []
        if self.use_oasis:
            modules_to_load += [self.get_oasis_module_path(True)]

        modules_to_load += [remote_mod_writer1.module_relative_path]

        remote_prg_env_writer1 = \
            XiosModuleWriter.XiosCrayRemotePrgEnvWriter(
                self.prg_env_version,
                self.module_root_dir,
                modules_to_load,
                self.system_name,
                self.suite_url,
                self.suite_revision_number)

        remote_prg_env_writer1.write_module()


class XiosLinuxIntelSystem(XiosBuildSystem):

    """
    Subclass of XiosBuildSystem that implements Xios build
    on Cray XC-40 system.

    WARNING!  Linux/Intel platform version of these build and
    test scripts is not currently working but should be fixed soon.
    """
    SYSTEM_NAME = 'UKMO_LINUX_INTEL'

    def __init__(self, settings_dict):
        """
        """
        XiosBuildSystem.__init__(self, settings_dict)
        self.arch_name = 'LINUX_INTEL'
        self.file_name_base = 'arch-{0}'.format(self.arch_name)

    def create_build_command(self):
        """
        Write out the build script to a file (verbose mode only).
        """

        xios_src_dir = os.path.join(self.working_dir, self.library_name)
        build_cmd = ''

        build_cmd += '. /data/cr1/mhambley/modules/setup\n'
        for mod_1 in self.prerequisite_modules:
            build_cmd += 'module load {0}\n'.format(mod_1)
        build_cmd += '\n'
        build_cmd += '\ncd {0}\n\n'.format(xios_src_dir)
        build_cmd += './make_xios --dev --arch {0}'.format(self.arch_name)
        if self.do_clean_build:
            build_cmd += ' --full '
        if self.use_oasis:
            build_cmd += ' --use_oasis oasis3_mct '
        build_cmd += ' --job {0} '.format(self.number_of_build_tasks)
        build_cmd += '\n'

        if self.verbose:
            build_script_file_name = os.path.join(self.working_dir,
                                                  BUILD_SCRIPT_FILENAME)

            if os.path.exists(build_script_file_name) and \
                    os.path.isfile(build_script_file_name):
                os.remove(build_script_file_name)

            with open(build_script_file_name, 'w') as build_script:
                build_script.write('#!/bin/sh\n')
                build_script.write(build_cmd)
        return build_cmd

    def setup_arch_fcm_file(self, file_name):
        """
        Sets up the arch.fcm file used in the build.
        """
        with open(file_name, 'w') as fcm_file:
            fcm_file.write('###################################################'
                           '#############################\n')
            fcm_file.write('###################'
                           '        Projet xios - xmlioserver       '
                           '#####################\n')
            fcm_file.write('###################################################'
                           '#############################\n')
            fcm_file.write('%CCOMPILER      mpicc\n')
            fcm_file.write('%FCOMPILER      mpif90\n')
            fcm_file.write('%LINKER         mpif90\n')
            fcm_file.write('\n')
            fcm_file.write('%BASE_CFLAGS    -w\n')
            fcm_file.write('%PROD_CFLAGS    -O3 -DBOOST_DISABLE_ASSERTS\n')
            fcm_file.write('%DEV_CFLAGS     -g -O2\n')
            fcm_file.write('%DEBUG_CFLAGS   -DBZ_DEBUG -g -fno-inline\n')
            fcm_file.write('\n')
            fcm_file.write('%BASE_FFLAGS    -D__NONE__\n')
            fcm_file.write('%PROD_FFLAGS    -O3\n')
            fcm_file.write('%DEV_FFLAGS     -g -O2 -traceback\n')
            fcm_file.write('%DEBUG_FFLAGS   -g -traceback\n')
            fcm_file.write('\n')
            fcm_file.write('%BASE_INC       -D__NONE__\n')
            fcm_file.write('%BASE_LD        -lstdc++ -lifcore -lintlc\n')
            fcm_file.write('\n')
            fcm_file.write('%CPP            cpp\n')
            fcm_file.write('%FPP            cpp -P\n')
            fcm_file.write('%MAKE           gmake\n')
            fcm_file.write('\n')

    def setup_arch_path_file(self, file_name):
        """
        Sets up the arch.path file used in the build.
        """
        with open(file_name, 'w') as path_file:
            path_file.write('NETCDF_INCDIR="-I$NETCDF_ROOT/include"\n')
            path_file.write('NETCDF_LIBDIR="-L$NETCDF_ROOT/lib"\n')
            path_file.write('\n')
            path_file.write('NETCDF_LIB="-lnetcdf"\n')
            path_file.write('\n')
            path_file.write('MPI_INCDIR=""\n')
            path_file.write('MPI_LIBDIR=""\n')
            path_file.write('MPI_LIB=""\n')
            path_file.write('\n')
            path_file.write('HDF5_INCDIR="-I$HDF5_ROOT/include"\n')
            path_file.write('HDF5_LIBDIR="-I$HDF5_ROOT/lib"\n')
            path_file.write('HDF5_LIB="-I$HDF5_ROOT/lib"\n')
            path_file.write('\n')
            path_file.write('\n')
            if self.use_oasis:
                path_file.write('OASIS_INCDIR='
                                '"-I$PWD/../../oasis3-mct/BLD/'
                                'build/lib/psmile.MPI1"\n')
                path_file.write('OASIS_LIBDIR='
                                '"-L$PWD/../../oasis3-mct/BLD/lib"\n')
                path_file.write('OASIS_LIB='
                                '"-lpsmile.MPI1 -lscrip -lmct -lmpeu"\n')
            else:
                path_file.write('OASIS_INCDIR=""\n')
                path_file.write('OASIS_LIBDIR=""\n')
                path_file.write('OASIS_LIB=""\n')

    def setup_arch_env_file(self, file_name, oasis_root_path):
        """
        Sets up the arch.env file used in the build.
        """
        # no arch.env needed for desktop system
        return

    def create_module(self):
        """
        Create a module file and associated package files for XIOS.
        """
        if not os.path.exists(self.module_root_dir):
            os.makedirs(self.module_root_dir)
        elif not os.path.isdir(self.module_root_dir):
            err_msg1 = 'Module install directory {0} not found, module '\
                       'not deployed.\n'.format(self.module_root_dir)
            raise common.ModuleCreationError(err_msg1)

        module_package_directory = os.path.join(self.module_root_dir,
                                                'packages',
                                                self.library_name,
                                                self.module_version)
        self.copy_files_to_dir(module_package_directory)

        mw1 = XiosModuleWriter.XiosLinuxIntelModuleWriter(
            self.module_version,
            self.module_root_dir,
            self.xios_repository_url,
            self.xios_revision_number,
            self.system_name)
        mw1.write_module()


def create_build_system(system_name, build_settings):
    """
    usage:
    bs1 = create_build_system(system_name, build_settings)

    Inputs:
    system_name - The name of the platform to be built on (e.g. UKMO_CRAY_XC40)
    build_settings - A dictionary of built setting, usually based on os.environ
    """
    system1 = None
    if system_name == XiosCrayBuildSystem.SYSTEM_NAME:
        system1 = XiosCrayBuildSystem(build_settings)
    elif system_name == common.SYSTEM_NAME_MONSOON:
        system1 = XiosCrayBuildSystem(build_settings)
    elif system_name == XiosLinuxIntelSystem.SYSTEM_NAME:
        system1 = XiosLinuxIntelSystem(build_settings)
    else:
        raise common.ConfigError('invalid build system name')
    return system1
