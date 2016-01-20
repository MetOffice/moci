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
import NemoCommon

SCRIPT_DIR = CrayXc40Common.setupPathToScripts()
import xiosBuild

class NemoTestCraySettings(CrayXc40Common.CrayXc40CommonSettings,
                           OasisCommon.OasisCommonSettings,
                           XiosCommon.XiosCommonSettings,
                           NemoCommon.NemoCommonSettings):
    def __init__(self):
        CrayXc40Common.CrayXc40CommonSettings.__init__(self)
        OasisCommon.OasisCommonSettings.__init__(self)
        XiosCommon.XiosCommonSettings.__init__(self)
        NemoCommon.NemoCommonSettings.__init__(self)
        
        self.workingDir = os.getcwd()
        
        self.BUILD_PATH = '{PWD}/install'.format(PWD=self.workingDir)
        self.nemoTasksJpi = '8'
        self.nemoTasksJpj = '16'
        self.xiosTasks = '16'
        self.JP_CFG = '50'
        self.NEMO_EXP_REL_PATH = ''
        self.TasksPerNode = '32'
        self.XiosTasksPerNode = '8'        
        
        
def main():
    testSettings = NemoTestCraySettings()
    envVars = os.environ.copy()
    envVars.update(testSettings.__dict__)
    
    execName1 = '{0}/nemoTest.py'.format(SCRIPT_DIR)
    cmd1 = '''module use $MODULE_INSTALL_PATH/modules
module load {XIOS_PRGENV}/{XIOS_PRGENV_MOD_VER}
{EXEC}'''
    cmd1 = cmd1.format(EXEC=execName1,
                       XIOS_PRGENV=xiosBuild.XiosPrgEnvWriter.XIOS_PRGENV_NAME,
                       XIOS_PRGENV_MOD_VER=testSettings.XIOS_PRGENV_VERSION)
    subprocess.call(cmd1,
                    env=envVars,
                    shell=True)

if __name__ == '__main__':
    main()