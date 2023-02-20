#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2023 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    cpmip_controller.py

DESCRIPTION
    Controller for the generation of CPMIP metrics
'''

#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
from __future__ import division
import math
import sys
import common
import cpmip_metrics
import cpmip_nemo
import cpmip_um
import cpmip_utils
import cpmip_xios
import dr_env_lib.cpmip_def
import dr_env_lib.env_lib

CORES_PER_NODE = {'broadwell': 36,
                  'haswell' :32,
                  'exz' : 128}


def get_allocated_cpus(cpmip_envar):
    '''
    Grab the allocated CPUs for all component models
    '''
    models = ['UM', 'JNR', 'NEMO', 'XIOS']
    allocated_cpu = {}
    mpi_tasks = {}
    for model in models:
        preopt_string = 'ROSE_LAUNCHER_PREOPTS_%s' % model
        if cpmip_envar.contains(preopt_string):
            preopts = cpmip_envar[preopt_string]
            preopts = preopts.split(' ')
            # must have -n for total number MPI tasks
            n_mpi = float(preopts[preopts.index('-n') + 1])
            mpi_tasks[model] = int(n_mpi)
            try:
                strides = float(preopts[preopts.index('-d') + 1])
            except ValueError:
                strides = 1.0
            try:
                hyperthreads = float(preopts[preopts.index('-j') + 1])
            except ValueError:
                hyperthreads = 1.0
            cores = int((n_mpi * strides) / hyperthreads)
            allocated_cpu[model] = cores
        else:
            allocated_cpu[model] = 0
            mpi_tasks[model] = 0
    return allocated_cpu, mpi_tasks


def _update_namelists_for_metrics(common_env, cpmip_envar):
    '''
    Update the UM and NEMO namelists to ensure that the timers are set
    to be running
    '''
    # Update namelists for UM
    if 'um' in common_env['models']:
        nn_timing_val = \
            cpmip_um.update_input_for_metrics_um(cpmip_envar, 'SHARED',
                                                 'IOSCNTL')

    # Update namelists for Jnr
    if 'jnr' in common_env['models']:
        _ = cpmip_um.update_input_for_metrics_um(cpmip_envar, 'SHARED_JNR',
                                                 'IOSCNTL_JNR')

    # Update namelist for NEMO
    if 'nemo' in common_env['models']:
        # if NEMO is in the model list then um also has to be, as we need
        # the value for nn_timing_val
        assertion_string = 'To determine metrics for NEMO, we must be' \
                           ' running in a configuration that also includes' \
                           ' the UM'
        assert ('um' in common_env['models']), assertion_string
        cpmip_nemo.update_namelists_for_timing_nemo(cpmip_envar, nn_timing_val)


def _load_environment_variables(cpmip_envar):
    '''
    Load the CPMIP environment variables required for the model run
    into the cpmip_envar container
    '''
    cpmip_envar = dr_env_lib.env_lib.load_envar_from_definition(
        cpmip_envar, dr_env_lib.cpmip_def.CPMIP_ENVIRONMENT_VARS_INITIAL)

    # Remove models from the cpmip_var environment, as this will get
    # exported by link_drivers. This is here for correct triggering
    cpmip_envar.remove('models')

    return cpmip_envar


def _load_environment_variables_finalise(cpmip_envar):
    '''
    Load the CPMIP environment variables required for the model finalize
    into the cpmip_envar container
    '''
    cpmip_envar = dr_env_lib.env_lib.load_envar_from_definition(
        cpmip_envar, dr_env_lib.cpmip_def.CPMIP_ENVIRONMENT_VARS_FINAL)

    return cpmip_envar


def _setup_cpmip_controller(common_env):
    '''
    Setup the environment and any files required by the executable
    '''
    # Create the environment variable container
    cpmip_envar = dr_env_lib.env_lib.LoadEnvar()
    # Load the environment variables required
    cpmip_envar = _load_environment_variables(cpmip_envar)

    # Make sure we keep the standard out
    cpmip_envar['ATMOS_KEEP_MPP_STDOUT'] = 'true'

    # Modify namelists, so information is available to plot later
    _update_namelists_for_metrics(common_env, cpmip_envar)

    # Are we prerforming the data intensity or data cost calculations
    # Modify iodef.xml file so that timing files are produced
    if (cpmip_envar['DATA_INTENSITY'] in ('true', 'True') or \
        cpmip_envar['IO_COST'] in ('true', 'True')) and \
        'nemo' in common_env['models']:
        cpmip_xios.data_metrics_setup_nemo()

    if cpmip_envar['DATA_INTENSITY'] in ('true', 'True'):
        sys.stdout.write('[INFO] Calculating the data intensity metric.'
                         ' Whilst this will not affect the execution time'
                         ' of the model, it may increase time spent in the'
                         ' model drivers\n')
        # Get the intial data size for DATAM directory (for all model
        # components)
        cpmip_metrics.data_intensity_initial(common_env, cpmip_envar)


    return cpmip_envar


def _set_launcher_command(_):
    '''
    Setup launcher command
    '''
    launch_cmd = ''
    return launch_cmd


def _finalize_cpmip_controller(common_env):
    '''
    Finalize the CPMIP controller.
    '''
    secs_to_hours = 1./3600.
    # Create the environment variable container
    cpmip_envar = dr_env_lib.env_lib.LoadEnvar()

    # Load the environment variables required
    cpmip_envar = _load_environment_variables_finalise(cpmip_envar)

    cpus, mpi_tasks = get_allocated_cpus(cpmip_envar)
    # Processor resource for all components
    um_cpus = cpus['UM']
    jnr_cpus = cpus['JNR']
    nemo_cpus = cpus['NEMO']
    xios_cpus = cpus['XIOS']
    total_cpus = um_cpus + jnr_cpus + nemo_cpus + xios_cpus

    # Time resources for UM
    if 'um' in common_env['models']:
        um_time, um_coupling_time, um_put_time, um_pe0_stdout_file = \
            cpmip_um.time_resources_um(cpmip_envar,
                                       mpi_tasks['UM'], 'STDOUT_FILE')

    # Time resources for Jnr
    if 'jnr' in common_env['models']:
        jnr_time, jnr_coupling_time, jnr_put_time, jnr_pe0_stdout_file = \
            cpmip_um.time_resources_um(cpmip_envar, mpi_tasks['JNR'],
                                       'STDOUT_FILE_JNR')

    # NEMO time is integrated over all processors when returned from
    # get_nemo_info()
    if 'nemo' in common_env['models']:
        nemo_time, nemo_coupling_time, nemo_put_time, cice_time = \
            cpmip_nemo.get_nemo_info()
        nemo_time /= nemo_cpus
        nemo_coupling_time /= nemo_cpus
        nemo_put_time /= nemo_cpus
        if cice_time:
            cice_time /= nemo_cpus
    else:
        cice_time = False

    if cpmip_envar['COUPLED_PLATFORM'].lower() == 'exz':
        # Get the number of nodes from the -l PBS directives for each model.
        # These come in the same order they appear in the models environment
        # variable
        pbs_l_nodes = cpmip_utils.get_select_nodes(
            cpmip_envar['CYLC_TASK_LOG_ROOT'])
        plat_cores_per_node = CORES_PER_NODE['exz']
        number_nodes = sum(pbs_l_nodes)
        allocated_cpus = number_nodes * plat_cores_per_node
        allocated_um = 0
        allocated_jnr = 0
        allocated_nemo = 0
        allocated_xios = 0
        for i_model in common_env['models'].split():
            if i_model == 'cice':
                pass
            elif i_model == 'um':
                allocated_um = pbs_l_nodes.pop(0) * plat_cores_per_node
            elif i_model == 'jnr':
                allocated_jnr = pbs_l_nodes.pop(0) * plat_cores_per_node
            elif i_model == 'nemo':
                allocated_nemo = pbs_l_nodes.pop(0) * plat_cores_per_node
            elif i_model == 'xios':
                allocated_xios = pbs_l_nodes.pop(0) * plat_cores_per_node

    else:
        # Get the arguments from the -l PBS directive (for the XC40 systems)
        pbs_l_dict = cpmip_utils.get_jobfile_info(
            cpmip_envar['CYLC_TASK_LOG_ROOT'])

        # Determine the total number of CPUS ALLOCATED for the run. If the
        # coretype can not be determined we can not calculate this value
        # and so allocated_cpus will be set to zero. If we cant pick up a
        # coretype, override the allocated figures for the components to the
        # number of cpus used per component to allow the CPMIP coupling metric
        # to be calculated, albiet with a slightly reduced accuracy.
        number_nodes = int(pbs_l_dict['select'])
        if 'coretype' in pbs_l_dict.keys():
            plat_cores_per_node = CORES_PER_NODE[pbs_l_dict['coretype'].lower()]
            allocated_cpus = number_nodes * plat_cores_per_node
            allocated_um = int(math.ceil(
                um_cpus/float(plat_cores_per_node))) * plat_cores_per_node
            allocated_jnr = int(math.ceil(
                jnr_cpus/float(plat_cores_per_node))) * plat_cores_per_node
            allocated_nemo = int(math.ceil(
                nemo_cpus/float(plat_cores_per_node))) * plat_cores_per_node
            allocated_xios = int(math.ceil(
                xios_cpus/float(plat_cores_per_node))) *plat_cores_per_node
        elif int(cpmip_envar['PPN']) > 0:
            plat_cores_per_node = int(cpmip_envar['PPN'])
            sys.stdout.write('[INFO] plat_cores_per_node = %s\n' %
                             plat_cores_per_node)
            allocated_cpus = number_nodes * plat_cores_per_node
            allocated_um = int(math.ceil(
                um_cpus/float(plat_cores_per_node))) * plat_cores_per_node
            allocated_jnr = int(math.ceil(
                jnr_cpus/float(plat_cores_per_node))) * plat_cores_per_node
            allocated_nemo = int(math.ceil(
                nemo_cpus/float(plat_cores_per_node))) * plat_cores_per_node
            allocated_xios = int(math.ceil(
                    xios_cpus/float(plat_cores_per_node))) * plat_cores_per_node
        else:
            allocated_cpus = 0
            sys.stdout.write('[INFO] Can not determine coretype, unable to '
                             'calculate CHSY metric\n')
            allocated_um = um_cpus
            allocated_jnr = jnr_cpus
            allocated_nemo = nemo_cpus
            allocated_xios = xios_cpus


    # calculate the CPMIP coupling
    # metric. This provides a fractional value
    # of the resource wasted. We assume that we can encapuslate the resource
    # used by a model run in units of (number cores * time). Where possible
    # use allocated cores to ensure consistancy with the definition of the
    # metric
    total_resource = float(
        allocated_cpus * int(cpmip_envar['time_in_launcher']))
    if 'um' in common_env['models']:
        um_resource = float(allocated_um * um_time)
    else:
        um_resource = 0
    if 'jnr' in common_env['models']:
        jnr_resource = float(allocated_jnr * jnr_time)
    else:
        jnr_resource = 0
    if 'nemo' in common_env['models']:
        nemo_resource = float(allocated_nemo * nemo_time)
        # we assume that XIOS takes the whole length of the model run. If
        # XIOS is not used, or used in attatched mode xios_cpus will be 0,
        # so this line still makes sense
        xios_resource = float(allocated_xios *
                              int(cpmip_envar['time_in_launcher']))
    else:
        nemo_resource = 0
        xios_resource = 0

    coupling_metric = (total_resource - um_resource - jnr_resource
                       - nemo_resource - xios_resource) / total_resource

    # Run in years per day (as measured by the time spent in the launcher)
    years_run = cpmip_utils.tasklength_to_years(cpmip_envar['TASKLENGTH'])
    runtime_days = cpmip_utils.seconds_to_days(
        int(cpmip_envar['time_in_launcher']))
    years_per_day = years_run / runtime_days

    launcher_time_message \
        = 'Time in MPI Launcher: %s s\n' % cpmip_envar['time_in_launcher']
    if 'um' in common_env['models']:
        um_time_message = 'Time in UM model code: %i s\nTime in UM' \
            ' coupling code: %i s\n   Time in UM put code: %i s\n' % \
            ((um_time+0.5), (um_coupling_time+0.5), (um_put_time+0.5))
    if 'jnr' in common_env['models']:
        jnr_time_message = 'Time in Jnr model code: %i s\nTime in Jnr' \
            ' coupling code: %i s\n   Time in Jnr put code: %i s\n' % \
            ((jnr_time+0.5), (jnr_coupling_time+0.5), (jnr_put_time+0.5))
    if 'nemo' in common_env['models']:
        if cice_time:
            nemo_time_message = 'Time in NEMO model code: %i s\n' \
                '   Including %is in CICE\nTime in NEMO coupling code:' \
                '%i s\n   Time in NEMO put code: %i s\n' % \
                ((nemo_time+0.5), (cice_time+0.5), (nemo_coupling_time+0.5),
                 (nemo_put_time+0.5))
        else:
            nemo_time_message = 'Time in NEMO model code: %i s\nTime in' \
                ' NEMO coupling code: %i s\n   Time in NEMO put code: ' \
                '%i s\n' % ((nemo_time+0.5), (nemo_coupling_time+0.5),
                            (nemo_put_time+0.5))
    ypd_message = 'This equates to %.2f years per day run (SYPD)\n' % \
        years_per_day

    # Other metrics
    if allocated_cpus:
        chsy_message = cpmip_metrics.chsy_metric(
            allocated_cpus, total_cpus, years_run,
            int(cpmip_envar['time_in_launcher']) * secs_to_hours)
        cores_message = 'Cores per node: %s\n' % plat_cores_per_node
    else:
        chsy_message = ''
        cores_message = 'Cores per node: Unable to determine cores per node' \
            ' the CPMIP metric will be\ncalculated with USED cores rather' \
            ' than ALLOCATED cores, so will be slightly\ninconsistent\n'

    coupling_metric_message = 'The CPMIP coupling metric for this run is ' \
        '%.3f\n' % coupling_metric

    if cpmip_envar['IO_COST'] in ('true', 'True'):

        # Determine for the UM
        if 'um' in common_env['models']:
            um_io_time = cpmip_um.get_um_io(um_pe0_stdout_file)
            um_io_frac = float(um_io_time) / float(um_time)
            um_io_frac_mess = 'The UM spends %i s performing IO\n   This' \
                ' is a fraction of %.2f\n' % (um_io_time, um_io_frac)

        # Determine for Jnr
        if 'jnr' in common_env['models']:
            jnr_io_time = cpmip_um.get_um_io(jnr_pe0_stdout_file)
            jnr_io_frac = float(jnr_io_time) / float(jnr_time)
            jnr_io_frac_mess = 'Jnr spends %i s performing IO\n   This' \
                ' is a fraction of %.2f\n' % (jnr_io_time, jnr_io_frac)

        # Determine for NEMO
        if 'nemo' in common_env['models']:
            nemo_io_time = cpmip_nemo.get_nemo_io()
            nemo_io_time /= nemo_cpus
            nemo_io_frac = float(nemo_io_time) / float(nemo_time)
            nemo_io_frac_mess = 'NEMO spends %i s performing IO\n   This' \
                ' is a fraction of %.2f\n' % (nemo_io_time, nemo_io_frac)

        # Determine XIOS client
        if 'xios' in common_env['models']:
            xios_client_mean, xios_client_max \
                = cpmip_xios.measure_xios_client_times()
            xios_io_mess = 'XIOS spends on average %i s in each client, and' \
                ' a maxiumum time of %i s\n' % (int(xios_client_mean),
                                                int(xios_client_max))
    else:
        um_io_frac_mess = ''
        jnr_io_frac_mess = ''
        nemo_io_frac_mess = ''
        xios_io_mess = ''

    if cpmip_envar['DATA_INTENSITY'] in ('true', 'True'):
        core_hour_cycle = total_cpus * \
            float(int(cpmip_envar['time_in_launcher']) * secs_to_hours)
        data_produced, data_intensity = \
            cpmip_metrics.data_intensity_final(core_hour_cycle,
                                               common_env,
                                               cpmip_envar)
        if data_intensity > -1:
            data_intensity_msg = 'This cycle produces %.2f GiB of data.\n' \
                '  The data intensity metric is %.6f GiB per core hour\n' % \
                (data_produced, data_intensity)
        else:
            #The du operation timed out
            data_intensity_msg = 'Data intensity measurement unavailable' \
                ' owing to filesystem timeout\n'
    else:
        data_intensity_msg = ''


    if 'true' in cpmip_envar['COMPLEXITY'].lower():
        complexity_msg = cpmip_metrics.complexity_metric(common_env,
                                                         cpmip_envar)
    else:
        complexity_msg = ''
    jpsy_msg = cpmip_metrics.jpsy_metric(
        cpmip_envar['TOTAL_POWER_CONSUMPTION'],
        cpmip_envar['NODES_IN_HPC'], number_nodes,
        cpmip_envar['time_in_launcher'], years_run)



    # Produce a nice summary of the coupling metric and various information
    sys.stdout.write('\nSUMMARY FROM CPMIP CONTROLLER\n')
    sys.stdout.write('%s\n' % ('-'*80,))
    sys.stdout.write(cores_message)
    sys.stdout.write('%s\n' % ('-'*80,))
    sys.stdout.write(launcher_time_message)
    if 'um' in common_env['models']:
        sys.stdout.write(um_time_message)
    if 'jnr' in common_env['models']:
        sys.stdout.write(jnr_time_message)
    if 'nemo' in common_env['models']:
        sys.stdout.write(nemo_time_message)
    if xios_cpus:
        sys.stdout.write('It is assumed that XIOS takes the same time as '
                         'the time spent in the MPI launcher\n')
    sys.stdout.write(ypd_message)
    sys.stdout.write('\nResource for components in units of core hours\n')
    if 'um' in common_env['models']:
        sys.stdout.write('  UM Resource %.2f\n' % (um_resource *
                                                   secs_to_hours,))
    if 'jnr' in common_env['models']:
        sys.stdout.write('  Jnr Resource %.2f\n' % (jnr_resource *
                                                    secs_to_hours,))
    if 'nemo' in common_env['models']:
        sys.stdout.write('  NEMO Resource %.2f\n' %
                         (nemo_resource * secs_to_hours,))
    if xios_cpus:
        sys.stdout.write('  XIOS Resource %.2f\n' %
                         (xios_resource * secs_to_hours,))
    sys.stdout.write('\n%s' % coupling_metric_message)
    sys.stdout.write('\nThis implies that %.2f core hours are wasted in this'
                     ' run\n' %
                     (coupling_metric * total_resource * secs_to_hours,))
    sys.stdout.write(chsy_message)
    sys.stdout.write(complexity_msg)
    sys.stdout.write(jpsy_msg)
    sys.stdout.write(data_intensity_msg)
    if 'um' in common_env['models']:
        sys.stdout.write('\n%s' % um_io_frac_mess)
    if 'jnr' in common_env['models']:
        sys.stdout.write('\n%s' % jnr_io_frac_mess)
    if 'nemo' in common_env['models']:
        sys.stdout.write('\n%s' % nemo_io_frac_mess)
        sys.stdout.write('\n%s' % xios_io_mess)
        sys.stdout.write('%s\n' % ('-'*80,))

    # Write an output file containing runtime and processor number information
    # gleaned from the model output file to enable further analysis on this
    # data
    output_file = 'cpmip.output'
    with common.open_text_file(output_file, 'w') as cpmip_f:
        if allocated_cpus:
            cpmip_f.write('%s' % cores_message)
        cpmip_f.write('%s' % launcher_time_message)
        if 'um' in common_env['models']:
            cpmip_f.write('%s' % um_time_message)
        if 'jnr' in common_env['models']:
            cpmip_f.write('%s' % jnr_time_message)
        if 'nemo' in common_env['models']:
            cpmip_f.write('%s' % nemo_time_message)
        cpmip_f.write('%s%s%s' % (ypd_message, chsy_message,
                                  coupling_metric_message))
        if 'um' in common_env['models']:
            cpmip_f.write(um_io_frac_mess)
        if 'jnr' in common_env['models']:
            cpmip_f.write(jnr_io_frac_mess)
        if 'nemo' in common_env['models']:
            cpmip_f.write(nemo_io_frac_mess)
            cpmip_f.write(xios_io_mess)
        cpmip_f.write(data_intensity_msg)
        if 'um' in common_env['models']:
            cpmip_f.write('UM Processors: %i\n' % um_cpus)
            cpmip_f.write('UM Available Processors: %i\n' % allocated_um)
        if 'jnr' in common_env['models']:
            cpmip_f.write('Jnr Processors: %i\n' % jnr_cpus)
            cpmip_f.write('Jnr Available Processors: %i\n' % allocated_jnr)
        if 'nemo' in common_env['models']:
            cpmip_f.write('NEMO Processors: %i\n' % nemo_cpus)
            cpmip_f.write('NEMO Available Processors: %i\n' % allocated_nemo)
        if xios_cpus:
            cpmip_f.write('XIOS Processors: %i\n' % xios_cpus)
            cpmip_f.write('XIOS Available Processors: %i\n' % allocated_xios)
        cpmip_f.write(complexity_msg)
        cpmip_f.write(jpsy_msg)



def run_controller(mode, common_env):
    '''
    Run the CPMIP controller.
    '''
    if mode == 'run_controller':
        exe_envar = _setup_cpmip_controller(common_env)

        launch_cmd = _set_launcher_command(exe_envar)
    elif mode == 'finalize':
        _finalize_cpmip_controller(common_env)
        exe_envar = None
        launch_cmd = None

    return exe_envar, launch_cmd
