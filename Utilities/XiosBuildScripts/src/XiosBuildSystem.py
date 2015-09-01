import os

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
        
        self.SystemName = settingsDict['TEST_SYSTEM']
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
        self.buildXios()
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
        
        scriptFileName = '{0}/updateSourceScript01.sh'.format(self.workingDir)
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
        
        scriptFileName = '{0}/extractScript01.sh'.format(self.workingDir)
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
    def CreateModule(self):
        pass
    
    @abstractmethod
    def WriteModuleFile(self):
        pass
    