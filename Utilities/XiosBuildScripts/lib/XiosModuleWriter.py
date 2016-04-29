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
   XiosModuleWriter.py

 DESCRIPTION
    Creates Environment Module files for both the XIOS library and
    to set up the programming environment (PrgEnv).

"""
import os

import EnvironmentModules


class XiosModuleWriter(EnvironmentModules.SingleModuleWriter):

    """
    Abstract Class responsible for writing XIOS environment module. This
    class defines which parameters need to be defined by the concrete system
    specific derived classes. The module created will  define the following
    environment variables:
    * XIOS_PATH -  the root directory of the XIOS library files
    * xios_path -  same as XIOS_PATH
    * XIOS_INC - The directory containing the include and fortran module files
    * XIOS_LIB - The directory containing the files for linking
    * XIOS_EXEC - Path to the XIOS server executable
    * PATH - adds the location of the XIOS executable to the path
    """

    def __init__(self,
                 version,
                 modulePath,
                 prerequisites,
                 srcUrl,
                 revNo,
                 external_url,
                 suiteUrl,
                 suite_revision_number,
                 parents,
                 platform):
        EnvironmentModules.SingleModuleWriter.__init__(self)
        self.module_name = 'XIOS'
        self.module_version = version
        self.module_home_path = modulePath
        self.parent_modules = parents
        self.xios_repository_url = srcUrl
        self.xios_revision_number = revNo
        self.revision_number = revNo
        self.external_url = external_url
        self.suite_url = suiteUrl
        self.suite_revision_number = suite_revision_number
        self.config_revision_number = suite_revision_number
        self.platform = platform
        self.help_msg = '''Sets up XIOS I/O server for use.
Met Office Source URL {srcUrl}
Revision: {revNo}
'''
        self.help_msg = self.help_msg.format(srcUrl=self.xios_repository_url,
                                             revNo=self.xios_revision_number)
        if self.external_url != '':
            help_msg_ext_url = 'External URL: {0}\n'.format(self.external_url)
            self.help_msg += help_msg_ext_url

        if self.suite_url != '' and self.suite_revision_number != '':
            help_msg_suite = '''Build using Rose suite:
URL: {0}
Revision: {1}
'''
            help_msg_suite = help_msg_suite.format(self.suite_url,
                                                   self.suite_revision_number)
            self.help_msg += help_msg_suite

        self.what_is_msg = 'The XIOS I/O server for use with '\
            'weather/climate models'

        self.local_variables_list = [('module_base', self.module_home_path)]
        self.setup_file_path()

        mod_base1 = '$module_base/packages/{rel_path}'
        mod_base1 = mod_base1.format(rel_path=self.module_relative_path)
        self.local_variables_list += [('xiosdir', mod_base1)]

        self.prerequisite_list = prerequisites

        self.prepend_path_list = []
        self.prepend_path_list += [('PATH', '$xiosdir/bin')]

        self.set_env_list = [('XIOS_PATH', '$xiosdir'),
                             ('xios_path', '$xiosdir'),
                             ('XIOS_INC', '$xiosdir/inc'),
                             ('XIOS_LIB', '$xiosdir/lib'),
                             ('XIOS_EXEC', '$xiosdir/bin/xios_server.exe')]


class XiosPrgEnvWriter(EnvironmentModules.PrgEnvModuleWriter):

    """
    Abstract class for writing out the XIOS programming environment module
    name. The module does not load any settings, but loads other modules.
    It primarily loads the compatible Oasis3-mct and XIOS mdoules.
    """
    XIOS_PRGENV_NAME = 'XIOS-PrgEnv'
    GC3_PRGENV_NAME = 'GC3-PrgEnv'

    def __init__(self,
                 version,
                 modulePath,
                 parents,
                 platform,
                 suiteUrl,
                 suite_revision_number):
        EnvironmentModules.PrgEnvModuleWriter.__init__(self)
        self.module_name = XiosPrgEnvWriter.XIOS_PRGENV_NAME
        self.module_version = version
        self.module_home_path = modulePath
        self.parent_modules = parents
        self.suite_url = suiteUrl
        self.suite_revision_number = suite_revision_number
        self.revision_number = suite_revision_number
        self.platform = platform
        self.help_msg = '''Sets up the programming environment for XIOS and
Oasis3-mct (if required)
Build by Rose suite:
Suite URL: {url}
Suite Revision Number: {revno}
'''
        self.help_msg = self.help_msg.format(url=self.suite_url,
                                             revno=self.suite_revision_number)
        self.what_is_msg = 'The XIOS I/O server for use with '\
            'weather/climate models '

        self.local_variables_list = []
        self.prerequisite_list = []
        self.modules_to_load = []


class XiosCrayModuleWriter(XiosModuleWriter):

    """
    Class for Cray platform to create XIOS module.

    Creation:
    module_writer = XiosCrayModuleWriter(version,
                                         modulePath,
                                         srcUrl,
                                         revNo,
                                         external_url,
                                         suiteUrl,
                                         suite_revision_number,
                                         platform,
                                         prerequisites)

    Parameters:
     * version - The module file version number (a string)
     * modulePath - The path to the root directory for the Environment Modules
     * srcUrl - The repository URL of the source code for XIOS
     * revNo - The revision number of the source code for XIOS (a string)
     * external_url - The external URL of the source code for XIOS
     * suiteUrl - The repository URL of the suite used to build the library
     * suite_revision_number - The revision number of the suite used to build
                               the library
     * platform - A string identifying the system the library is built on
     * prerequisites - The list of modules that must already be loaded for this
                       module to load successfully
    """

    def __init__(self,
                 version,
                 modulePath,
                 srcUrl,
                 revNo,
                 external_url,
                 suiteUrl,
                 suite_revision_number,
                 platform,
                 prerequisites):
        XiosModuleWriter.__init__(self,
                                  version,
                                  modulePath,
                                  prerequisites,
                                  srcUrl,
                                  revNo,
                                  external_url,
                                  suiteUrl,
                                  suite_revision_number,
                                  '',
                                  platform)


class XiosCrayPrgEnvWriter(XiosPrgEnvWriter):

    """
    Class for Cray platform to create XIOS module for loading
    or remote systems when cray is the target.

    Creation:

    XiosCrayPrgEnvWriter(version,
                         modulePath,
                         module_list,
                         platform,
                         suiteUrl,
                         suite_revision_number,
                         prerequisites)
    Parameters:
     * version - The module file version number (a string)
     * modulePath - The path to the root directory for the Environment Modules
     * module_list - List of library modules to be loaded as part of the
                     programming environment
     * platform - A string identifying the system the library is built on
     * suiteUrl - The repository URL of the suite used to build the library
     * suite_revision_number - The revision number of the suite used to build
                               the library
     * prerequisites - List of modules to be loaded before library modules are
                       loaded.



    """

    def __init__(self,
                 version,
                 modulePath,
                 module_list,
                 platform,
                 suiteUrl,
                 suite_revision_number,
                 prerequisites,
                 compiler_module):
        XiosPrgEnvWriter.__init__(self,
                                  version,
                                  modulePath,
                                  '',
                                  platform,
                                  suiteUrl,
                                  suite_revision_number)
        self.compiler_module = compiler_module
        self.default_compiler = 'PrgEnv-cray'
        self.modules_to_load = []

        for mod1 in prerequisites:
            self.modules_to_load += [mod1]

        for mod1 in module_list:
            self.modules_to_load += [mod1]


class XiosCrayRemoteModuleWriter(XiosModuleWriter):

    """
    Class for Cray platform to create XIOS module for loading
    or remote systems when cray is the target.

    Creation:

    XiosCrayRemoteModuleWriter(version,
                         modulePath,
                         srcUrl,
                         revNo,
                         external_url,
                         suiteUrl,
                         suite_revision_number,
                         platform)
    Parameters:
     * version - The module file version number (a string)
     * modulePath - The path to the root directory for the Environment Modules
     * srcUrl - The repository URL of the source code for XIOS
     * revNo - The revision number of the source code for XIOS (a string)
     * external_url - The external URL of the source code for XIOS
     * suiteUrl- The repository URL of the suite used to build the library
     * suite_revision_number - The revision number of the suite used to build
                               the library
     * platform - A string identifying the system the library is built on

    """

    def __init__(self,
                 version,
                 modulePath,
                 srcUrl,
                 revNo,
                 external_url,
                 suiteUrl,
                 suite_revision_number,
                 platform):
        prereq = []
        XiosModuleWriter.__init__(self,
                                  version,
                                  modulePath,
                                  prereq,
                                  srcUrl,
                                  revNo,
                                  external_url,
                                  suiteUrl,
                                  suite_revision_number,
                                  'remote/{0}'.format(platform),
                                  platform)


class XiosCrayRemotePrgEnvWriter(XiosPrgEnvWriter):

    """
    Class for Cray platform to create XIOS programming environment for loading
    or remote systems when cray is the target.

    Creation:
    Parameters:
     * version - The module file version number (a string)
     * modulePath - The path to the root directory for the Environment Modules
     * prerequisites - List of modules to be loaded before library modules are
                       loaded.
     * srcUrl - The repository URL of the source code for XIOS
     * revNo - The revision number of the source code for XIOS (a string)
     * external_url - The external URL of the source code for XIOS
     * suiteUrl- The repository URL of the suite used to build the library
     * suite_revision_number - The revision number of the suite used to build
                               the library
     * platform - A string identifying the system the library is built on
    """

    def __init__(self,
                 version,
                 modulePath,
                 module_list,
                 platform,
                 suiteUrl,
                 suite_revision_number):
        XiosPrgEnvWriter.__init__(self,
                                  version,
                                  modulePath,
                                  os.path.join('remote', platform),
                                  platform,
                                  suiteUrl,
                                  suite_revision_number)

        for mod1 in module_list:
            self.modules_to_load += [mod1]


class XiosLinuxIntelModuleWriter(XiosModuleWriter):

    """
    Class for Linux Intel platform to create XIOS module.

    WARNING!  Linux/Intel platform version of these build and
    test scripts is not currently working but should be fixed soon.
    """

    def __init__(self,
                 version,
                 modulePath,
                 srcUrl,
                 revNo,
                 platform):
        prereq = ['fortran/intel/15.0.0',
                  'mpi/mpich/3.1.2/ifort/15.0.0',
                  'hdf5/1.8.12/ifort/15.0.0',
                  'netcdf/4.3.3-rc1/ifort/15.0.0']

        XiosModuleWriter.__init__(self,
                                  version,
                                  modulePath,
                                  prereq,
                                  srcUrl,
                                  revNo,
                                  '',
                                  platform)
