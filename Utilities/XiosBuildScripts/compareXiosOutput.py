#!/usr/bin/env python2.7
import sys
import compareUtils
from xiosTest import XiosTestSystem
import os
import subprocess

def main():
    xiosKgoDir = os.environ['XIOS_KGO_DIR']
    xiosResultDir = os.environ['XIOS_RESULT_DIR']
    xiosRemoteRsultDir = os.environ['XIOS_REMOTE_RESULT_DIR']    
    
    #copy files
    subprocess.call('scp {remoteDir}/*.nc {resultDir}'.format(remoteDir=xiosRemoteRsultDir,
                                                              resultDir=xiosResultDir),
                    shell=True)
    
    print 'comparing XIOS output files'

    for fileName1 in XiosTestSystem.OUTPUT_FILE_LIST:
        print 'evaluating file {filename}'.format(filename=fileName1)
        try:
            compareUtils.compareCubeListFiles(xiosKgoDir, xiosResultDir, fileName1)
        except Exception as e1:
            sys.stderr.write(str(e1))
            raise e1            
        
    print 'xios output data match successful'
    sys.exit(0)            

if __name__ == '__main__':
    main()