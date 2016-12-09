#!/usr/bin/env python2.7
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
'''
Created on Jul 22, 2015

@author: Stephen Haddad

The EnvironmentModules module handles creation of files to be used by the
"Environment Modules" system. Modules files handle setting up environment
variables on linux/unix systems such the correct versions of compilers,
libraries and application are used.

A module file for a library make typically
set environment variables such as MYLIB_INC to point to the directory containing
include files and MYLIB_LIB to point to files used during linking. Any
environment variables can be set my the module file.

The advantage of the module system over manually setting environment is that
one can easily load, unload or swap modules and the system ensures that
different variables are consistent. Often particular versions of libraries and
compilers will be loaded together in the same modules. This ensures that
compatible versions are used.

'''

from abc import ABCMeta, abstractmethod
import os


class ModuleMissingInformationError(Exception):

    '''
    Raised when writing a module if important information has not been
    passed to the Module Writer class.
    '''
    pass


class ModuleWriterBase(object):

    '''
    Abstract Base class for all Environment Module writing classes.
    '''
    __metaclass__ = ABCMeta

    def __init__(self):
        '''
        Constructor for module writer base class. To keep the object
        construction more compact, the parameters are not passed as parameters
        but should be set in the __init__ constructor function of the concrete
        class.
        '''
        self.help_msg = ''
        self.what_is_msg = ''
        self.module_name = ''
        self.parent_modules = ''
        self.module_version = ''
        self.revision_number = ''
        self.config_revision_number = ''
        self.module_home_path = ''
        self.module_file_directory = ''

        self.local_variables_list = []
        self.prerequisite_list = []
        self.set_env_list = []
        self.prepend_path_list = []

        self.module_relative_path = None
        self.module_file_path = None
        self.compiler_module = None

    @abstractmethod
    def write_module(self):
        '''
        Function that actually writes the module file. This function calls
        setup_file_path() which sets up the absolute file path to the module
        file that will be written out.
        Usage:
        writer.write_module()
        '''
        pass

    def setup_file_path(self):
        '''
        Function to create the absolute path to the module file that will be
        written out. This is constructed from several pieces of information
        which are are member variables:
         * module_ name - The module name
         * module_version - The module version number
         * revision_number - The revision number of the source code used for
                            building the module
         * config_revision_number - (optional) The revision number of the
                                 configuration used to build the modules. Only
                                 used if there are separate revision numbers for
                                 the source code and the build configs.

         If any of the non-optional parameters are missing, a
         ModuleMissingInformationError is raised.

         Usage:
         writer.setup_file_path()
        '''
        err_msg_base = '{0} field required to create the '\
            'module file(s) is missing '
        if self.module_home_path == '':
            err_msg1 = err_msg_base.format('Module home path')
            raise ModuleMissingInformationError(err_msg1)
        if self.module_name == '':
            err_msg1 = err_msg_base.format('Module Name')
            raise ModuleMissingInformationError(err_msg1)
        if self.module_version == '':
            err_msg1 = err_msg_base.format('Module Version')
            raise ModuleMissingInformationError(err_msg1)
        if self.revision_number == '':
            err_msg1 = err_msg_base.format('Revision Number')
            raise ModuleMissingInformationError(err_msg1)

        if self.parent_modules is None:
            parent_modules1 = ''
        else:
            parent_modules1 = self.parent_modules

        self.module_file_directory = os.path.join(self.module_home_path,
                                                  'modules',
                                                  parent_modules1,
                                                  self.module_name,
                                                  self.module_version,
                                                  self.config_revision_number)

        self.module_relative_path = os.path.join(self.module_name,
                                                 self.module_version,
                                                 self.config_revision_number,
                                                 self.revision_number)


        self.module_file_path = os.path.join(self.module_file_directory,
                                             self.revision_number)

        if not os.path.exists(self.module_file_directory):
            os.makedirs(self.module_file_directory)


class SingleModuleWriter(ModuleWriterBase):

    '''
    Abstract class to write out a module which represent a single unit. This
    may be a library, application, compiler etc. This is primarily
    differentiated from the PrgEnvModuleWriter which is essentially a compound
    module.

    Put another way, the modules written out by SingleModuleWriter
    usually set the actual environment variable for a library, compiler etc.
    while the PrgEnvModuleWriter primarily loads other modules.
    '''

    def __init__(self):
        '''
        Constructor for Single Module Writer class. To keep the object
        construction more compact, the parameters are not passed as parameters
        but should be set in the __init__ constructor function of the concrete
        class.
        '''
        ModuleWriterBase.__init__(self)

    def write_module(self):

        self.setup_file_path()

        with open(self.module_file_path, 'w') as module_file:
            module_file.write('#%Module1.0\n')
            module_file.write('proc ModulesHelp { } {\n')
            module_file.write('    puts stderr "{0}"\n'.format(self.help_msg))
            module_file.write('}\n')
            module_file.write('\n')
            module_file.write('module-whatis {0}\n'.format(self.what_is_msg))
            module_file.write('\n')
            module_file.write('conflict {0}\n'.format(self.module_name))
            module_file.write('\n')

            module_file.write('set version {0}\n'.format(self.module_version))
            for local_var1 in self.local_variables_list:
                module_file.write('set {0} {1}\n'.format(*local_var1))
            module_file.write('\n')

            if self.compiler_module:
                module_file.write('prereq {0}\n'.format(self.compiler_module))

            for prereq1 in self.prerequisite_list:
                module_file.write('prereq {0}\n'.format(prereq1))
            module_file.write('\n')

            for env_str1 in self.set_env_list:
                module_file.write('setenv {0} {1}\n'.format(*env_str1))
            module_file.write('\n')

            for path1 in self.prepend_path_list:
                module_file.write('prepend-path {0} {1}\n'.format(*path1))
            module_file.write('\n')


class PrgEnvModuleWriter(ModuleWriterBase):

    '''
    Abstract class to write out a module which load one or more other modules.
    These may be libraries, applications, compilers etc. This is primarily
    differentiated from the SingleModuleWriter which represents a single
    library, application etc.

    Put another way, the modules written out by SingleModuleWriter
    usually set the actual environment variable for a library, compiler etc.
    while the PrgEnvModuleWriter primarily loads other modules.
    '''

    def __init__(self):
        '''
        Constructor for PrgEnv Module Writer base class. To keep the object
        construction more compact, the parameters are not passed as parameters
        but should be set in the __init__ constructor function of the concrete
        class.
        '''
        ModuleWriterBase.__init__(self)
        self.modules_to_load = []
        self.default_compiler = None

    def write_module(self):
        self.setup_file_path()

        with open(self.module_file_path, 'w') as module_file:
            module_file.write('#%Module1.0#####################################'
                              '###############################\n')
            module_file.write('proc ModulesHelp { } {\n')
            module_file.write('    puts stderr "{0}"\n'.format(self.help_msg))
            module_file.write('}\n')
            module_file.write('\n')
            module_file.write('module-whatis {0}\n'.format(self.what_is_msg))
            module_file.write('\n')
            module_file.write('conflict {0}\n'.format(self.module_name))
            module_file.write('\n')
            module_file.write('set version {0}\n'.format(self.module_version))
            module_file.write('\n')
            for prereq1 in self.prerequisite_list:
                module_file.write('prereq {0}\n'.format(prereq1))
            module_file.write('\n')
            for env_str1 in self.set_env_list:
                module_file.write('setenv {0} {1}\n'.format(*env_str1))
            module_file.write('\n')
            for path1 in self.prerequisite_list:
                module_file.write('prepend-path {0}\n'.format(path1))
            module_file.write('\n')
            if not self.compiler_module is None:
                comp_str = 'module swap {0} {1}\n\n'
                comp_str = comp_str.format(self.default_compiler,
                                           self.compiler_module)
                module_file.write(comp_str)

            for mod1 in self.modules_to_load:
                module_file.write('module load {0}\n'.format(mod1))
            module_file.write('\n')
