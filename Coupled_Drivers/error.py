#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    error.py

DESCRIPTION
    Module containing error codes for the drivers. To ensure consistancy over
    all the scripts that will make up the drivers, it is recommended that the
    follwing error codes be used for self consistancy. Any error codes <100
    are to be used within the drivers themselves, for specific errors.
'''
# Python errors
VERSION_ERROR = 1

# File I/O errors
IOERROR = 100

# Missing Environment variable
MISSING_EVAR_ERROR = 101

# Subprocess Error
SUBPROC_ERROR = 102

# Invalid environment variable
INVALID_EVAR_ERROR = 103

# Date matching error
DATE_MISMATCH_ERROR = 104

# Invalid local variable
INVALID_LOCAL_ERROR = 110

# Missing Driver
MISSING_DRIVER_ERROR = 200

# Missing file required by a driver
MISSING_DRIVER_FILE_ERROR = 201

# Invalid argument to driver script
INVALID_DRIVER_ARG_ERROR = 202

# Missing file required by a controller
MISSING_CONTROLLER_FILE_ERROR = 251

# Type conversion error
TYPE_COVERSION_ERROR = 300

# Missing file that will be required by a component model
MISSING_MODEL_FILE_ERROR = 400

# An error in the component model
COMPONENT_MODEL_ERROR = 401

# Invalid function argument
INVALID_FUNC_ARG_ERROR = 500

# Invalid component version
INVALID_COMPONENT_VER_ERROR = 600

# Restart date error
MISMATCH_RESTART_DATE_ERROR = 700

