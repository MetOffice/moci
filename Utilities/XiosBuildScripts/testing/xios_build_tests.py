#!/usr/bin/env python2.7
"""
Unit test module to test XIOS build scripts.
"""
import unittest
import os
import filecmp
import abc
import copy

import mock

# this must be imported before the other local imports as it sets up the path
# to import the main scripts
import unit_test_common

import XiosBuildSystem
import XiosModuleWriter
import common

class XiosBuildTests(unittest.TestCase):
    """
    Base class for running XIOS build tests
    """
    CONFIG_LIST = ['XIOS',
                   'XIOS-app',
                   'XIOS_unit',
                   'oasis3-mct-app']

    def setUp(self):
        """
        Setup XIOS build tests
        """
        print 'Setting up tests'
        self.config_list = XiosBuildTests.CONFIG_LIST
        self.system_name = self.get_system_name()
        self.settings_dir = unit_test_common.get_settings_dir()

        self.environment = unit_test_common.get_settings(self.config_list,
                                                         self.settings_dir,
                                                         self.system_name)


        self.verbose = self.environment['VERBOSE'] == 'true'
        self.xios_repo_url = self.environment['XIOS_REPO_URL']
        self.xios_rev_no = self.environment['XIOS_REV']
        self.num_cores = int(self.environment['XIOS_NUM_CORES'])
        self.external_repo_url = self.environment['XIOS_EXTERNAL_REPO_URL']
        self.build_system = \
            XiosBuildSystem.create_build_system(self.system_name,
                                                self.environment)
        self.test_script_directory = os.path.dirname(os.path.realpath(__file__))

    @abc.abstractmethod
    def get_system_name(self):
        """
        Get the build system name
        """
        pass

    def tearDown(self):
        """
        Clean up after XIOS build tests
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

    @mock.patch('XiosBuildSystem.subprocess.call', return_value=0)
    def test_extraction_script_url(self, mock_spc):
        """
        Test XiosBuildSystem.extract_xios_source_code() function
        """
        self.build_system.source_code_location_type = 'URL'
        self.build_system.get_source_code()
        #only check extract script if using a repository URL

        dest_dir = os.path.join(self.build_system.working_dir,
                                self.build_system.library_name)
        extract_cmd_string = '''
fcm co {url}@{rev} {dest_dir}
cd {dest_dir}
for i in tools/archive/*.tar.gz; do  tar -xzf $i; done
'''.format(dest_dir=dest_dir,
           url=self.build_system.xios_repository_url,
           rev=self.build_system.xios_revision_number)

        mock_spc.assert_called_once_with(extract_cmd_string,
                                         shell=True)

    @mock.patch('XiosBuildSystem.shutil.copytree', return_value=0)
    def test_extraction_script_local_dir(self, mock_copy):
        """
        Test XiosBuildSystem.extract_xios_source_code() function
        """
        self.build_system.source_code_location_type = 'local'
        self.build_system.xios_source_code_dir = '/path/to/source/code'
        self.build_system.get_source_code()
        # only check extract script if using a repository URL

        destination_dir = os.path.join(self.build_system.working_dir,
                                       self.build_system.library_name,
                                      )

        mock_copy.assert_called_once_with(
            self.build_system.xios_source_code_dir,
            destination_dir)

    @abc.abstractmethod
    def create_module_writer(self):
        """
        Test writing of XIOS modules
        """
        pass

    @abc.abstractmethod
    def create_module_file_reference(self, module_relative_path):
        """
        Create a reference module file
        """
        pass

    def test_write_module(self):
        """
        Test the relevant XiosModuleWriter class.
        """
        mw1 = self.create_module_writer()
        mw1.write_module()

        # check for existence of module
        module_file_path = os.path.join(self.build_system.module_root_dir,
                                        'modules',
                                        mw1.module_relative_path)

        self.assertTrue(os.path.exists(module_file_path),
                        'Module file {0} not found'.format(module_file_path))

        # check contents
        reference_file_path = \
            self.create_module_file_reference(mw1.module_relative_path)

        self.assertTrue(filecmp.cmp(module_file_path,
                                    reference_file_path,
                                    shallow=False),
                        'module file {0} not identical to '
                        'reference file {1}'.format(module_file_path,
                                                    reference_file_path))
    @abc.abstractmethod
    def create_reference_build_script(self):
        """
        Create a reference build script.
        """
        pass

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

        ref_file_path = self.create_reference_build_script()
        err_msg1 = 'build script {0} not identical to reference script {1}'
        err_msg1 = err_msg1.format(script_file_path, ref_file_path)
        self.assertTrue(filecmp.cmp(script_file_path,
                                    ref_file_path,
                                    shallow=False),
                        err_msg1)

    def test_prereq_modules(self):
        """
        Run unit test to check prerequisite modules correctly read in and
        parsed by the build class.
        """
        tmp_settings = copy.deepcopy(self.environment)
        mod_list = ['mod_a/001', 'mod_b/002']
        mod_list_str = "['" + "','".join(mod_list) + "']"
        tmp_settings['XBS_PREREQ_MODULES_SWAP'] = mod_list_str

        build_system_test = \
            XiosBuildSystem.create_build_system(self.system_name, tmp_settings)

        for mod1 in mod_list:
            self.assertIn(mod1, build_system_test.prerequisite_swaps)


class XiosBuildCrayTests(XiosBuildTests):
    """
    Class to XIOS build tests on UKMO Cray XC40
    """
    def get_system_name(self):
        return XiosBuildSystem.XiosCrayBuildSystem.SYSTEM_NAME

    def create_module_writer(self):
        """
        Create a module writer object.
        """
        mw1 = XiosModuleWriter.XiosCrayModuleWriter(
            self.build_system.library_name,
            self.build_system.module_version,
            self.build_system.module_root_dir,
            self.build_system.xios_repository_url,
            self.build_system.xios_revision_number,
            self.build_system.xios_external_url,
            self.build_system.suite_url,
            self.build_system.suite_revision_number,
            self.build_system.system_name,
            self.build_system.all_prerequisites,
        )
        return mw1

    def create_module_file_reference(self, module_relative_path):
        """
        Create a reference module file
        """
        reference_file_path = \
            '{0}/xiosBuild_{1}_moduleFile'\
            .format(self.build_system.working_dir,
                    self.system_name)

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
        for mod_name in self.build_system.all_prerequisites:
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
            rel_path=module_relative_path,
            **self.build_system.__dict__)
        with open(reference_file_path, 'w') as ref_file:
            ref_file.write(mod_file_string)

        return reference_file_path

    def create_reference_build_script(self):
        """
        Create a reference build script.
        """
        ref_file_path = '{0}/xiosBuild_cray_referenceBuildScript.sh'
        ref_file_path = ref_file_path.format(self.build_system.working_dir)
        ref_file_str = '''#!/bin/sh

echo CURRENT MODULES:
module list
'''
        for swap_mod_name in self.build_system.prerequisite_swaps:
            ref_file_str += \
                'module swap {mod_in}\n'.format(mod_in=swap_mod_name)

        for mod_name in self.build_system.prerequisite_modules:
            ref_file_str += 'module load {0}\n'.format(mod_name)

        option_str = ''
        if self.build_system.do_clean_build:
            option_str += '--full '
        if self.build_system.use_oasis:
            option_str += '--use_oasis oasis3_mct '
        ref_file_str += '''
echo MODULES AFTER LOAD:
module list
cd {working_dir}/XIOS
./make_xios --arch {system_name} {options} --job {num_procs}
'''
        ref_file_str = ref_file_str.format(
            working_dir=self.build_system.working_dir,
            system_name=self.build_system.system_name,
            options=option_str,
            num_procs=self.build_system.number_of_build_tasks)

        with open(ref_file_path, 'w') as ref_file:
            ref_file.write(ref_file_str)

        return ref_file_path




class XiosBuildMonsoonTests(XiosBuildCrayTests):
    """
    Unit test class for running XIOS Build tests on Monsoon
    """
    def get_system_name(self):
        return unit_test_common.SYSTEM_NAME_MONSOON

class XiosBuildExternalTests(XiosBuildCrayTests):
    """
    Unit test class for running XIOS Build tests on an external system
    """
    def get_system_name(self):
        return common.SYSTEM_NAME_EXTERNAL

def main():
    """
    Entry function for running only the XIOS build tests
    """
    test_list_dict = {}
    test_list_dict[XiosBuildSystem.XiosCrayBuildSystem.SYSTEM_NAME] = [
        XiosBuildCrayTests]
    test_list_dict[unit_test_common.SYSTEM_NAME_MONSOON] = [
        XiosBuildMonsoonTests]
    test_list_dict[common.SYSTEM_NAME_EXTERNAL] = [
        XiosBuildMonsoonTests]
    unit_test_common.run_tests(test_list_dict)

if __name__ == '__main__':
    main()
