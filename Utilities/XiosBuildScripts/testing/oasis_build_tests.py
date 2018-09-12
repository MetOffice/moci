#!/usr/bin/env python2.7
"""
Unit test module to test Oasis-3mct build scripts.
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

import OasisBuildSystem
import OasisModuleWriter
import common

class OasisBuildTests(unittest.TestCase):
    """
    Base class for testing functions in the Oasis build classes.
    """

    CONFIG_LIST = ['oasis3-mct', 'oasis3-mct-app']
    @abc.abstractmethod
    def get_system_name(self):
        """
        Get the build system name
        """
        pass

    def setUp(self):
        """
        Setup Oasis build tests.
        """

        self.system_name = self.get_system_name()
        self.config_list = OasisBuildTests.CONFIG_LIST
        self.settings_dir = unit_test_common.get_settings_dir()

        self.settings_dict = unit_test_common.get_settings(self.config_list,
                                                           self.settings_dir,
                                                           self.system_name)


        self.library_name = self.settings_dict['OASIS3_MCT']
        self.oasis_repository_url = self.settings_dict['OASIS_REPO_URL']
        self.oasis_revision_number = self.settings_dict['OASIS_REV_NO']

        self.verbose = self.settings_dict['VERBOSE'] == 'true'

        self.build_system = \
            OasisBuildSystem.create_build_system(self.system_name,
                                                 self.settings_dict)

    def tearDown(self):
        """
        Cleanup after Oasis3-mct build tests
        """
        self.build_system = None

    def test_setup(self):
        """
        Test setup of OasisBuildSystem derived objects
        """
        err_msg1 = 'Input parameters {0} do not match, {1} != {2}'
        self.assertEqual(self.verbose,
                         self.build_system.verbose,
                         err_msg1.format('verbose',
                                         self.verbose,
                                         self.build_system.verbose))
        self.assertEqual(self.system_name,
                         self.build_system.system_name,
                         err_msg1.format('system_name',
                                         self.system_name,
                                         self.build_system.system_name))
        self.assertEqual(\
            self.oasis_repository_url,
            self.build_system.oasis_repository_url,
            err_msg1.format('oasis_repository_url',
                            self.oasis_repository_url,
                            self.build_system.oasis_repository_url))

    def test_prereq_modules(self):
        """
        Unit test for checking that the prerequisite_modules are correctly
        read in by the build system class.
        """
        tmp_settings = copy.deepcopy(self.settings_dict)
        mod_list = ['mod_a/001', 'mod_b/002']
        mod_list_str = "['" + "','".join(mod_list) + "']"
        tmp_settings['XBS_PREREQ_MODULES_SWAP'] = mod_list_str

        build_system_test = \
            OasisBuildSystem.create_build_system(self.system_name,
                                                 tmp_settings,
                                                )

        for mod1 in mod_list:
            self.assertIn(mod1, build_system_test.prerequisite_swaps)

    @mock.patch('OasisBuildSystem.subprocess.call', return_value=0)
    def test_code_extraction_url(self, mock_sp):
        """
        Test the OasisBuildSystem.extract_source_code() function.
        """
        self.build_system.source_code_location_type = 'URL'
        self.build_system.extract_source_code()
        #only check extract script if using a repository URL
        ref_file_str = \
            'fcm co {oasis_repository_url}@{oasis_revision_number} '\
            '{oasis_src_dir}\n'

        if self.build_system.separate_make_file:
            ref_file_str += \
                'fcm export {make_config_repo_url}'\
                '/{make_config_file_name}@{make_config_rev_no}'\
                ' {oasis_src_dir}/util/make_dir/'\
                '{make_config_file_name}\n'
        if self.build_system.build_tutorial and \
            self.build_system.separate_tutorial_location:
            ref_file_str += \
                'rm -rf {oasis_src_dir}/examples/tutorial/\n'
            ref_file_str += \
                'fcm export {tutorial_repository_url}@'\
                '{tutorial_revision_number} '\
                '{oasis_src_dir}/examples/tutorial/ \n'

        ref_file_str = ref_file_str.format(**self.build_system.__dict__)

        # check the mock calls
        mock_sp.assert_called_once_with(ref_file_str, shell=True)

    @mock.patch('OasisBuildSystem.shutil.copytree', return_value=0)
    def test_code_extraction_local_dir(self, mock_copy):
        """
        Test the OasisBuildSystem.extract_source_code() function.
        """
        self.build_system.source_code_location_type = 'local'
        self.build_system.oasis_src_code_dir = '/path/to/source/code'
        self.build_system.extract_source_code()

        mock_copy.assert_called_once_with(
            self.build_system.oasis_src_code_dir,
            self.build_system.oasis_src_dir,
        )

    @abc.abstractmethod
    def create_reference_build_cmd(self):
        """
        Create a reference build command.
        """
        pass

    def test_build_command(self):
        """
        Test the OasisBuildSystem.create_build_command() function.
        """
        verbose_old = self.build_system.verbose
        self.build_system.verbose = True
        _ = self.build_system.create_build_command()
        self.build_system.verbose = verbose_old

        script_file_path = '{working_dir}/{fileName}'
        script_file_path = script_file_path.format(
            working_dir=self.build_system.working_dir,
            fileName=OasisBuildSystem.BUILD_SCRIPT_FILENAME)

        self.assertTrue(os.path.exists(script_file_path),
                        'build script {0} not found!'.format(script_file_path))

        ref_file_path = self.create_reference_build_cmd()

        err_msg1 = 'file {resultFile} does not match {kgoFile}'
        err_msg1 = err_msg1.format(resultFile=script_file_path,
                                   kgoFile=ref_file_path)
        self.assertTrue(filecmp.cmp(script_file_path,
                                    ref_file_path),
                        err_msg1)

    @abc.abstractmethod
    def create_reference_module(self, module_relative_path):
        """
        Create a reference module file.
        """
        pass

    @abc.abstractmethod
    def create_module_writer(self):
        """
        Create a module writer object
        """
        pass

    def test_module_write(self):
        """
        Test the OasisModuleWriter derived class class.
        """
        mw1 = self.create_module_writer()
        mw1.write_module()

        # check for existence of module
        temp_mod_str1 = '{root_dir}/modules/{rel_path}'
        module_file_path = temp_mod_str1.format(
            root_dir=self.build_system.module_root_dir,
            rel_path=mw1.module_relative_path)
        module_file_path = \
            module_file_path.format(**self.build_system.__dict__)
        self.assertTrue(os.path.exists(module_file_path),
                        'Module file {0} not found'.format(module_file_path))

        # check contents
        reference_file_path = \
            self.create_reference_module(mw1.module_relative_path)

        msg1 = 'module file {0} not identical to reference file {1}'
        msg1 = msg1.format(module_file_path, reference_file_path)
        self.assertTrue(filecmp.cmp(module_file_path,
                                    reference_file_path),
                        msg1)

class OasisBuildCrayTests(OasisBuildTests):
    """
    Class for testing functions in the Oasis Cray build class.
    """
    def get_system_name(self):
        print 'retrieving system name: {0}'.format(
            OasisBuildSystem.OasisCrayBuildSystem.SYSTEM_NAME)
        return OasisBuildSystem.OasisCrayBuildSystem.SYSTEM_NAME

    def create_module_writer(self):
        mw1 = OasisModuleWriter.OasisCrayModuleWriter(
            self.build_system.module_version,
            self.build_system.module_root_dir,
            self.build_system.oasis_repository_url,
            self.build_system.oasis_revision_number,
            self.oasis_repository_url,
            self.oasis_revision_number,
            self.build_system.suite_url,
            self.build_system.suite_revision_number,
            self.build_system.library_name,
            self.build_system.system_name,
            self.build_system.all_prerequisites,
        )
        return mw1


    def create_reference_build_cmd(self):
        """
        Create a reference build command.
        """
        ref_file_path = \
            '{0}/oasisBuild_{1}_referenceBuildScript.sh'\
            .format(self.build_system.working_dir,
                    self.system_name)
        ref_file_str = '''#!/bin/sh

'''
        ref_file_str += 'echo CURRENT MODULES:\n'
        ref_file_str += 'module list\n'

        for swap_mod_name in self.build_system.prerequisite_swaps:
            ref_file_str += \
                'module swap {mod_in}\n'.format(mod_in=swap_mod_name)

        for mod_name in self.build_system.prerequisite_modules:
            ref_file_str += 'module load {0}\n'.format(mod_name)

        ref_file_str += 'echo MODULES AFTER LOAD:\n'
        ref_file_str += 'module list\n'
        ref_file_str += '''
cd {oasis_src_dir}/util/make_dir
make -f TopMakefileOasis3
'''
        if self.build_system.build_tutorial:
            ref_file_str += '''
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

        ref_file_str = ref_file_str.format(**self.build_system.__dict__)

        with open(ref_file_path, 'w') as ref_file:
            ref_file.write(ref_file_str)

        return ref_file_path

    def create_reference_module(self, module_relative_path):
        """
        Create a reference module file.
        """
        reference_file_path = '{0}/oasisBuild_cray_referenceModuleFile'
        reference_file_path = \
            reference_file_path.format(self.build_system.working_dir)
        mod_file_string = '''#%Module1.0
proc ModulesHelp {{ }} {{
    puts stderr "Sets up Oasis3-MCT coupler I/O server for use.
Met Office source code URL: {oasis_repository_url}
Revision: {oasis_revision_number}
External URL: {oasis_repository_url}
External revision number: {oasis_revision_number}
Build using Rose suite:
URL: {suite_url}
Revision: {suite_revision_number}
"
}}

module-whatis The Oasis3-mct coupler for use with weather/climate models

conflict {library_name}

set version {module_version}
set module_base {module_root_dir}
set oasisdir $module_base/packages/{rel_path}

'''
        for mod_name in self.build_system.all_prerequisites:
            mod_file_string += 'prereq {0}\n'.format(mod_name)
        mod_file_string += '''
setenv OASIS_ROOT $oasisdir
setenv prism_path $oasisdir
setenv OASIS_INC $oasisdir/inc
setenv OASIS_LIB $oasisdir/lib
setenv OASIS3_MCT {library_name}
setenv OASIS_MODULE_VERSION {module_version}


'''
        mod_file_string = mod_file_string.format(
            rel_path=module_relative_path,
            **self.build_system.__dict__)

        with open(reference_file_path, 'w') as ref_file:
            ref_file.write(mod_file_string)

        return reference_file_path

class OasisBuildMonsoonTests(OasisBuildCrayTests):
    """
    Unit test class for running Oasis Build tests on Monsoon
    """
    def get_system_name(self):
        print 'retrieving system name: {0}'.\
            format(unit_test_common.SYSTEM_NAME_MONSOON)
        return unit_test_common.SYSTEM_NAME_MONSOON

class OasisBuildExternalTests(OasisBuildCrayTests):
    """
    Unit test class for running Oasis Build tests on an external system
    """
    def get_system_name(self):
        print 'retrieving system name: {0}'.format(common.SYSTEM_NAME_EXTERNAL)
        return common.SYSTEM_NAME_EXTERNAL

def suite():
    """
    Build up the Oasis3-mct build unit test suite.
    """
    return_suite = \
        unittest.TestLoader().loadTestsFromTestCase(OasisBuildCrayTests)
    return return_suite

def main():
    """
    Entry function for running only the Oasis3-mct build tests
    """
    test_list_dict = {}
    test_list_dict[OasisBuildSystem.OasisCrayBuildSystem.SYSTEM_NAME] = [
        OasisBuildCrayTests]
    test_list_dict[unit_test_common.SYSTEM_NAME_MONSOON] = [
        OasisBuildMonsoonTests]
    test_list_dict[common.SYSTEM_NAME_EXTERNAL] = [
        OasisBuildExternalTests]
    unit_test_common.run_tests(test_list_dict)

if __name__ == '__main__':
    main()
