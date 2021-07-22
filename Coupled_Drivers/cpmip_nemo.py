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
    cpmip_nemo.py

DESCRIPTION
    CPMIP functions for NEMO
'''
import re
import sys
import common
import error


def update_namelists_for_timing_nemo(cpmip_envar, nn_timing_val):
    '''
    Update NEMO namelist to ensure that timers are running
    '''
    mod_namelist_cfg = common.ModNamelist(cpmip_envar['NEMO_NL'])
    mod_namelist_cfg.var_val('nn_timing', nn_timing_val)
    mod_namelist_cfg.replace()


def get_nemo_info(nemo_timing_output='timing.output'):
    '''
    Grab NEMO timing output. Takes an optional argument, the path to the NEMO
    timing.output file for NEMO/CICE. Returns the time spent in the NEMO
    model, less the time spent in the coupling routines, and the time spent
    in the coupling routines themselves, as well as the (inclusive) time in
    CICE.
    '''
    # There are three coupling routines we need to remove from the total time
    # sbc_cpl_rcv, sbc_cpl_init, and sbc_cpl_snd.
    # Compile the regular expressions needed to pull out the timings. Use the
    # elapsed times
    # This searches for a time
    total_time_regex = re.compile(r"\s*Total\s*\|\s*(\d+.\d+)")
    # These regexes will pull out a percentage
    sbc_cpl_rcv_regex = re.compile(r"\s*sbc_cpl_rcv\s*\d+.\d+\s*(\d+.\d+)")
    sbc_cpl_init_regex = re.compile(r"\s*sbc_cpl_init\s*\d+.\d+\s*(\d+.\d+)")
    sbc_cpl_snd_regex = re.compile(r"\s*sbc_cpl_snd\s*\d+.\d+\s*(\d+.\d+)")
    sbc_ice_cice_regex = re.compile(r"\s*sbc_ice_cice\s*\d+.\d+\s*(\d+.\d+)")

    #depending on the particular configuration we may not be able to determine
    #the time spent in CICE
    cice_measurement = False
    with common.open_text_file(nemo_timing_output, 'r') as nemo_timing_handle:
        for line in nemo_timing_handle.readlines():
            tot_match = total_time_regex.search(line)
            cpl_rcv_match = sbc_cpl_rcv_regex.search(line)
            cpl_init_match = sbc_cpl_init_regex.search(line)
            cpl_snd_match = sbc_cpl_snd_regex.search(line)
            sbc_ice_cice_match = sbc_ice_cice_regex.search(line)
            if tot_match:
                total_time = float(tot_match.group(1))
            if cpl_rcv_match:
                rcv_percentge = float(cpl_rcv_match.group(1))
            if cpl_init_match:
                init_percentge = float(cpl_init_match.group(1))
            if cpl_snd_match:
                snd_percentge = float(cpl_snd_match.group(1))
            if sbc_ice_cice_match:
                cice_percentage = float(sbc_ice_cice_match.group(1))
                cice_measurement = True

    try:
        model_time = total_time * \
            ((100.0 - rcv_percentge - init_percentge - snd_percentge) * 0.01)
        coupling_time = total_time * \
            (rcv_percentge + init_percentge + snd_percentge) * 0.01
        put_time = total_time * snd_percentge * 0.01
    except NameError:
        sys.stderr.write('[FAIL] Unable to determine Oasis timings from'
                         ' the NEMO standard output\n')
        sys.exit(error.MISSING_CONTROLLER_FILE_ERROR)

    if cice_measurement:
        cice_time = total_time * cice_percentage * 0.01
    else:
        sys.stdout.write('[INFO] Unable to determine time in CICE for this'
                         ' configuration')
        cice_time = False

    return model_time, coupling_time, put_time, cice_time


def get_nemo_io(nemo_timing_output='timing.output'):
    '''
    Grab NEMO IO timing output. Takies an optional argument, the path to the
    NEMO timing.output file for NEMO/CICE. Returns the time spent in the
    restart file writing routines (not including file writing in XIOS)
    '''
    # Both put and get may not necessarily be in the timing.output file
    rstget_measurement = False
    rstput_measurement = False
    total_time_regex = re.compile(r"\s*Total\s*\|\s*(\d+.\d+)")
    # These regexes will pull out a percentage
    iom_rstget_regex = re.compile(r"\s*iom_rstget\s*\d+.\d+\s*(\d+.\d+)")
    iom_rstput_regex = re.compile(r"\s*iom_rstput\s*\d+.\d+\s*(\d+.\d+)")
    with common.open_text_file(nemo_timing_output, 'r') as nemo_timing_handle:
        for line in nemo_timing_handle.readlines():
            tot_match = total_time_regex.search(line)
            iom_rstget_match = iom_rstget_regex.search(line)
            iom_rstput_match = iom_rstput_regex.search(line)
            if tot_match:
                total_time = float(tot_match.group(1))
            if iom_rstget_match:
                iom_rstget_percentage = float(iom_rstget_match.group(1))
                rstget_measurement = True
            if iom_rstput_match:
                iom_rstput_percentage = float(iom_rstput_match.group(1))
                rstput_measurement = True
    restart_io_time = 0.0
    if rstget_measurement:
        rstget_io_time = total_time * iom_rstget_percentage * 0.01
        restart_io_time += rstget_io_time
    if rstput_measurement:
        rstput_io_time = total_time * iom_rstput_percentage * 0.01
        restart_io_time += rstput_io_time
    return restart_io_time
