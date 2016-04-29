#!/usr/bin/env python2.7
"""
Unit test module to test Oasis-3mct build scripts.
"""
import unittest
import os
import filecmp

import OasisBuildSystem
import OasisModuleWriter


class OasisBuildCrayTests(unittest.TestCase):
    """
    Class for testing functions in the Oasis Cray build class.q
    """
    def setUp(self):
        """
        Setup Oasis Cray build tests.
        """
        self.working_dir = os.getcwd()
        settings_dict = {}
        self.system_name = 'UKMO_CRAY_XC40'
        settings_dict['SYSTEM_NAME'] = self.system_name
        self.library_name = 'oasis3-mct'
        settings_dict['OASIS3_MCT'] = self.library_name
        settings_dict['BUILD_OASIS'] = 'true'
        settings_dict['OASIS_DIR'] = '{0}/install/{1}'.format(self.working_dir,
                                                              self.library_name)

        settings_dict['OASIS_SRC_LOCATION_TYPE'] = 'URL'
        settings_dict['OASIS_MAKE_FILE_NAME'] = 'make.cray_xc40_mo'

        self.oasis_repository_url = \
            'svn://fcm2/PRISM_svn/OASIS3_MCT/branches/dev/shaddad/'\
            'r1267_GC3_projOceanTutorial/oasis3-mct'

        settings_dict['OASIS_REPO_URL'] = self.oasis_repository_url
        settings_dict['OASIS_REV_NO'] = '1327'
        settings_dict['OASIS_SEPARATE_MAKEFILE'] = 'false'
        settings_dict['OASIS_SEPARATE_TUTORIAL'] = 'false'

        self.external_repo_url = 'http://server.name/path/to/repository'
        self.external_rev_no = '1234'
        settings_dict['OASIS_EXTERNAL_REPO_URL'] = self.external_repo_url
        settings_dict['OASIS_EXTERNAL_REV_NO'] = self.external_rev_no
        settings_dict['ROSE_SUITE_URL'] = 'path/to/repository'
        settings_dict['ROSE_SUITE_REV_NO'] = '1234'


        settings_dict['OASIS_PLATFORM_NAME'] = 'crayxc40'
        self.verbose = True
        if self.verbose:
            settings_dict['VERBOSE'] = 'true'
        else:
            settings_dict['VERBOSE'] = 'false'
        settings_dict['DEPLOY_AS_MODULE'] = 'true'
        settings_dict['MODULE_INSTALL_PATH'] = \
            '{0}/modules'.format(self.working_dir)
        settings_dict['OASIS_MODULE_VERSION'] = '1.0'
        settings_dict['XBS_PREREQ_MODULES'] =\
            "['cray-hdf5-parallel/1.8.13',"\
            "'cray-netcdf-hdf5parallel/4.3.2']"


        self.build_system = OasisBuildSystem.OasisCrayBuildSystem(settings_dict)

    def tearDown(self):
        """
        Cleanup after Oasis3-mct cray build tests
        """
        self.build_system = None

    def test_setup(self):
        """
        Test setup of OasisCrayBuildSystem object
        """
        err_msg1 = 'Input parameters do not match'
        self.assertEqual(self.verbose,
                         self.build_system.verbose,
                         err_msg1)
        self.assertEqual(self.system_name,
                         self.build_system.system_name,
                         err_msg1)
        self.assertEqual(self.oasis_repository_url,
                         self.build_system.oasis_repository_url,
                         err_msg1)

    def test_code_extraction(self):
        """
        Test the OasisBuildSystem.extract_source_code() function.
        """
        self.build_system.extract_source_code()
        script_file_path = '{working_dir}/{fileName}'
        script_file_path = script_file_path.format(
            working_dir=self.build_system.working_dir,
            fileName=OasisBuildSystem.EXTRACT_SCRIPT_FILE_NAME)
        self.assertTrue(os.path.exists(script_file_path),
                        'script file {0} not found!'.format(script_file_path))
        # compare contents to reference file
        ref_file_path = '{0}/oasisBuild_cray_reference_extractScript.sh'
        ref_file_path = ref_file_path.format(os.getcwd())

        ref_file_str = 'fcm co {oasis_repository_url}@{oasis_revision_number} '\
                     '{oasis_src_dir}\n'
        ref_file_str = ref_file_str.format(**self.build_system.__dict__)

        with open(ref_file_path, 'w') as ref_file:
            ref_file.write(ref_file_str)
        self.assertTrue(filecmp.cmp(script_file_path,
                                    ref_file_path),
                        'script file {0} not identical to reference file {1}'
                        .format(script_file_path, ref_file_path))

        # check extracted source code for existence of some files
        self.assertTrue(os.path.exists(self.build_system.oasis_src_dir))
        self.assertTrue(os.path.isdir(self.build_system.oasis_src_dir))
        file_check_list = [
            '{0}/lib/mct/Makefile'.format(self.build_system.oasis_src_dir),
            '{0}/lib/mct/mct/mct_mod.F90'
            .format(self.build_system.oasis_src_dir),
            '{0}/util/make_dir/make.cray_xc40_mo'
            .format(self.build_system.oasis_src_dir)]
        for file_path1 in file_check_list:
            self.assertTrue(os.path.exists(file_path1),
                            ' file {0} not found'.format(file_path1))

    def test_build_command(self):
        """
        Test the OasisBuildSystem.create_build_command() function.
        """
        build_cmd = self.build_system.create_build_command()

        script_file_path = '{working_dir}/{fileName}'
        script_file_path = script_file_path.format(
            working_dir=self.build_system.working_dir,
            fileName=OasisBuildSystem.BUILD_SCRIPT_FILENAME)

        self.assertTrue(os.path.exists(script_file_path),
                        'build script {0} not found!'.format(script_file_path))

        ref_file_path = \
            '{0}/oasisBuild_cray_referenceBuildScript.sh'\
            .format(self.build_system.working_dir)
        ref_file_str = '''#!/bin/sh

'''
        for mod_name in self.build_system.prerequisite_modules:
            ref_file_str += 'module load {0}\n'.format(mod_name)
        ref_file_str += '''
cd {oasis_src_dir}/util/make_dir
make -f TopMakefileOasis3
'''

        ref_file_str = ref_file_str.format(**self.build_system.__dict__)

        with open(ref_file_path, 'w') as ref_file:
            ref_file.write(ref_file_str)

        err_msg1 = 'file {resultFile} does not match {kgoFile}'
        err_msg1 = err_msg1.format(resultFile=script_file_path,
                                   kgoFile=ref_file_path)
        self.assertTrue(filecmp.cmp(script_file_path,
                                    ref_file_path),
                        err_msg1)

    def test_module_write(self):
        """
        Test the OasisCrayModuleWriter class.
        """
        mw1 = OasisModuleWriter.OasisCrayModuleWriter(
            self.build_system.module_version,
            self.build_system.module_root_dir,
            self.build_system.oasis_repository_url,
            self.build_system.oasis_revision_number,
            self.external_repo_url,
            self.external_rev_no,
            self.build_system.suite_url,
            self.build_system.suite_revision_number,
            self.build_system.library_name,
            self.build_system.SYSTEM_NAME,
            self.build_system.prerequisite_modules)
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
        reference_file_path = '{0}/oasisBuild_cray_referenceModuleFile'
        reference_file_path = \
            reference_file_path.format(self.build_system.working_dir)
        mod_file_string = '''#%Module1.0
proc ModulesHelp {{ }} {{
    puts stderr "Sets up Oasis3-MCT coupler I/O server for use.
Met Office source code URL: {oasis_repository_url}
Revision: {oasis_revision_number}
External URL: {oasis_external_url}
 External revision number: {oasis_external_revision_number}
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
        for mod_name in self.build_system.prerequisite_modules:
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
            rel_path=mw1.module_relative_path,
            **self.build_system.__dict__)

        with open(reference_file_path, 'w') as ref_file:
            ref_file.write(mod_file_string)

        msg1 = 'module file {0} not identical to reference file {1}'
        msg1 = msg1.format(module_file_path, reference_file_path)
        self.assertTrue(filecmp.cmp(module_file_path,
                                    reference_file_path),
                        msg1)

def suite():
    return_suite = \
        unittest.TestLoader().loadTestsFromTestCase(OasisBuildCrayTests)
    return return_suite

if __name__ == '__main__':
    unittest.main()
