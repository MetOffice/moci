import unittest
import os
import nemoBuild
import filecmp

class NemoBuildCrayTests(unittest.TestCase):
    def setUp(self):
        setupDict = {}
        self.SystemName = 'UKMO_CRAY_XC40'
        setupDict['TEST_SYSTEM']= self.SystemName
        setupDict['NEMO']= 'NEMO'
        self.RepoUrl = ('svn://fcm3/NEMO.xm_svn/branches/dev/shaddad/' + 
                       'r5643_buildWithOasisNoKeys/NEMOGCM')
        setupDict['NEMO_REPO_URL'] = self.RepoUrl 
        self.RevNo = '5648'
        setupDict['NEMO_REV']= self.RevNo
        self.UseOasis = True
        setupDict['USE_OASIS'] = 'true'
        setupDict['OASIS_ROOT'] = ('/home/d02/shaddad/Projects/GC3Port/' + 
                                  'r1217_port_mct_xcf/oasis3-mct/crayxc40')
        setupDict['JP_CFG'] = '50'
        setupDict['BUILD_PATH'] = '{0}/install'.format(os.getcwd())
        setupDict['NEMO_POST_BUILD_CLEANUP'] = 'false'
        setupDict['XIOS_PATH'] = '/projects/moci/modules/packages/XIOS/1.0'
        
        self.BuildSystem = nemoBuild.NemoCrayXC40BuildSystem(setupDict)
        self.WorkingDir = os.getcwd()
    
    def tearDown(self):
        self.BuildSystem = None
    
    def test_BuildSystemCreation(self):
        errMsg1 = 'System names do not match {0}!={1}'
        errMsg1 = errMsg1.format(self.SystemName,
                                 self.BuildSystem.TestSystem)
        self.assertEqual(self.BuildSystem.TestSystem, 
                         self.SystemName,
                         errMsg1 )
        errMsg1 = 'repository URLS  do not match {0}!={1}'
        errMsg1 = errMsg1.format(self.RepoUrl,
                                 self.BuildSystem.RepositoryUrl)
        self.assertEqual(self.RepoUrl,
                        self.BuildSystem.RepositoryUrl,
                        errMsg1)
 
        errMsg1 = 'NEMO revision numbers  do not match {0}!={1}'
        errMsg1 = errMsg1.format(self.RevNo,
                                 self.BuildSystem.RevisionNumber)
        self.assertEqual(self.BuildSystem.RevisionNumber,
                         self.RevNo,
                         errMsg1)
        
        self.assertEqual(self.BuildSystem.UseOasis,
                         self.UseOasis,
                         'Oasis flags do not match')
    
    def test_SetupFiles(self):
        self.BuildSystem.SetupFiles()
        
        self.checkArchFiles()
        self.checkSourceFiles()

    def checkArchFiles(self):
        archFileString ="""%NCDF_HOME           $NETCDF_DIR
%HDF5_HOME           $HDF5_DIR
%XIOS_HOME           {XiosDirectory}
%OASIS_HOME           {OasisDirectory}

%NCDF_INC            -I%NCDF_HOME/include -I%HDF5_HOME/include
%NCDF_LIB            -L%HDF5_HOME/lib -L%NCDF_HOME/lib -lnetcdff -lnetcdf -lhdf5_hl -lhdf5 -lz

%XIOS_INC            -I%XIOS_HOME/inc
%XIOS_LIB            -L%XIOS_HOME/lib -lxios

%OASIS_INC           -I%OASIS_HOME/build/lib/mct -I%OASIS_HOME/build/lib/psmile.MPI1
%OASIS_LIBDIR        -L%OASIS_HOME/lib
%OASIS_LIB           -lpsmile.MPI1 -lmct -lmpeu -lscrip
%CPP                 cpp
%FC                  ftn

%FCFLAGS             -em -s real64 -s integer32  -O2 -hflex_mp=intolerant -e0 -ez
%FFLAGS              -em -s real64 -s integer32  -O0 -hflex_mp=strict -e0 -ez -Rb
%LD                  ftn
%FPPFLAGS            -P -E -traditional-cpp
%LDFLAGS             -hbyteswapio
%AR                  ar
%ARFLAGS             -r
%MK                  gmake

%USER_INC            %NCDF_INC %OASIS_INC %XIOS_INC  
%USER_LIB            %NCDF_LIB %OASIS_LIBDIR %OASIS_LIB %XIOS_LIB %OASIS_LIB

"""
        archFileString = archFileString.format(**self.BuildSystem.__dict__)
        referenceFilePath = '{0}/nemo_archFile_{1}_reference.fcm'
        referenceFilePath = referenceFilePath.format(self.WorkingDir, 
                                                     self.BuildSystem.TestSystem)
        with open(referenceFilePath,'w') as refFile:
            refFile.write(archFileString)
            
        archFilePath = '{0}/ARCH/{1}'.format(self.BuildSystem.SourceDirectory,
                                             self.BuildSystem.ArchFileName)
        
        errMsg1 = 'arch file {0} does not match reference {1}'
        errMsg1 = errMsg1.format(archFilePath,
                                 referenceFilePath)
        self.assertTrue(filecmp.cmp(referenceFilePath,
                                    archFilePath),
                        errMsg1)

    def checkSourceFiles(self):
        srcFileList = ['{0}/CONFIG/makenemo'.format(self.BuildSystem.LibraryName), 
                       '{0}/ARCH/arch-XC40_METO.fcm'.format(self.BuildSystem.LibraryName)]
        
        errMsg1 = 'source file {0} not found'
        for file1 in srcFileList:
            self.assertTrue(os.path.exists(file1),
                            errMsg1.format(file1))
                 
    def test_WriteBuildScript(self):
        # change source directory as the source directory is not created 
        # for this test
        self.BuildSystem.SourceDirectory = self.WorkingDir
        self.BuildSystem.writeBuildScript()
        buildScriptFilePath = '{workingDir}/{fileName}'
        buildScriptFilePath = buildScriptFilePath.format(workingDir=self.WorkingDir,
                                                         fileName=nemoBuild.BUILD_SCRIPT_FILENAME)
        
        refBuildScriptStr = """#!/bin/sh
cd {SourceDirectory}/CONFIG
module load cray-hdf5-parallel/1.8.13
module load cray-netcdf-hdf5parallel/4.3.2

./makenemo -m {TestSystem} -r {NemoConfig} -n {NemoConfigBuildName} -j {NumberOfBuildProcessors} add_key "key_mpp_mpi key_iomput"

"""
        refBuildScriptStr = refBuildScriptStr.format(**self.BuildSystem.__dict__)
          
        refFilePath = '{0}/nemo_buildScript_{1}_reference.sh'
        refFilePath = refFilePath.format(self.WorkingDir, 
                                         self.BuildSystem.TestSystem)
        with open(refFilePath,'w') as refFile:
            refFile.write(refBuildScriptStr)
        
        
        errMsg1 = 'arch file {0} does not match reference {1}'
        errMsg1 = errMsg1.format(buildScriptFilePath,
                                 refFilePath)
        self.assertTrue(filecmp.cmp(refFilePath,
                                    buildScriptFilePath),
                        errMsg1)
      
class NemoBuildLinuxIntelTests(unittest.TestCase):
    def setUp(self):
        setupDict = {}
        self.SystemName = 'UKMO_LINUX_INTEL'
        setupDict['TEST_SYSTEM']= self.SystemName
        setupDict['NEMO']= 'NEMO'
        self.RepoUrl = ('svn://fcm3/NEMO.xm_svn/branches/dev/shaddad/' + 
                       'r5643_buildWithOasisNoKeys/NEMOGCM')
        setupDict['NEMO_REPO_URL'] = self.RepoUrl 
        self.RevNo = '5648'
        setupDict['NEMO_REV']= self.RevNo
        self.UseOasis = False
        if self.UseOasis:
            setupDict['USE_OASIS'] = 'true'
            setupDict['OASIS_ROOT'] = ('/path/to/oasis')
        else:
            setupDict['USE_OASIS'] = 'false'
            setupDict['OASIS_ROOT'] = ''
        setupDict['JP_CFG'] = '50'
        setupDict['BUILD_PATH'] = '{0}/install'.format(os.getcwd())
        setupDict['NEMO_POST_BUILD_CLEANUP'] = 'false'
        setupDict['XIOS_PATH'] = '/projects/moci/modules/packages/XIOS/1.0'
        
        self.BuildSystem = nemoBuild.NemoLinuxIntelBuildSystem(setupDict)
        self.WorkingDir = os.getcwd()
        
    def tearDown(self):
        self.BuildSystem = None
    
    def test_BuildSystemCreation(self):
        errMsg1 = 'System names do not match {0}!={1}'
        errMsg1 = errMsg1.format(self.SystemName,
                                 self.BuildSystem.TestSystem)
        self.assertEqual(self.BuildSystem.TestSystem, 
                         self.SystemName,
                         errMsg1 )
        errMsg1 = 'repository URLS  do not match {0}!={1}'
        errMsg1 = errMsg1.format(self.RepoUrl,
                                 self.BuildSystem.RepositoryUrl)
        self.assertEqual(self.RepoUrl,
                        self.BuildSystem.RepositoryUrl,
                        errMsg1)
 
        errMsg1 = 'NEMO revision numbers  do not match {0}!={1}'
        errMsg1 = errMsg1.format(self.RevNo,
                                 self.BuildSystem.RevisionNumber)
        self.assertEqual(self.BuildSystem.RevisionNumber,
                         self.RevNo,
                         errMsg1)
        
        self.assertEqual(self.BuildSystem.UseOasis,
                         self.UseOasis,
                         'Oasis flags do not match')
            
        self.BuildSystem.SetupFiles()
        
        self.checkArchFiles()
        self.checkSourceFiles()

    def checkArchFiles(self):
        archFileString ="""%XIOS_HOME           {XiosDirectory}

%OASIS_HOME
%NCDF_INC            -I$NETCDF_ROOT/include/
%NCDF_LIB            -L$NETCDF_ROOT/lib -lnetcdf -lnetcdff
%XIOS_INC            -I%XIOS_HOME/inc
%XIOS_LIB            -L%XIOS_HOME/lib -lxios

%OASIS_INC
%OASIS_LIB

%FC                  mpif90
%FCFLAGS            -r8 -xHOST  -traceback
%FFLAGS                -r8 -xHOST  -traceback
%LD                  mpif90
%CPP                 cpp
%FPPFLAGS            -P -C -traditional
%LDFLAGS             -lstdc++
%AR                  ar
%ARFLAGS             -r
%MK                  gmake
%USER_INC            %XIOS_INC %NCDF_INC
%USER_LIB            %XIOS_LIB %NCDF_LIB
"""
        archFileString = archFileString.format(**self.BuildSystem.__dict__)
        referenceFilePath = '{0}/nemo_archFile_{1}_reference.fcm'
        referenceFilePath = referenceFilePath.format(self.WorkingDir, 
                                                     self.BuildSystem.TestSystem)
        with open(referenceFilePath,'w') as refFile:
            refFile.write(archFileString)
            
        archFilePath = '{0}/ARCH/{1}'.format(self.BuildSystem.SourceDirectory,
                                             self.BuildSystem.ArchFileName)
        
        errMsg1 = 'arch file {0} does not match reference {1}'
        errMsg1 = errMsg1.format(archFilePath,
                                 referenceFilePath)
        self.assertTrue(filecmp.cmp(referenceFilePath,
                                    archFilePath),
                        errMsg1)

    def checkSourceFiles(self):
        srcFileList = ['{0}/CONFIG/makenemo'.format(self.BuildSystem.LibraryName), 
                       '{0}/ARCH/arch-XC40_METO.fcm'.format(self.BuildSystem.LibraryName)]
        
        errMsg1 = 'source file {0} not found'
        for file1 in srcFileList:
            self.assertTrue(os.path.exists(file1),
                            errMsg1.format(file1))
                
    def test_WriteBuildScript(self):
        # change source directory as the source directory is not created 
        # for this test
        self.BuildSystem.SourceDirectory = self.WorkingDir
        self.BuildSystem.writeBuildScript()
        buildScriptFilePath = '{0}/{1}'.format(self.WorkingDir,
                                               nemoBuild.BUILD_SCRIPT_FILENAME)
        
        refBuildScriptStr = """#!/bin/sh
cd {SourceDirectory}/CONFIG
source /data/cr1/mhambley/modules/setup
module load environment/dynamo/compiler/intelfortran/15.0.0


./makenemo -m {TestSystem} -r {NemoConfig} -n {NemoConfigBuildName} -j {NumberOfBuildProcessors} add_key "key_mpp_mpi key_iomput"

"""
        refBuildScriptStr = refBuildScriptStr.format(**self.BuildSystem.__dict__)
          
        refFilePath = '{0}/nemo_buildScript_{1}_reference.sh'
        refFilePath = refFilePath.format(self.WorkingDir, 
                                         self.BuildSystem.TestSystem)
        with open(refFilePath,'w') as refFile:
            refFile.write(refBuildScriptStr)
        
        
        errMsg1 = 'arch file {0} does not match reference {1}'
        errMsg1 = errMsg1.format(buildScriptFilePath,
                                 refFilePath)
        self.assertTrue(filecmp.cmp(refFilePath,
                                    buildScriptFilePath),
                        errMsg1)
    
    