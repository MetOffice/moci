#!/usr/bin/env python2.7
import sys
import compareUtils
import nemoTest
import os
import subprocess

def main():
    nemoKgoDir = os.environ['NEMO_KGO_DIR']
    nemoResultDir = os.environ['NEMO_RESULT_DIR']
    nemoRemoteResultDir = os.environ['NEMO_REMOTE_RESULT_DIR']    
    
    #copy files
    subprocess.call('scp {remoteDir}/*.nc {resultDir}'.format(remoteDir=nemoRemoteResultDir,
                                                              resultDir=nemoResultDir),
                    shell=True)

    print 'comparing NEMO output files'

    for fileName1 in nemoTest.TestSystem.OUTPUT_FILE_LIST:
        print 'evaluating file {filename}'.format(filename=fileName1)
        try:
            compareUtils.compareCubeListFiles(nemoKgoDir, nemoResultDir, fileName1)
        except Exception as e1:
            sys.stderr.write(str(e1))
            raise e1
        
    print 'NEMO output data match successful'
            
if __name__ == '__main__':
    main()