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
   OasisModuleWriter

"""

import EnvironmentModules


class OasisModuleWriter(EnvironmentModules.SingleModuleWriter):

    '''
    Abstract Class responsible for writing Oasis3-mct environment module. This
    class defines which parameters need to be defined by the concrete system
    specific derived classes. The module defines the following environment
    variables:
    * OASIS_ROOT -  the root directory of the Oasis3-mct library files
    * prism_path -  the root directory of the Oasis3-mct library files
    * OASIS_INC - The directory containing the include and fortran module files
    * OASIS_LIB - The directory containing the files for linking
    * OASIS3_MCT - The name of the library and module
    * OASIS_MODULE_VERSION - The environment module version
    '''

    def __init__(self,
                 version,
                 modulePath,
                 prerequisites,
                 srcUrl,
                 revNo,
                 externalUrl,
                 externalRevNo,
                 suiteUrl,
                 suite_rev_num,
                 moduleName,
                 parents,
                 platform):
        EnvironmentModules.SingleModuleWriter.__init__(self)
        self.module_name = moduleName
        self.module_version = version
        self.module_home_path = modulePath
        self.parent_modules = parents
        self.platform = platform
        self.oasis_repo_url = srcUrl
        self.oasis_revision_number = revNo
        self.revision_number = revNo
        self.external_url = externalUrl
        self.external_revision_number = externalRevNo
        self.suite_url = suiteUrl
        self.suite_rev_num = suite_rev_num
        self.config_revision_number = suite_rev_num
        self.help_msg = """Sets up Oasis3-MCT coupler I/O server for use.
Met Office source code URL: {srcUrl}
Revision: {revNo}
"""
        self.help_msg = self.help_msg.format(srcUrl=self.oasis_repo_url,
                                             revNo=self.oasis_revision_number)

        if self.external_url != '' and self.external_revision_number != '':
            help_msg_ext_url = 'External URL: {0}\n'\
                'External revision number: {1}\n'
            help_msg_ext_url = \
                help_msg_ext_url.format(self.external_url,
                                        self.external_revision_number)
            self.help_msg += help_msg_ext_url

        if self.suite_url != '' and self.suite_rev_num != '':
            help_msg_suite = '''Build using Rose suite:
URL: {0}
Revision: {1}
'''
            help_msg_suite = help_msg_suite.format(self.suite_url,
                                                   self.suite_rev_num)
            self.help_msg += help_msg_suite

        self.what_is_msg = 'The Oasis3-mct coupler for use '
        self.what_is_msg += 'with weather/climate models'

        self.local_variables_list = []
        self.local_variables_list += [('module_base', self.module_home_path)]

        self.setup_file_path()

        module_dir_str = '$module_base/packages/{0}'
        module_dir_str = module_dir_str.format(self.module_relative_path)

        self.local_variables_list += [('oasisdir',
                                       module_dir_str)]

        self.prerequisite_list = prerequisites

        self.set_env_list = [('OASIS_ROOT', '$oasisdir'),
                             ('prism_path', '$oasisdir'),
                             ('OASIS_INC', '$oasisdir/inc'),
                             ('OASIS_LIB', '$oasisdir/lib'),
                             ('OASIS3_MCT', self.module_name),
                             ('OASIS_MODULE_VERSION', self.module_version)]


class OasisCrayModuleWriter(OasisModuleWriter):

    '''
    Concrete Class to write out an Environment Moduules file for the Oasis3-mct
    library on the CRAY XC40 platform.

    Creation:
    writer = OasisCrayModuleWriter(version,
                                   modulePath,
                                   srcUrl,
                                   revNo,
                                   externalUrl,
                                   externalRevNo,
                                   suiteUrl,
                                   suite_rev_num,
                                   moduleName,
                                   platform,
                                   prerequisites,
                                   )

    Parameters:
    * version - The module file version number (a string)
    * modulePath - The path to the root directory for the Environment Modules
    * srcUrl - The repository URL of the source code for Oasis3-mct
    * revNo - The revision number of the source code for Oasis3-mct (a string)
    * externalUrl - The external URL of the source code for Oasis3-mct
    * externalRevNo - The external revision number of the source code
                      for Oasis3-mct (a string)
    * suiteUrl - The repository URL of the suite used to build the library
    * suite_rev_num - The revision number of the suite used to build the library
    * moduleName - The name to use for module
    * platform - A string identifying the system the library is built on
    '''

    def __init__(self,
                 version,
                 modulePath,
                 srcUrl,
                 revNo,
                 externalUrl,
                 externalRevNo,
                 suiteUrl,
                 suite_rev_num,
                 moduleName,
                 platform,
                 prerequisites):
        OasisModuleWriter.__init__(self,
                                   version=version,
                                   modulePath=modulePath,
                                   prerequisites=prerequisites,
                                   srcUrl=srcUrl,
                                   revNo=revNo,
                                   externalUrl=externalUrl,
                                   externalRevNo=externalRevNo,
                                   suiteUrl=suiteUrl,
                                   suite_rev_num=suite_rev_num,
                                   moduleName=moduleName,
                                   parents='',
                                   platform=platform)

class OasisCrayRemoteModuleWriter(OasisModuleWriter):

    '''
    Class to write out the Oasis3-mct CRAY XC40 environment module for use on
    remote systems. This allows one to create a script to run on the cray
    on a different system. This is typically used with the FCM build system
    where the build may be setup on one platform and built on another.

    Creation:
    writer = OasisCrayRemoteModuleWriter(version,
                                         modulePath,
                                         srcUrl,
                                         revNo,
                                         externalUrl,
                                         externalRevNo,
                                         suiteUrl,
                                         suite_rev_num,
                                         moduleName,
                                         platform)

    Parameters:
    * version - The module file version number (a string)
    * modulePath - The path to the root directory for the Environment Modules
    * srcUrl - The repository URL of the source code for Oasis3-mct
    * revNo - The revision number of the source code for Oasis3-mct (a string)
    * externalUrl - The external URL of the source code for Oasis3-mct
    * externalRevNo - The external revision number of the source code
                      for Oasis3-mct (a string)
    * suiteUrl - The repository URL of the suite used to build the library
    * suite_rev_num - The revision number of the suite used to build the library
    * moduleName - The name to use for module
    * platform - A string identifying the system the library is built on
    '''

    def __init__(self,
                 version,
                 modulePath,
                 srcUrl,
                 revNo,
                 externalUrl,
                 externalRevNo,
                 suiteUrl,
                 suite_rev_num,
                 moduleName,
                 platform):
        prereq = []
        OasisModuleWriter.__init__(self,
                                   version=version,
                                   modulePath=modulePath,
                                   prerequisites=prereq,
                                   srcUrl=srcUrl,
                                   revNo=revNo,
                                   externalUrl=externalUrl,
                                   externalRevNo=externalRevNo,
                                   suiteUrl=suiteUrl,
                                   suite_rev_num=suite_rev_num,
                                   moduleName=moduleName,
                                   parents='remote/{0}/'.format(platform),
                                   platform=platform)
