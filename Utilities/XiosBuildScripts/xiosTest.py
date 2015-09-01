#!/usr/bin/env python2.7

# expected environment variables:
#   TEST_SYSTEM
#   XIOS_PATH

import os
import shutil
import subprocess
from abc import ABCMeta, abstractmethod

class XiosTestSystem(object):
    SYSTEM_NAME='Base'
    __metaclass__ = ABCMeta

    OUTPUT_FILE_LIST=['output_atmosphere_0.nc',
                      'output_atmosphere_zoom_0.nc',
                      'output_surface_6h_2.nc',
                      'output_atmosphere_1.nc',
                      'output_surface_1d.nc',
                      'output_surface_6h_3.nc',
                      'output_atmosphere_2.nc',
                      'output_surface_6h_0.nc',
                      'output_atmosphere_3.nc',
                      'output_surface_6h_1.nc']    

    def __init__(self, settingsDict):
        self.WorkingDir = os.getcwd()
        self.TestDir = '{0}/xiosTestComplete'.format(self.WorkingDir) 
        if os.path.exists(self.TestDir):
            if os.path.isdir(self.TestDir):
                shutil.rmtree(self.TestDir)
            else:
                os.remove(self.TestDir)
        os.mkdir(self.TestDir)
        
        self.SuiteMode = settingsDict.has_key('ROSE_DATA')
        self.XiosRootDir = settingsDict['XIOS_PATH']
        self.XiosServerLocation = self.XiosRootDir + '/bin/xios_server.exe'
        self.TestClientLocation = self.XiosRootDir + '/bin/test_complete.exe'
        
        if not os.path.exists(self.XiosServerLocation):
            raise Exception('Xios server executable not found: {0}'.format(self.XiosServerLocation))
        if not os.path.exists(self.TestClientLocation):
            raise Exception('Xios testclient executable not found: {0}'.format(self.TestClientLocation))
        
        #copy XML def files
        xmlFileList1 = ['{0}/inputs/COMPLETE/context_atmosphere.xml'.format(self.XiosRootDir)]
        xmlFileList1 += ['{0}/inputs/COMPLETE/context_surface.xml'.format(self.XiosRootDir)]
        xmlFileList1 += ['{0}/inputs/COMPLETE/iodef.xml'.format(self.XiosRootDir)]
        for defFileName1 in xmlFileList1:
            shutil.copy(defFileName1, self.TestDir)
            
        # link to executables
        self.ServerLinkPath = self.TestDir + '/xios_server.exe'
        if os.path.islink(self.ServerLinkPath):
            os.remove(self.ServerLinkPath)
        os.symlink(self.XiosServerLocation,self.ServerLinkPath)
        
        self.ClientLinkPath = self.TestDir + '/test_complete.exe'
        if os.path.islink(self.ClientLinkPath):
            os.remove(self.ClientLinkPath)
        os.symlink(self.TestClientLocation,self.ClientLinkPath)
        
        self.TestScriptFileName = '{0}/testScript.sh'.format(self.WorkingDir)
        
        try:
            self.ResultDestDir = settingsDict['XIOS_RESULT_DIR']
            self.DoResultCopy = True
        except:
            self.ResultDestDir = ''
            self.DoResultCopy = False
        
         
    @abstractmethod
    def __str__(self):
        pass

    def runTest(self):
        self.writeTestFile()
        self.executeTestScript()
        self.CopyOutput() 
    
    @abstractmethod
    def writeTestFile(self):
        pass
    
        
    @abstractmethod
    def executeTestScript(self):
        pass
    
    def CopyOutput(self):
        if not self.DoResultCopy:
            print 'output not being copied'
            return
        
        if not os.path.exists(self.ResultDestDir):
            os.makedirs(self.ResultDestDir)
    
        for fileName1 in self.OUTPUT_FILE_LIST:
            path1 = '{0}/{1}'.format(self.TestDir, fileName1)
            print 'copying from {src} to {dest}/'.format(src=path1, 
                                                        dest=self.ResultDestDir)
            subprocess.call('cp {src} {dest}/'.format(src=path1,
                                                       dest=self.ResultDestDir),
                            shell=True)
    
    
class XiosIBMPW7TestSystem(XiosTestSystem):
    SYSTEM_NAME='UKMO_IBM_PW7'
    def __init__(self, settingsDict):
        XiosTestSystem.__init__(self, settingsDict)
        self.CommandFileName = 'runFile'
        self.CommandFilePath = '{0}/{1}'.format(self.TestDir,self.CommandFileName)
        self.NumServers = 2
        self.NumClients=8

    def __str__(self):
        return 'Class to run XIOS complete test on UKMO IBM Power-7 supercomputer'

    def writeTestFile(self):
        '''
        '''
        if os.path.exists(self.TestScriptFileName):
            os.remove(self.TestScriptFileName)
        
        with open(self.TestScriptFileName,'w') as scriptFile1:
            if not self.SuiteMode:
                scriptFile1.write('#!/bin/ksh \n')
                scriptFile1.write('#@ shell = /bin/ksh\n')
                scriptFile1.write('#@ class = parallel\n')
                scriptFile1.write('#@ job_type = parallel\n')
                scriptFile1.write('#@ job_name = xiosTest_detached\n')
                scriptFile1.write('#@ resources = ConsumableMemory(1500mb)\n')
                scriptFile1.write('#@ node = 1\n')
                scriptFile1.write('#@ total_tasks=10\n')
                scriptFile1.write('#@ wall_clock_limit = 00:15:00\n')
                scriptFile1.write('#@ notification = error\n')
                scriptFile1.write('#@ output = xiosTestDetached.log\n')
                scriptFile1.write('#@ error = xiosTestDetached.log\n')
                scriptFile1.write('#@ environment = COPY_ALL\n')
                scriptFile1.write('#@ queue\n')
            else:
                scriptFile1.write('#!/bin/ksh\n')        
                
            scriptFile1.write('cd {0}\n'.format(self.TestDir))
            scriptFile1.write('echo current dir is $(pwd)\n')
            scriptFile1.write('rm -rf *.csv *.nc\n')        
            scriptFile1.write('poe -pgmmodel MPMD -cmdfile ./{0}\n'.format(self.CommandFileName))
            scriptFile1.write('\n')
                  
       
        os.chmod(self.TestScriptFileName,477)
        
        with open(self.CommandFilePath,'w') as commandFile:
            commandFile.write((self.ServerLinkPath+'\n') * self.NumServers)
            commandFile.write((self.ClientLinkPath+'\n') * self.NumClients)
    
    def executeTestScript(self):
        print '\nExecuting xios test configuration'
        if self.SuiteMode:
            result1 = subprocess.call(self.TestScriptFileName)
        else:
            result1 = subprocess.call(['llsubmit',self.TestScriptFileName])
        if result1 != 0:
            raise Exception('Error executing XIOS test')
                
class XiosCrayXC40TestSystem(XiosTestSystem):
    SYSTEM_NAME='UKMO_CRAY_XC40'
    def __init__(self, settingsDict):
        XiosTestSystem.__init__(self, settingsDict)
    
    def __str__(self):
        return 'Class to run XIOS complete test on UKMO Cray XC-40 HPC'
    
    def writeTestFile(self):
        '''
        '''
        if os.path.exists(self.TestScriptFileName):
            os.remove(self.TestScriptFileName)
        
        with open(self.TestScriptFileName,'w') as scriptFile1:
            if not self.SuiteMode:
                scriptFile1.write('#!/bin/bash --login\n')        
                scriptFile1.write('#PBS -N XIOScomplete\n')        
                scriptFile1.write('#PBS -l select=2\n')        
                scriptFile1.write('#PBS -l walltime=00:15:00\n')        
                scriptFile1.write('#PBS -j oe\n')
            else:
                scriptFile1.write('#!/bin/bash\n')        
                    
            scriptFile1.write('\n')        
            scriptFile1.write('cd {0}\n'.format(self.TestDir))
            scriptFile1.write('echo current dir is $(pwd)\n')
            scriptFile1.write('rm -rf *.csv *.nc\n')        
            scriptFile1.write('\n')        
            scriptFile1.write('aprun -n 28 ./test_complete.exe : -n 4 ./xios_server.exe\n')        
            scriptFile1.write('\n')      
        os.chmod(self.TestScriptFileName,477)
    
    def executeTestScript(self):
        print '\nExecuting xios test configuration'
        if self.SuiteMode:
            result1 = subprocess.call(self.TestScriptFileName)
        else:
            result1 = subprocess.call(['qsub',self.TestScriptFileName])
        if result1 != 0:
            raise Exception('Error executing XIOS test')    

class XiosLinuxIntelTestSystem(XiosTestSystem):
    SYSTEM_NAME='UKMO_LINUX_INTEL'
    def __init__(self, settingsDict):
        XiosTestSystem.__init__(self, settingsDict)
    
    def __str__(self):
        return 'Class to run XIOS complete test on UKMO Linux Desktop with Intel compiler environment'
    
    def writeTestFile(self):
        '''
        '''
        if os.path.exists(self.TestScriptFileName):
            os.remove(self.TestScriptFileName)
        
        with open(self.TestScriptFileName,'w') as scriptFile1:
            scriptFile1.write('#!/bin/bash\n')        
            scriptFile1.write('\n')        
            scriptFile1.write('cd {0}\n'.format(self.TestDir))
            scriptFile1.write('echo current dir is $(pwd)\n')
            scriptFile1.write('rm -rf *.csv *.nc\n')        
            scriptFile1.write('\n')        
            scriptFile1.write('mpirun -n 3 ./test_complete.exe : -n 1 ./xios_server.exe\n')        
            scriptFile1.write('\n')      
        os.chmod(self.TestScriptFileName,477)
    
    def executeTestScript(self):
        print '\nExecuting xios test configuration'
        result1 = subprocess.call(self.TestScriptFileName)
        if result1 != 0:
            raise Exception('Error executing XIOS test')        
def createTestSystem(systemName, settingsDict):
    testSystem1 = None
    if systemName == XiosIBMPW7TestSystem.SYSTEM_NAME:
        testSystem1 = XiosIBMPW7TestSystem(settingsDict)
    elif systemName == XiosCrayXC40TestSystem.SYSTEM_NAME:
        testSystem1 = XiosCrayXC40TestSystem(settingsDict)
    elif systemName == XiosLinuxIntelTestSystem.SYSTEM_NAME:
        testSystem1 = XiosLinuxIntelTestSystem(settingsDict)
    else:
        raise Exception('Invalid system name for test system')
    return testSystem1

def main():
    systemName = os.environ['TEST_SYSTEM']
    testSystem1 = createTestSystem(systemName, os.environ) 

    testSystem1.runTest()    

if __name__=='__main__':
    main()

