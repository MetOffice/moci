#!/usr/bin/env python
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
    cpmip_controller.py

DESCRIPTION
    Controller for the generation of CPMIP metrics
'''

#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
from __future__ import division
import math
import re
import sys
import os
import shutil
import time
import common
import error

try:
    # Mule is not part of the standard Python package
    import mule
    MULE_AVAIL = True
except ImportError:
    sys.stdout.write('[WARN] Mule utility is unavaliable, unable to calculate'
                     ' complexity for UM\n')
    MULE_AVAIL = False


CORES_PER_NODE_UKMO_XC40 = {'broadwell': 36,
                            'haswell': 32}


def _get_directory_usage(directory_path, timeout=60):
    '''
    Get the data used in a directory, using the du -s command. This
    command takes two arguments, the path to the directory and a timeout
    in seconds. This timeout is required as some filesystems (notably Lustre)
    can take a long time to respond to metadata queries.
    '''
    size_k = -1.0
    if os.path.isdir(directory_path):
        du_command = ['du', '-s', directory_path]
        rcode, output = common.exec_subproc_timeout(du_command, timeout)
        if rcode == 0:
            size_k = float(output.split()[0])
    else:
        sys.stderr.write('[WARN] Attempting to determine size of directory %s'
                         ' This directory doesnt exist\n' % directory_path)
    return size_k


def _get_workdir_netcdf_output(timeout=60):
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

def _measure_xios_client_times(timeout=120):
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
    wall_start = time.time()
    for i_f in files:
        rcode, out = common.exec_subproc(['grep', 'total time', i_f],
                                         verbose=False)
        if rcode == 0:
            meas_time = float(out.split()[-2])
            total_measured += 1
            total_time += meas_time
            if meas_time > max_time:
                max_time = meas_time
        #check if out timeout has been reached
        accum_wall = time.time() - wall_start
        if accum_wall > timeout:
            break
    sys.stdout.write('[INFO] Measured timings for (%s/%s) XIOS clients\n' %
                     (total_measured, total_files))
    mean_time = total_time / float(total_measured)
    return mean_time, max_time


def data_intensity_initial(common_envar):
    '''
    Setup for the data intensity metric, getting intial directory sizes,
    and write to a placeholder file. Also set up IODEF file to produce
    XIOS timing files
    '''
    size_k = _get_directory_usage(common_envar['DATAM'])
    with common.open_text_file('datam.size', 'w') as f_size:
        f_size.write(str(size_k))
    with open('iodef.xml', 'r') as f_in, \
            open('iodef_out.xml', 'w') as f_out:
        update = False
        for line in f_in.readlines():
            if update:
                if 'variable id="print_file"' in line:
                    f_out.write(line)
                    update = False
                else:
                    new_line = '\t  <variable id="print_file"           ' + \
                        '     type="bool">true</variable>\n'
                    f_out.write(new_line)
                    f_out.write(line)
                    update = False
            else:
                f_out.write(line)
                if 'variable id="using_server"' in line:
                    update = True
    shutil.move('iodef_out.xml', 'iodef.xml')

def data_intensity_final(core_hour_cycle, common_envar):
    '''
    Calculate the data intensity metric. This is the increase in size of
    DATAM between the start and end of the coupled app, as well as the
    total size of the NEMO output files in the coupled work directory
    '''
    with common.open_text_file('datam.size', 'r') as f_size:
        for line in f_size.readlines():
            size_init = float(line)
    size_final = _get_directory_usage(common_envar['DATAM'])
    size_wrkdir = _get_workdir_netcdf_output()
    if size_final > -1.0 and size_init > -1.0 and size_wrkdir > -1.0:
        data_produced_k = (size_final - size_init) + size_wrkdir
        data_produced_g = data_produced_k / (1024. * 1024.)
        data_intensity = data_produced_g / core_hour_cycle
    else:
        sys.stderr.write('[WARN] The du operation to determine the data volume'
                         ' has timed out. This metric will be ignored\n')
        data_produced_g = -1
        data_intensity = -1
    return data_produced_g, data_intensity

def get_allocated_cpus(cpmip_envar):
    '''
    Grab the allocated nproc for the UM XC40
    '''
    models = ['UM', 'NEMO', 'XIOS']
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


def jpsy_metric(total_power, total_hpc_nodes, number_nodes,
                aprun_time, years_run):
    '''
    Calculate the Joules per simulated year metric, and return an appropriate
    message to be written to stdout and the cpmip.out file. Takes arguments
    of total machine power (MW), total number of nodes, core hours per
    simulated year and the number of allocated nodes
    '''
    if total_power == '' or total_hpc_nodes == '':
        sys.stdout.write('[INFO] Unable to determine the JPSY metric')
        message = ''
    else:
        power_for_run_w = (float(total_power) / float(total_hpc_nodes)) * \
            (float(number_nodes) * 1000 * 1000)
        energy_for_run_joules = float(aprun_time) * power_for_run_w
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


def __get_jobfile_info(jobfile):
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


def __get_um_io(pe0_output):
    '''
    Grab the UM timing information for IO routines if avaliable. These
    routines are AS STASH, DUMPCTL, MEANCTL, IOS_Shutdown,
    IOS_stash_client_fini
    Note that not all these routines may be avaliable in a given
    Run
    '''
    get_times = False
    possible_routines = ['AS STASH', 'DUMPCTL', 'MEANCTL',
                         'IOS_Shutdown', 'IOS_stash_client_fini']
    present = []
    times = []
    with open(pe0_output, 'r') as f_pe0:
        for line in f_pe0:
            if 'MPP : Inclusive timer summary' in line:
                get_times = True
            if 'CPU TIMES (sorted by wallclock times)' in line:
                get_times = False
            if get_times:
                for routine in possible_routines:
                    routine_regex = re.compile(
                        r"\d+\s*%s\s*(\d+.\d+)" % routine)
                    routine_match = routine_regex.search(line)
                    if routine_match:
                        present.append(routine)
                        cpu_time = float(routine_match.group(1))
                        times.append(cpu_time)
    missing = set(possible_routines) - set(present)
    missing = list(missing)
    if len(missing) > 0:
        for missing_routine in missing:
            sys.stdout.write('[INFO] IO timings running, routine %s'
                             ' unavaliable in this configuration\n' %
                             (missing_routine,))
    total_io_times = sum(times)
    return total_io_times



def __get_um_info(pe0_output):
    '''
    Grab the UM output. Returns the UM CPU time (sans coupling), and the time
    spent in the UMs coupling routines
    '''
    get_times = False
    geto2a_regex = re.compile(r"\d+\s*oasis3_geto2a\s*(\d+.\d+)")
    puta2o_regex = re.compile(r"\d+\s*oasis3_puta2o\s*(\d+.\d+)")
    inita2o_regex = re.compile(r"\d+\s*oasis3_inita2o\s*(\d+.\d+)")
    um_shell_regex = re.compile(r"\d+\s*UM_SHELL\s*(\d+.\d+)")
    with open(pe0_output, 'r') as f_pe0:
        for line in f_pe0:
            if 'MPP : Non Inclusive timer summary' in line:
                get_times = True
            if 'CPU TIMES (sorted by wallclock times)' in line:
                get_times = False
            # Pull out the average times for the coupling routines
            if get_times:
                geto2a_match = geto2a_regex.search(line)
                puta2o_match = puta2o_regex.search(line)
                inita2o_match = inita2o_regex.search(line)
                um_shell_match = um_shell_regex.search(line)
                if geto2a_match:
                    geto2a_time = float(geto2a_match.group(1))
                if puta2o_match:
                    puta2o_time = float(puta2o_match.group(1))
                if inita2o_match:
                    inita2o_time = float(inita2o_match.group(1))
                if um_shell_match:
                    um_shell_time = float(um_shell_match.group(1))
    try:
        coupling_time = geto2a_time + puta2o_time + inita2o_time
        model_time = um_shell_time
    except NameError:
        sys.stderr.write('[FAIL] Unable to determine Oasis timings from'
                         ' the UM standard output\n')
        sys.exit(error.MISSING_CONTROLLER_FILE_ERROR)
    return model_time, coupling_time


def __get_nemo_io(nemo_timing_output='timing.output'):
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


def __get_nemo_info(nemo_timing_output='timing.output'):
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
            (100.0 - rcv_percentge - init_percentge - snd_percentge) * 0.01
        coupling_time = total_time * \
            (rcv_percentge + init_percentge + snd_percentge) * 0.01
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

    return model_time, coupling_time, cice_time


def __update_namelists_for_timing(cpmip_envar):
    '''
    Update the UM and NEMO namelists to ensure that the timers are set
    to be running
    '''
    mod_shared_nl = common.ModNamelist('SHARED')
    try:
        num_version = float(cpmip_envar['VN'])
    except ValueError:
        sys.stderr.write('Expecting a numerical value for UM Version in'
                         ' environment variable VN. Instead got %s\n' %
                         cpmip_envar['VN'])
        sys.exit(error.INVALID_EVAR_ERROR)
    # For versions of UM prior to 10.7 the oasis timers can not be run
    # independently from the general UM timers
    if num_version < 10.7:
        mod_shared_nl.var_val('ltimer', '.true.')
    else:
        mod_shared_nl.var_val('ltimer', '.false.')
    mod_shared_nl.var_val('l_oasis_timers', '.true.')

    #If required update the namelist for IO timing.
    if cpmip_envar['IO_COST'] in ('true', 'True'):
        mod_shared_nl.var_val('lstashdumptimer', '.true.')
        nn_timing_val = 2
    else:
        nn_timing_val = 1

    mod_shared_nl.replace()

    # Let the UM only write out on the first task (rank 0) to attempt to
    # avoid too much skewing of load balancing information. prnt_writers
    # takes integer values: 1 - all tasks, 2 - rank 0, 3 - rank 0 and head
    # IO servers
    mod_ioscntl_nl = common.ModNamelist('IOSCNTL')
    mod_ioscntl_nl.var_val('prnt_writers', 2)
    mod_ioscntl_nl.replace()

    mod_namelist_cfg = common.ModNamelist(cpmip_envar['NEMO_NL'])
    mod_namelist_cfg.var_val('nn_timing', nn_timing_val)
    mod_namelist_cfg.replace()


def _get_component_resolution(nlist_file, resolution_variables):
    '''
    Get the total componenet resolution nx x ny x nz from a given namelist
    file. The arguments are a namelist file, and a list of the resolution
    variables within that namelist. Returns a single value
    '''
    resolution = 1
    for res_var in resolution_variables:
        _, out = common.exec_subproc(['grep', res_var, nlist_file],
                                     verbose=True)
        i_res = int(re.search(r'(\d+)', out).group(0))
        resolution *= i_res
    return resolution


def __increment_dump(datestr, resub, resub_units):
    '''
    Increment the dump date to end of cycle, so it can be found to
    calculate complexity
    '''
    resub = int(resub)
    if 'm' in resub_units.lower():
        resub *= 30
    year = int(datestr[:4])
    month = int(datestr[4:6])
    day = int(datestr[6:])
    day += resub
    if day > 30:
        day = day - 30
        month += 1
    if month > 12:
        month = month - 12
        year += 1
    return '%04d%02d%02d' % (year, month, day)


def _get_complexity(common_envar, cpmip_envar):
    '''
    Calculate the model complexity. Takes in the cpmip_envar object and
    returns a message containing the complexity and resolution of indivdual
    models, and the total complexity of the coupled configuration to be
    written to standard output and cpmip.output
    '''
    cycle_date = cpmip_envar['CYLC_TASK_CYCLE_POINT'].split('T')[0]
    msg = ''
    total_complexity = 0.0

    cycle_date = __increment_dump(cycle_date, cpmip_envar['RESUB'],
                                  cpmip_envar['CYCLE'])
    if 'um' in cpmip_envar['models']:
        dump_name = '%sa.da%s_00' % (common_envar['RUNID'], cycle_date)
        dump_path = os.path.join(cpmip_envar['DATAM'], dump_name)
        # Get the fraction of fields within the model that are prognostic
        if MULE_AVAIL and os.path.isfile(dump_path):
            umfile = mule.UMFile.from_file(dump_path,
                                           remove_empty_lookups=True)
            # What number of our fields are prognostics?
            prog_fields = umfile.fixed_length_header.raw[153]
            # how many levels are in the model (p_levels)
            number_p_levels = umfile.integer_constants.raw[8]
            # what is the resolution of the model?
            um_res = umfile.integer_constants.raw[6] * \
                umfile.integer_constants.raw[7] * number_p_levels
            um_complexity = float(prog_fields) / float(number_p_levels)
            msg += 'The UM complexity is %i, and total resolution %i\n' % \
                (um_complexity, um_res)
            total_complexity += um_complexity
        else:
            msg += 'Unable to calculate UM complexity and UM resolution\n'

    if 'nemo' in cpmip_envar['models']:
        nemo_res = _get_component_resolution(cpmip_envar['NEMO_NL'],
                                             ('jpiglo', 'jpjglo', 'jpkdta'))
        rcode, out = common.__exec_subproc_true_shell( \
            'du -c %s/NEMOhist/*%s*' % (cpmip_envar['DATAM'], cycle_date),
            verbose=False)
        if rcode == 0:
            nemo_words = (int(out.split()[-2])) * (1024./8)
            nemo_complexity = nemo_words / float(nemo_res)
            msg += 'NEMO complexity is %i, and total resolution %i\n' % \
                (nemo_complexity, nemo_res)
            total_complexity += nemo_complexity

    if 'cice' in cpmip_envar['models']:
        cice_cycle_date = '%s-%s-%s' % (cycle_date[:4],
                                        cycle_date[4:6], cycle_date[6:])
        cice_res = int(cpmip_envar['CICE_COL']) * int(cpmip_envar['CICE_ROW'])
        rcode, out = common.__exec_subproc_true_shell( \
            'du -c %s/CICEhist/*%s*' % (cpmip_envar['DATAM'], cice_cycle_date),
            verbose=False)
        if rcode == 0:
            cice_words = (int(out.split()[-2])) * (1024./8)
            cice_complexity = cice_words / float(cice_res)
            msg += 'CICE complexity is %i, and total resolution %i\n' % \
                (cice_complexity, cice_res)
            total_complexity += cice_complexity

    msg += 'Total model complexity is %i\n' % (total_complexity)
    return msg


def _load_environment_variables(cpmip_envar):
    '''
    Load the CPMIP environment variables required for the model run
    into the cpmip_envar container
    '''
    if cpmip_envar.load_envar('VN') != 0:
        sys.stderr.write('[FAIL] Environment variable VN containing the '
                         'UM version is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    _ = cpmip_envar.load_envar('NEMO_NL', 'namelist_cfg')
    _ = cpmip_envar.load_envar('IO_COST', 'False')
    _ = cpmip_envar.load_envar('DATA_INTENSITY', 'False')

    return cpmip_envar


def _load_environment_variables_finalise(cpmip_envar):
    '''
    Load the CPMIP environment variables required for the model finalize
    into the cpmip_envar container
    '''
    _ = cpmip_envar.load_envar('NEMO_NL', 'namelist_cfg')

    _ = cpmip_envar.load_envar('TOTAL_POWER_CONSUMPTION', '')
    _ = cpmip_envar.load_envar('NODES_IN_HPC', '')

    _ = cpmip_envar.load_envar('COMPLEXITY', 'False')

    if cpmip_envar.load_envar('DATAM') != 0:
        sys.stderr.write('[FAIL] Environment variable DATAM is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)

    # Get the cyclepoint
    if cpmip_envar.load_envar('CYLC_TASK_CYCLE_POINT') != 0:
        sys.stderr.write('[FAIL] Environment variable CYLC_TASK_CYCLE_POINT'
                         '  is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)

    if cpmip_envar.load_envar('CYCLE') != 0:
        sys.stderr.write('[FAIL] Environment variable CYCLE is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)

    if cpmip_envar.load_envar('RESUB') != 0:
        sys.stderr.write('[FAIL] Environment variable RESUB is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)

    # Get the component models
    if cpmip_envar.load_envar('models') != 0:
        sys.stderr.write('[FAIL] Environment variable models containing a list'
                         ' of component models is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)

    # Get the number of processors the components run on
    # UM
    if cpmip_envar.load_envar('UM_ATM_NPROCX') != 0:
        sys.stderr.write('[FAIL] Environment variable UM_ATM_NPROCX containing '
                         'the number of UM processors in the X direction '
                         'is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    if cpmip_envar.load_envar('UM_ATM_NPROCY') != 0:
        sys.stderr.write('[FAIL] Environment variable UM_ATM_NPROCY containing '
                         'the number of UM processors in the Y direction '
                         'is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    _ = cpmip_envar.load_envar('FLUME_IOS_NPROC', '0')
    # NEMO
    if cpmip_envar.load_envar('NEMO_NPROC') != 0:
        sys.stderr.write('[FAIL] Environment variable NEMO_NPROC containing '
                         'the number of NEMO processors not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)
    # XIOS (If applicable)
    _ = cpmip_envar.load_envar('XIOS_NPROC', '0')

    # CICE (If applicable)
    _ = cpmip_envar.load_envar('CICE_ROW', '0')
    _ = cpmip_envar.load_envar('CICE_COL', '0')

    # Get the preopts for the various components
    if cpmip_envar.load_envar('ROSE_LAUNCHER_PREOPTS_UM') != 0:
        sys.stderr.write('[FAIL] Environment variable '
                         'ROSE_LAUNCHER_PREOPTS_UM is not set\n')

    if cpmip_envar.load_envar('ROSE_LAUNCHER_PREOPTS_NEMO') != 0:
        sys.stderr.write('[FAIL] Environment variable '
                         'ROSE_LAUNCHER_PREOPTS_NEMO is not set\n')

    if cpmip_envar['XIOS_NPROC'] != '0':
        if cpmip_envar.load_envar('ROSE_LAUNCHER_PREOPTS_XIOS') != 0:
            sys.stderr.write('[FAIL] Environment variable '
                             'ROSE_LAUNCHER_PREOPTS_XIOS is not set\n')

    # Get the time spent in aprun
    if cpmip_envar.load_envar('time_in_aprun') != 0:
        sys.stderr.write('[FAIL] Environment variable time_in_aprun '
                         'containing the time spent in the aprun command '
                         'not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)

    # Get the tasklength variable so we can work out years per day of
    # simulation performed
    if cpmip_envar.load_envar('TASKLENGTH') != 0:
        sys.stderr.write('[FAIL] Environment variable TASKLENGTH not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)

    # Get the UM stdout file
    if cpmip_envar.load_envar('STDOUT_FILE') != 0:
        sys.stderr.write('[FAIL] Environment variable STDOUT_FILE containing '
                         'the path to the UM standard out is not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)

    # Get the task jobfile
    if cpmip_envar.load_envar('CYLC_TASK_LOG_ROOT') != 0:
        sys.stderr.write('[FAIL] Environment variable CYLC_TASK_LOG_ROOT  is '
                         'not set\n')
        sys.exit(error.MISSING_EVAR_ERROR)

    # Are we calculating IO cost
    _ = cpmip_envar.load_envar('IO_COST', 'False')
    # Are we calculating data intensity
    _ = cpmip_envar.load_envar('DATA_INTENSITY', 'False')

    return cpmip_envar


def _setup_cpmip_controller(common_envar):
    '''
    Setup the environment and any files required by the executable
    '''
    # Create the environment variable container
    cpmip_envar = common.LoadEnvar()
    # Load the environment variables required
    cpmip_envar = _load_environment_variables(cpmip_envar)

    # Make sure we keep the standard out
    cpmip_envar['ATMOS_KEEP_MPP_STDOUT'] = 'true'

    __update_namelists_for_timing(cpmip_envar)

    # Are we prerforming the data intensity calculations
    if cpmip_envar['DATA_INTENSITY'] in ('true', 'True'):
        sys.stdout.write('[INFO] Calculating the data intensity metric.'
                         ' Whilst this will not affect the execution time'
                         ' of the model, it may increase time spent in the'
                         ' model drivers\n')
        data_intensity_initial(common_envar)

    return cpmip_envar


def _set_launcher_command(_):
    '''
    Setup launcher command
    '''
    launch_cmd = ''
    return launch_cmd


def _finalize_cpmip_controller(common_envar):
    '''
    Finalize the CPMIP controller.
    '''
    secs_to_hours = 1./3600.
    # Create the environment variable container
    cpmip_envar = common.LoadEnvar()
    # Load the environment variables required
    cpmip_envar = _load_environment_variables_finalise(cpmip_envar)

    cpus, mpi_tasks = get_allocated_cpus(cpmip_envar)
    # Processor resource for all components
    um_cpus = cpus['UM']
    nemo_cpus = cpus['NEMO']
    xios_cpus = cpus['XIOS']
    total_cpus = um_cpus + nemo_cpus + xios_cpus

    # Determine the name of the UM pe0 output file.
    pe0_suffix = '0'*(len(str(mpi_tasks['UM'] - 1)))
    um_pe0_stdout_file = '%s%s' % (cpmip_envar['STDOUT_FILE'],
                                   pe0_suffix)

    # Time resource for all components
    # UM time is for one processor
    um_time, um_coupling_time = __get_um_info(um_pe0_stdout_file)
    # NEMO time is integrated over all processors when returned from
    # __get_nemo_info()
    nemo_time, nemo_coupling_time, cice_time = __get_nemo_info()
    nemo_time /= nemo_cpus
    nemo_coupling_time /= nemo_cpus
    if cice_time:
        cice_time /= nemo_cpus
    # Get the arguments from the -l PBS directive
    pbs_l_dict = __get_jobfile_info(cpmip_envar['CYLC_TASK_LOG_ROOT'])

    # Determine the total number of CPUS ALLOCATED for the run. If the
    # coretype can not be determined we can not calculate this value
    # and so allocated_cpus will be set to zero. If we cant pick up a
    # coretype, override the allocated figures for the components to the
    # number of cpus used per component to allow the CPMIP coupling metric
    # to be calculated, albiet with a slightly reduced accuracy.
    number_nodes = int(pbs_l_dict['select'])
    plat_cores_per_node = \
        CORES_PER_NODE_UKMO_XC40[pbs_l_dict['coretype'].lower()]
    if 'coretype' in pbs_l_dict:
        allocated_cpus = number_nodes * plat_cores_per_node
        allocated_um = int(math.ceil(um_cpus/float(plat_cores_per_node))) \
            * plat_cores_per_node
        allocated_nemo = int(math.ceil(nemo_cpus/float(plat_cores_per_node))) \
            * plat_cores_per_node
        allocated_xios = int(math.ceil(xios_cpus/float(plat_cores_per_node))) \
            * plat_cores_per_node
    else:
        allocated_cpus = 0
        sys.stdout.write('[INFO] Can not determine coretype, unable to '
                         'calculate CHSY metric\n')
        allocated_um = um_cpus
        allocated_nemo = nemo_cpus
        allocated_xios = xios_cpus

    # calculate the CPMIP coupling
    # metric. This provides a fractional value
    # of the resource wasted. We assume that we can encapuslate the resource
    # used by a model run in units of (number cores * time). Where possible
    # use allocated cores to ensure consistancy with the definition of the
    # metric
    total_resource = float(allocated_cpus * int(cpmip_envar['time_in_aprun']))
    um_resource = float(allocated_um * um_time)
    nemo_resource = float(allocated_nemo * nemo_time)
    # we assume that XIOS takes the whole length of the model run. If XIOS
    # is not used, or used in attatched mode xios_cpus will be 0, so this
    # line still makes sense
    xios_resource = float(allocated_xios * int(cpmip_envar['time_in_aprun']))

    coupling_metric = (total_resource - um_resource - nemo_resource
                       - xios_resource) / total_resource

    # Run in years per day (as measured by APRUN)
    years_run = tasklength_to_years(cpmip_envar['TASKLENGTH'])
    runtime_days = seconds_to_days(int(cpmip_envar['time_in_aprun']))
    years_per_day = years_run / runtime_days

    aprun_time_message = 'Time in APRUN: %s s\n' % cpmip_envar['time_in_aprun']
    um_time_message = 'Time in UM model code: %i s\nTime in UM coupling' \
        ' code: %i s\n' % (um_time, um_coupling_time)
    if cice_time:
        nemo_time_message = 'Time in NEMO model code: %i s\n   Including' \
            ' %is in CICE\nTime in NEMO coupling code: %i s\n' % \
            (nemo_time, cice_time, nemo_coupling_time)
    else:
        nemo_time_message = 'Time in NEMO model code: %i s\nTime in' \
            ' NEMO coupling code: %i s\n' % \
            (nemo_time, nemo_coupling_time)
    ypd_message = 'This equates to %.2f years per day run (SYPD)\n' % \
        years_per_day

    # Other metrics
    if allocated_cpus:
        chsy_message = chsy_metric(allocated_cpus, total_cpus, years_run, \
                                       int(cpmip_envar['time_in_aprun']) * \
                                       secs_to_hours)
        cores_message = 'Cores per node: %s\n' % plat_cores_per_node
    else:
        chsy_message = ''
        cores_message = 'Cores per node: Unable to determine cores per node' \
            ' the CPMIP metric will be\ncalculated with USED cores rather' \
            ' than ALLOCATED cores, so will be slightly\ninconsistent\n'

    coupling_metric_message = 'The CPMIP coupling metric for this run is ' \
        '%.3f\n' % coupling_metric

    if cpmip_envar['IO_COST'] in ('true', 'True'):
        # determine for the UM
        um_io_time = __get_um_io(um_pe0_stdout_file)
        um_io_frac = float(um_io_time) / float(um_time)
        um_io_frac_mess = 'The UM spends %i s performing IO\n   This' \
            ' is a fraction of %.2f\n' % (um_io_time, um_io_frac)
        # determine for NEMO
        nemo_io_time = __get_nemo_io()
        nemo_io_time /= nemo_cpus
        nemo_io_frac = float(nemo_io_time) / float(nemo_time)
        nemo_io_frac_mess = 'NEMO spends %i s performing IO\n   This' \
            ' is a fraction of %.2f\n' % (nemo_io_time, nemo_io_frac)
        # determine XIOS client
        xios_client_mean, xios_client_max = _measure_xios_client_times()
        xios_io_mess = 'XIOS spends on average %i s in each client, and' \
            ' a maxiumum time of %i s\n' % (xios_client_mean,
                                            xios_client_max)
    else:
        um_io_frac_mess = ''
        nemo_io_frac_mess = ''
        xios_io_mess = ''

    if cpmip_envar['DATA_INTENSITY'] in ('true', 'True'):
        core_hour_cycle = total_cpus * \
            float(int(cpmip_envar['time_in_aprun']) * secs_to_hours)
        data_produced, data_intensity = \
            data_intensity_final(core_hour_cycle, common_envar)
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
        complexity_msg = _get_complexity(common_envar, cpmip_envar)
    else:
        complexity_msg = ''
    jpsy_msg = jpsy_metric(cpmip_envar['TOTAL_POWER_CONSUMPTION'],
                           cpmip_envar['NODES_IN_HPC'], number_nodes,
                           cpmip_envar['time_in_aprun'], years_run)



    # Produce a nice summary of the coupling metric and various information
    sys.stdout.write('\nSUMMARY FROM CPMIP CONTROLLER\n')
    sys.stdout.write('%s\n' % ('-'*80,))
    sys.stdout.write(cores_message)
    sys.stdout.write('%s\n' % ('-'*80,))
    sys.stdout.write(aprun_time_message)
    sys.stdout.write(um_time_message)
    sys.stdout.write(nemo_time_message)
    if xios_cpus:
        sys.stdout.write('It is assumed that XIOS takes the same time as '
                         'APRUN\n')
    sys.stdout.write(ypd_message)
    sys.stdout.write('\nResource for components in units of core hours\n')
    sys.stdout.write('  UM Resource %.2f\n' % (um_resource * secs_to_hours,))
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
    sys.stdout.write('\n%s' % um_io_frac_mess)
    sys.stdout.write('\n%s' % nemo_io_frac_mess)
    sys.stdout.write('\n%s' % xios_io_mess)
    sys.stdout.write('%s\n' % ('-'*80,))

    # Write an output file containing runtime and processor number information
    # gleaned from the model output file to enable further analysis on this
    # data that can not be performed by the drivers for reasons of performance
    # (MOM node restrictiions in the case of the UKMO Cray XC40
    output_file = 'cpmip.output'
    with common.open_text_file(output_file, 'w') as cpmip_f:
        if allocated_cpus:
            cpmip_f.write('%s' % cores_message)
        cpmip_f.write('%s%s%s%s%s%s' % (aprun_time_message, um_time_message,
                                        nemo_time_message, ypd_message,
                                        chsy_message, coupling_metric_message))
        cpmip_f.write(um_io_frac_mess)
        cpmip_f.write(nemo_io_frac_mess)
        cpmip_f.write(xios_io_mess)
        cpmip_f.write(data_intensity_msg)
        cpmip_f.write('UM Processors: %i\n' % um_cpus)
        cpmip_f.write('NEMO Processors: %i\n' % nemo_cpus)
        if xios_cpus:
            cpmip_f.write('XIOS Processors: %i\n' % xios_cpus)
        cpmip_f.write(complexity_msg)
        cpmip_f.write(jpsy_msg)



def run_controller(mode, common_envar):
    '''
    Run the CPMIP controller.
    '''
    if mode == 'run_controller':
        exe_envar = _setup_cpmip_controller(common_envar)

        launch_cmd = _set_launcher_command(exe_envar)
    elif mode == 'finalize':
        _finalize_cpmip_controller(common_envar)
        exe_envar = None
        launch_cmd = None

    return exe_envar, launch_cmd
