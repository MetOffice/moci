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
    write_namcouple_header.py

DESCRIPTION
    Code for writing the namcouple header at run time.
'''
import common

def write_namcouple_header(common_env, nam_file, run_info, n_fields):
    '''
    Write the namcouple header
    '''
    # Create the header
    nam_file.write('#===================================================\n'
                   '# Control file for OASIS-MCT\n'
                   '# This file is created automatically using the drivers.\n'
                   '#---------------------------------------------------\n'
                   ' $NFIELDS\n'
                   '# This is the total number of fields being exchanged.\n'
                   '# For the definition of the fields, see under '
                   '$STRINGS keyword\n'
                   '#\n')
    nam_file.write('  %d\n' % n_fields)
    nam_file.write(' $END\n'
                   '#---------------------------------------------------\n'
                   ' $NBMODEL\n')
    arg1_list = ''
    arg2_list = ''
    for exec_name in run_info['exec_list']:
        arg1_list = arg1_list + ' ' + exec_name
        arg2_list = arg2_list + ' 1024'
    nam_file.write('   %d%s%s\n' % (len(run_info['exec_list']), arg1_list,
                                    arg2_list))
    nam_file.write(' $END\n'
                   '#---------------------------------------------------\n'
                   ' $RUNTIME\n')
    nam_file.write('  %d\n' % common.setup_runtime(common_env))
    nam_file.write(' $END\n'
                   '#---------------------------------------------------\n'
                   ' $INIDATE\n'
                   '# This is the initial date of the run. This is '
                   'important only if\n'
                   '# FILLING analysis is used for a coupling field in '
                   'the run.\n'
                   '# The format is YYYYMMDD.\n'
                   '#\n'
                   '# RH: This may become important in all cases if we '
                   'want to\n'
                   '#     cross check to ensure all components start at '
                   'the same\n'
                   '#     date/time.\n'
                   '#\n'
                   '  00010101\n'
                   ' $END\n'
                   '#---------------------------------------------------\n'
                   ' $MODINFO\n'
                   '# Indicates if a header is encapsulated within the '
                   'field brick\n'
                   '# in binary restart files for all communication '
                   'techniques,\n'
                   '# (and for coupling field exchanges for PIPE, SIPC '
                   'and GMEM.\n'
                   '# (YES or NOT)\n'
                   '  NOT\n'
                   ' $END\n'
                   '#---------------------------------------------------\n'
                   ' $NLOGPRT\n'
                   '# Index of printing level in output file cplout: '
                   '0 = no printing\n'
                   '#  1 = main routines and field names when treated, '
                   '30 = complete output\n')
    if len(run_info['nlogprt']) == 2:
        # Time statistics information is on
        nam_file.write('  %d %d\n' % (run_info['nlogprt'][0],
                                      run_info['nlogprt'][1]))
    else:
        nam_file.write('  %d\n' % run_info['nlogprt'][0])
    nam_file.write(' $END\n'
                   '#---------------------------------------------------\n'
                   ' $CALTYPE\n'
                   '# Calendar type :  0      = 365 day calendar (no '
                   'leap years)\n'
                   '#                  1      = 365 day, or 366 days '
                   'for leap years, calendar\n'
                   '#                  n (>1) = n day month calendar\n'
                   '# This is important only if FILLING analysis is '
                   'used for a coupling\n'
                   '# field in the run.\n'
                   '#\n'
                   '  30\n'
                   ' $END\n'
                   '#===================================================\n'
                   '# Start of transient definitions\n'
                   '#---------------------------------------------------\n'
                   ' $STRINGS\n'
                   '#\n'
                   '# The above variables are the general parameters '
                   'for the experiment.\n'
                   '# Everything below has to do with the fields being '
                   'exchanged.\n')
