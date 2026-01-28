#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2023-2026 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    cpmip_utils.py

DESCRIPTION
    Utility functions for the CPMIP controller
'''
import glob
import os
import re
import sys
import error
import common

def get_component_resolution(nlist_file, resolution_variables):
    '''
    Get the total componenet resolution nx x ny x nz from a given namelist
    file. The arguments are a namelist file, and a list of the resolution
    variables within that namelist. Returns a single value
    '''
    resolution = 1
    for res_var in resolution_variables:
        _, out = common.exec_subproc(['grep', res_var, nlist_file],
                                     verbose=True)
        try:
            i_res = int(re.search(r'(\d+)', out).group(0))
            resolution *= i_res
        except AttributeError:
            msg = '[WARN] Failed to find resolution %s in file %s.\n' % \
                  (res_var, nlist_file)
            sys.stdout.write(msg)

    return resolution

def get_glob_usage(glob_path, timeout=60):
    '''
    Get the total data from a list of files produced by a glob expression,
    using the du -c command. This command takes two arguments, a glob
    expression, and a timeout in seconds. This timeout is required as some
    filesystems (notably Lustre) can take a long time to respond to metadata
    queries
    '''
    size_k = -1.0
    filelist = glob.glob(glob_path)
    if filelist:
        du_command = ['du', '-c'] + filelist
        rcode, output = common.exec_subproc_timeout(du_command, timeout)
        if rcode == 0:
            size_k = float(output.split()[-2])
    else:
        sys.stderr.write('[WARN] Attepting to find the size of files described'
                         ' by glob expression %s. There are no files found'
                         % glob_path)
        size_k = 0.0
    return size_k

def get_datam_output_runonly(common_envar, cpmip_envar, timeout):
    '''
    Grab the data of interest within the datam directory. We only want the
    contents of NEMOhist and CICEhist, and the output files labelled with
    the runid. We must avoid any directories containing lrun/nrun/crun restart
    tests etc.
    '''
    total_usage = 0.0
    failed_components = []
    # um files
    if 'um' in common_envar['models']:
        um_path_gl = os.path.join(common_envar['DATAM'],
                                  '%s*' % common_envar['RUNID'])
        um_usage = get_glob_usage(um_path_gl, timeout)
        if um_usage >= 0.0:
            total_usage += um_usage
        else:
            failed_components.append('UM')

    # Jnr UM files
    if 'jnr' in common_envar['models']:
        jnr_path_gl = os.path.join(common_envar['DATAM'],
                                   '%s*' % cpmip_envar['RUNID_JNR'])
        jnr_usage = get_glob_usage(jnr_path_gl, timeout)
        if jnr_usage >= 0.0:
            total_usage += jnr_usage
        else:
            failed_components.append('Jnr')

    # nemo files
    if 'nemo' in common_envar['models']:
        nemo_path_gl = os.path.join(common_envar['DATAM'], 'NEMOhist', '*')
        nemo_usage = get_glob_usage(nemo_path_gl, timeout)
        if nemo_usage >= 0.0:
            total_usage += nemo_usage
        else:
            failed_components.append('NEMO')

    # cice file
    if 'cice' in common_envar['models']:
        cice_path_gl = os.path.join(common_envar['DATAM'], 'CICEhist', '*')
        cice_usage = get_glob_usage(cice_path_gl, timeout)
        if cice_usage >= 0.0:
            total_usage += cice_usage
        else:
            failed_components.append('CICE')

    if failed_components:
        for failed_component in failed_components:
            sys.stderr.write('[FAIL] Unable to determine the usage in DATAM'
                             ' for the %s component\n' %
                             failed_component)
        sys.exit(error.MISSING_MODEL_FILE_ERROR)
    else:
        return total_usage


def get_workdir_netcdf_output(timeout=60):
    '''
    Gather any netcdf output files written to the work directory
    '''
    output_files = [i_f for i_f in os.listdir('.') if \
                        i_f.split('.')[-1] == 'nc' and not os.path.islink(i_f)]
    size_k = -1.0
    du_command = ['du', '-c'] + output_files
    rcode, output = common.exec_subproc_timeout(du_command, timeout)
    if rcode == 0:
        size_k = float(output.split()[-2])
    return size_k

def tasklength_to_years(tasklength):
    '''
    Takes in a tasklength variable (string of form Y,M,D,h,m,s) and returns
    an integer value of the equivalent number of years for a 360 day
    calendar.
    '''
    length = [int(i) for i in tasklength.split(',')]
    to_years = (1, 1./30., 1./360., 1./(360.*24.),
                1./(360.*24.*60.), 1./(360.*24.*3600.))
    years = sum([x*y for x, y in zip(to_years, length)])
    return years

def seconds_to_days(time_secs):
    '''
    Takes in an integer value in units of seconds, and returns a floating point
    value of that time in days
    '''
    time_days = time_secs / (24.*3600.)
    return time_days

def get_jobfile_info(jobfile):
    '''
    Takes in a path to the jobfile and returns a dictionary containing
    all the directives set by PBS -l. This code is specific to the PBS
    load scheduler present on the Cray systems
    '''
    job_f = common.open_text_file(jobfile, 'r')
    pbs_l_dict = {}

    for line in job_f.readlines():
        # Grab key value pairs of the PBS variables. The pairs are delimited
        # by colons in the PBS directive. Times are also however defined using
        # colons (for example on hour is 01:00:00).
        if line.strip().startswith('#PBS -l'):
            for item in re.findall(r'(\w+)=(\w+(:\d+)*)', line):
                pbs_l_dict[item[0]] = item[1]
    job_f.close()
    return pbs_l_dict


def get_select_nodes(jobfile):
    '''
    Takes in a path to the jobfile and returns a dictionary containing
    the selected nodes for each component MPMD model
    '''
    pbs_line = ''
    model_nodes = []

    with common.open_text_file(jobfile, 'r') as job_handle:
        for line in job_handle.readlines():
            # Grab the line containing the -l select command
            if line[:14] == '#PBS -l select':
                pbs_line = line
                break
    #break up the line
    #First model
    first_model_nodes = re.match(r'#PBS -l select=(\d+)', pbs_line).group(1)
    model_nodes.append(int(first_model_nodes))
    # Any additional models
    split_pbs_line = pbs_line.split('+')[1:]
    for i_model in split_pbs_line:
        i_model_node = re.match(r'(\d+):', i_model).group(1)
        model_nodes.append(int(i_model_node))
    # Check for a coretype
    try:
        coretype = re.match(r'.+coretype=([a-z]+)', line).group(1)
    except AttributeError:
        # As chip not specified assume milan chip
        coretype = 'milan'
    return model_nodes, coretype


def increment_dump(datestr, resub, resub_units):
    '''
    Increment the dump date to end of cycle, so it can be found to
    calculate complexity
    '''
    year = int(datestr[:4])
    month = int(datestr[4:6])
    day = int(datestr[6:8])
    resub = int(resub)
    if 'm' in resub_units.lower():
        resub *= 30
    if resub >= 360:
        i_years = resub // 360
        resub = resub % 360
    else:
        i_years = 0
    if resub >= 30:
        i_months = resub // 30
        resub = resub % 30
    else:
        i_months = 0
    i_days = resub

    output_day = day + i_days
    if output_day > 30:
        output_day -= 30
        i_months += 1
    output_month = month + i_months
    if output_month > 12:
        output_month -= 12
        i_years += 12
    output_year = year + i_years
    return '%04d%02d%02d' % (output_year, output_month, output_day)
