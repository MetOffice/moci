#!/usr/bin/env python2.7
'''
Created on 13 January 2016

@author: Stephen Haddad
'''
import os 
import subprocess

import OasisCommon
import CrayXc40Common

SCRIPT_DIR = CrayXc40Common.setupPathToScripts()
import oasisTest

class OasisTestCraySettings(CrayXc40Common.CrayXc40CommonSettings,
                            OasisCommon.OasisCommonSettings):
    def __init__(self):
        CrayXc40Common.CrayXc40CommonSettings.__init__(self)
        OasisCommon.OasisCommonSettings.__init__(self)
        self.workingDir = os.getcwd()
        self.OASIS_DATA_DIRECTORY = '/data/d02/shaddad/oasis3-mct_tutorialData/'
        self.OASIS_PLATFORM_NAME = 'crayxc40'
        self.VERBOSE= 'true'
        self.OASIS_DIR = '{PWD}/install/{OASIS3_MCT}'.format(
                            PWD=self.workingDir,
                            OASIS3_MCT=self.OASIS3_MCT)

        self.OASIS_ROOT = self.OASIS_DIR
        
        self.OASIS_RESULT_DIR='{PWD}/oasisOutput/'.format(PWD=self.workingDir)
        if not os.path.exists(self.OASIS_RESULT_DIR):
            os.makedirs(self.OASIS_RESULT_DIR)
        self.OASIS_TEST_NAME = 'oasis3mct_tutorial'
        
        
def main():
    testSettings = OasisTestCraySettings()
    envVars = os.environ.copy()
    envVars.update(testSettings.__dict__)
    
    execName1 = '{0}/oasisTest.py'.format(SCRIPT_DIR)
    cmd1 = '''module use $MODULE_INSTALL_PATH/modules
module load $OASIS3_MCT/$OASIS_MODULE_VERSION/$ROSE_SUITE_REV_NO/$OASIS_REV_NO
{EXEC}'''
    cmd1 = cmd1.format(EXEC=execName1)
    subprocess.call(cmd1,
                    env=envVars,
                    shell=True)

if __name__ == '__main__':
    main()