#!/usr/bin/env python2.7
import sys

import iris

ERROR_TOLERANCE =  1e-10

class MissingArgumentException(Exception):
    pass

class FileLoadException(Exception):
    def __init__(self,filePath):
        Exception.__init__(self)
        self.message = 'failed to load file {0}'
        self.message = self.message.format(filePath)
    
    def __str__(self):
        return self.message
        
class CubeCountMismatchException(Exception):
    def __init__(self):
        Exception.__init__(self)
        self.message = 'mismatch in number of cubes'

    def __str__(self):
        return self.message

class DataMismatchException(Exception):
    def __init__(self,cubeNum,fileName):
        Exception.__init__(self)
        self.message = 'mismatch in cube {cubeNum} in output file {fileName}'
        self.message = self.message.format(cubeNum=cubeNum,
                                     fileName=fileName)

    def __str__(self):
        return self.Message


def compareCubeListFiles(directory1, directory2, fileName1):
    filePath1='{0}/{1}'.format(directory1,fileName1)
    filePath2='{0}/{1}'.format(directory2,fileName1)

    try:
        cubeList1 = iris.load(filePath1)
    except:
        raise FileLoadException(filePath1)

    try:
        cubeList2 = iris.load(filePath2)
    except:
        raise FileLoadException(filePath2)
        
    if len(cubeList1) != len(cubeList2):
        raise CubeCountMismatchException()
            
    for ix1, (cube1,cube2) in enumerate(zip(cubeList1, cubeList2)):
        msg1 = 'comparing cube {currentCube} of {totalCubes}'
        msg1 = msg1.format(currentCube=ix1+1,
                           totalCubes=len(cubeList1),
                           filename=fileName1)
        print msg1
        cubeDiff = (cube1.data-cube2.data).flatten().sum()
        if abs(cubeDiff) > ERROR_TOLERANCE:
            raise DataMismatchException(ix1,fileName1)
            