#!/usr/bin/env python2.7
import os
import subprocess
import shutil
import sys
from abc import ABCMeta, abstractmethod

# Build nemo executable
#
# Inputs
# 
#   Environment variables:
#     NEMO
#     NEMO_REPO_URL
#     NEMO_REV
#     BUILD_PATH
#     XIOS
#     MTOOLS
#     XIOS_PATH
#     USE_OASIS: 
#      if true: 
#        OASIS_ROOT        
#     XLF_MODULE
#     XLCPP_MODULE
#     JP_CFG
#     NEMO_POST_BUILD_CLEANUP

    
BUILD_SCRIPT_FILENAME = 'nemoBuildScript01.sh'
EXTRACT_SCRIPT_FILENAME = 'nemoExtractScript01.sh'

class NemoBuildSystem(object):
    __metaclass__ = ABCMeta
    SYSTEM_NAME = 'BASE_CLASS'
    def __init__(self, settingsDict):
        self.TestSystem = settingsDict['TEST_SYSTEM']
        self.WorkingDirectory = os.getcwd()
        self.ShellSpecifierString = '#!/bin/sh'
        self.ModulesToLoad = []
        self.LibraryName = settingsDict['NEMO']
        self.SourceDirectory = '{0}/{1}'.format(self.WorkingDirectory,self.LibraryName)
        self.RepositoryUrl = settingsDict['NEMO_REPO_URL']
        self.RevisionNumber = settingsDict['NEMO_REV']
        self.BuildPath = settingsDict['BUILD_PATH']
        self.XiosDirectory = settingsDict['XIOS_PATH']
        self.UseOasis = settingsDict['USE_OASIS'] == 'true'
        if self.UseOasis:
            self.OasisDirectory = settingsDict['OASIS_ROOT']
        else:
            self.OasisDirectory = ''
        self.NemoConfig = 'GYRE'
        self.ConfigSuffix = settingsDict['JP_CFG']
        self.NemoConfigBuildName = '{0}_{1}'.format(self.NemoConfig,self.ConfigSuffix)
        self.OasisFcFlags = ''
        self.OasisLdFlags = ''
        self.TarCommand = 'tar'
        self.ArchFileName = None
        self.DoPostBuildCleanup = settingsDict['NEMO_POST_BUILD_CLEANUP'] == 'true'
        self.NumberOfBuildProcessors = 4

    def __str__(self):
        return 'Nemo build system base class'

    def SetupFiles(self):
        self.getSourceCode()
        self.writeArchFiles()
        self.setupConfigFiles()

    def getSourceCode(self):
        destinationDir = self.SourceDirectory
        if os.path.exists(destinationDir) and os.path.isdir(destinationDir):
            shutil.rmtree(destinationDir)
        
        scriptFileName = '{0}/{1}'.format(self.WorkingDirectory,
                                          EXTRACT_SCRIPT_FILENAME)
        if os.path.exists(scriptFileName) and os.path.isfile(scriptFileName):
            os.remove(scriptFileName)
        with open(scriptFileName,'w') as extractScript:
            extractScript.write('{0}\n'.format(self.ShellSpecifierString))
            extractScript.write('fcm co {0}@{1} {2}\n'.format(self.RepositoryUrl,self.RevisionNumber,destinationDir))
        os.chmod(scriptFileName,477)
        print '\nexecuting fcm check-out command\n'
        result1 = subprocess.call(scriptFileName)
        if result1 != 0:
            raise Exception('Error extracting {0} source code'.format(self.LibraryName))

    @abstractmethod
    def writeArchFiles(self):
        pass
    
    @abstractmethod
    def setupConfigFiles(self):
        pass
    
    def DoBuild(self):
        scriptName = self.writeBuildScript()
        self.executeBuildScript(scriptName)

    @abstractmethod
    def writeBuildScript(self):
        pass
    
    def executeBuildScript(self, buildScriptFileName):
        print 'executing build script {0}'.format(buildScriptFileName)
        returnCode = subprocess.call(buildScriptFileName)
        if returnCode != 0:
            raise Exception('Error compiling NEMO: build failed!')
    
    def checkBuild(self):
        nemoExePath = '{0}/{1}/CONFIG/{2}/BLD/bin/nemo.exe'.format(self.WorkingDirectory,self.LibraryName,self.NemoConfigBuildName)
        if not os.path.exists(nemoExePath):
            raise Exception('NEMO executable file not found at {0}, build failed!'.format(nemoExePath))
    
    def copyFiles(self):
        destBase = self.BuildPath + '/' + self.LibraryName
        print 'copying output files'
        if os.path.exists(destBase) and os.path.isdir(destBase):
            print 'removing dir {0}'.format(destBase)
            shutil.rmtree(destBase)
        
        sourceDir = '{0}/{1}/CONFIG/{2}'.format(self.WorkingDirectory,self.LibraryName,self.NemoConfigBuildName)
        destDir = '{0}/{1}'.format(destBase,self.NemoConfigBuildName)
        print 'copying {2} config directory from  {0} to {1}'.format(sourceDir,destDir,self.NemoConfigBuildName)
        shutil.copytree(sourceDir, destDir)
        
        sourceSharedDir = '{0}/{1}/CONFIG/SHARED'.format(self.WorkingDirectory,self.LibraryName)
        destSharedDir = '{0}/SHARED'.format(destBase)
        print 'copying SHARED directory from  {0} to {1}'.format(sourceSharedDir,destSharedDir)
        shutil.copytree(sourceSharedDir, destSharedDir)
        
    def cleanup(self):
        if self.DoPostBuildCleanup:
            print 'removing build working directory {0}'.format(self.SourceDirectory)
            shutil.rmtree(self.SourceDirectory)    
        
    
class NemoIBMPW7BuildSystem(NemoBuildSystem):
    SYSTEM_NAME = 'UKMO_IBM_PW7'
    def __init__(self, settingsDict):
        NemoBuildSystem.__init__(self)
        self.ShellSpecifierString = '#!/bin/ksh'
        self.ThirdPartyLibraryDir = settingsDict['MTOOLS']
        self.ModulesToLoad += [settingsDict['XLF_MODULE']]
        self.ModulesToLoad += [settingsDict['XLCPP_MODULE']]
        self.ModulesToLoad += ['aix/libc-compile-fix']
        if self.UseOasis:
            self.OasisFcFlags = '-I{0}/build'.format(self.OasisDirectory)
            self.OasisLdFlags = '-L{0}/lib -lmct -lmpeu -lscrip -lpsmile.MPI1'.format(self.OasisDirectory)
        self.TarCommand = '/opt/freeware/bin/tar'
        self.ArchFileName = 'arch-{0}.fcm'.format(NemoIBMPW7BuildSystem.SYSTEM_NAME)
      
    def __str__(self):
        return 'Nemo build system for UKMO IBM Power 7 HPC'
    

    def writeArchFiles(self):
	archFilePath = '{0}/ARCH/{1}'.format(self.SourceDirectory,self.ArchFileName)
        with open(archFilePath,'w') as archFile:
            archFile.write('%XIOS_ROOT           {0}\n'.format(self.XiosDirectory))
            archFile.write('%NCDF_INC            -I{0}/include\n'.format(self.ThirdPartyLibraryDir))
            archFile.write('%NCDF_LIB            -L {0}/lib -lnetcdf -lnetcdff -lhdf5 -lhdf5_hl -lhdf5_fortran -lz\n'.format(self.ThirdPartyLibraryDir))
            archFile.write('%FC                   mpxlf2003_r -WF,-P -qsuffix=cpp=f90 -q64\n')
            archFile.write('%FCFLAGS             -qrealsize=8 -qextname -qsuffix=f=f90 -qarch=pwr7 -qtune=pwr7 -NS32768 -I{0}/include {1} -g -O3\n'.format(self.ThirdPartyLibraryDir,self.OasisFcFlags))
            archFile.write('%-qnostrict\n')
            archFile.write('%FFLAGS              -qrealsize=8 -qextname -qsuffix=f=f90 -qarch=pwr7 -qtune=pwr7 -NS32768 -I{0}/include -g -O3\n'.format(self.ThirdPartyLibraryDir))
            archFile.write('%-qnostrict\n')
            archFile.write('%LD                  mpCC_r -q64\n')
            archFile.write('%LDFLAGS             -lxlf90 -L {0}/lib -lnetcdf {1} -L/projects/um1/lib -lsig -O3 -L MASS\n'.format(self.ThirdPartyLibraryDir, self.OasisLdFlags))
            archFile.write('%FPPFLAGS            -E -P -traditional -I/opt/ibmhpc/pecurrent/ppe.poe/include -I/usr/lpp/ppe.poe/include/thread64\n')
            archFile.write('%AR                  ar\n')
            archFile.write('%ARFLAGS             rs\n')
            archFile.write('%MK                  gmake\n')
            archFile.write('%USER_INC            %NCDF_INC -I%XIOS_ROOT/inc\n')
            archFile.write('%USER_LIB            -L%XIOS_ROOT/lib -lxios %NCDF_LIB\n')
            
    def setupConfigFiles(self):
        scriptFileName = '{0}/setupConfig01.sh'.format(self.WorkingDirectory)
        if os.path.exists(scriptFileName) and os.path.isfile(scriptFileName):
            os.remove(scriptFileName)
        with open(scriptFileName,'w') as configScript:
            configScript.write('#!/bin/ksh\n')
            configScript.write('cd {0}/NEMO/OPA_SRC\n'.format(self.SourceDirectory))
            configScript.write("sed 's|.*jp_cfg\ =.*|      jp_cfg\ = '$JP_CFG' ,                \&   \!\:|' par_GYRE.h90 > tmp\n")
            configScript.write('mv tmp par_GYRE.h90\n')
        os.chmod(scriptFileName,477)
        print '\nsetting up nemo config files\n'
        result1 = subprocess.call(scriptFileName)
        if result1 != 0:
            raise Exception('Error setting up nemo config'.format(self.LibraryName))

    def writeBuildScript(self):
        buildScriptFileName = '{0}/{1}'.format(self.WorkingDirectory,
                                               BUILD_SCRIPT_FILENAME)
        if os.path.exists(buildScriptFileName) and os.path.isfile(buildScriptFileName):
            os.remove(buildScriptFileName)
        with open(buildScriptFileName,'w') as buildScript:
            buildScript.write('#!/bin/ksh\n')
            buildScript.write('cd {0}/CONFIG\n'.format(self.SourceDirectory))
            buildScript.write('. /critical/opt/Modules/default/init/ksh\n')
            for module1 in self.ModulesToLoad:
                buildScript.write('module load {0}\n'.format(module1))
            buildScript.write('echo $(module list)\n')
            buildScript.write('\n')
            buildScript.write('./makenemo -m {2} -r {0} -n {1} add_key key_nosignedzero\n'.format(self.NemoConfig,self.NemoConfigBuildName,NemoIBMPW7BuildSystem.SYSTEM_NAME))
            buildScript.write('\n')
        os.chmod(buildScriptFileName,477)
        return buildScriptFileName
    
    

class NemoCrayXC40BuildSystem(NemoBuildSystem):
    SYSTEM_NAME = 'UKMO_CRAY_XC40'
    
    
    def __init__(self, settingsDict):
        NemoBuildSystem.__init__(self, settingsDict)
        self.ArchFileName = 'arch-CRAY_XC40.fcm'
        self.ModulesToLoad += ['cray-hdf5-parallel/1.8.13']
        self.ModulesToLoad += ['cray-netcdf-hdf5parallel/4.3.2']
        if self.UseOasis:
            self.OasisFcFlags = '-I{0}/build'.format(self.OasisDirectory)
            self.OasisLdFlags = '-L{0}/lib -lmct -lmpeu -lscrip -lpsmile.MPI1'.format(self.OasisDirectory)
        self.TarCommand = 'tar'
        self.ArchFileName = 'arch-{0}.fcm'.format(NemoCrayXC40BuildSystem.SYSTEM_NAME)
        
    def __str__(self):
        return 'Nemo build system for UKMO Cray XC40 HPC'

    def writeArchFiles(self):
        archFilePath = '{0}/ARCH/{1}'.format(self.SourceDirectory,self.ArchFileName)
        with open(archFilePath,'w') as archFile:
            archFile.write('%NCDF_HOME           $NETCDF_DIR\n')
            archFile.write('%HDF5_HOME           $HDF5_DIR\n')
            archFile.write('%XIOS_HOME           {0}\n'.format(self.XiosDirectory))
            archFile.write('%OASIS_HOME           {0}\n'.format(self.OasisDirectory))
            archFile.write('\n')
            archFile.write('%NCDF_INC            -I%NCDF_HOME/include -I%HDF5_HOME/include\n')
            archFile.write('%NCDF_LIB            -L%HDF5_HOME/lib -L%NCDF_HOME/lib -lnetcdff -lnetcdf -lhdf5_hl -lhdf5 -lz\n')
            archFile.write('\n')
            archFile.write('%XIOS_INC            -I%XIOS_HOME/inc\n')
            archFile.write('%XIOS_LIB            -L%XIOS_HOME/lib -lxios\n')
            archFile.write('\n')
            archFile.write('%OASIS_INC           -I%OASIS_HOME/build/lib/mct -I%OASIS_HOME/build/lib/psmile.MPI1\n')
            archFile.write('%OASIS_LIBDIR        -L%OASIS_HOME/lib\n')
            archFile.write('%OASIS_LIB           -lpsmile.MPI1 -lmct -lmpeu -lscrip\n')
            archFile.write('%CPP                 cpp\n')
            archFile.write('%FC                  ftn\n')
            archFile.write('\n')
            archFile.write('%FCFLAGS             -em -s real64 -s integer32  -O2 -hflex_mp=intolerant -e0 -ez\n')
            archFile.write('%FFLAGS              -em -s real64 -s integer32  -O0 -hflex_mp=strict -e0 -ez -Rb\n')
            archFile.write('%LD                  ftn\n')
            archFile.write('%FPPFLAGS            -P -E -traditional-cpp\n')
            archFile.write('%LDFLAGS             -hbyteswapio\n')
            archFile.write('%AR                  ar\n')
            archFile.write('%ARFLAGS             -r\n')
            archFile.write('%MK                  gmake\n')
            archFile.write('\n')
            archFile.write('%USER_INC            %NCDF_INC %OASIS_INC %XIOS_INC  \n')
            archFile.write('%USER_LIB            %NCDF_LIB %OASIS_LIBDIR %OASIS_LIB %XIOS_LIB %OASIS_LIB\n')
            archFile.write('\n')

    def setupConfigFiles(self):
        pass

    def writeBuildScript(self):
        buildScriptFileName = '{0}/{1}'.format(self.WorkingDirectory,
                                               BUILD_SCRIPT_FILENAME)
        if os.path.exists(buildScriptFileName) and os.path.isfile(buildScriptFileName):
            os.remove(buildScriptFileName)
#        oasisKeys = ''
#        if self.UseOasis:
#            oasisKeys = 'key_oasis3 key_oa3mct_v3'
        with open(buildScriptFileName,'w') as buildScript:
            buildScript.write('#!/bin/sh\n')
            buildScript.write('cd {0}/CONFIG\n'.format(self.SourceDirectory))
            for module1 in self.ModulesToLoad:
                buildScript.write('module load {0}\n'.format(module1))
            buildScript.write('\n')
#            buildScript.write('./makenemo -m {2} -r {0} -n {1} -j {3} add_key "key_mpp_mpi key_iomput {4}"\n'.format(self.NemoConfig,self.NemoConfigBuildName,NemoCrayXC40BuildSystem.SYSTEM_NAME,self.NumberOfBuildProcessors, oasisKeys))
            buildScript.write('./makenemo -m {2} -r {0} -n {1} -j {3} add_key "key_mpp_mpi key_iomput"\n'.format(self.NemoConfig,self.NemoConfigBuildName,NemoCrayXC40BuildSystem.SYSTEM_NAME,self.NumberOfBuildProcessors))
            buildScript.write('\n')
        
        os.chmod(buildScriptFileName,477)
        return buildScriptFileName
            
class NemoLinuxIntelBuildSystem(NemoBuildSystem):
    SYSTEM_NAME = 'UKMO_LINUX_INTEL'
    
    def __init__(self, settingsDict):
        NemoBuildSystem.__init__(self, settingsDict)
        self.TarCommand = 'tar'
        self.ArchFileName = 'arch-{0}.fcm'.format(self.SYSTEM_NAME)
        
        self.ModulesToLoad += ['environment/dynamo/compiler/intelfortran/15.0.0']
    
    def __str__(self):
        return 'Nemo build system for GNU/Linux (UKMO scientific desktop)'

    def writeArchFiles(self):
        archFilePath = '{0}/ARCH/{1}'.format(self.SourceDirectory,self.ArchFileName)
        with open(archFilePath,'w') as archFile:

            
            archFile.write('%XIOS_HOME           {0}\n'.format(self.XiosDirectory))
            archFile.write('\n')
            if self.UseOasis:
                archFile.write('%OASIS_HOME {0}\n'.format(self.OasisDirectory))
            else:
                archFile.write('%OASIS_HOME\n')
            archFile.write('%NCDF_INC            -I$NETCDF_ROOT/include/\n')
            archFile.write('%NCDF_LIB            -L$NETCDF_ROOT/lib -lnetcdf -lnetcdff\n')
            archFile.write('%XIOS_INC            -I%XIOS_HOME/inc\n')
            archFile.write('%XIOS_LIB            -L%XIOS_HOME/lib -lxios\n')
            archFile.write('\n')
            if self.UseOasis:
                archFile.write('%OASIS_INC           -I%OASIS_HOME/build/lib/mct -I%OASIS_HOME/build/lib/psmile.MPI1\n')
                archFile.write('%OASIS_LIB           -L%OASIS_HOME/lib -lpsmile.MPI1 -lmct -lmpeu -lscrip\n')
            else:
                archFile.write('%OASIS_INC\n')
                archFile.write('%OASIS_LIB\n')
                
            archFile.write('\n')
            archFile.write('%FC                  mpif90\n')
            archFile.write('%FCFLAGS            -r8 -xHOST  -traceback\n')
            archFile.write('%FFLAGS                -r8 -xHOST  -traceback\n')
            archFile.write('%LD                  mpif90\n')
            archFile.write('%CPP                 cpp\n')
            archFile.write('%FPPFLAGS            -P -C -traditional\n')
            archFile.write('%LDFLAGS             -lstdc++\n')
            archFile.write('%AR                  ar\n')
            archFile.write('%ARFLAGS             -r\n')
            archFile.write('%MK                  gmake\n')
            archFile.write('%USER_INC            %XIOS_INC %NCDF_INC\n')
            archFile.write('%USER_LIB            %XIOS_LIB %NCDF_LIB\n')

    def setupConfigFiles(self):
        pass
    
    def writeBuildScript(self):
        buildScriptFileName = '{0}/{1}'.format(self.WorkingDirectory,
                                               BUILD_SCRIPT_FILENAME)
        if os.path.exists(buildScriptFileName) and os.path.isfile(buildScriptFileName):
            os.remove(buildScriptFileName)
        with open(buildScriptFileName,'w') as buildScript:
            buildScript.write('#!/bin/sh\n')
            buildScript.write('cd {0}/CONFIG\n'.format(self.SourceDirectory))
            buildScript.write('source /data/cr1/mhambley/modules/setup\n')
            for module1 in self.ModulesToLoad:
                buildScript.write('module load {0}\n'.format(module1))
            buildScript.write('\n')
            buildScript.write('\n')
            buildScript.write('./makenemo -m {2} -r {0} -n {1} -j {3} add_key "key_mpp_mpi key_iomput"\n'.format(self.NemoConfig,self.NemoConfigBuildName,self.SYSTEM_NAME,self.NumberOfBuildProcessors))
            buildScript.write('\n')
        
        os.chmod(buildScriptFileName,477)
        return buildScriptFileName    
    


def createNemoBuildSystem(systemName):
    buildSystem1 = None
    if systemName == NemoIBMPW7BuildSystem.SYSTEM_NAME:
        buildSystem1 = NemoIBMPW7BuildSystem(os.environ)
    elif  systemName == NemoCrayXC40BuildSystem.SYSTEM_NAME:
        buildSystem1 = NemoCrayXC40BuildSystem(os.environ)
    elif systemName == NemoLinuxIntelBuildSystem.SYSTEM_NAME:
        buildSystem1 = NemoLinuxIntelBuildSystem(os.environ)
    return buildSystem1

def main():
    systemName = os.environ['TEST_SYSTEM']
    buildSystem1 = createNemoBuildSystem(systemName)
    buildSystem1.SetupFiles()
    buildSystem1.DoBuild()
    buildSystem1.checkBuild()
    buildSystem1.copyFiles()
    buildSystem1.cleanup()
    

if __name__=='__main__':
    main()
