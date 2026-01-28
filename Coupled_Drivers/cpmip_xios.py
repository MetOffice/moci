#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021-2026 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    cpmip_xios.py

DESCRIPTION
    CPMIP functions for XIOS
'''
import os
import shutil
import sys
import common

def data_metrics_setup_nemo():
    '''
    Set up IODEF file to produce XIOS timing files
    '''
    with open('iodef.xml', 'r') as f_in, \
            open('iodef_out.xml', 'w') as f_out:
        update = False
        for line in f_in.readlines():
            if 'variable id="print_file"' in line:
                continue
            if update:
                updated_line = '\t  <variable id="print_file"           ' + \
                               '     type="bool">true</variable>\n'
                f_out.write(updated_line)
                f_out.write(line)
                update = False
            else:
                f_out.write(line)
                if 'variable id="using_server"' in line:
                    update = True
    shutil.move('iodef_out.xml', 'iodef.xml')

def measure_xios_client_times(timeout=120):
    '''
    Gather the output from XIOS client files. Takes in an optional value
    of timeout in seconds, as there may be a lot of files and we don't want
    to hang around forever if there is a problem opening them all. Returns
    the mean time and high watermark time
    '''
    total_measured = 0
    total_time = 0.
    max_time = 0.
    files = [i_f for i_f in os.listdir('.') if \
                 'xios_client' in i_f and 'out' in i_f]
    total_files = len(files)
    for i_f in files:
        rcode, out = common.exec_subproc_timeout(
            ['grep', 'total time', i_f], timeout)
        if rcode == 0:
            meas_time = float(out.split()[-2])
            total_measured += 1
            total_time += meas_time
            if meas_time > max_time:
                max_time = meas_time
    sys.stdout.write('[INFO] Measured timings for (%s/%s) XIOS clients\n' %
                     (total_measured, total_files))
    if total_measured == 0:
        sys.stderr.write('[WARN] Unable to find any XIOS client output files\n')
        mean_time = 0.0
        max_time = 0.0
    else:
        mean_time = total_time / float(total_measured)
    return mean_time, max_time
