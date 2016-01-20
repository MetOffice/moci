#!/usr/bin/env python2.7
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
        self.HelpMsg = ''
        self.WhatIsMsg = ''
        self.ModuleName = ''
        self.ParentModules = ''
        self.ModuleVersion = ''
        self.RevisionNumber = ''
        self.ConfigRevisionNumber = ''
        self.ModuleHomePath = ''
        self.ModuleFileDirectory = ''

        self.LocalVariablesList = []
        self.PrerequisiteList = []
        self.SetEnvList = []
        self.PrependPathList = []

    @abstractmethod
    def WriteModule(self):
        '''
        Function that actually writes the module file. This function calls
        SetupFilePath() which sets up the absolute file path to the module
        file that will be written out.
        Usage:
        writer.WriteModule()
        '''
        pass

    def SetupFilePath(self):
        '''
        Function to create the absolute path to the module file that will be 
        written out. This is constructed from several pieces of information 
        which are are member variables:
         * ModuleName - The module name
         * ModuleVersion - The module version number 
         * RevisionNumber - The revision number of the source code used for 
                            building the module
         * ConfigRevisionNumber - (optional) The revision number of the 
                                 configuration used to build the modules. Only 
                                 used if there are separate revision numbers for
                                 the source code and the build configs.   

         If any of the non-optional parameters are missing, a 
         ModuleMissingInformationError is raised.
         
         Usage:
         writer.SetupFilePath()
        '''
        if (self.ModuleHomePath == ''
                or self.ModuleName == ''
                or self.ModuleVersion == ''
                or self.RevisionNumber == ''):
            errMsg1 = 'Information required to create ' \
                      'the module file(s) is missing '
            raise ModuleMissingInformationError(errMsg1)

        if self.ParentModules is None or self.ParentModules == '':
            filePathTemplate = '{ModuleHomePath}/modules/{ModuleName}/' \
                               '{ModuleVersion}'
        else:
            filePathTemplate = '{ModuleHomePath}/modules/{ParentModules}/' \
                               '{ModuleName}/{ModuleVersion}'

        relativePathTemplate = '{ModuleName}/{ModuleVersion}'
        if self.ConfigRevisionNumber != '':
            filePathTemplate += '/{ConfigRevisionNumber}'
            relativePathTemplate += '/{ConfigRevisionNumber}'
        relativePathTemplate += '/{RevisionNumber}'
        self.ModuleFileDirectory = filePathTemplate.format(**self.__dict__)
        self.ModuleRelativePath = relativePathTemplate.format(**self.__dict__)

        self.ModuleFilePath = '{0}/{1}'.format(self.ModuleFileDirectory,
                                               self.RevisionNumber)

        if not os.path.exists(self.ModuleFileDirectory):
            os.makedirs(self.ModuleFileDirectory)


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
        class.        '''
        ModuleWriterBase.__init__(self)

    def WriteModule(self):

        self.SetupFilePath()

        with open(self.ModuleFilePath, 'w') as moduleFile:
            moduleFile.write('#%Module1.0#####################################'
                             '###############################\n')
            moduleFile.write('proc ModulesHelp { } {\n')
            moduleFile.write('    puts stderr "{0}"\n'.format(self.HelpMsg))
            moduleFile.write('}\n')
            moduleFile.write('\n')
            moduleFile.write('module-whatis {0}\n'.format(self.WhatIsMsg))
            moduleFile.write('\n')
            moduleFile.write('conflict {0}\n'.format(self.ModuleName))
            moduleFile.write('\n')

            moduleFile.write('set version {0}\n'.format(self.ModuleVersion))
            for localVar1 in self.LocalVariablesList:
                moduleFile.write('set {0} {1}\n'.format(*localVar1))
            moduleFile.write('\n')

            for prereq1 in self.PrerequisiteList:
                moduleFile.write('prereq {0}\n'.format(prereq1))
            moduleFile.write('\n')

            for envStr1 in self.SetEnvList:
                moduleFile.write('setenv {0} {1}\n'.format(*envStr1))
            moduleFile.write('\n')

            for path1 in self.PrependPathList:
                moduleFile.write('prepend-path {0} {1}\n'.format(*path1))
            moduleFile.write('\n')


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
        self.ModulesToLoad = []

    def WriteModule(self):
        self.SetupFilePath()

        with open(self.ModuleFilePath, 'w') as moduleFile:
            moduleFile.write('#%Module1.0#####################################'
                             '###############################\n')
            moduleFile.write('proc ModulesHelp { } {\n')
            moduleFile.write('    puts stderr "{0}"\n'.format(self.HelpMsg))
            moduleFile.write('}\n')
            moduleFile.write('\n')
            moduleFile.write('module-whatis {0}\n'.format(self.WhatIsMsg))
            moduleFile.write('\n')
            moduleFile.write('conflict {0}\n'.format(self.ModuleName))
            moduleFile.write('\n')
            moduleFile.write('set version {0}\n'.format(self.ModuleVersion))
            moduleFile.write('\n')
            for prereq1 in self.PrerequisiteList:
                moduleFile.write('prereq {0}\n'.format(prereq1))
            moduleFile.write('\n')
            for envStr1 in self.SetEnvList:
                moduleFile.write('setenv {0} {1}\n'.format(*envStr1))
            moduleFile.write('\n')
            for path1 in self.PrependPathList:
                moduleFile.write('prepend-path {0}\n'.format(path1))
            moduleFile.write('\n')
            for mod1 in self.ModulesToLoad:
                moduleFile.write('module load {0}\n'.format(mod1))
            moduleFile.write('\n')
