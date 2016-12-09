#!/usr/bin/env python2.7
"""
Unit test module to test Nemo build scripts.
"""
import unittest
import os
import filecmp
import abc

# this must be imported before the other local imports as it sets up the path
# to import the main scripts
import unit_test_common

import common
import NemoBuildSystem

class NemoBuildTests(unittest.TestCase):
    """
    Class to test Nemo build scripts
    """

    CONFIG_LIST = ['NEMO', 'NEMO_unit', 'XIOS-app']
    def setUp(self):
        """
        Setup class to test Nemo build scripts
        """
        self.config_list = NemoBuildTests.CONFIG_LIST
        self.system_name = self.get_system_name()
        self.settings_dir = unit_test_common.get_settings_dir()

        setup_dict = unit_test_common.get_settings(self.config_list,
                                                   self.settings_dir,
                                                   self.system_name)

        self.repo_url = setup_dict['NEMO_REPO_URL']
        self.rev_no = setup_dict['NEMO_REV']
        self.use_oasis = setup_dict['USE_OASIS'] == 'true'

        self.build_system = \
            NemoBuildSystem.create_nemo_build_system(self.system_name,
                                                     setup_dict)

    @abc.abstractmethod
    def get_system_name(self):
        """
        Get the name of the build system
        """
        pass

    def get_settings(self):
        """
        Get the settings for running the unit tests. If we are in a rose suite
        we will use the settings provided. If not in a rose suite, we can use
        the settings provided in .conf files in the local copy.
        """
        if os.environ.has_key('ROSE_SUITE_NAME'):
            settings_dict = os.environ
        else:
            settings_dict = self.get_settings_from_conf()
        return settings_dict

    def tearDown(self):
        """
        Cleanup after tests of Nemo build scripts
        """
        self.build_system = None

    def test_build_system_creation(self):
        """
        Test the creation of NemoBuildSystem object
        """
        err_msg1 = 'System names do not match {0}!={1}'
        err_msg1 = err_msg1.format(self.system_name,
                                   self.build_system.system_name)
        self.assertEqual(self.build_system.system_name,
                         self.system_name,
                         err_msg1)
        err_msg1 = 'repository URLS  do not match {0}!={1}'
        err_msg1 = err_msg1.format(self.repo_url,
                                   self.build_system.repository_url)
        self.assertEqual(self.repo_url,
                         self.build_system.repository_url,
                         err_msg1)

        err_msg1 = 'NEMO revision numbers  do not match {0}!={1}'
        err_msg1 = err_msg1.format(self.rev_no,
                                   self.build_system.revision_number)
        self.assertEqual(self.build_system.revision_number,
                         self.rev_no,
                         err_msg1)

        self.assertEqual(self.build_system.use_oasis,
                         self.use_oasis,
                         'Oasis flags do not match')

    def test_setup_files(self):
        """
        Test the NemoBuildSystem.check_arch_files() function.
        """
        self.build_system.setup_files()

        self.check_arch_files()
        self.check_source_files()

    def check_arch_files(self):
        """
        Check that the NEMO arch files have been correctly written out.
        """
        arch_file_string = """%NCDF_HOME           $NETCDF_DIR
%HDF5_HOME           $HDF5_DIR
%XIOS_HOME           {xios_directory}
%OASIS_HOME           {oasis_directory}

%NCDF_INC            -I%NCDF_HOME/include -I%HDF5_HOME/include
%NCDF_LIB            -L%HDF5_HOME/lib -L%NCDF_HOME/lib -lnetcdff -lnetcdf -lhdf5_hl -lhdf5 -lz

%XIOS_INC            -I%XIOS_HOME/inc
%XIOS_LIB            -L%XIOS_HOME/lib -lxios

%OASIS_INC           -I%OASIS_HOME/build/lib/mct -I%OASIS_HOME/build/lib/psmile.MPI1
%OASIS_LIBDIR        -L%OASIS_HOME/lib
%OASIS_LIB           -lpsmile.MPI1 -lmct -lmpeu -lscrip
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

%USER_INC            %NCDF_INC %OASIS_INC %XIOS_INC
%USER_LIB            %NCDF_LIB %OASIS_LIBDIR %OASIS_LIB %XIOS_LIB %OASIS_LIB
"""
        arch_file_string = arch_file_string.format(**self.build_system.__dict__)
        ref_file_name = 'nemo_archFile_{0}_reference.fcm'
        ref_file_name = ref_file_name.format(self.build_system.system_name)
        reference_file_path = os.path.join(self.build_system.working_dir,
                                           ref_file_name)

        with open(reference_file_path, 'w') as ref_file:
            ref_file.write(arch_file_string)

        arch_file_path = os.path.join(self.build_system.source_directory,
                                      'ARCH',
                                      self.build_system.arch_file_name)

        err_msg1 = 'arch file {0} does not match reference {1}'
        err_msg1 = err_msg1.format(arch_file_path,
                                   reference_file_path)
        self.assertTrue(filecmp.cmp(reference_file_path,
                                    arch_file_path),
                        err_msg1)

    def check_source_files(self):
        """
        Check that the correct source files have been extracted.
        """
        src_file_list = [os.path.join(self.build_system.working_dir,
                                      self.build_system.library_name,
                                      'CONFIG',
                                      'makenemo'),
                         os.path.join(self.build_system.working_dir,
                                      self.build_system.library_name,
                                      'ARCH',
                                      'arch-XC40_METO.fcm')]

        err_msg1 = 'source file {0} not found'
        for file1 in src_file_list:
            self.assertTrue(os.path.exists(file1),
                            err_msg1.format(file1))

    def test_write_build_script(self):
        """
        Test the NemoBuildSystem.create_build_command() function.
        """
        # change source directory as the source directory is not created
        # for this test
        self.build_system.source_directory = self.build_system.working_dir
        self.build_system.create_build_command()
        build_script_file_path = '{workingDir}/{fileName}'
        build_script_file_path = build_script_file_path.format(
            workingDir=self.build_system.working_dir,
            fileName=NemoBuildSystem.BUILD_SCRIPT_FILENAME)

        ref_build_script_str = """#!/bin/sh
cd {source_directory}/CONFIG
./makenemo -m {system_name} -r {nemo_config} -n {nemo_config_build_name} -j {number_of_build_processors} add_key "{build_keys}" del_key "{remove_keys}"
"""
        ref_build_script_str = \
            ref_build_script_str.format(**self.build_system.__dict__)

        ref_file_name = 'nemo_buildScript_{0}_reference.sh'
        ref_file_name = ref_file_name.format(self.build_system.system_name)
        ref_file_path = os.path.join(self.build_system.working_dir,
                                     ref_file_name)

        with open(ref_file_path, 'w') as ref_file:
            ref_file.write(ref_build_script_str)

        err_msg1 = 'arch file {0} does not match reference {1}'
        err_msg1 = err_msg1.format(build_script_file_path,
                                   ref_file_path)
        self.assertTrue(filecmp.cmp(ref_file_path,
                                    build_script_file_path),
                        err_msg1)

class NemoBuildLinuxIntelTests(unittest.TestCase):
    """
    Class to test Nemo build script on the UKMO Linux desktop with
    Intel compiler
    """
    def setUp(self):
        """
        Setup class to test Nemo build script on the v
        """
        setup_dict = {}
        self.system_name = 'UKMO_LINUX_INTEL'
        setup_dict['SYSTEM_NAME'] = self.system_name
        setup_dict['NEMO'] = 'NEMO'
        self.repo_url = 'svn://fcm3/NEMO.xm_svn/branches/dev/shaddad/'\
                        'r5643_buildWithOasisNoKeys/NEMOGCM'
        setup_dict['NEMO_REPO_URL'] = self.repo_url
        self.rev_no = '5648'
        setup_dict['NEMO_REV'] = self.rev_no
        self.use_oasis = False
        if self.use_oasis:
            setup_dict['USE_OASIS'] = 'true'
            setup_dict['OASIS_ROOT'] = ('/path/to/oasis')
        else:
            setup_dict['USE_OASIS'] = 'false'
            setup_dict['OASIS_ROOT'] = ''
        setup_dict['JP_CFG'] = '50'
        setup_dict['BUILD_PATH'] = '{0}/install'.format(os.getcwd())
        setup_dict['NEMO_POST_BUILD_CLEANUP'] = 'false'
        setup_dict['XIOS_PATH'] = '/projects/moci/modules/packages/XIOS/1.0'

        self.build_system = \
            NemoBuildSystem.NemoLinuxIntelBuildSystem(setup_dict)

    def tearDown(self):
        """
        Cleanup after tests of Nemo build scripts on the UKMO Linux desktop with
        Intel compiler
        """
        self.build_system = None

    def test_build_system_creation(self):
        """
        Test the creation of NemoBuildSystem object
        """
        err_msg1 = 'System names do not match {0}!={1}'
        err_msg1 = err_msg1.format(self.system_name,
                                   self.build_system.system_name)
        self.assertEqual(self.build_system.system_name,
                         self.system_name,
                         err_msg1)
        err_msg1 = 'repository URLS  do not match {0}!={1}'
        err_msg1 = err_msg1.format(self.repo_url,
                                   self.build_system.repository_url)
        self.assertEqual(self.repo_url,
                         self.build_system.repository_url,
                         err_msg1)

        err_msg1 = 'NEMO revision numbers  do not match {0}!={1}'
        err_msg1 = err_msg1.format(self.rev_no,
                                   self.build_system.revision_number)
        self.assertEqual(self.build_system.revision_number,
                         self.rev_no,
                         err_msg1)

        self.assertEqual(self.build_system.use_oasis,
                         self.use_oasis,
                         'Oasis flags do not match')

        self.build_system.setup_files()

        self.check_arch_files()
        self.check_source_files()

    def check_arch_files(self):
        """
        Check that the NEMO arch files have been correctly written out.
        """
        arch_file_string = """%XIOS_HOME           {XiosDirectory}

%OASIS_HOME
%NCDF_INC            -I$NETCDF_ROOT/include/
%NCDF_LIB            -L$NETCDF_ROOT/lib -lnetcdf -lnetcdff
%XIOS_INC            -I%XIOS_HOME/inc
%XIOS_LIB            -L%XIOS_HOME/lib -lxios

%OASIS_INC
%OASIS_LIB

%FC                  mpif90
%FCFLAGS            -r8 -xHOST  -traceback
%FFLAGS                -r8 -xHOST  -traceback
%LD                  mpif90
%CPP                 cpp
%FPPFLAGS            -P -C -traditional
%LDFLAGS             -lstdc++
%AR                  ar
%ARFLAGS             -r
%MK                  gmake
%USER_INC            %XIOS_INC %NCDF_INC
%USER_LIB            %XIOS_LIB %NCDF_LIB
"""
        arch_file_string = arch_file_string.format(**self.build_system.__dict__)
        reference_file_path = '{0}/nemo_archFile_{1}_reference.fcm'
        reference_file_path = reference_file_path.format(
            self.build_system.working_dir,
            self.build_system.system_name)
        with open(reference_file_path, 'w') as ref_file:
            ref_file.write(arch_file_string)

        arch_file_path = '{0}/ARCH/{1}'.format(
            self.build_system.source_directory,
            self.build_system.arch_file_name)

        err_msg1 = 'arch file {0} does not match reference {1}'
        err_msg1 = err_msg1.format(arch_file_path,
                                   reference_file_path)
        self.assertTrue(filecmp.cmp(reference_file_path,
                                    arch_file_path),
                        err_msg1)

    def check_source_files(self):
        """
        Check that the correct source files have been extracted.
        """
        src_file_list = [
            '{0}/CONFIG/makenemo'
            .format(self.build_system.library_name),
            '{0}/ARCH/arch-XC40_METO.fcm'
            .format(self.build_system.library_name)]

        err_msg1 = 'source file {0} not found'
        for file1 in src_file_list:
            self.assertTrue(os.path.exists(file1),
                            err_msg1.format(file1))

    def test_write_build_script(self):
        """
        Test the NemoBuildSystem.create_build_command() function.
        """
        # change source directory as the source directory is not created
        # for this test
        self.build_system.source_directory = self.build_system.working_dir
        self.build_system.create_build_command()
        build_script_file_path = '{0}/{1}'.format(
            self.build_system.working_dir,
            NemoBuildSystem.BUILD_SCRIPT_FILENAME)

        ref_build_script_str = """#!/bin/sh
cd {source_directory}/CONFIG
source /data/cr1/mhambley/modules/setup
module load environment/dynamo/compiler/intelfortran/15.0.0


./makenemo -m {system_name} -r {nemo_config} -n {nemo_config_build_name} -j {number_of_build_processors} add_key "key_mpp_mpi key_iomput"

"""
        ref_build_script_str = \
            ref_build_script_str.format(**self.build_system.__dict__)

        ref_file_path = '{0}/nemo_buildScript_{1}_reference.sh'
        ref_file_path = ref_file_path.format(self.build_system.working_dir,
                                             self.build_system.system_name)
        with open(ref_file_path, 'w') as ref_file:
            ref_file.write(ref_build_script_str)


        err_msg1 = 'arch file {0} does not match reference {1}'
        err_msg1 = err_msg1.format(build_script_file_path,
                                   ref_file_path)
        self.assertTrue(filecmp.cmp(ref_file_path,
                                    build_script_file_path),
                        err_msg1)

class NemoBuildCrayTests(NemoBuildTests):
    """
    Unit test class for running Nemo Build tests on Mett Office Cray XC40
    """
    def get_system_name(self):
        return NemoBuildSystem.NemoCrayXC40BuildSystem.SYSTEM_NAME

class NemoBuildMonsoonTests(NemoBuildCrayTests):
    """
    Unit test class for running Nemo Build tests on Monsoon
    """
    def get_system_name(self):
        return unit_test_common.SYSTEM_NAME_MONSOON


class NemoBuildExternalTests(NemoBuildCrayTests):
    """
    Unit test class for running Nemo Build tests on an external system
    """
    def get_system_name(self):
        return common.SYSTEM_NAME_EXTERNAL

def suite():
    """
    Build up the NEMO build unit test suite.
    """
    return_suite = \
        unittest.TestLoader().loadTestsFromTestCase(NemoBuildCrayTests)
    return return_suite

def main():
    """
    Entry function for running only the NEMO build tests
    """
    test_list_dict = {}
    test_list_dict[NemoBuildSystem.NemoCrayXC40BuildSystem.SYSTEM_NAME] = [
        NemoBuildCrayTests]
    test_list_dict[unit_test_common.SYSTEM_NAME_MONSOON] = [
        NemoBuildCrayTests]
    test_list_dict[common.SYSTEM_NAME_EXTERNAL] = [
        NemoBuildExternalTests]
    unit_test_common.run_tests(test_list_dict)

if __name__ == '__main__':
    main()
