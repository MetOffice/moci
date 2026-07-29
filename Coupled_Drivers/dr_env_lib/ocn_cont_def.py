#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    ocn_cont_def.py

DESCRIPTION
    Definition of the environment variables required for the ocean
    controllers
'''
SI3_ENVIRONMENT_VARS_COMMON = {'SI3_NL': {'default_val': 'namelist_ice_cfg'}}
SI3_ENVIRONMENT_VARS_INITIAL = {
    'SI3_START': {'default_val': ''},
    'SI3_NL': {'default_val': 'namelist_ice_cfg'}}
SI3_ENVIRONMENT_VARS_FINAL = SI3_ENVIRONMENT_VARS_COMMON
TOP_ENVIRONMENT_VARS_COMMON = {
    'TOP_NL': {'default_val': 'namelist_top_cfg'}}
TOP_ENVIRONMENT_VARS_INITIAL = {
    'TOP_START': {'default_val': ''},
    'CONTINUE': {'default_val': 'false'},
    'CONTINUE_FROM_FAIL': {'default_val': 'false'}}

TOP_ENVIRONMENT_VARS_INITIAL = {**TOP_ENVIRONMENT_VARS_COMMON,
                                **TOP_ENVIRONMENT_VARS_INITIAL}
TOP_ENVIRONMENT_VARS_FINAL = TOP_ENVIRONMENT_VARS_COMMON
