import unittest
import subprocess
import os
import oasisBuild
import filecmp

class OasisBuildCrayTests(unittest.TestCase):
    def setUp(self):
        self.workingDir = os.getcwd()
        settingsDict = {} 
        self.SystemName = 'UKMO_CRAY_XC40'
        settingsDict['SYSTEM_NAME'] = self.SystemName
        self.LibraryName = 'oasis3-mct'
        settingsDict['OASIS3_MCT'] = self.LibraryName
        settingsDict['BUILD_OASIS'] = 'true'
        settingsDict['OASIS_DIR'] = '{0}/install/{1}'.format(self.workingDir,
                                                             self.LibraryName)
        self.OasisRepostoryUrl = ('svn://fcm2/PRISM_svn/OASIS3_MCT/' +
                                  'branches/dev/frrj/' +
                                  'r1217_port_mct_xcf/oasis3-mct' )
        settingsDict['OASIS_REPO_URL'] = self.OasisRepostoryUrl
        settingsDict['OASIS_REV_NO'] = '1313'
        self.ExternalRepoUrl = 'http://server.name/path/to/repository'
        self.ExternalRevNo = '1234'
        settingsDict['OASIS_EXTERNAL_REPO_URL'] = self.ExternalRepoUrl
        settingsDict['OASIS_EXTERNAL_REV_NO'] = self.ExternalRevNo
        settingsDict['ROSE_SUITE_URL'] = 'path/to/repository'
        settingsDict['ROSE_SUITE_REV_NO'] = '1234'
        
        
        settingsDict['OASIS_PLATFORM_NAME'] = 'crayxc40'
        self.Verbose = True
        if self.Verbose:
            settingsDict['VERBOSE'] = 'true'
        else:
            settingsDict['VERBOSE'] = 'false'
        settingsDict['DEPLOY_AS_MODULE'] = 'true'
        settingsDict['MODULE_INSTALL_PATH'] = '{0}/modules'.format(self.workingDir)
        settingsDict['OASIS_MODULE_VERSION'] = '1.0'
        
        self.BuildSystem = oasisBuild.OasisCrayBuildSystem(settingsDict)
    
    def tearDown(self):
        self.BuildSystem = None
    
    def test_setup(self):
        errMsg1 = 'Input parameters do not match'
        self.assertEqual(self.Verbose,
                         self.BuildSystem.Verbose,
                         errMsg1)
        self.assertEqual(self.SystemName,
                         self.BuildSystem.SystemName,
                         errMsg1)
        self.assertEqual(self.OasisRepostoryUrl,
                         self.BuildSystem.OasisRepositoryUrl,
                         errMsg1)
    
    def test_codeExtraction(self):
        self.BuildSystem.ExtractSourceCode()
        scriptFilePath = '{workingDir}/{fileName}'
        scriptFilePath = scriptFilePath.format(workingDir=self.BuildSystem.WorkingDir,
                                               fileName=oasisBuild.EXTRACT_SCRIPT_FILE_NAME)
        self.assertTrue(os.path.exists(scriptFilePath),'script file {0} not found!'.format(scriptFilePath))

        # compare contents to reference file
        refFilePath = '{0}/oasisBuild_cray_reference_extractScript.sh'.format(os.getcwd())
        refFileStr = 'fcm co {OasisRepositoryUrl}@{OasisRevisionNumber} {OasisSrcDir}\n'
        refFileStr = refFileStr.format(**self.BuildSystem.__dict__)
        with open(refFilePath,'w') as refFile:
            refFile.write(refFileStr)
        self.assertTrue(filecmp.cmp(scriptFilePath, refFilePath), 'script file {0} not identical to reference file {1}'.format(scriptFilePath, refFilePath))
        
        # check extracted source code for existence of some files
        self.assertTrue(os.path.exists(self.BuildSystem.OasisSrcDir))
        self.assertTrue(os.path.isdir(self.BuildSystem.OasisSrcDir))
        fileCheckList = ['{0}/lib/mct/Makefile'.format(self.BuildSystem.OasisSrcDir)]
        fileCheckList += ['{0}/lib/mct/mct/mct_mod.F90'.format(self.BuildSystem.OasisSrcDir)]
        fileCheckList += ['{0}/util/make_dir/make.cray_xc40_mo'.format(self.BuildSystem.OasisSrcDir)]
        for filePath1 in fileCheckList:
            self.assertTrue(os.path.exists(filePath1),' file {0} not found'.format(filePath1))                
                 
    
    def test_buildCommand(self):
        buildCmd = self.BuildSystem.CreateBuildCommand()

        scriptFilePath = '{workingDir}/{fileName}'
        scriptFilePath = scriptFilePath.format(workingDir=self.BuildSystem.WorkingDir,
                                               fileName=oasisBuild.BUILD_SCRIPT_FILENAME)
        
        self.assertTrue(os.path.exists(scriptFilePath), 'build script {0} not found!'.format(scriptFilePath) )
        
        refFilePath = '{0}/oasisBuild_cray_referenceBuildScript.sh'.format(self.BuildSystem.WorkingDir)
        refFileStr='''#!/bin/sh

module load PrgEnv-cray/5.2.40
module load cray-netcdf-hdf5parallel/4.3.2

cd {OasisSrcDir}/util/make_dir
make -f TopMakefileOasis3
'''
        
        refFileStr = refFileStr.format(**self.BuildSystem.__dict__)
        
        with open(refFilePath,'w') as refFile:
            refFile.write(refFileStr)
        
        errMsg1 = 'file {resultFile} does not match {kgoFile}'
        errMsg1 = errMsg1.format(resultFile=scriptFilePath,
                                 kgoFile=refFilePath)
        self.assertTrue(filecmp.cmp(scriptFilePath,refFilePath), errMsg1)
        
    def test_moduleWrite(self):
        mw1 = oasisBuild.OasisCrayModuleWriter(
                self.BuildSystem.ModuleVersion,
                self.BuildSystem.ModuleRootDir,
                self.BuildSystem.OasisRepositoryUrl,
                self.BuildSystem.OasisRevisionNumber,
                self.ExternalRepoUrl,
                self.ExternalRevNo,
                self.BuildSystem.SuiteUrl,
                self.BuildSystem.SuiteRevisionNumber,
                self.BuildSystem.LibraryName,
                self.BuildSystem.SYSTEM_NAME)
        mw1.WriteModule()
        
        # check for existence of module
        tempModStr1 = '{root_dir}/modules/{rel_path}'
        moduleFilePath = tempModStr1.format(
                             root_dir = self.BuildSystem.ModuleRootDir,
                             rel_path = mw1.ModuleRelativePath)
        moduleFilePath = moduleFilePath.format( **self.BuildSystem.__dict__)
        self.assertTrue(os.path.exists(moduleFilePath),
                        'Module file {0} not found'.format(moduleFilePath))
                
        # check contents
        referenceFilePath='{0}/oasisBuild_cray_referenceModuleFile'
        referenceFilePath = referenceFilePath.format(self.BuildSystem.WorkingDir)
        modFileString = '''#%Module1.0####################################################################
proc ModulesHelp {{ }} {{
    puts stderr "Sets up Oasis3-MCT coupler I/O server for use. 
Met Office source code URL: {OasisRepositoryUrl} 
Revision: {OasisRevisionNumber}
External URL: {OasisExternalUrl}
 External revision number: {OasisExternalRevisionNum}
Build using Rose suite:
URL: {SuiteUrl}
Revision: {SuiteRevisionNumber}
"
}}

module-whatis The Oasis3-mct coupler for use with weather/climate models

conflict {LibraryName}

set version {ModuleVersion}
set module_base {ModuleRootDir}
set oasisdir $module_base/packages/{rel_path}

prereq PrgEnv-cray/5.2.40
prereq cray-mpich/7.0.4

setenv OASIS_ROOT $oasisdir
setenv prism_path $oasisdir
setenv OASIS_INC $oasisdir/inc
setenv OASIS_LIB $oasisdir/lib
setenv OASIS3_MCT {LibraryName}
setenv OASIS_MODULE_VERSION {ModuleVersion}


'''
        modFileString = modFileString.format(rel_path=mw1.ModuleRelativePath,
                                             **self.BuildSystem.__dict__)
        
        with open(referenceFilePath,'w') as refFile:
            refFile.write(modFileString)
            
        msg1 = 'module file {0} not identical to reference file {1}'
        msg1 = msg1.format(moduleFilePath, referenceFilePath)
        self.assertTrue(filecmp.cmp(moduleFilePath, 
                                    referenceFilePath), 
                        msg1) 
    
def suite():
    suite  = unittest.TestLoader().loadTestsFromTestCase(OasisBuildCrayTests)
    return suite

if __name__ == '__main__':
    unittest.main()    
    