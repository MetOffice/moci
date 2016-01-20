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
import oasisBuild

class OasisBuildCraySettings(OasisCommon.OasisCommonSettings,
                             CrayXc40Common.CrayXc40CommonSettings):
    def __init__(self):
        CrayXc40Common.CrayXc40CommonSettings.__init__(self)
        OasisCommon.OasisCommonSettings.__init__(self)
        self.workingDir = os.getcwd()
        
        self.OASIS_DIR = self.workingDir + '/install/' + self.OASIS3_MCT
        self.OASIS_PLATFORM_NAME = 'crayxc40'
        self.VERBOSE = 'true'
        self.BUILD_OASIS = 'true'
        self.OASIS_BUILD_TUTORIAL = 'true'
        self.USE_OASIS = 'true'
        self.OASIS_EXTERNAL_REPO_URL = 'http://oasis3mct.cerfacs.fr/svn/trunk/oasis3-mct'
        self.OASIS_EXTERNAL_REV_NO = '1120'
        
def main():
    buildSettings1 = OasisBuildCraySettings()
    envVars = os.environ.copy()
    envVars.update(buildSettings1.__dict__) 
    

    execName1 = '{0}/oasisBuild.py'.format(SCRIPT_DIR)
    
    cmd1 = '{EXEC}'.format(EXEC=execName1)
    subprocess.call(cmd1,
                    env=envVars)
    
    #buildSystem1 = oasisBuild.OasisCrayBuildSystem(envVars)
    #buildSystem1.RunBuild()

if __name__ == '__main__':
    main()