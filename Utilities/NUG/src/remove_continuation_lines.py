#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2018 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    remove_continuation_lines.py

DESCRIPTION
    auxiliary service function.
    qstat_snapshot files have lines split after 80 characters.
    The breaks are removed using this funtion

ENVIRONMENT VARIABLES
'''


from os.path import expandvars

def remove_continuation_lines(job_file):
    ''' auxiliary funtion to remove breaks after 80 characters '''

    aux_name = expandvars('$TMPDIR/aux_pbs')

    inp = open(job_file, "r")
    onp = open(aux_name, "w")

    newset = ['']
    for line in inp:
        if ' = '  in line:
            newset.append(line.rstrip())
        else:
            newset[-1] = newset[-1]+line.rstrip()

    for line in newset:
        onp.write(line+'\n')

    inp.close()
    onp.close()

    return aux_name
