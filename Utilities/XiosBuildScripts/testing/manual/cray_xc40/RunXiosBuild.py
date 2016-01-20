#!/usr/bin/env python2.7
'''
Created on 13 January 2016

@author: Stephen Haddad
'''

import os
import subprocess

import CrayXc40Common
import OasisCommon
import XiosCommon

SCRIPT_DIR = CrayXc40Common.setupPathToScripts()
import xiosBuild


class XiosBuildCraySettings(CrayXc40Common.CrayXc40CommonSettings,
                            OasisCommon.OasisCommonSettings,
                            XiosCommon.XiosCommonSettings):
    def __init__(self):
        CrayXc40Common.CrayXc40CommonSettings.__init__(self)
        OasisCommon.OasisCommonSettings.__init__(self)
        XiosCommon.XiosCommonSettings.__init__(self)
        
        self.workingDir = os.getcwd()
        self.XIOS_DO_CLEAN_BUILD = 'true'
        self.XIOS_POST_BUILD_CLEANUP = 'false'
        self.USE_OASIS = 'true'
        self.BUILD_PATH = '{pwd}/install'.format(pwd=self.workingDir)
        self.MTOOLS=''
        self.XIOS_NUM_CORES = '8'
        self.XLF_MODULE = ''
        self.XLCPP_MODULE = ''
        self.XIOS_EXTERNAL_REPO_URL = 'http://forge.ipsl.jussieu.fr/ioserver/svn/XIOS/trunk'
#        self.XIOS_USE_PREBUILT_LIB=true
#        self.XIOS_PREBUILT_DIR=/home/d02/shaddad/cylc-run/XBS_oasisTest/share/XIOS
        
def main():
    buildSettings1 = XiosBuildCraySettings()
    
    envVars = os.environ.copy()
    envVars.update(buildSettings1.__dict__) 

    execName1 = '{0}/xiosBuild.py'.format(SCRIPT_DIR)
    
    cmd1 = '''module load cray-hdf5-parallel/1.8.13
module load cray-netcdf-hdf5parallel/4.3.2

module use $MODULE_INSTALL_PATH/modules
module load $OASIS3_MCT/$OASIS_MODULE_VERSION/$ROSE_SUITE_REV_NO/$OASIS_REV_NO

{EXEC}'''

    cmd1 = cmd1.format(EXEC=execName1)
    subprocess.call(cmd1,
                    env=envVars,
                    shell=True)
    
if __name__ == '__main__':
    main()
    
    
    
    
    