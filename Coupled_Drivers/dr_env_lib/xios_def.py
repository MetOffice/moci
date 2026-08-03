#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021-2025 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    xios_def.py

DESCRIPTION
    Definition of the environment variables required for an xios model
    run
'''

XIOS_ENVIRONMENT_VARS_INITIAL = {
    'COUPLING_COMPONENTS' : {'default_val': ''},
    'XIOS_NPROC': {'default_val': '0',
                   'triggers': [[lambda my_val: my_val != '0',
                                 ['XIOS_LINK', 'ROSE_LAUNCHER_PREOPTS_XIOS',
                                  'XIOS_EXEC']]]},
    'IODEF_CUSTOM': {'default_val': ''},
    'IODEF_FILENAME': {'default_val': 'iodef.xml'},
    'ROSE_LAUNCHER_PREOPTS_XIOS': {'default_val': 'unset'},
    'XIOS_EXEC': {},
    'XIOS_LINK': {'default_val': 'xios.exe'},
    'XIOS_VERSION': {'default_val': '2'}
    }
