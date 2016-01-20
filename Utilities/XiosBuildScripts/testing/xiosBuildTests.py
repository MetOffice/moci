import unittest
import subprocess
import os
import xiosBuild
import filecmp
import pdb

class XiosBuildCrayTests(unittest.TestCase):
    def setUp(self):
        print 'Setting up tests'
        self.environment = {}
        self.SystemName = 'UKMO_CRAY_XC40'
        self.environment['TEST_SYSTEM']=self.SystemName
        self.environment['XIOS_DO_CLEAN_BUILD'] = 'true'
        self.environment['XIOS_POST_BUILD_CLEANUP'] = 'false'
        self.XiosRepoUrl = 'svn://fcm1/xios.xm_svn/XIOS/branchs/xios-1.0'
        self.environment['XIOS_REPO_URL'] = self.XiosRepoUrl
        self.XiosRevNo = 'HEAD'
        self.environment['XIOS_REV'] = self.XiosRevNo 
        self.environment['XIOS'] = 'XIOS'
        self.environment['USE_OASIS'] = 'false'
        self.environment['OASIS_ROOT'] = '/home/d02/shaddad/Projects/GC3Port/r1217_port_mct_xcf/oasis3-mct/crayxc40'
        self.environment['BUILD_PATH'] = '{0}/install'.format(os.getcwd())
        self.NetCdfDirStr = subprocess.check_output('module load cray-netcdf-hdf5parallel/4.3.2; echo $NETCDF_DIR',shell=True)
        self.NetCdfDirStr = self.NetCdfDirStr.strip('\n')
        self.environment['MTOOLS'] = self.NetCdfDirStr
        self.NumCores = 4
        self.environment['XIOS_NUM_CORES'] = str(self.NumCores)
        self.environment['XLF_MODULE'] = ''
        self.environment['XLCPP_MODULE'] = ''
        self.environment['DEPLOY_AS_MODULE'] = 'true'
        self.environment['MODULE_INSTALL_PATH'] = '{0}/modules'.format(os.getcwd())
        self.environment['XIOS_MODULE_VERSION'] = '1.0'
        self.environment['XIOS_PRGENV_VERSION'] = '1.0'
        self.environment['OASIS_MODULE_VERSION'] = '1.0'
        self.environment['OASIS3_MCT'] = "oasis3-mct"
        self.environment['ROSE_SUITE_URL'] = 'path/to/repository'
        self.environment['ROSE_SUITE_REV_NO'] = '1234'
        self.ExternalRepoUrl = 'http://external.server.gov/path/to/repository'
        self.environment['XIOS_EXTERNAL_REPO_URL'] = self.ExternalRepoUrl

        
        # NOTE: 
        self.BuildSystem = xiosBuild.XiosCrayBuildSystem(self.environment)
        self.TestScriptDirectory = os.path.dirname(os.path.realpath(__file__))

    def tearDown(self):
        pass

    def test_setup(self):
        self.assertEqual(self.BuildSystem.NumberOfBuildTasks, self.NumCores)
        self.assertEqual(self.BuildSystem.TestSystem, self.SystemName)
        self.assertEqual(self.BuildSystem.XiosRepositoryUrl, self.XiosRepoUrl)
        self.assertEqual(self.NetCdfDirStr, self.BuildSystem.ThirdPartyLibs)
        self.assertEqual(self.ExternalRepoUrl,
                         self.BuildSystem.XiosExternalUrl)
        
    def test_ExtractionScript(self):
        self.BuildSystem.extractXiosSourceCode()
        scriptFilePath = '{workingDir}/{fileName}'
        scriptFilePath = scriptFilePath.format(workingDir=self.BuildSystem.workingDir,
                                               fileName=xiosBuild.EXTRACT_SCRIPT_FILENAME)
        self.assertTrue(os.path.exists(scriptFilePath),'script file {0} not found!'.format(scriptFilePath))
        # compare contents to reference file
        refFilePath = '{0}/resources/cray_xiosBuild_extractScript.sh'.format(self.TestScriptDirectory)
        self.assertTrue(filecmp.cmp(scriptFilePath, refFilePath), 'script file {0} not identical to reference file {1}'.format(scriptFilePath, refFilePath))
        
        # check extracted source code for existence of some files
        extractDirectory = '{0}/{1}'.format(self.BuildSystem.workingDir, self.BuildSystem.LibraryName)
        self.assertTrue(os.path.exists(extractDirectory))
        self.assertTrue(os.path.isdir(extractDirectory))
        fileCheckList = ['{0}/make_xios'.format(extractDirectory)]
        fileCheckList += ['{0}/bld.cfg'.format(extractDirectory)]
        fileCheckList += ['{0}/src/xios_server.f90'.format(extractDirectory)]
        for filePath1 in fileCheckList:
            self.assertTrue(os.path.exists(filePath1),' file {0} not found'.format(filePath1))   
                
    def test_WriteModule(self):
        mw1 = xiosBuild.XiosCrayModuleWriter(self.BuildSystem.ModuleVersion,
                                             self.BuildSystem.ModuleRootDir,
                                             self.BuildSystem.XiosRepositoryUrl,
                                             self.BuildSystem.XiosRevisionNumber,
                                             self.BuildSystem.XiosExternalUrl,
                                             self.BuildSystem.SuiteUrl,
                                             self.BuildSystem.SuiteRevisionNumber,                                          
                                             self.BuildSystem.SYSTEM_NAME)
        mw1.WriteModule()
        
        # check for existence of module
        tempModStr1 = '{root_dir}/modules/{rel_path}'
        moduleFilePath = tempModStr1.format(
                             root_dir = self.BuildSystem.ModuleRootDir,
                             rel_path = mw1.ModuleRelativePath)
        self.assertTrue(os.path.exists(moduleFilePath),'Module file {0} not found'.format(moduleFilePath))
                
        # check contents
        referenceFilePath='{0}/xiosBuild_cray_moduleFile'.format(self.BuildSystem.workingDir)
        modFileString = '''#%Module1.0####################################################################
proc ModulesHelp {{ }} {{
    puts stderr "Sets up XIOS I/O server for use.
Met Office Source URL {XiosRepositoryUrl} 
Revision: {XiosRevisionNumber}
External URL: {XiosExternalUrl}
Build using Rose suite:
URL: {SuiteUrl}
Revision: {SuiteRevisionNumber}
"
}}

module-whatis The XIOS I/O server for use with weather/climate models

conflict XIOS

set version {ModuleVersion}
set module_base {ModuleRootDir}
set xiosdir $module_base/packages/{rel_path}

prereq PrgEnv-cray/5.2.40
prereq cray-mpich/7.0.4
prereq cray-hdf5-parallel/1.8.13
prereq cray-netcdf-hdf5parallel/4.3.2

setenv XIOS_PATH $xiosdir
setenv xios_path $xiosdir
setenv XIOS_INC $xiosdir/inc
setenv XIOS_LIB $xiosdir/lib
setenv XIOS_EXEC $xiosdir/bin/xios_server.exe

prepend-path PATH $xiosdir/bin
\n'''
        modFileString = modFileString.format(rel_path=mw1.ModuleRelativePath,
                                             **self.BuildSystem.__dict__)
        with open(referenceFilePath,'w') as refFile:
            refFile.write(modFileString)

        self.assertTrue(filecmp.cmp(moduleFilePath, 
                                    referenceFilePath), 
                        'module file {0} not identical to '
                        'reference file {1}'.format(moduleFilePath, 
                                                    referenceFilePath))    
        
        
    def test_writeBuildScript(self):
        self.BuildSystem.writeBuildScript()
        
        scriptFilePath = '{workingDir}/{fileName}'
        scriptFilePath = scriptFilePath.format(workingDir=self.BuildSystem.workingDir,
                                               fileName=xiosBuild.BUILD_SCRIPT_FILENAME)

        self.assertTrue(os.path.exists(scriptFilePath), 'build script {0} not found!'.format(scriptFilePath) )
        refFilePath = '{0}/xiosBuild_cray_referenceBuildScript.sh'.format(self.BuildSystem.workingDir)
        refFileStr='''#!/bin/sh

module load cray-hdf5-parallel/1.8.13
module load cray-netcdf-hdf5parallel/4.3.2

cd {workingDir}/XIOS
./make_xios --arch XC30_Cray --full  --job 4 
'''
        refFileStr = refFileStr.format(workingDir=self.BuildSystem.workingDir)
        
        with open(refFilePath,'w') as refFile:
            refFile.write(refFileStr)
        errMsg1 = 'build script {0} not identical to reference script {1}'.format(scriptFilePath,refFilePath)
        self.assertTrue(filecmp.cmp(scriptFilePath,refFilePath), errMsg1)
    
class XiosBuildLinuxIntelTests(unittest.TestCase):
    def setUp(self):
        self.environment = {}
        self.SystemName = 'UKMO_LINUX_INTEL'
        self.environment['TEST_SYSTEM']=self.SystemName
        self.environment['XIOS_DO_CLEAN_BUILD'] = 'true'
        self.environment['XIOS_POST_BUILD_CLEANUP'] = 'false'
        self.XiosRepoUrl = 'svn://fcm1/xios.xm_svn/XIOS/branchs/xios-1.0'
        self.environment['XIOS_REPO_URL'] = self.XiosRepoUrl 
        self.environment['XIOS_REV'] = 'HEAD'
        self.environment['XIOS'] = 'XIOS'
        self.environment['USE_OASIS'] = 'false'
        self.environment['OASIS_ROOT'] = ''
        self.environment['BUILD_PATH'] = '{0}/install'.format(os.getcwd())
        self.NetCdfDirStr = subprocess.check_output('. /data/cr1/mhambley/modules/setup; module load environment/dynamo/compiler/intelfortran/15.0.0; echo $NETCDF_ROOT',shell=True)
        self.NetCdfDirStr = self.NetCdfDirStr.strip('\n')
        self.environment['MTOOLS'] = self.NetCdfDirStr
        self.NumCores = 4
        self.environment['XIOS_NUM_CORES'] = str(self.NumCores)
        self.environment['XLF_MODULE'] = ''
        self.environment['XLCPP_MODULE'] = ''
        self.environment['DEPLOY_AS_MODULE'] = 'true'
        self.environment['MODULE_INSTALL_PATH'] = '{0}/modules'.format(os.getcwd())
        self.environment['MODULE_VERSION'] = '1.0'
        # NOTE: 
        self.BuildSystem = xiosBuild.XiosLinuxIntelSystem(self.environment)
        
        self.TestScriptDirectory = os.path.dirname(os.path.realpath(__file__))
        
    
    def tearDown(self):
        pass

    def test_setup(self):
        self.assertEqual(self.BuildSystem.NumberOfBuildTasks, self.NumCores)
        self.assertEqual(self.BuildSystem.TestSystem, self.SystemName)
        self.assertEqual(self.BuildSystem.XiosRepositoryUrl, self.XiosRepoUrl)
        self.assertEqual(self.NetCdfDirStr, self.BuildSystem.ThirdPartyLibs)
        
    def test_ExtractionScript(self):
        self.BuildSystem.extractXiosSourceCode()
        scriptFilePath = '{workingDir}/{fileName}'
        scriptFilePath = scriptFilePath.format(workingDir=self.BuildSystem.workingDir,
                                               fileName=xiosBuild.EXTRACT_SCRIPT_FILENAME)
        self.assertTrue(os.path.exists(scriptFilePath),'script file {0} not found!'.format(scriptFilePath))

        # compare contents to reference file
        refFilePath = '{0}/resources/linuxIntel_xiosBuild_extractScript.sh'.format(self.TestScriptDirectory)
        self.assertTrue(filecmp.cmp(scriptFilePath, refFilePath), 'script file {0} not identical to reference file {1}'.format(scriptFilePath, refFilePath))
        
        # check extracted source code for existence of some files
        extractDirectory = '{0}/{1}'.format(self.BuildSystem.workingDir, self.BuildSystem.LibraryName)
        self.assertTrue(os.path.exists(extractDirectory))
        self.assertTrue(os.path.isdir(extractDirectory))
        fileCheckList = ['{0}/make_xios'.format(extractDirectory)]
        fileCheckList += ['{0}/bld.cfg'.format(extractDirectory)]
        fileCheckList += ['{0}/src/xios_server.f90'.format(extractDirectory)]
        for filePath1 in fileCheckList:
            self.assertTrue(os.path.exists(filePath1),' file {0} not found'.format(filePath1))                
                       
    
    def test_WriteModule(self):
        mw1 = xiosBuild.XiosLinuxIntelModuleWriter(self.BuildSystem.ModuleVersion,
                                                   self.BuildSystem.ModuleRootDir,
                                                   self.BuildSystem.XiosRevisionNumber)
        mw1.WriteModule()
        
        # check for existence of module
        moduleFilePath = '{ModuleRootDir}/modules/{LibraryName}/{ModuleVersion}'.format( **self.BuildSystem.__dict__)
        self.assertTrue(os.path.exists(moduleFilePath),'Module file {0} not found'.format(moduleFilePath))
                
        # check contents
        referenceFilePath='{0}/xiosBuild_linuxIntel_moduleFile'.format(self.BuildSystem.workingDir)
        modFileString = '''#%Module1.0####################################################################
proc ModulesHelp {{ }} {{
    puts stderr "Sets up XIOS I/O server for use.branch xios-1.0 revision HEAD"
}}

module-whatis The XIOS I/O server for use with weather/climate models

conflict XIOS

set version 1.0
set module_base {ModuleRootDir}
set xiosdir $module_base/packages/XIOS/1.0

prereq fortran/intel/15.0.0
prereq mpi/mpich/3.1.2/ifort/15.0.0
prereq hdf5/1.8.12/ifort/15.0.0
prereq netcdf/4.3.3-rc1/ifort/15.0.0

setenv XIOS_PATH $xiosdir
setenv XIOS_INC $xiosdir/inc
setenv XIOS_LIB $xiosdir/lib

prepend-path PATH $xiosdir/bin
\n'''
        modFileString = modFileString.format(**self.BuildSystem.__dict__)
        
        with open(referenceFilePath,'w') as refFile:
            refFile.write(modFileString)
            
        self.assertTrue(filecmp.cmp(moduleFilePath, referenceFilePath), 'module file {0} not identical to reference file {1}'.format(moduleFilePath, referenceFilePath))
    
    def test_writeBuildScript(self):
        self.BuildSystem.writeBuildScript()
        
        scriptFilePath = '{workingDir}/{fileName}'
        scriptFilePath = scriptFilePath.format(workingDir=self.BuildSystem.workingDir,
                                               fileName=xiosBuild.BUILD_SCRIPT_FILENAME)
        
        self.assertTrue(os.path.exists(scriptFilePath), 'build script {0} not found!'.format(scriptFilePath) )
        refFilePath = '{0}/xiosBuild_linuxIntel_referenceBuildScript.sh'.format(self.BuildSystem.workingDir)
        refFileStr='''#!/bin/bash

. /data/cr1/mhambley/modules/setup
module load environment/dynamo/compiler/intelfortran/15.0.0

cd {workingDir}/XIOS

./make_xios --dev --arch LINUX_INTEL --full  --job 4 
'''
        refFileStr = refFileStr.format(workingDir=self.BuildSystem.workingDir)
        
        with open(refFilePath,'w') as refFile:
            refFile.write(refFileStr)
        errMsg1 = 'file {resultFile} does not match {kgoFile}'
        errMsg1 = errMsg1.format(resultFile=scriptFilePath,
                                 kgoFile=refFilePath)
        self.assertTrue(filecmp.cmp(scriptFilePath,refFilePath), errMsg1)
    
def suite():
    suite  = unittest.TestLoader().loadTestsFromTestCase(XiosBuildLinuxIntelTests)
    return suite

if __name__ == '__main__':
    unittest.main()