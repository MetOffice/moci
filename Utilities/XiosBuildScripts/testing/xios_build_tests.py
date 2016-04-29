#!/usr/bin/env python2.7
"""
Unit test module to test XIOS build scripts.
"""
import unittest
import os
import filecmp

import XiosBuildSystem
import XiosModuleWriter

class XiosBuildCrayTests(unittest.TestCase):
    """
    Class to XIOS build tests on UKMO Cray XC40
    """
    def setUp(self):
        """
        Setup XIOS build tests on Cray XC40
        """
        print 'Setting up tests'
        self.environment = {}
        self.system_name = 'UKMO_CRAY_XC40'
        self.environment['SYSTEM_NAME'] = self.system_name
        self.verbose = True
        if self.verbose:
            self.environment['VERBOSE'] = 'true'
        else:
            self.environment['VERBOSE'] = 'false'
        self.environment['XIOS_DO_CLEAN_BUILD'] = 'true'
        self.environment['XIOS_POST_BUILD_CLEANUP'] = 'false'
        self.environment['XIOS_SRC_LOCATION_TYPE'] = 'URL'
        self.xios_repo_url = 'svn://fcm1/xios.xm_svn/XIOS/branchs/xios-1.0'
        self.environment['XIOS_REPO_URL'] = self.xios_repo_url
        self.xios_rev_no = 'HEAD'
        self.environment['XIOS_REV'] = self.xios_rev_no
        self.environment['XIOS'] = 'XIOS'
        self.environment['USE_OASIS'] = 'false'
        self.environment['OASIS_ROOT'] = \
            '/home/d02/shaddad/Projects/GC3Port/r1217_port_mct_xcf/'\
            'oasis3-mct/crayxc40'
        self.environment['BUILD_PATH'] = '{0}/install'.format(os.getcwd())
        self.num_cores = 4
        self.environment['XIOS_NUM_CORES'] = str(self.num_cores)
        self.environment['XLF_MODULE'] = ''
        self.environment['XLCPP_MODULE'] = ''
        self.environment['DEPLOY_AS_MODULE'] = 'true'
        self.environment['MODULE_INSTALL_PATH'] = \
            '{0}/modules'.format(os.getcwd())
        self.environment['XIOS_MODULE_VERSION'] = '1.0'
        self.environment['XIOS_PRGENV_VERSION'] = '1.0'
        self.environment['OASIS_MODULE_VERSION'] = '1.0'
        self.environment['OASIS3_MCT'] = "oasis3-mct"
        self.environment['ROSE_SUITE_URL'] = 'path/to/repository'
        self.environment['ROSE_SUITE_REV_NO'] = '1234'
        self.external_repo_url = 'http://external.server.gov/path/to/repository'
        self.environment['XIOS_EXTERNAL_REPO_URL'] = self.external_repo_url
        self.environment['XBS_PREREQ_MODULES'] = \
            "['cray-hdf5-parallel/1.8.13',"\
            "'cray-netcdf-hdf5parallel/4.3.2']"

        # NOTE:
        self.build_system = \
            XiosBuildSystem.XiosCrayBuildSystem(self.environment)
        self.test_script_directory = os.path.dirname(os.path.realpath(__file__))

    def tearDown(self):
        """
        Clean up after XIOS build tests on Cray XC40
        """
        pass

    def test_setup(self):
        """
        Test creation of XiosBuildSystem object
        """
        self.assertEqual(self.build_system.number_of_build_tasks,
                         self.num_cores)
        self.assertEqual(self.build_system.system_name,
                         self.system_name)
        self.assertEqual(self.build_system.xios_repository_url,
                         self.xios_repo_url)
        self.assertEqual(self.external_repo_url,
                         self.build_system.xios_external_url)

    def test_extraction_script(self):
        """
        Test XiosBuildSystem.extract_xios_source_code() function
        """
        self.build_system.extract_xios_source_code()
        script_file_path = '{working_dir}/{file_name}'
        script_file_path = script_file_path.format(
            working_dir=self.build_system.working_dir,
            file_name=XiosBuildSystem.EXTRACT_SCRIPT_FILENAME)
        self.assertTrue(os.path.exists(script_file_path),
                        'script file {0} not found!'.format(script_file_path))
        # compare contents to reference file
        ref_file_path = '{0}/cray_xiosBuild_extractScript.sh'
        ref_file_path = ref_file_path.format(self.build_system.working_dir)

        dest_dir = os.path.join(self.build_system.working_dir,
                                self.build_system.library_name)
        extract_cmd_string = '''#!/bin/sh
fcm co svn://fcm1/xios.xm_svn/XIOS/branchs/xios-1.0@HEAD {dest_dir}
cd {dest_dir}
for i in tools/archive/*.tar.gz; do  tar -xzf $i; done
'''.format(dest_dir=dest_dir)

        with open(ref_file_path, 'w') as extractref_file:
            extractref_file.write(extract_cmd_string)

        assert_msg1 = 'script file {0} not identical to reference file {1}'
        assert_msg1 = assert_msg1.format(script_file_path,
                                         ref_file_path)
        self.assertTrue(
            filecmp.cmp(script_file_path,
                        ref_file_path,
                        shallow=False),
            assert_msg1)

        # check extracted source code for existence of some files
        extract_directory = '{0}/{1}'.format(self.build_system.working_dir,
                                             self.build_system.library_name)
        self.assertTrue(os.path.exists(extract_directory))
        self.assertTrue(os.path.isdir(extract_directory))
        file_check_list = ['{0}/make_xios'.format(extract_directory)]
        file_check_list += ['{0}/bld.cfg'.format(extract_directory)]
        file_check_list += ['{0}/src/xios_server.f90'.format(extract_directory)]
        for file_path1 in file_check_list:
            self.assertTrue(os.path.exists(file_path1),
                            ' file {0} not found'.format(file_path1))

    def test_write_module(self):
        """
        Test the XiosCrayModuleWriter class.
        """
        mw1 = XiosModuleWriter.XiosCrayModuleWriter( \
            self.build_system.module_version,
            self.build_system.module_root_dir,
            self.build_system.xios_repository_url,
            self.build_system.xios_revision_number,
            self.build_system.xios_external_url,
            self.build_system.suite_url,
            self.build_system.suite_revision_number,
            self.build_system.SYSTEM_NAME,
            self.build_system.prerequisite_modules)
        mw1.write_module()

        # check for existence of module
        temp_mod_str1 = '{root_dir}/modules/{rel_path}'
        module_file_path = temp_mod_str1.format(
            root_dir=self.build_system.module_root_dir,
            rel_path=mw1.module_relative_path)
        self.assertTrue(os.path.exists(module_file_path),
                        'Module file {0} not found'.format(module_file_path))

        # check contents
        reference_file_path = \
            '{0}/xiosBuild_cray_moduleFile'\
            .format(self.build_system.working_dir)

        mod_file_string = '''#%Module1.0
proc ModulesHelp {{ }} {{
    puts stderr "Sets up XIOS I/O server for use.
Met Office Source URL {xios_repository_url}
Revision: {xios_revision_number}
External URL: {xios_external_url}
Build using Rose suite:
URL: {suite_url}
Revision: {suite_revision_number}
"
}}

module-whatis The XIOS I/O server for use with weather/climate models

conflict XIOS

set version {module_version}
set module_base {module_root_dir}
set xiosdir $module_base/packages/{rel_path}

'''
        for mod_name in self.build_system.prerequisite_modules:
            mod_file_string += 'prereq {0}\n'.format(mod_name)
        mod_file_string += '''
setenv XIOS_PATH $xiosdir
setenv xios_path $xiosdir
setenv XIOS_INC $xiosdir/inc
setenv XIOS_LIB $xiosdir/lib
setenv XIOS_EXEC $xiosdir/bin/xios_server.exe

prepend-path PATH $xiosdir/bin
\n'''
        mod_file_string = mod_file_string.format(
            rel_path=mw1.module_relative_path,
            **self.build_system.__dict__)
        with open(reference_file_path, 'w') as ref_file:
            ref_file.write(mod_file_string)

        self.assertTrue(filecmp.cmp(module_file_path,
                                    reference_file_path,
                                    shallow=False),
                        'module file {0} not identical to '
                        'reference file {1}'.format(module_file_path,
                                                    reference_file_path))


    def test_write_build_script(self):
        """
        Test the XiosBuildSystem.create_build_command()
        """
        self.build_system.create_build_command()

        script_file_path = '{working_dir}/{file_name}'
        script_file_path = script_file_path.format(
            working_dir=self.build_system.working_dir,
            file_name=XiosBuildSystem.BUILD_SCRIPT_FILENAME)

        self.assertTrue(os.path.exists(script_file_path),
                        'build script {0} not found!'.format(script_file_path))
        ref_file_path = '{0}/xiosBuild_cray_referenceBuildScript.sh'
        ref_file_path = ref_file_path.format(self.build_system.working_dir)
        ref_file_str = '''#!/bin/sh

module load cray-hdf5-parallel/1.8.13
module load cray-netcdf-hdf5parallel/4.3.2

cd {working_dir}/XIOS
./make_xios --arch XC30_Cray --full  --job 4
'''
        ref_file_str = ref_file_str.format(
            working_dir=self.build_system.working_dir)

        with open(ref_file_path, 'w') as ref_file:
            ref_file.write(ref_file_str)
        err_msg1 = 'build script {0} not identical to reference script {1}'
        err_msg1 = err_msg1.format(script_file_path, ref_file_path)
        self.assertTrue(filecmp.cmp(script_file_path,
                                    ref_file_path,
                                    shallow=False),
                        err_msg1)

class XiosBuildLinuxIntelTests(unittest.TestCase):
    """
    Class for running XIOS build script test on Linux/Intel platform.
    """
    def setUp(self):
        """
        Setup XIOS build script tests on Linux/Intel platform.
        """
        self.environment = {}
        self.system_name = 'UKMO_LINUX_INTEL'
        self.environment['SYSTEM_NAME'] = self.system_name
        self.environment['XIOS_DO_CLEAN_BUILD'] = 'true'
        self.environment['XIOS_POST_BUILD_CLEANUP'] = 'false'
        self.xios_repo_url = 'svn://fcm1/xios.xm_svn/XIOS/branchs/xios-1.0'
        self.environment['XIOS_REPO_URL'] = self.xios_repo_url
        self.environment['XIOS_REV'] = 'HEAD'
        self.environment['XIOS'] = 'XIOS'
        self.environment['USE_OASIS'] = 'false'
        self.environment['OASIS_ROOT'] = ''
        self.environment['BUILD_PATH'] = '{0}/install'.format(os.getcwd())
        self.num_cores = 4
        self.environment['XIOS_NUM_CORES'] = str(self.num_cores)
        self.environment['XLF_MODULE'] = ''
        self.environment['XLCPP_MODULE'] = ''
        self.environment['DEPLOY_AS_MODULE'] = 'true'
        self.environment['MODULE_INSTALL_PATH'] = \
            '{0}/modules'.format(os.getcwd())
        self.environment['MODULE_VERSION'] = '1.0'
        # NOTE:
        self.build_system = \
            XiosBuildSystem.XiosLinuxIntelSystem(self.environment)

        self.test_script_directory = os.path.dirname(os.path.realpath(__file__))


    def tearDown(self):
        """
        Clean up after XIOS build tests on Linux/Intel platform.
        """
        pass

    def test_setup(self):
        """
        Test creation of XiosBuildSystem object
        """
        self.assertEqual(self.build_system.number_of_build_tasks,
                         self.num_cores)
        self.assertEqual(self.build_system.system_name, self.system_name)
        self.assertEqual(self.build_system.xios_repository_url,
                         self.xios_repo_url)

    def test_extraction_script(self):
        """
        Test XiosBuildSystem.extract_xios_source_code() function
        """
        self.build_system.extract_xios_source_code()
        script_file_path = '{working_dir}/{file_name}'
        script_file_path = script_file_path.format(
            working_dir=self.build_system.working_dir,
            file_name=XiosBuildSystem.EXTRACT_SCRIPT_FILENAME)
        self.assertTrue(os.path.exists(script_file_path),
                        'script file {0} not found!'.format(script_file_path))

        # compare contents to reference file
        ref_file_path = '{0}/resources/linuxIntel_xiosBuild_extractScript.sh'
        ref_file_path = ref_file_path.format(self.test_script_directory)
        extract_cmd_string = '''#!/bin/ksh
fcm co svn://fcm1/xios.xm_svn/XIOS/branchs/xios-1.0@HEAD XIOS
cd XIOS
for i in tools/archive/*.tar.gz; do  tar -xzf $i; done
'''
        with open(ref_file_path, 'w') as extractref_file:
            extractref_file.write(extract_cmd_string)

        self.assertTrue(filecmp.cmp(script_file_path,
                                    ref_file_path,
                                    shallow=False),
                        'script file {0} not identical to reference file {1}'
                        .format(script_file_path, ref_file_path))

        # check extracted source code for existence of some files
        extract_directory = '{0}/{1}'.format(self.build_system.working_dir,
                                             self.build_system.library_name)
        self.assertTrue(os.path.exists(extract_directory))
        self.assertTrue(os.path.isdir(extract_directory))
        file_check_list = ['{0}/make_xios'.format(extract_directory),
                           '{0}/bld.cfg'.format(extract_directory),
                           '{0}/src/xios_server.f90'.format(extract_directory)]

        for file_path1 in file_check_list:
            self.assertTrue(os.path.exists(file_path1),
                            ' file {0} not found'.format(file_path1))


    def test_write_module(self):
        """
        Test the XiosLinuxIntelModuleWriter class.
        """
        mw1 = XiosModuleWriter.XiosLinuxIntelModuleWriter(
            self.build_system.module_version,
            self.build_system.module_root_dir,
            self.build_system.xios_revision_number)
        mw1.write_module()

        # check for existence of module
        module_file_path = \
            '{ModuleRootDir}/modules/{library_name}/{ModuleVersion}'\
            .format(**self.build_system.__dict__)
        self.assertTrue(os.path.exists(module_file_path),
                        'Module file {0} not found'.format(module_file_path))

        # check contents
        reference_file_path = \
            '{0}/xiosBuild_linuxIntel_moduleFile'\
            .format(self.build_system.working_dir)

        mod_file_string = '''#%Module1.0
proc ModulesHelp {{ }} {{
    puts stderr "Sets up XIOS I/O server for use.branch xios-1.0 revision HEAD"
}}

module-whatis The XIOS I/O server for use with weather/climate models

conflict XIOS

set version 1.0
set module_base {ModuleRootDir}
set xiosdir $module_base/packages/XIOS/1.0

prereq fortran/intel/15.0.0
prereq mpi/mpich/3.1.2/ifort/15.0.0
prereq hdf5/1.8.12/ifort/15.0.0
prereq netcdf/4.3.3-rc1/ifort/15.0.0

setenv XIOS_PATH $xiosdir
setenv XIOS_INC $xiosdir/inc
setenv XIOS_LIB $xiosdir/lib

prepend-path PATH $xiosdir/bin
\n'''
        mod_file_string = mod_file_string.format(**self.build_system.__dict__)

        with open(reference_file_path, 'w') as ref_file:
            ref_file.write(mod_file_string)

        self.assertTrue(filecmp.cmp(module_file_path,
                                    reference_file_path,
                                    shallow=False),
                        'module file {0} not identical to reference file {1}'
                        .format(module_file_path, reference_file_path))

    def test_write_build_script(self):
        """
        Test the XiosBuildSystem.create_build_command()
        """
        self.build_system.create_build_command()

        script_file_path = '{working_dir}/{file_name}'
        script_file_path = script_file_path.format(
            working_dir=self.build_system.working_dir,
            file_name=XiosBuildSystem.BUILD_SCRIPT_FILENAME)

        self.assertTrue(os.path.exists(script_file_path),
                        'build script {0} not found!'.format(script_file_path))
        ref_file_path = \
            '{0}/xiosBuild_linuxIntel_referenceBuildScript.sh'\
            .format(self.build_system.working_dir)
        ref_file_str = '''#!/bin/bash

. /data/cr1/mhambley/modules/setup
module load environment/dynamo/compiler/intelfortran/15.0.0

cd {working_dir}/XIOS

./make_xios --dev --arch LINUX_INTEL --full  --job 4
'''
        ref_file_str = ref_file_str.format(
            working_dir=self.build_system.working_dir)

        with open(ref_file_path, 'w') as ref_file:
            ref_file.write(ref_file_str)
        err_msg1 = 'file {resultFile} does not match {kgoFile}'
        err_msg1 = err_msg1.format(resultFile=script_file_path,
                                   kgoFile=ref_file_path)
        self.assertTrue(filecmp.cmp(script_file_path,
                                    ref_file_path,
                                    shallow=False),
                        err_msg1)

def suite():
    suite = \
        unittest.TestLoader().loadTestsFromTestCase(XiosBuildLinuxIntelTests)
    return suite

if __name__ == '__main__':
    unittest.main()
