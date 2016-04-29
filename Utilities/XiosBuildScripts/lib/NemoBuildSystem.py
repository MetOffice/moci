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
   NemoBuildSystem.py

"""
import os
import subprocess
import shutil
import abc
import textwrap

import common

BUILD_SCRIPT_FILENAME = 'nemoBuildScript01.sh'
EXTRACT_SCRIPT_FILENAME = 'nemoExtractScript01.sh'


class NemoInvalidSourceCodeOptionError(Exception):

    """
    Exception raised if the there is an invalid option chosen for
    the source code location type.
    """
    pass


class NemoBuildSystem(common.XbsBase):

    """
    Base class for building the NEMO executable.
    """
    __metaclass__ = abc.ABCMeta
    SYSTEM_NAME = 'BASE_CLASS'

    def __init__(self, settings_dict):

        common.XbsBase.__init__(self, settings_dict)

        self.modules_to_load = []
        self.library_name = settings_dict['NEMO']
        self.source_directory = '{0}/{1}'.format(self.working_dir,
                                                 self.library_name)
        self.source_code_location_type = \
            settings_dict['NEMO_SRC_LOCATION_TYPE']
        self.repository_url = settings_dict['NEMO_REPO_URL']
        self.revision_number = settings_dict['NEMO_REV']

        if self.source_code_location_type == 'URL':
            pass
        elif self.source_code_location_type == 'local':
            # repository URL and revision only used for info purposes
            # as the source code is actually retrieved from disk
            self.source_code_dir = settings_dict['NEMO_SRC_CODE_DIR']
        else:
            raise NemoInvalidSourceCodeOptionError()
        self.build_path = settings_dict['BUILD_PATH']
        self.xios_directory = settings_dict['XIOS_PATH']
        self.use_oasis = settings_dict['USE_OASIS'] == 'true'
        if self.use_oasis:
            self.oasis_directory = settings_dict['OASIS_ROOT']
        else:
            self.oasis_directory = ''
        self.nemo_config = 'GYRE'
        self.config_suffix = settings_dict['JP_CFG']
        self.nemo_config_build_name = '{0}_{1}'.format(self.nemo_config,
                                                       self.config_suffix)
        self.oasis_fcflags = ''
        self.oasis_ldflags = ''
        self.tar_command = 'tar'
        self.arch_file_name = None
        self.do_post_build_cleanup = \
            settings_dict['NEMO_POST_BUILD_CLEANUP'] == 'true'
        self.number_of_build_processors = 4

    def __str__(self):
        return 'Nemo build system base class'

    def run_build(self):
        """
        Main build function.
        """
        self.setup_files()
        build_command = self.create_build_command()
        self.execute_build_command(build_command)
        self.check_build()
        self.copy_files()
        self.cleanup()

    def setup_files(self):
        """
        Retrieve NEMO source code and write out arch and config files
        for the particular platform.
        """
        self.get_source_code()
        self.write_arch_files()

    def get_source_code(self):
        """
        Retrieve the NEMO source code either from a repository specified by
        a URL, or copy from a directory.
        """
        if self.source_code_location_type == 'URL':
            self.extract_from_repository()
        elif self.source_code_location_type == 'local':
            self.copy_from_directory()
        else:
            raise NemoInvalidSourceCodeOptionError()

    def extract_from_repository(self):
        """
        Extract the NEMO source code from
        self.repository_url @ self.revision_number
        """
        destination_dir = self.source_directory
        if os.path.exists(destination_dir) and os.path.isdir(destination_dir):
            shutil.rmtree(destination_dir)

        extract_cmd1 = '''
fcm co {repository_url}@{revision_number} {destination_dir}
'''.format(destination_dir=destination_dir,
           **self.__dict__)

        if self.verbose:
            script_file_name = os.path.join(self.working_dir,
                                            EXTRACT_SCRIPT_FILENAME)
            if os.path.exists(script_file_name) \
                    and os.path.isfile(script_file_name):
                os.remove(script_file_name)

            with open(script_file_name, 'w') as extract_script:
                extract_script.write('#!/bin/sh\n')
                extract_script.write(extract_cmd1)

        print '\nexecuting fcm check-out command\n'
        result1 = subprocess.call(extract_cmd1, shell=True)
        if result1 != 0:
            err_msg1 = \
                'Error extracting {0} source code'.format(self.library_name)
            raise common.SourceCodeExtractionError(err_msg1)

    def copy_from_directory(self):
        """
        Copy the NEMO source code from the directory given by
        self.source_code_dir
        """
        # if source code directory already exists, delete to ensure correct
        # version of code is present.
        if os.path.exists(self.source_directory):
            os.rmdir(self.source_directory)

        os.mkdir(self.source_directory)

        print 'copying source code from {SRC} to {DEST}'\
              .format(SRC=self.source_code_dir,
                      DEST=self.source_directory)

        shutil.copytree(self.source_code_dir,
                        self.source_directory)

    @abc.abstractmethod
    def write_arch_files(self):
        """
        Write out the arch file used by the make_nemo script to define the
        build config for the platform.
        """
        pass

    @abc.abstractmethod
    def create_build_command(self):
        """
        Using the user specified, construct the build command which calls the
        make_nemo build script with the relvant options.
        """
        pass

    def execute_build_command(self, build_command):
        """
        Execute the command given by the build_command argument. The
        build_command should be created by create_build_command.
        """
        print 'executing build command'
        return_code = subprocess.call(build_command, shell=True)
        if return_code != 0:
            raise common.BuildError('Error compiling NEMO: build failed!')

    def check_build(self):
        """
        Check that the expected build output is present.
        """
        nemo_exe_path = os.path.join(self.working_dir,
                                     self.library_name,
                                     'CONFIG',
                                     self.nemo_config_build_name,
                                     'BLD',
                                     'bin',
                                     'nemo.exe')

        if not os.path.exists(nemo_exe_path):
            err_msg1 = 'NEMO executable file not found at {0}, build failed!'
            err_msg1 = err_msg1.format(nemo_exe_path)
            raise common.BuildError(err_msg1)

    def copy_files(self):
        """
        Copy the build output files to the specified directory.
        """
        dest_base = os.path.join(self.build_path,
                                 self.library_name)
        print 'copying output files'
        if os.path.exists(dest_base) and os.path.isdir(dest_base):
            print 'removing dir {0}'.format(dest_base)
            shutil.rmtree(dest_base)

        source_dir = os.path.join(self.working_dir,
                                  self.library_name,
                                  'CONFIG',
                                  self.nemo_config_build_name)

        dest_dir = os.path.join(dest_base,
                                self.nemo_config_build_name)
        msg1 = 'copying {2} config directory from  {0} to {1}'
        msg1 = msg1.format(source_dir,
                           dest_dir,
                           self.nemo_config_build_name)
        print msg1
        shutil.copytree(source_dir, dest_dir)

        source_shared_dir = os.path.join(self.working_dir,
                                         self.library_name,
                                         'CONFIG',
                                         'SHARED')
        dest_shared_dir = os.path.join(dest_base,
                                       'SHARED')
        print 'copying SHARED directory from  {0} to {1}'\
              .format(source_shared_dir, dest_shared_dir)

        shutil.copytree(source_shared_dir, dest_shared_dir)

    def cleanup(self):
        """
        If do_post_build_cleanup flag is true, remove the build directory
        """
        if self.do_post_build_cleanup:
            print 'removing build working directory {0}'\
                  .format(self.source_directory)
            shutil.rmtree(self.source_directory)


class NemoCrayXC40BuildSystem(NemoBuildSystem):

    """
    The class for building NEMO on the Met Office Cray XC40 supercomputer.
    """
    SYSTEM_NAME = 'UKMO_CRAY_XC40'

    def __init__(self, settings_dict):
        """
        The constructor for the class for building NEMO on the Met Office
        Cray XC40 supercomputer.
        """
        NemoBuildSystem.__init__(self, settings_dict)

        self.arch_file_name = 'arch-CRAY_XC40.fcm'
        self.modules_to_load += ['cray-hdf5-parallel/1.8.13']
        self.modules_to_load += ['cray-netcdf-hdf5parallel/4.3.2']
        if self.use_oasis:
            self.oasis_fcflags = '-I{0}/build'.format(self.oasis_directory)
            self.oasis_ldflags = \
                '-L{0}/lib -lmct -lmpeu -lscrip -lpsmile.MPI1'\
                .format(self.oasis_directory)
        self.tar_command = 'tar'
        self.arch_file_name = \
            'arch-{0}.fcm'.format(self.system_name)

    def __str__(self):
        """
        """
        return 'Nemo build system for UKMO Cray XC40 HPC'

    def write_arch_files(self):
        """
        Write out the arch file used by the make_nemo script to define the
        build config for the platform.
        """
        arch_str1 = '''%NCDF_HOME           $NETCDF_DIR
%HDF5_HOME           $HDF5_DIR
%XIOS_HOME           {xios_directory}
%OASIS_HOME           {oasis_directory}

%NCDF_INC            -I%NCDF_HOME/include -I%HDF5_HOME/include
%NCDF_LIB            -L%HDF5_HOME/lib -L%NCDF_HOME/lib -lnetcdff -lnetcdf -lhdf5_hl -lhdf5 -lz

%XIOS_INC            -I%XIOS_HOME/inc
%XIOS_LIB            -L%XIOS_HOME/lib -lxios
'''
        if self.use_oasis:
            arch_str1 += '''
%OASIS_INC           -I%OASIS_HOME/build/lib/mct -I%OASIS_HOME/build/lib/psmile.MPI1
%OASIS_LIBDIR        -L%OASIS_HOME/lib
%OASIS_LIB           -lpsmile.MPI1 -lmct -lmpeu -lscrip'''
        else:
            arch_str1 += '''
%OASIS_INC
%OASIS_LIBDIR
OASIS_LIB'''

        arch_str1 += '''
%CPP                 cpp
%FC                  ftn

%FCFLAGS             -em -s real64 -s integer32  -O2 -hflex_mp=intolerant -e0 -ez
%FFLAGS              -em -s real64 -s integer32  -O0 -hflex_mp=strict -e0 -ez -Rb
%LD                  ftn
%FPPFLAGS            -P -E -traditional-cpp
%LDFLAGS             -hbyteswapio
%AR                  ar
%ARFLAGS             -r
%MK                  gmake
'''
        if self.use_oasis:
            arch_str1 += '''
%USER_INC            %NCDF_INC %OASIS_INC %XIOS_INC
%USER_LIB            %NCDF_LIB %OASIS_LIBDIR %OASIS_LIB %XIOS_LIB %OASIS_LIB
'''
        else:
            arch_str1 += '''
%USER_INC            %NCDF_INC %XIOS_INC
%USER_LIB            %NCDF_LIB %XIOS_LIB
'''

        arch_str1 = arch_str1.format(**self.__dict__)

        arch_file_path = os.path.join(self.source_directory,
                                      'ARCH',
                                      self.arch_file_name)
        with open(arch_file_path, 'w') as arch_file:
            arch_file.write(arch_str1)

    def create_build_command(self):
        """
        Using the user specified, construct the build command which calls the
        make_nemo build script with the relvant options.
        """
        build_str1 = 'cd {source_directory}/CONFIG\n'
#        for module1 in self.modules_to_load:
#            build_str1 += 'module load {0}\n'.format(module1)
        build_str1 += './makenemo -m {system_name} -r {nemo_config} '\
                      '-n {nemo_config_build_name} '\
                      '-j {number_of_build_processors} '\
                      'add_key "key_mpp_mpi key_iomput"\n'

        build_str1 = build_str1.format(**self.__dict__)

        if self.verbose:
            build_script_file_name = '{0}/{1}'.format(self.working_dir,
                                                      BUILD_SCRIPT_FILENAME)
            if os.path.exists(build_script_file_name) \
                    and os.path.isfile(build_script_file_name):
                os.remove(build_script_file_name)

            with open(build_script_file_name, 'w') as build_script:
                build_script.write('#!/bin/sh\n')
                build_script.write(build_str1)

            msg1 = 'build command written to {0}'
            msg1 = msg1.format(build_script_file_name)
            print msg1

        return build_str1


class NemoLinuxIntelBuildSystem(NemoBuildSystem):

    """
    The class for building NEMO on the Met Office Cray Linux desktop with
    Intel compiler environment.

    WARNING!  Linux/Intel platform version of these build and
    test scripts is not currently working but should be fixed soon.
    """
    SYSTEM_NAME = 'UKMO_LINUX_INTEL'

    def __init__(self, settingsDict):
        """
        The constructor for the class for building NEMO on the Met Office
        Cray XC40 supercomputer.
        """
        NemoBuildSystem.__init__(self, settingsDict)
        self.tar_command = 'tar'
        self.arch_file_name = 'arch-{0}.fcm'.format(self.SYSTEM_NAME)

        self.modules_to_load += \
            ['environment/dynamo/compiler/intelfortran/15.0.0']

    def __str__(self):
        return '\n'.join(textwrap.wrap('Nemo build system for Linux (UKMO '
                                       'scientific desktop) with Intel compiler'
                                       'environment.'))

    def write_arch_files(self):
        """
        Write out the arch file used by the make_nemo script to define the
        build config for the platform.
        """
        arch_str1 = '%XIOS_HOME           {xios_directory}\n'
        if self.use_oasis:
            arch_str1 += '%OASIS_HOME {oasis_directory}\n'
        else:
            arch_str1 += '%OASIS_HOME\n'
        arch_str1 += '''
%NCDF_INC            -I$NETCDF_ROOT/include/\n')
%NCDF_LIB            -L$NETCDF_ROOT/lib -lnetcdf -lnetcdff\n')
%XIOS_INC            -I%XIOS_HOME/inc\n')
%XIOS_LIB            -L%XIOS_HOME/lib -lxios\n')
'''
        if self.use_oasis:
            arch_str1 += '''
%OASIS_INC           -I%OASIS_HOME/build/lib/mct -I%OASIS_HOME/build/lib/psmile.MPI1
%OASIS_LIB           -L%OASIS_HOME/lib -lpsmile.MPI1 -lmct -lmpeu -lscrip
'''
        else:
            arch_str1 += '''
%OASIS_INC
%OASIS_LIB
'''
        arch_str1 += '''
%FC                  mpif90\n')
%FCFLAGS            -r8 -xHOST  -traceback\n')
%FFLAGS                -r8 -xHOST  -traceback\n')
%LD                  mpif90\n')
%CPP                 cpp\n')
%FPPFLAGS            -P -C -traditional\n')
%LDFLAGS             -lstdc++\n')
%AR                  ar\n')
%ARFLAGS             -r\n')
%MK                  gmake\n')
%USER_INC            %XIOS_INC %NCDF_INC\n')
%USER_LIB            %XIOS_LIB %NCDF_LIB\n')
'''
        arch_str1 = arch_str1.format(**self.__dict__)

        arch_file_path = os.path.join(self.source_directory,
                                      'ARCH',
                                      self.arch_file_name)
        with open(arch_file_path, 'w') as arch_file:
            arch_file.write(arch_str1)

    def create_build_command(self):
        """
        Using the user specified, construct the build command which calls the
        make_nemo build script with the relvant options.
        """
        build_str1 = 'cd {SourceDirectory}/CONFIG\n'
        # TODO: take in location as an option
        build_str1 += 'source /data/cr1/mhambley/modules/setup\n'
#        for module1 in self.modules_to_load:
#            build_str1 +='module load {0}\n'.format(module1)
        build_str1 += '\n'
        build_str1 += './makenemo -m {system_name} -r {nemo_config}'\
                      '-n {nemo_config_build_name} '\
                      '-j {number_of_build_processors} '\
                      'add_key "key_mpp_mpi key_iomput"\n'

        build_str1 = build_str1.format(**self.__dict__)

        if self.verbose:
            build_script_file_name = '{0}/{1}'.format(self.working_dir,
                                                      BUILD_SCRIPT_FILENAME)
            if os.path.exists(build_script_file_name) \
                    and os.path.isfile(build_script_file_name):
                os.remove(build_script_file_name)

            with open(build_script_file_name, 'w') as build_script:
                build_script.write('#!/bin/sh\n')
                build_script.write(build_str1)

        return build_str1


def create_nemo_build_system(system_name):
    """
    Factory method to create a class for building NEMO on the platform
    specified by system_name.
    """
    build_system1 = None
    if system_name == NemoCrayXC40BuildSystem.SYSTEM_NAME:
        build_system1 = NemoCrayXC40BuildSystem(os.environ)
    elif system_name == common.SYSTEM_NAME_MONSOON:
        build_system1 = NemoCrayXC40BuildSystem(os.environ)
    elif system_name == NemoLinuxIntelBuildSystem.SYSTEM_NAME:
        build_system1 = NemoLinuxIntelBuildSystem(os.environ)
    return build_system1
