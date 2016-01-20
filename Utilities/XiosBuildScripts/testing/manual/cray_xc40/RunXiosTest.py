#!/usr/bin/env python2.7
'''
Created on 13 January 2016

@author: Stephen Haddad
'''
import os 
import subprocess

import crayXc40Common
import oasisCommon
import xiosCommon

SCRIPT_DIR = crayXc40Common.setupPathToScripts()
import xiosBuild

class XiosTestCraySettings(crayXc40Common.CrayXc40CommonSettings,
                           oasisCommon.OasisCommonSettings,
                           xiosCommon.XiosCommonSettings):
    def __init__(self):
        crayXc40Common.CrayXc40CommonSettings.__init__(self)
        oasisCommon.OasisCommonSettings.__init__(self)
        xiosCommon.XiosCommonSettings.__init__(self)
        
        self.workingDir = os.getcwd()
        
        
def main():
    testSettings = XiosTestCraySettings()
    envVars = os.environ.copy()
    envVars.update(testSettings.__dict__)
    
    execName1 = '{0}/xiosTest.py'.format(SCRIPT_DIR)
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