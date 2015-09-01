#!/usr/bin/env python2.7

# Environment variables expected
#    TEST_SYSTEM
#    BUILD_PATH
#    XIOS_REPO_URL
#    XIOS_REV
#    XIOS
#    BUILD_PATH
#    MTOOLS
#    XIOS_NUM_CORES
#    USE_OASIS 
#    OASIS_ROOT
#    XIOS_POST_BUILD_CLEANUP
#    XIOS_DO_CLEAN_BUILD
#    XIOS_USE_PREBUILT_LIB
#    XIOS_PREBUILT_DIR
#    DEPLOY_AS_MODULE
#    MODULE_INSTALL_PATH
#    MODULE_VERSION
#    
#    IBM only:
#      XLF_MODULE
#      XLCPP_MODULE

    
import os
import subprocess
import shutil
import sys
import ConfigParser
from abc import ABCMeta, abstractmethod
from EnvironmentModules import PrgEnvModuleWriter, SingleModuleWriter

REPOSITORY_SECTION_TITLE='Repository'
DEPENDENCIES_SECTION_TITLE='Dependencies'

BUILD_SCRIPT_FILENAME = 'xiosBuildScript01.sh'
EXTRACT_SCRIPT_FILENAME = 'xiosExtractScript01.sh'

class XiosModuleWriter(SingleModuleWriter):
    
    def __init__(self, version, modulePath, prerequisites, revNo):
        SingleModuleWriter.__init__(self)
        self.ModuleName = 'XIOS'
        self.ModuleVersion = version
        self.ModuleHomePath = modulePath
        self.ParentModules=''
        self.XiosRevisionNumber = revNo
        self.HelpMsg = 'Sets up XIOS I/O server for use.branch xios-1.0 revision {0}'.format(self.XiosRevisionNumber)
        self.WhatIsMsg = 'The XIOS I/O server for use with weather/climate models'


        self.LocalVariablesList = []
        self.LocalVariablesList += [('module_base',self.ModuleHomePath)]
        self.LocalVariablesList += [('xiosdir','$module_base/packages/{1}/{0}'.format(self.ModuleVersion, self.ModuleName))]

        self.PrerequisiteList = prerequisites

        self.PrependPathList = []
        self.PrependPathList += [('PATH','$xiosdir/bin')]

        self.SetEnvList = []
        self.SetEnvList += [('XIOS_PATH','$xiosdir')]
        self.SetEnvList += [('XIOS_INC','$xiosdir/inc')]
        self.SetEnvList += [('XIOS_LIB','$xiosdir/lib')]
        

class XiosBuildSystem(object):
    '''
    Base class containing functionality to build xios. For a particular 
    system, e.g. linux desktop or Cray XC-40, the subclasses will implement
    system specific functions.s    
    '''
    __metaclass__ = ABCMeta
    SYSTEM_NAME='XIOS_BASE_SYSTEM'
    XiosSubDirList = ['bin','inc','lib','inputs']

    def __init__(self, settingsDict):
        self.workingDir = os.getcwd()
        self.buildRequired = False
        self.preBuildClean = False
        self.updateRequired = False
        self.TarCommand = 'tar'
        
        self.TestSystem = settingsDict['TEST_SYSTEM']
        self.BuildPath = settingsDict['BUILD_PATH']
        
        self.LibraryName = settingsDict['XIOS']
        self.XiosRepositoryUrl = settingsDict['XIOS_REPO_URL']
        self.XiosRevisionNumber = settingsDict['XIOS_REV']
        self.ThirdPartyLibs = settingsDict['MTOOLS'] 
        
        try:
            self.NumberOfBuildTasks = int(settingsDict['XIOS_NUM_CORES'])
        except:
            self.NumberOfBuildTasks = 8
   
        try:
            self.CopyPrebuild = settingsDict['XIOS_USE_PREBUILT_LIB']=='true'
            if self.CopyPrebuild:
                self.PrebuildDirectory = settingsDict['XIOS_PREBUILT_DIR']
        except:
            self.CopyPrebuild = False
            self.PrebuildDirectory = ''
                
        self.UseOasis = settingsDict['USE_OASIS'] =='true'
        if self.UseOasis: 
            if settingsDict.has_key('OASIS_ROOT'):
                self.OasisRoot = settingsDict['OASIS_ROOT']
                print 'OASIS found at {0}'.format(self.OasisRoot) 
            else:
                print 'OASIS not found'
                raise Exception('OASIS not found')
        else:
            self.OasisRoot=''
    
        self.PostBuildCleanup = settingsDict['XIOS_POST_BUILD_CLEANUP'] =='true'
        self.DoCleanBuild = settingsDict['XIOS_DO_CLEAN_BUILD'] =='true'
    
        try:
            self.DeployXiosAsModule = settingsDict['DEPLOY_AS_MODULE'] == 'true'
            self.ModuleRootDir = settingsDict['MODULE_INSTALL_PATH']
            self.ModuleVersion = settingsDict['MODULE_VERSION']
        except:
            self.DeployXiosAsModule = False
            self.ModuleRootDir = ''
            self.ModuleVersion = ''

    def RunBuild(self):
        if self.CopyPrebuild:
            self.setupPrebuild()
            return
    
        self.checkBuildRequired()
        if self.buildRequired:
            self.getSourceCode()
        if self.preBuildClean:
            self.setupArchFiles()
        self.writeBuildScript()
        self.executeBuildScript()
        self.checkXiosBuild()
        self.copyFiles()
        if self.DeployXiosAsModule:
            self.CreateModule()
        self.cleanUp()
        
    def setupPrebuild(self):
        sourceBase = self.PrebuildDirectory
        xiosLibraryName = self.LibraryName
        destBase = self.BuildPath + '/' + xiosLibraryName
        self.copyXiosFilesFromSourceToDest(sourceBase, destBase)
        
        if self.DeployXiosAsModule:
            moduleFileDirectory='{0}/modules/{1}'.format(self.ModuleRootDir,self.LibraryName)
#            moduleFilePath =  '{0}/{1}'.format(moduleFileDirectory,self.ModuleVersion)
            if not os.path.exists(moduleFileDirectory):
                os.makedirs(moduleFileDirectory)
            self.WriteModuleFile()
            modulePackageDirectory = '{0}/packages/{1}/{2}'.format(self.ModuleRootDir,self.LibraryName, self.ModuleVersion)
            self.copyXiosFilesFromSourceToDest(sourceBase, modulePackageDirectory)   


    def writeBuildConf(self):
        buildPathRoot = self.BuildPath + '/' + self.LibraryName
        confFileName1 = buildPathRoot + '/build.conf'
        if os.path.exists(confFileName1):
            os.remove(confFileName1)
        conf1 = ConfigParser.RawConfigParser()
        conf1.add_section(REPOSITORY_SECTION_TITLE)
        conf1.set(REPOSITORY_SECTION_TITLE,'URL',self.XiosRepositoryUrl)
        conf1.set(REPOSITORY_SECTION_TITLE,'revision',self.XiosRevisionNumber)
        
        conf1.add_section(DEPENDENCIES_SECTION_TITLE)
        
                
        conf1.set(DEPENDENCIES_SECTION_TITLE,'useOasis',self.UseOasis)
        conf1.set(DEPENDENCIES_SECTION_TITLE,'oasisRoot',self.OasisRoot)
        
        conf1.set(DEPENDENCIES_SECTION_TITLE,'mtoolsPath',self.ThirdPartyLibs)
        
        buildPathRoot = self.BuildPath + '/' + self.LibraryName
        confFileName1 = buildPathRoot + '/build.conf'
        with open(confFileName1,'w') as confFile1:
            conf1.write(confFile1)
    
    def checkBuildRequired(self):
        '''
        check if build output and working folders exist and match. Updates the member 
        variables  buildRequired, preBuildClean and updateRequired as required.
        '''
        
        if self.DoCleanBuild:
            self.buildRequired = True
            self.preBuildClean = True
            return
        
        buildPathRoot = self.BuildPath + '/' + self.LibraryName
        if not os.path.exists(buildPathRoot) or not os.path.isdir(buildPathRoot):
            self.buildRequired = True
            self.preBuildClean = True
        
        fileNameList = ['bin/xios_server.exe', 'lib/libxios.a']
        for relFileName1 in fileNameList: 
            if not os.path.exists('{0}/{1}'.format(buildPathRoot,relFileName1)):
                self.buildRequired = True # an important build file is missing, rebuild required.
        
        # read in build settings from build folder
        confFileName1 = buildPathRoot + '/build.conf'
        if not os.path.exists(confFileName1):
            self.buildRequired = True
            self.preBuildClean = True # if we don't know what build settings were used, build from scratch
    
        conf1 = ConfigParser.RawConfigParser()
        conf1.read(confFileName1)
        
        # compare with current settings
        try:
            old_repositoryUrl = conf1.get(REPOSITORY_SECTION_TITLE,'URL')
            new_repositoryUrl = self.XiosRepositoryUrl
            if old_repositoryUrl != new_repositoryUrl:
                self.buildRequired = True
                self.preBuildClean = True
            
            old_revisionNumber = conf1.get(REPOSITORY_SECTION_TITLE,'revision')
            new_revisionNumber = self.XiosRevisionNumber
            if old_revisionNumber != new_revisionNumber:
                self.buildRequired = True
                try:
                    oldRevNum = int(old_revisionNumber)
                    newRevNum = int(new_revisionNumber)
                    if newRevNum != oldRevNum:
                        self.updateRequired = True
                except:
                    #there will be an exception if the revision is head, in which we will do an update
                    self.updateRequired = True
            
            old_useOasis = conf1.get(DEPENDENCIES_SECTION_TITLE,'useOasis')
            new_useOasis = self.UseOasis
            if old_useOasis != new_useOasis:
                self.buildRequired = True
                self.preBuildClean = True
        
            old_oasisRoot = conf1.get(DEPENDENCIES_SECTION_TITLE,'oasisRoot')
            new_oasisRoot = self.OasisRoot
            if old_oasisRoot != new_oasisRoot:
                self.buildRequired = True
                self.preBuildClean = True
        
            old_mtoolsPath = conf1.get(DEPENDENCIES_SECTION_TITLE,'mtoolsPath')
            new_mtoolsPath = self.ThirdPartyLibs
            if old_mtoolsPath != new_mtoolsPath:
                self.buildRequired = True
                self.preBuildClean = True
        except:
            # an exception will generated if any of the settings are missing 
            # from the conf file, in which case rebuild
            sys.stderr.write('Error reading conf file, triggering clean build') 
            self.buildRequired = True
            self.preBuildClean = True
    
    def getSourceCode(self):
        destinationDir = self.LibraryName
        
        if not os.path.exists(destinationDir) or not os.path.isdir(destinationDir) or self.DoCleanBuild:
            self.extractXiosSourceCode()
            return
    
        if not self.updateRequired:
            return
        
        scriptFileName = '{0}/{1}.sh'.format(self.workingDir,
                                             EXTRACT_SCRIPT_FILENAME)
        if os.path.exists(scriptFileName) and os.path.isfile(scriptFileName):
            os.remove(scriptFileName)
        with open(scriptFileName,'w') as extractScript:
            extractScript.write('#!/bin/ksh\n')
            extractScript.write('cd {0}\n'.format(destinationDir))
            extractScript.write('fcm update --non-interactive -r {0}\n'.format(self.XiosRevisionNumber))
        os.chmod(scriptFileName,477)
        print '\nExecuting fcm update command\n'
        result1 = subprocess.call(scriptFileName)
        if result1 != 0:
            raise Exception('Error updating XIOS source code')
            
        
    def extractXiosSourceCode(self):
        '''
        '''
        repoUrl = self.XiosRepositoryUrl
        revNumber = self.XiosRevisionNumber  
        destinationDir = self.LibraryName

        if os.path.exists(destinationDir) and os.path.isdir(destinationDir):
            shutil.rmtree(destinationDir)
        
        scriptFileName = '{0}/{1}'.format(self.workingDir,
                                          EXTRACT_SCRIPT_FILENAME)
        if os.path.exists(scriptFileName) and os.path.isfile(scriptFileName):
            os.remove(scriptFileName)
        with open(scriptFileName,'w') as extractScript:
            extractScript.write('#!/bin/ksh\n')
            extractScript.write('fcm co {0}@{1} {2}\n'.format(repoUrl,revNumber,destinationDir))
            extractScript.write('cd {0}\n'.format(destinationDir))
            extractScript.write('for i in tools/archive/*.tar.gz; do  {0} -xzf $i; done\n'.format(self.TarCommand))
        os.chmod(scriptFileName,477)
        print '\nexecuting fcm check-out command\n'
        result1 = subprocess.call(scriptFileName)
        if result1 != 0:
            raise Exception('Error extracting XIOS source code')

    def checkXiosBuild(self):
        sourceBase = self.LibraryName
        xiosLibPath = '{0}/lib/libxios.a'.format(sourceBase)
        if not os.path.exists(xiosLibPath):
            raise Exception('XIOS lib file not found at {0}, build failed!'.format(xiosLibPath))
        xiosServerExe = '{0}/bin/xios_server.exe'.format(sourceBase)
        if not os.path.exists(xiosServerExe):
            raise Exception('XIOS server binary file not found at {0}, build failed!'.format(xiosServerExe))
            
    def copyFiles(self):
        destBase = self.BuildPath + '/' + self.LibraryName
        self.copyFilesToDir(destBase)
        
    def copyFilesToDir(self,destBase):
        sourceBase = self.workingDir + '/' + self.LibraryName
        self.copyXiosFilesFromSourceToDest(sourceBase, destBase)
        self.writeBuildConf()
        
    def copyXiosFilesFromSourceToDest(self, sourceBase, destBase):
        subDirList = self.XiosSubDirList
        sourceDirs = [sourceBase + '/' + dir1 for dir1 in subDirList]
        print 'copying output files'
        if os.path.exists(destBase) and os.path.isdir(destBase):
            print 'removing dir {0}'.format(destBase)
            shutil.rmtree(destBase)
        destinationDirs = [destBase + '/' + dir1 for dir1 in subDirList]
        for sourceDir,destDir in zip(sourceDirs,destinationDirs):
            print 'copying directory from  {0} to {1}'.format(sourceDir,destDir)
            shutil.copytree(sourceDir, destDir)    
        
                
    def cleanUp(self):
        if self.PostBuildCleanup:
            print 'removing build working directory {0}'.format(self.LibraryName)
            shutil.rmtree(self.LibraryName)    
            
    def setupArchFiles(self):
        '''
        Setup the arch files to be used by the make_xios build script
        Inputs:
        archPath: full path where the arch files should be written
        fileNameBase: the base name for the files (based on the build architecture)
        oasisRootPath: The full path to the root of the OASIS directory if used for this build. empty string  
        '''

        archPath='{0}/{1}/arch'.format(self.workingDir, self.LibraryName)
        mtoolsPath = self.ThirdPartyLibs
        try:
            oasisRootPath = self.OasisRoot
        except:
            oasisRootPath = None
        
        fileNameEnv = archPath + '/' + self.fileNameBase + '.env'
        if os.path.isfile(fileNameEnv):
            os.remove(fileNameEnv)
        self.setupArchEnvFile(fileNameEnv, mtoolsPath, oasisRootPath)
        print 'writing out arch file {0}'.format(fileNameEnv)
        
        fileNamePath = archPath + '/' + self.fileNameBase + '.path'
        if os.path.isfile(fileNamePath):
            os.remove(fileNamePath)
        self.setupArchPathFile(fileNamePath)
        print 'writing out arch file {0}'.format(fileNamePath)
        
        fileNameFcm = archPath + '/' + self.fileNameBase + '.fcm'
        if os.path.isfile(fileNameFcm):
            os.remove(fileNameFcm)
        self.setupArchFcmFile(fileNameFcm)
        print 'writing out arch file {0}'.format(fileNameFcm)            

    @abstractmethod
    def setupArchFcmFile(self, fileNameFcm):
        pass
    
    @abstractmethod
    def setupArchEnvFile(self, fileName,mtoolsPath,oasisRootPath):
        pass
    
    @abstractmethod
    def setupArchPathFile(self, fileName):
        pass

    @abstractmethod
    def writeBuildScript(self):
        pass
    
    @abstractmethod
    def executeBuildScript(self):
        pass

    @abstractmethod
    def CreateModule(self):
        pass
    
    @abstractmethod
    def WriteModuleFile(self):
        pass
    
    
class XiosIBMPW7BuildSystem(XiosBuildSystem):
    '''
    Class representing the build parameters for building XIOS on the UKMO IBM Power7 supercomputer.    
    '''
    
    SYSTEM_NAME='UKMO_IBM_PW7'
  
    def __init__(self, settingsDict):
        XiosBuildSystem.__init__(self, settingsDict)
        self.fileNameBase='arch-pwr7_UKMO'
        self.TarCommand = '/opt/freeware/bin/tar' 
        self.XlfModule = settingsDict['XLF_MODULE']
        self.XlcppModule = settingsDict['XLCPP_MODULE']
    
    def setupArchEnvFile(self, fileName,mtoolsPath,oasisRootPath):
        with open(fileName,'w') as envFile:
            envFile.write('export HDF5_INC_DIR={0}/include\n'.format(mtoolsPath))
            envFile.write('export HDF5_LIB_DIR={0}/lib\n\n'.format(mtoolsPath))
            envFile.write('export NETCDF_INC_DIR={0}/include\n'.format(mtoolsPath))
            envFile.write('export NETCDF_LIB_DIR={0}/lib\n\n'.format(mtoolsPath))
            if oasisRootPath == None or oasisRootPath == '':
                envFile.write('export OASIS_INC_DIR=\n')
                envFile.write('export OASIS_LIB_DIR=\n\n')
            else:
                envFile.write('export OASIS_INC_DIR={0}/build\n'.format(oasisRootPath))
                envFile.write('export OASIS_LIB_DIR={0}/lib\n\n'.format(oasisRootPath))
    
    def setupArchPathFile(self, fileName):
        with open(fileName,'w') as pathFile:
            pathFile.write('NETCDF_INCDIR="-I $NETCDF_INC_DIR"\n')
            pathFile.write('NETCDF_LIBDIR="-L $NETCDF_LIB_DIR"\n')
            pathFile.write('NETCDF_LIB="-lnetcdf"\n')
    
            pathFile.write('MPI_INCDIR=""\n')
            pathFile.write('MPI_LIBDIR=""\n')
            pathFile.write('MPI_LIB=""\n')
    
            pathFile.write('HDF5_INCDIR=""\n')
            pathFile.write('HDF5_LIBDIR=""\n')
            pathFile.write('HDF5_LIB="-lhdf5_hl -lhdf5 -lhdf5 -lz"\n')
    
            pathFile.write('OASIS_INCDIR="-I$OASIS_INC_DIR/lib/psmile.MPI1"\n')
            pathFile.write('OASIS_LIBDIR="-L$OASIS_LIB_DIR"\n')
            pathFile.write('OASIS_LIB="-lpsmile.MPI1 -lscrip -lmct -lmpeu"\n')
    
    def setupArchFcmFile(self, fileName):
        with open(fileName,'w') as fcmFile:
            fcmFile.write('################################################################################\n')
            fcmFile.write('###################        Projet xios - xmlioserver       #####################\n')
            fcmFile.write('################################################################################\n')
    
            fcmFile.write('%CCOMPILER      mpCC_r\n')
            fcmFile.write('%FCOMPILER      mpxlf2003_r\n')
            fcmFile.write('%LINKER         mpCC_r\n')
    
            fcmFile.write('%BASE_CFLAGS    -qflttrap=nanq:enable -qsigtrap -qmkshrobj -qrtti -DXIOS_LIBRARY -DNONE -DXIOS_LIBRARY\n')
            fcmFile.write('%PROD_CFLAGS    -O3 -DBOOST_DISABLE_ASSERTS\n')
            fcmFile.write('%DEV_CFLAGS     -DXIOS_DEBUG -g\n')
            fcmFile.write('%DEBUG_CFLAGS   -DXIOS_DEBUG -g\n')
    
            fcmFile.write('%BASE_FFLAGS    -qflttrap=nanq:enable -qsigtrap -qmkshrobj -WF,-DXIOS_LIBRARY -WF,-DXIOS_LIBRARY\n')
            fcmFile.write('%PROD_FFLAGS    -O3\n')
            fcmFile.write('%DEV_FFLAGS     -WF,-DXIOS_DEBUG -g\n')
            fcmFile.write('%DEBUG_FFLAGS   -WF,-DXIOS_DEBUG -g\n')
    
            fcmFile.write('%BASE_INC       -D__NONE__\n')
            fcmFile.write('%BASE_LD        -lxlf90\n')
    
            fcmFile.write('%CPP            cpp\n')
            fcmFile.write('%FPP            cpp -P\n')
            fcmFile.write('%MAKE           gmake\n')

    def writeBuildScript(self):
        self.buildScriptFileName = '{0}/{1}'.format(self.workingDir,
                                                    BUILD_SCRIPT_FILENAME)
        if os.path.exists(self.buildScriptFileName) and os.path.isfile(self.buildScriptFileName):
            os.remove(self.buildScriptFileName)
        
        with open(self.buildScriptFileName,'w') as buildScript:
            buildScript.write('#!/bin/ksh\n')
            buildScript.write('. /critical/opt/Modules/default/init/ksh\n')
            buildScript.write('module load aix/libc-compile-fix\n')
            buildScript.write('module load {0}\n'.format(self.XlfModule))
            buildScript.write('module load {0}\n'.format(self.XlcppModule))
            buildScript.write('module list\n')
            buildScript.write('cd {0}/{1}\n'.format(self.workingDir,self.LibraryName))
            buildScript.write('echo current directory is $(pwd)\n')
            buildScript.write('./make_xios ')
            if self.DoCleanBuild:
                buildScript.write('--full ')
            buildScript.write('--arch pwr7_UKMO ')
            buildScript.write('--netcdf_lib netcdf4_par ')
            if self.UseOasis:
                buildScript.write('--use_oasis oasis3_mct ')
            buildScript.write('--job {0} \n'.format(self.NumberOfBuildTasks))
            buildScript.write('')
            buildScript.write('\n')
            buildScript.write('\n')
        os.chmod(self.buildScriptFileName,477)

    def executeBuildScript(self):
        print 'executing build script {0}'.format(self.buildScriptFileName)
        returnCode = subprocess.call(self.buildScriptFileName)
        if returnCode != 0:
            raise Exception('Error compiling XIOS: build failed!')

class XiosCrayModuleWriter(XiosModuleWriter):
    def __init__(self, version, modulePath, revNo):
        prereq = []
        prereq += ['PrgEnv-cray/5.2.40']
        prereq += ['cray-mpich/7.0.4']
        prereq += ['cray-hdf5-parallel/1.8.13']
        prereq += ['cray-netcdf-hdf5parallel/4.3.2']        
        XiosModuleWriter.__init__(self, version, modulePath, prereq, revNo)
        
class XiosCrayBuildSystem(XiosBuildSystem):
    '''
    Subclass of XiosBuildSystem that implements Xios build
    on Cray XC-40 system.
    '''
    SYSTEM_NAME='UKMO_CRAY_XC40'
    def __init__(self, settingsDict):
        XiosBuildSystem.__init__(self, settingsDict)
        self.fileNameBase='arch-XC30_Cray'

    def writeBuildScript(self):
        self.buildScriptFileName = '{0}/{1}'.format(self.workingDir,
                                                    BUILD_SCRIPT_FILENAME)
        if os.path.exists(self.buildScriptFileName) and os.path.isfile(self.buildScriptFileName):
            os.remove(self.buildScriptFileName)
        
        xiosSrcDir = self.workingDir + '/' + self.LibraryName
        with open(self.buildScriptFileName,'w') as buildScript:
            buildScript.write('#!/bin/sh\n')
            buildScript.write('\n')
            buildScript.write('module load cray-hdf5-parallel/1.8.13\n')
            buildScript.write('module load cray-netcdf-hdf5parallel/4.3.2\n')
            buildScript.write('\n')
            buildScript.write('cd {0}\n'.format(xiosSrcDir) )
            
            #main build command
            buildScript.write('./make_xios --arch XC30_Cray')
            if (self.DoCleanBuild):
                buildScript.write(' --full ')
            if self.UseOasis:
                buildScript.write(' --use_oasis oasis3_mct ')
            buildScript.write(' --job {0} '.format(self.NumberOfBuildTasks))
            buildScript.write('\n')
        os.chmod(self.buildScriptFileName,477)
        
    def executeBuildScript(self):
        print 'executing build script {0}'.format(self.buildScriptFileName)
        returnCode = subprocess.call(self.buildScriptFileName)
        if returnCode != 0:
            raise Exception('Error compiling XIOS: build failed!')
    
    def setupArchFcmFile(self,fileName):
        with open(fileName,'w') as fcmFile:
            fcmFile.write('\n')
            fcmFile.write('%CCOMPILER      CC\n')
            fcmFile.write('%FCOMPILER      ftn\n')
            fcmFile.write('%LINKER         CC\n')
            fcmFile.write('\n')
            fcmFile.write('%BASE_CFLAGS    -em -DMPICH_SKIP_MPICXX -h msglevel_4 -h zero -h gnu\n')
            fcmFile.write('\n')
            fcmFile.write('%PROD_CFLAGS    -O1 -DBOOST_DISABLE_ASSERTS\n')
            fcmFile.write('%DEV_CFLAGS     -O2\n')
            fcmFile.write('%DEBUG_CFLAGS   -g\n')
            fcmFile.write('\n')
            fcmFile.write('%BASE_FFLAGS    -em -m 4 -e0 -eZ\n')
            fcmFile.write('%PROD_FFLAGS    -O3\n')
            fcmFile.write('%DEV_FFLAGS     -G2\n')
            fcmFile.write('\n')
            fcmFile.write('%DEBUG_FFLAGS   -g\n')
            fcmFile.write('%BASE_INC       -D__NONE__\n')
            fcmFile.write('%BASE_LD        -D__NONE__\n')
            fcmFile.write('\n')
            fcmFile.write('%CPP            cpp\n')
            fcmFile.write('%FPP            cpp -P -CC\n')
            fcmFile.write('%MAKE           gmake\n')
    
    def setupArchPathFile(self,fileName):
        with open(fileName,'w') as pathFile:
            pathFile.write('NETCDF_INCDIR=""\n')
            pathFile.write('NETCDF_LIBDIR=""\n')
            pathFile.write('NETCDF_LIB=""\n')
            pathFile.write('\n')
            pathFile.write('MPI_INCDIR=""\n')
            pathFile.write('MPI_LIBDIR=""\n')
            pathFile.write('MPI_LIB=""\n')
            pathFile.write('\n')
            pathFile.write('HDF5_INCDIR=""\n')
            pathFile.write('HDF5_LIBDIR=""\n')
            pathFile.write('HDF5_LIB=""\n')
            pathFile.write('\n')
            if self.UseOasis:
                
                pathFile.write('OASIS_INCDIR="-I{0}/build/lib/psmile.MPI1"\n'.format(self.OasisRoot))
                pathFile.write('OASIS_LIBDIR="-L{0}/lib"\n'.format(self.OasisRoot))
                pathFile.write('OASIS_LIB="-lpsmile.MPI1 -lscrip -lmct -lmpeu"\n')
            else:
                pathFile.write('OASIS_INCDIR=""\n')
                pathFile.write('OASIS_LIBDIR=""\n')
                pathFile.write('OASIS_LIB=""\n')

            pathFile.write('\n')

    def setupArchEnvFile(self,fileName,mtoolsPath,oasisRootPath):
        with open(fileName,'w') as envFile:
            envFile.write('export HDF5_INC_DIR=""\n')
            envFile.write('export HDF5_LIB_DIR=""\n')
            envFile.write('\n')
            envFile.write('export NETCDF_INC_DIR=""\n')
            envFile.write('export NETCDF_LIB_DIR=""\n')
            
    def CreateModule(self):
        if not os.path.exists(self.ModuleRootDir): 
            os.makedirs(self.ModuleRootDir)
        elif not os.path.isdir(self.ModuleRootDir):
            raise Exception('Module install directory {0} not found, module not deployed.\n'.format(self.ModuleRootDir))
        
        modulePackageDirectory='{0}/packages/{1}/{2}'.format(self.ModuleRootDir,self.LibraryName,self.ModuleVersion)
        
        modWriter1 = XiosCrayModuleWriter(self.ModuleVersion, self.ModuleRootDir, self.XiosRevisionNumber)
        modWriter1.WriteModule()
        
        self.copyFilesToDir(modulePackageDirectory)
        
        
        
    def WriteModuleFile(self):
        moduleFileDirectory='{0}/modules/{1}'.format(self.ModuleRootDir,self.LibraryName)
        moduleFilePath =  '{0}/{1}'.format(moduleFileDirectory,self.ModuleVersion)
        if not os.path.exists(moduleFileDirectory):
            os.makedirs(moduleFileDirectory)

        with open(moduleFilePath,'w') as moduleFile:
            moduleFile.write('#%Module1.0####################################################################\n')
            moduleFile.write('proc ModulesHelp { } {\n')
            moduleFile.write('    puts stderr "Sets up XIOS I/O server for use.branch xios-1.0 revision 618."\n')
            moduleFile.write('}\n')
            moduleFile.write('\n')
            moduleFile.write('module-whatis "The XIOS I/O server for use with weather/climate models"\n')
            moduleFile.write('\n')
            moduleFile.write('conflict {0}\n'.format(self.LibraryName))
            moduleFile.write('set version {0}\n'.format(self.ModuleVersion))
            moduleFile.write('set module_base {0}/\n'.format(self.ModuleRootDir))
            moduleFile.write('set xiosdir $module_base/packages/{1}/{0}\n'.format(self.ModuleVersion, self.LibraryName))
            moduleFile.write('\n')
            moduleFile.write('prereq PrgEnv-cray/5.2.40\n')
            moduleFile.write('prereq cray-mpich/7.0.4\n')
            moduleFile.write('prereq cray-hdf5-parallel/1.8.13\n')
            moduleFile.write('prereq cray-netcdf-hdf5parallel/4.3.2\n')
            moduleFile.write('\n')
            moduleFile.write('setenv XIOS_PATH $xiosdir/\n')
            moduleFile.write('setenv XIOS_LIB $xiosdir/lib\n')
            moduleFile.write('setenv XIOS_INC $xiosdir/inc\n')
            moduleFile.write('\n')
            moduleFile.write('prepend-path PATH $xiosdir/bin\n')
            moduleFile.write('\n')        
        
class XiosLinuxIntelModuleWriter(XiosModuleWriter):
    def __init__(self, version, modulePath, revNo):
        prereq = []
        prereq += ['fortran/intel/15.0.0']
        prereq += ['mpi/mpich/3.1.2/ifort/15.0.0']
        prereq += ['hdf5/1.8.12/ifort/15.0.0']
        prereq += ['netcdf/4.3.3-rc1/ifort/15.0.0']
        
        XiosModuleWriter.__init__(self, version, modulePath, prereq, revNo)
            

class XiosLinuxIntelSystem(XiosBuildSystem):
    '''
    Subclass of XiosBuildSystem that implements Xios build
    on Cray XC-40 system.
    '''
    SYSTEM_NAME='UKMO_LINUX_INTEL'
    def __init__(self, settingsDict):
        XiosBuildSystem.__init__(self, settingsDict)
        self.archName='LINUX_INTEL'
        self.fileNameBase='arch-{0}'.format(self.archName)

    def writeBuildScript(self):
        self.buildScriptFileName = '{0}/{1}'.format(self.workingDir,
                                                    BUILD_SCRIPT_FILENAME)
        if os.path.exists(self.buildScriptFileName) and os.path.isfile(self.buildScriptFileName):
            os.remove(self.buildScriptFileName)
        
        xiosSrcDir = self.workingDir + '/' + self.LibraryName
        with open(self.buildScriptFileName,'w') as buildScript:
            buildScript.write('#!/bin/bash\n')
            buildScript.write('\n')
            buildScript.write('. /data/cr1/mhambley/modules/setup\n')
            buildScript.write('module load environment/dynamo/compiler/intelfortran/15.0.0\n')
            buildScript.write('\n')
            buildScript.write('cd {0}\n'.format(xiosSrcDir) )
            buildScript.write('\n')
            buildScript.write('./make_xios --dev --arch {0}'.format(self.archName))
            if (self.DoCleanBuild):
                buildScript.write(' --full ')
            if self.UseOasis:
                buildScript.write(' --use_oasis oasis3_mct ')
            buildScript.write(' --job {0} '.format(self.NumberOfBuildTasks))
            buildScript.write('\n')
        os.chmod(self.buildScriptFileName,477)

    def executeBuildScript(self):
        print 'executing build script {0}'.format(self.buildScriptFileName)
        returnCode = subprocess.call(self.buildScriptFileName)
        if returnCode != 0:
            raise Exception('Error compiling XIOS: build failed!')
            
    def setupArchFcmFile(self,fileName):
        with open(fileName,'w') as fcmFile:
            fcmFile.write('################################################################################\n')
            fcmFile.write('###################        Projet xios - xmlioserver       #####################\n')
            fcmFile.write('################################################################################\n')
            fcmFile.write('%CCOMPILER      mpicc\n')
            fcmFile.write('%FCOMPILER      mpif90\n')
            fcmFile.write('%LINKER         mpif90\n')
            fcmFile.write('\n')
            fcmFile.write('%BASE_CFLAGS    -w\n')
            fcmFile.write('%PROD_CFLAGS    -O3 -DBOOST_DISABLE_ASSERTS\n')
            fcmFile.write('%DEV_CFLAGS     -g -O2\n')
            fcmFile.write('%DEBUG_CFLAGS   -DBZ_DEBUG -g -fno-inline\n')
            fcmFile.write('\n')
            fcmFile.write('%BASE_FFLAGS    -D__NONE__\n')
            fcmFile.write('%PROD_FFLAGS    -O3\n')
            fcmFile.write('%DEV_FFLAGS     -g -O2 -traceback\n')
            fcmFile.write('%DEBUG_FFLAGS   -g -traceback\n')
            fcmFile.write('\n')
            fcmFile.write('%BASE_INC       -D__NONE__\n')
            fcmFile.write('%BASE_LD        -lstdc++ -lifcore -lintlc\n')
            fcmFile.write('\n')
            fcmFile.write('%CPP            cpp\n')
            fcmFile.write('%FPP            cpp -P\n')
            fcmFile.write('%MAKE           gmake\n')
            fcmFile.write('\n')
        
    
    def setupArchPathFile(self,fileName):
        with open(fileName,'w') as pathFile:
            pathFile.write('NETCDF_INCDIR="-I$NETCDF_ROOT/include"\n')
            pathFile.write('NETCDF_LIBDIR="-L$NETCDF_ROOT/lib"\n')
            pathFile.write('\n')
            pathFile.write('NETCDF_LIB="-lnetcdf"\n')
            pathFile.write('\n')
            pathFile.write('MPI_INCDIR=""\n')
            pathFile.write('MPI_LIBDIR=""\n')
            pathFile.write('MPI_LIB=""\n')
            pathFile.write('\n')
            pathFile.write('HDF5_INCDIR="-I$HDF5_ROOT/include"\n')
            pathFile.write('HDF5_LIBDIR="-I$HDF5_ROOT/lib"\n')
            pathFile.write('HDF5_LIB="-I$HDF5_ROOT/lib"\n')
            pathFile.write('\n')
            pathFile.write('\n')
            if self.UseOasis:
                pathFile.write('OASIS_INCDIR="-I$PWD/../../oasis3-mct/BLD/build/lib/psmile.MPI1"\n')
                pathFile.write('OASIS_LIBDIR="-L$PWD/../../oasis3-mct/BLD/lib"\n')
                pathFile.write('OASIS_LIB="-lpsmile.MPI1 -lscrip -lmct -lmpeu"\n')
            else:
                pathFile.write('OASIS_INCDIR=""\n')
                pathFile.write('OASIS_LIBDIR=""\n')
                pathFile.write('OASIS_LIB=""\n')
                

    def setupArchEnvFile(self,fileName,mtoolsPath,oasisRootPath):
        # no arch.env needed for desktop system
        return
    
    def CreateModule(self):
        if not os.path.exists(self.ModuleRootDir): 
            os.makedirs(self.ModuleRootDir)
        elif not os.path.isdir(self.ModuleRootDir):
            raise Exception('Module install directory {0} not found, module not deployed.\n'.format(self.ModuleRootDir))
        
        modulePackageDirectory='{0}/packages/{1}/{2}'.format(self.ModuleRootDir,self.LibraryName,self.ModuleVersion)
        self.WriteModuleFile()
        self.copyFilesToDir(modulePackageDirectory)
        
        
        
    def WriteModuleFile(self):
        moduleFileDirectory='{0}/modules/{1}'.format(self.ModuleRootDir,self.LibraryName)
        moduleFilePath =  '{0}/{1}'.format(moduleFileDirectory,self.ModuleVersion)
        if not os.path.exists(moduleFileDirectory):
            os.makedirs(moduleFileDirectory)

        with open(moduleFilePath,'w') as moduleFile:
            moduleFile.write('#%Module1.0####################################################################\n')
            moduleFile.write('proc ModulesHelp { } {\n')
            moduleFile.write('    puts stderr "Sets up XIOS I/O server for use.branch xios-1.0 revision {0}."\n'.format(self.XiosRevisionNumber))
            moduleFile.write('}\n')
            moduleFile.write('\n')
            moduleFile.write('module-whatis "The XIOS I/O server for use with weather/climate models"\n')
            moduleFile.write('\n')
            moduleFile.write('conflict {0}\n'.format(self.LibraryName))
            moduleFile.write('set version {0}\n'.format(self.ModuleVersion))
            moduleFile.write('set module_base {0}/\n'.format(self.ModuleRootDir))
            moduleFile.write('set xiosdir $module_base/packages/{1}/{0}\n'.format(self.ModuleVersion, self.LibraryName))
            moduleFile.write('\n')
            moduleFile.write('prereq mpi/mpich/3.1.2/ifort/15.0.0\n')
            moduleFile.write('prereq fortran/intel/15.0.0\n')
            moduleFile.write('prereq libraries/zlib/1.2.8\n')
            moduleFile.write('prereq hdf5/1.8.12/ifort/15.0.0\n')
            moduleFile.write('prereq netcdf/4.3.3-rc1/ifort/15.0.0\n')
            moduleFile.write('\n')
            moduleFile.write('setenv XIOS_PATH $xiosdir/\n')
            moduleFile.write('setenv XIOS_LIB $xiosdir/lib\n')
            moduleFile.write('setenv XIOS_INC $xiosdir/inc\n')
            moduleFile.write('\n')
            moduleFile.write('prepend-path PATH $xiosdir/bin\n')
            moduleFile.write('\n')      
            

def createBuildSystem():
    systemName = os.environ['TEST_SYSTEM']
    system1 = None
    if systemName == XiosCrayBuildSystem.SYSTEM_NAME:
        system1 =  XiosCrayBuildSystem(os.environ)
    elif systemName == XiosIBMPW7BuildSystem.SYSTEM_NAME:
        system1 = XiosIBMPW7BuildSystem(os.environ)
    elif systemName == XiosLinuxIntelSystem.SYSTEM_NAME:
        system1 = XiosLinuxIntelSystem(os.environ)
    else:
        raise Exception('invalid build system name')
    return system1
        
def main(): 
    buildSystem1 = createBuildSystem()
    print buildSystem1
    buildSystem1.RunBuild()
    
if __name__=='__main__':
    main()
