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
import nemoBuild

class NemoBuildCraySettings(CrayXc40Common.CrayXc40CommonSettings,
                            OasisCommon.OasisCommonSettings,
                            XiosCommon.XiosCommonSettings,
                            NemoCommon.NemoCommonSettings):
    def __init__(self):
        CrayXc40Common.CrayXc40CommonSettings.__init__(self)
        OasisCommon.OasisCommonSettings.__init__(self)
        XiosCommon.XiosCommonSettings.__init__(self)
        NemoCommon.NemoCommonSettings.__init__(self)

        self.NEMO_REPO_URL = 'svn://fcm3/NEMO.xm_svn/branches/dev/shaddad/' \
                             'r5643_buildWithOasisNoKeys/NEMOGCM'
        self.NEMO_REV = '5648'
        self.USE_OASIS = 'true'
        self.JP_CFG = '50'
        self.BUILD_PATH = '{PWD}/install'.format(PWD=os.getcwd())
        self.NEMO_POST_BUILD_CLEANUP = 'false'
        


def main():
    buildSettings1 = NemoBuildCraySettings()
    
    envVars = os.environ.copy()
    envVars.update(buildSettings1.__dict__) 

    execName1 = '{0}/nemoBuild.py'.format(SCRIPT_DIR)
    
    cmd1 = '''module use $MODULE_INSTALL_PATH/modules
module load {XIOS_PRGENV}/{XIOS_PRGENV_MOD_VER}
{EXEC}'''
    
    cmd1 = cmd1.format(EXEC=execName1,
                       XIOS_PRGENV=xiosBuild.XiosPrgEnvWriter.XIOS_PRGENV_NAME,
                       XIOS_PRGENV_MOD_VER=buildSettings1.XIOS_PRGENV_VERSION)
    

    cmd1 = cmd1.format(EXEC=execName1)
    subprocess.call(cmd1,
                    env=envVars,
                    shell=True)
    
if __name__ == '__main__':
    main()