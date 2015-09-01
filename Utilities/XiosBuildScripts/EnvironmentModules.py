#!/usr/bin/env python2.7
'''
Created on Jul 22, 2015

@author: Stephen Haddad
'''

from abc import ABCMeta, abstractmethod
import os

class ModuleWriterBase(object):
    '''
    classdocs
    '''
    __metaclass__ = ABCMeta


    def __init__(self):
        '''
        Constructor
        '''
        self.HelpMsg = ''
        self.WhatIsMsg = ''
        self.ModuleName = ''
        self.ParentModules = ''
        self.ModuleVersion = ''
        self.ModuleHomePath = ''
        self.ModuleFileDirectory = ''
        
        self.LocalVariablesList = []
        self.PrerequisiteList = []
        self.SetEnvList = []
        self.PrependPathList = []

    @abstractmethod
    def WriteModule(self):
        pass

    def SetupFilePath(self):
        if self.ParentModules == None or self.ParentModules == '':
            self.ModuleFileDirectory='{0}/modules/{1}'.format(self.ModuleHomePath,self.ModuleName)
            self.ModuleFilePath = '{0}/{1}'.format(self.ModuleFileDirectory, self.ModuleVersion)
        else:
            self.ModuleFileDirectory = '{0}/modules/{1}/{2}'.format(self.ModuleHomePath, self.ParentModules, self.ModuleName)
            self.ModuleFilePath = '{0}/{1}'.format(self.ModuleFileDirectory, self.ModuleVersion)
        
        if not os.path.exists(self.ModuleFileDirectory):
            os.makedirs(self.ModuleFileDirectory)


class SingleModuleWriter(ModuleWriterBase):        
    def __init__(self):
        ModuleWriterBase.__init__(self)
    
    def WriteModule(self):

        self.SetupFilePath()

        with open(self.ModuleFilePath,'w') as moduleFile:
            moduleFile.write('#%Module1.0####################################################################\n')
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
    def __init__(self):
        ModuleWriterBase.__init__(self)
        self.ModulesToLoad = []
    
    def WriteModule(self):
        self.SetupFilePath()
        
        with open(self.ModuleFilePath,'w') as moduleFile:
            moduleFile.write('#%Module1.0####################################################################\n')
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
        