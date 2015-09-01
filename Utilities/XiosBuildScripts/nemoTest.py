#!/usr/bin/env python2.7

# Expected environment variables
# - TEST_SYSTEM
# - XIOS
# - XIOS_PATH
# - NEMO
# - BUILD_PATH
# - nemoTasksJpi
# - nemoTasksJpj
# - xiosTasks
# - JP_CFG
# - NEMO_EXP_REL_PATH
#

from generateRunfile import generateRunfile
import os
import sys
import subprocess
from abc import ABCMeta, abstractmethod

#######################################################################

def BuildTestSystem(systemName, settingsDict):
    testSystem = None
    if systemName == UKMO_IBM_PW7_system.SYSTEM_NAME:
        testSystem = UKMO_IBM_PW7_system(settingsDict)
    elif systemName == UKMO_CRAY_XC40_system.SYSTEM_NAME:
        testSystem = UKMO_CRAY_XC40_system(settingsDict)
    elif systemName == UKMO_Linux_Intel_system.SYSTEM_NAME:
        testSystem = UKMO_Linux_Intel_system(settingsDict)
    return testSystem

class TestSystem(object):
    '''
    Base class to represent the system that nemo is being tested on. 
    '''
    #factory method
    SYSTEM_NAME = 'BASE_NEMO_TEST_SYSTEM'
    __metaclass__ = ABCMeta
    
    OUTPUT_FILE_LIST=['GYRE_5d_00010101_00011230_grid_T.nc',
                      'GYRE_5d_00010101_00011230_grid_V.nc',
                      'GYRE_5d_00010101_00011230_grid_U.nc',
                      'GYRE_5d_00010101_00011230_grid_W.nc']        

    def __init__(self, settingsDict):
        self.ScriptName = ''
        self.ScriptPath = ''
        self.SystemName = settingsDict['TEST_SYSTEM']
        self.xiosPath=settingsDict['XIOS_PATH']
        self.nemoDirName=settingsDict['NEMO']
        self.buildPathDir=settingsDict['BUILD_PATH']
        self.nemoTasksJpi=int(settingsDict['nemoTasksJpi'])
        self.nemoTasksJpj=int(settingsDict['nemoTasksJpj'])
        self.xiosTasks=int(settingsDict['xiosTasks'])
        self.jpcfg=int(settingsDict['JP_CFG'])
        self.NemoExperimentRelPath=settingsDict['NEMO_EXP_REL_PATH']
        self.LaunchDirectory=os.getcwd()
        self.SuiteMode=settingsDict.has_key('ROSE_DATA')
        self.TasksPerNode=int(settingsDict['TasksPerNode'])
        self.XiosTasksPerNode=int(settingsDict['XiosTasksPerNode'])
        try:
            self.ResultDestDir = settingsDict['NEMO_RESULT_DIR']
            self.DoResultCopy = True
        except:
            self.ResultDestDir = ''
            self.DoResultCopy = False


        # Number of NEMO tasks
        self.nemoTasks=self.nemoTasksJpi*self.nemoTasksJpj
        # Total Number of tasks

        self.PathToNemoExperiment=self.buildPathDir+'/'+self.nemoDirName+'/' + self.NemoExperimentRelPath + '/GYRE_' + str(self.jpcfg)+'/EXP00'
        if not os.path.isdir(self.PathToNemoExperiment):
            raise Exception('NEMO experiment directory not found {0:s}'.format(self.PathToNemoExperiment))

    

    def editIodefXmlFile(self):
        '''
        Edit iodef.xml 
        'one_file' replaced by 'multiple_file'
        '''
        namein='{0}/iodef.xml'.format(self.PathToNemoExperiment)
        nameout='{0}~'.format(namein)
        with open(namein,'r') as fpin, open(nameout,'w') as fpout: 
            for line in fpin:
#                if 'one_file' in line:
#                    line=line.replace('one_file','multiple_file')
                if 'multiple_file' in line:
                    line=line.replace('multiple_file','one_file')
                
                if ('using_server' in line) and ('false' in line):
                    line=line.replace('false','true')
                fpout.write(line)
        os.rename(nameout,namein)

    @abstractmethod
    def writeScript(self):
        pass
    
    @abstractmethod
    def runTestScript(self):
        pass
    
    def CopyOutput(self):
        if not self.DoResultCopy:
            print 'output not being copied'
            return

        if not os.path.exists(self.ResultDestDir):
            os.makedirs(self.ResultDestDir)
    
        for fileName1 in self.OUTPUT_FILE_LIST:
            path1 = '{0}/{1}'.format(self.PathToNemoExperiment, fileName1)
            print 'copying {src} to {dest}/'.format(src=path1,
                                                   dest=self.ResultDestDir)
            subprocess.call('cp {src} {dest}/'.format(src=path1,
                                                      dest=self.ResultDestDir),
                            shell=True)
        
    
class UKMO_IBM_PW7_system(TestSystem):
    '''
    Class to run nemo test on IBM POwer 7 system
    '''
    SYSTEM_NAME = 'UKMO_IBM_PW7'

    def __init__(self, settingsDict):
        print 'creating IBM Power 7 test system'
        TestSystem.__init__(self, settingsDict)
        self.ScriptName = 'opa.ll'
        self.ScriptPath = '{0}/{1}'.format(self.PathToNemoExperiment, self.ScriptName)

        self.totalTasks=self.nemoTasks+ self.xiosTasks
        if self.totalTasks%self.TasksPerNode == 0:
            self.nnodes = self.totalTasks // self.TasksPerNode
        else:
            self.nnodes = (self.totalTasks // self.TasksPerNode) +1

        # Create Runfile
        runFile='{0}/run_file'.format(self.PathToNemoExperiment)
        if os.path.exists(runFile):
            os.remove(runFile)
        self.generateRunfile(runFile,'./opa','./xios_server.exe',self.nemoTasks,self.xiosTasks,self.TasksPerNode)
        self.editIodefXmlFile()

        self.editNameList()

    def __str__(self):
        return 'System for testing NEMO on MO IBM Power 7 environment'


    def editNameList(self):
        '''
        Edit namelist
        '''
        namein='namelist'
        nameout=namein+'~'
    
        with open(namein,'r') as fpin, open(nameout,'w') as fpout:  
            for line in fpin:
                if 'jpnij ' in line:
                    jpnij_old=line.split()[2]
                    line=line.replace(jpnij_old,str(self.nemoTasks))
                if 'jpni ' in line:
                    jpni_old=line.split()[2]
                    line=line.replace(jpni_old,str(self.nemoTasksJpi))
                if 'jpnj ' in line:
                    jpnj_old=line.split()[2]
                    line=line.replace(jpnj_old,str(self.nemoTasksJpj))
                if ('nn_bench' in line) and ('0' in line):
                    line=line.replace('0','1')
                    fpout.write(line)
  
        os.rename(nameout,namein)

    def writeScript(self):
        with open(self.ScriptPath,'w') as fpll: 
            fpll.write('#!/bin/bash\n')
            if not self.SuiteMode:
                fpll.write('#\n')
                fpll.write('#@ class           = parallel\n')
                fpll.write('#@ job_type        = parallel\n')
                fpll.write('#@ job_name        = gyre_orca25\n')
                fpll.write('#@ output          = $(job_name).$(jobid).out\n')
                fpll.write('#@ error           = $(job_name).$(jobid).out\n')
                fpll.write('#@ notification     = error\n')
                fpll.write('#@ resources       =  ConsumableMemory(1500mb)\n')
                fpll.write('#@ node             = '+str(self.nnodes)+'\n')
                fpll.write('#@ total_tasks      = '+str(self.totalTasks)+'\n')
                fpll.write('#@ node_usage = not_shared\n')
                fpll.write('#@ task_affinity = core(1)\n')
                fpll.write('#@ cpu_limit        = 00:45:00\n')
                fpll.write('#@ wall_clock_limit = 00:45:00\n')
                fpll.write('#@ queue\n')
                fpll.write('#\n')
            fpll.write('\n')
            fpll.write('ulimit -c unlimited\n')
            fpll.write('ulimit -s unlimited\n')
            fpll.write('. /critical/opt/ukmo/supported/sbin/module_init_load\n')
            fpll.write('module_load xlf v14.1.0.1\n')
            fpll.write('module load xlcpp/v12.1.0.0\n')
            fpll.write('\n')
            fpll.write('export MP_PGMMODEL=mpmd\n')
            fpll.write('\n')
            fpll.write('poe -pgmmodel $MP_PGMMODEL -cmdfile ./run_file\n')
            fpll.write('\n')
            
        if self.SuiteMode:
            os.chmod(self.ScriptPath,477)
    
    def runTestScript(self):
        if self.SuiteMode:
            result1 = subprocess.call(self.ScriptPath)
        else:
            result1 = subprocess.call(['llsubmit',self.ScriptPath])
        if result1 != 0:
            raise Exception('Error executing NEMO test - error code: {0:d}'.format(result1) )

class UKMO_CRAY_XC40_system(TestSystem):
    '''
    Class to run nemo test on Cray XC40 system
    '''

    SYSTEM_NAME = 'UKMO_CRAY_XC40'

    def __init__(self, settingsDict):
        print 'creating Cray XC40 test system'
        TestSystem.__init__(self, settingsDict)
        self.ScriptName = 'opa.pbs'
        self.ScriptPath = '{0}/{1}'.format(self.PathToNemoExperiment, self.ScriptName)

        self.totalTasks=self.nemoTasks+ self.xiosTasks

        self.nnodes = (self.nemoTasks // self.TasksPerNode) + (self.xiosTasks // self.XiosTasksPerNode)
        if self.nemoTasks % self.TasksPerNode != 0:
            self.nnodes += 1
        if self.xiosTasks % self.XiosTasksPerNode != 0:
            self.nnodes += 1
        
        self.editIodefXmlFile()

    def __str__(self):
        return 'System for testing NEMO on MO Cray XC40 environment'

    def writeScript(self):

        if os.path.exists(self.ScriptPath):
            os.remove(self.ScriptPath)

        with open(self.ScriptPath,'w') as scriptFile:
            if not self.SuiteMode:
                scriptFile.write('#!/bin/bash --login\n')
                scriptFile.write('#PBS -N {0}\n'.format('test_nemo_gyre'))
                scriptFile.write('#PBS -l select={0:d}\n'.format(self.nnodes) )
                scriptFile.write('#PBS -l walltime=00:15:00\n')
                scriptFile.write('#PBS -j oe\n')
                scriptFile.write('#PBS -q parallel\n')
                scriptFile.write('#PBS -P climate\n')
            else:
                scriptFile.write('#!/bin/bash\n')
            scriptFile.write('cd {0}'.format(self.PathToNemoExperiment))
            scriptFile.write('\n')
            scriptFile.write('module load cray-netcdf-hdf5parallel/4.3.2\n')
            scriptFile.write('\n')
            scriptFile.write('aprun -n {0:d} -N {2:d} ./xios_server.exe : -n {1:d} ./opa\n'.format(self.xiosTasks,self.nemoTasks,self.XiosTasksPerNode))
            scriptFile.write('\n')
        
        if self.SuiteMode:
            os.chmod(self.ScriptPath,477)
    
    def runTestScript(self):
        print 'running test script at location {0}'.format(self.ScriptPath)
        if not os.path.exists(self.ScriptPath) or not os.path.isfile(self.ScriptPath):
            print 'ERROR: test script not found    !'
            sys.stderr.write('Test script creation failed, aborting test.')
            raise Exception('Test script creation failed, aborting test.')
        if self.SuiteMode:
            result1 = subprocess.call(self.ScriptPath)
        else:
            result1 = subprocess.call(['qsub',self.ScriptPath])
        if result1 != 0:
            raise Exception('Error executing NEMO test - error code: {0:d}'.format(result1) )

class UKMO_Linux_Intel_system(TestSystem):
    '''
    Class to run nemo test on Linux Desktop system with Intel Compiler environment
    '''

    SYSTEM_NAME = 'UKMO_LINUX_INTEL'

    def __init__(self, settingsDict):
        print 'creating Linux Intel test system'
        TestSystem.__init__(self, settingsDict)
        self.ScriptName = 'opa.sh'
        self.ScriptPath = '{0}/{1}'.format(self.PathToNemoExperiment, self.ScriptName)

        self.totalTasks=self.nemoTasks+ self.xiosTasks

        self.nnodes = 1
        self.editIodefXmlFile()

    def __str__(self):
        return 'System for testing NEMO on MO Linux desktop with Intel Compiler environment'

    def writeScript(self):
        if os.path.exists(self.ScriptPath):
            os.remove(self.ScriptPath)
            
        with open(self.ScriptPath,'w') as scriptFile:
            scriptFile.write('#!/bin/bash\n')
            scriptFile.write('cd {0}'.format(self.PathToNemoExperiment))
            scriptFile.write('\n')
            scriptFile.write('source /data/cr1/mhambley/modules/setup\n')
            scriptFile.write('module load environment/dynamo/compiler/intelfortran/15.0.0\n')
            scriptFile.write('\n')
            scriptFile.write('mpirun -np {0:d} ./xios_server.exe : -np {1:d} ./opa\n'.format(self.xiosTasks,self.nemoTasks))
            scriptFile.write('\n')
            
        os.chmod(self.ScriptPath,477)
    
    def runTestScript(self):
        print 'running test script at location {0}'.format(self.ScriptPath)
        if not os.path.exists(self.ScriptPath) or not os.path.isfile(self.ScriptPath):
            print 'ERROR: test script not found    !'
            sys.stderr.write('Test script creation failed, aborting test.')
            raise Exception('Test script creation failed, aborting test.')
        
        result1 = subprocess.call(self.ScriptPath)
        if result1 != 0:
            raise Exception('Error executing NEMO test - error code: {0:d}'.format(result1) )



        
def main():
    
    try:
        systemName = os.environ['TEST_SYSTEM']
    except Exception as e1:
        print 'Unable to determine system type, {0}'.format(str(e1))
    
    testSystem = BuildTestSystem(systemName, os.environ)
    # Change Directory
    os.chdir(testSystem.PathToNemoExperiment)
    print 'launch directory is {0}'.format(testSystem.LaunchDirectory)
    print 'current directory is {0}'.format(os.getcwd())
    
    # Create symbolic link to IO server
    xiosBinaryPath = testSystem.xiosPath + '/bin/xios_server.exe'
    xiosBinaryLink = '{0}/xios_server.exe'.format(testSystem.PathToNemoExperiment)
    print 'creating symbolic link to XIOS server:\n target: {0}\n link: {1}'.format(xiosBinaryPath, xiosBinaryLink)
    if os.path.islink(xiosBinaryLink):
        os.remove(xiosBinaryLink)
    os.symlink(xiosBinaryPath,xiosBinaryLink)
    
    print 'writing test script'
    testSystem.writeScript()
    print 'running test script'
    testSystem.runTestScript()

    testSystem.CopyOutput()    
    return 0

if __name__ == '__main__':
    status = main()
    exit(status)
