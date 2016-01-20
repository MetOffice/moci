import os 
import sys

def setupPathToScripts():
    '''
    Get the path to the scripts to be tested, which should be 3 levels up
    '''
    runScriptDirPath = os.path.realpath(os.path.dirname(__file__))
    scriptDir = os.path.abspath(os.path.join(runScriptDirPath,
                                              os.pardir,
                                              os.pardir, 
                                              os.pardir))
    sys.path += [scriptDir]
    return scriptDir
    

class CrayXc40CommonSettings(object):
    def __init__(self):
        self.SYSTEM_NAME = 'UKMO_CRAY_XC40'
        self.TEST_SYSTEM = self.SYSTEM_NAME

        self.DEPLOY_AS_MODULE = 'true'
        self.MODULE_INSTALL_PATH=os.getcwd() + '/modules'

        self.ROSE_SUITE_URL = 'undefined'
        self.ROSE_SUITE_REV_NO=  'undefined'