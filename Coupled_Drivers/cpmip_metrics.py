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
    cpmip_metrics.py

DESCRIPTION
    CPMIP metrics that require calculations to separate out from the top
    level controller
'''
import sys
import common
import cpmip_um
import cpmip_utils

# timeout for filesystem operations in seconds to avoid delays intoduced by
# (especially Lustre) filesystems
FS_OPERATION_TIMEOUT = 60

def data_intensity_initial(common_envar, cpmip_envar):
    '''
    Setup for the data intensity metric, getting intial directory sizes,
    and write to a placeholder file.
    '''
    size_k = cpmip_utils.get_datam_output_runonly(common_envar, cpmip_envar,
                                                  FS_OPERATION_TIMEOUT)
    with common.open_text_file('datam.size', 'w') as f_size:
        f_size.write(str(size_k))


def data_intensity_final(core_hour_cycle, common_envar, cpmip_envar):
    '''
    Calculate the data intensity metric. This is the increase in size of
    DATAM between the start and end of the coupled app, as well as the
    total size of the NEMO output files in the coupled work directory
    '''
    if 'um' in common_envar['models']:
        with common.open_text_file('datam.size', 'r') as f_size:
            for line in f_size.readlines():
                size_init = float(line)
        size_final = cpmip_utils.get_datam_output_runonly(common_envar,
                                                          cpmip_envar,
                                                          FS_OPERATION_TIMEOUT)
        datam_size = size_final - size_init
    else:
        datam_size = 0

    if 'nemo' in common_envar['models']:
        size_wrkdir = cpmip_utils.get_workdir_netcdf_output()
    else:
        size_wrkdir = 0

    data_produced_k = 0
    timeout = False
    if datam_size >= 0:
        data_produced_k += datam_size
    else:
        timeout = True
    if size_wrkdir >= 0:
        data_produced_k += size_wrkdir
    else:
        timeout = True

    if not timeout:
        data_produced_g = data_produced_k / (1024. * 1024.)
        data_intensity = data_produced_g / core_hour_cycle
    else:
        sys.stderr.write('[WARN] The du operation to determine the data volume'
                         ' has timed out. This metric will be ignored\n')
        data_produced_g = -1
        data_intensity = -1
    return data_produced_g, data_intensity


def jpsy_metric(total_power, total_hpc_nodes, number_nodes,
                launcher_time, years_run):
    '''
    Calculate the Joules per simulated year metric, and return an appropriate
    message to be written to stdout and the cpmip.out file. Takes arguments
    of total machine power (MW), total number of nodes, core hours per
    simulated year and the number of allocated nodes
    '''
    if total_power == '' or total_hpc_nodes == '':
        sys.stdout.write('[INFO] Unable to determine the JPSY metric\n')
        message = ''
    else:
        power_for_run_w = (float(total_power) / float(total_hpc_nodes)) * \
            (float(number_nodes) * 1000 * 1000)
        energy_for_run_joules = float(launcher_time) * power_for_run_w
        jpsy = energy_for_run_joules / years_run
        message = 'Energy cost for run %.2E Joules per simulated year\n' % \
            jpsy
    return message

def chsy_metric(allocated_cpus, run_cpus, years_run_cycle, cycle_runtime_hr):
    '''
    Core hours per simulated year metric. This is the product of the model
    runtime for 1 simulated year, and the number of cores allocated. Note
    that these are the allocated cores, which may be a greater number than
    the cores used when considering non fully populated nodes. Returns a
    string of the message for this metric to be written to stdout/output file
    '''

    cpus_used_percentage = (float(run_cpus) / float(allocated_cpus)) * 100.
    cpus_message = 'This run uses %.2f percent of the allocated CPUS ' \
        '(%i/%i)\n' % (cpus_used_percentage, run_cpus, allocated_cpus)

    total_corehours = float(allocated_cpus) * float(cycle_runtime_hr)
    corehours_per_year = total_corehours / float(years_run_cycle)
    chsy_message = 'Corehours per simulated year (CHSY): %.2f\n' % \
        corehours_per_year
    return '%s%s' % (cpus_message, chsy_message)


def complexity_metric(common_envar, cpmip_envar):
    '''
    Calculate the model complexity. Takes in the cpmip_envar object and
    returns a message containing the complexity and resolution of indivdual
    models, and the total complexity of the coupled configuration to be
    written to standard output and cpmip.output
    '''
    cycle_date = cpmip_envar['CYLC_TASK_CYCLE_POINT'].split('T')[0]
    msg = ''
    total_complexity = 0

    cycle_date = cpmip_utils.increment_dump(cycle_date, cpmip_envar['RESUB'],
                                            cpmip_envar['CYCLE'])
    if 'um' in common_envar['models']:
        msg, total_complexity = \
            cpmip_um.get_complexity_um('UM', common_envar['RUNID'],
                                       cpmip_envar['DATAM'], cycle_date,
                                       msg, total_complexity)

    if 'jnr' in common_envar['models']:
        msg, total_complexity = \
            cpmip_um.get_complexity_um('Jnr', cpmip_envar['RUNID_JNR'],
                                       cpmip_envar['DATAM'], cycle_date,
                                       msg, total_complexity)

    if 'nemo' in common_envar['models']:
        nemo_res = cpmip_utils.get_component_resolution(cpmip_envar['NEMO_NL'],
                                                        ('jpiglo', 'jpjglo',
                                                         'jpkdta'))
        size_k = cpmip_utils.get_glob_usage('%s/NEMOhist/*%s*' %
                                            (cpmip_envar['DATAM'], cycle_date))
        if size_k > 0.0:
            nemo_words = size_k * (1024./8)
            nemo_complexity = nemo_words / float(nemo_res)
            msg += 'NEMO complexity is %i, and total resolution %i\n' % \
                (nemo_complexity, nemo_res)
            total_complexity += nemo_complexity

    if 'cice' in common_envar['models']:
        cice_cycle_date = '%s-%s-%s' % (cycle_date[:4],
                                        cycle_date[4:6], cycle_date[6:])
        cice_res = int(cpmip_envar['CICE_COL']) * int(cpmip_envar['CICE_ROW'])
        size_k = cpmip_utils.get_glob_usage('%s/CICEhist/*%s*' %
                                            (cpmip_envar['DATAM'],
                                             cice_cycle_date))
        if size_k > 0.0:
            cice_words = size_k * (1024./8)
            cice_complexity = cice_words / float(cice_res)
            msg += 'CICE complexity is %i, and total resolution %i\n' % \
                (cice_complexity, cice_res)
            total_complexity += cice_complexity

    msg += 'Total model complexity is %i\n' % (total_complexity)
    return msg
