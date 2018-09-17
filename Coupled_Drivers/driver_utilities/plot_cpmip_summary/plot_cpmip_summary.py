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
    plot_cpmip_summary.py

DESCRIPTION
    Provide a load balance plot for a coupled model, reading in data provided by
    the CPMIP driver in cpmip.output file.
'''

#The from __future__ imports ensure compatibility between python2.7 and 3.x
from __future__ import absolute_import
import argparse
import re
import os
import sys
# To run the code on the HPC the TKAgg backend must be used. To ensure
# interactive display an X-window display must be used on non HPC systems
try:
    _ = os.environ['CYLC_TASK_CYCLE_POINT']
    import matplotlib
    matplotlib.use('Agg')
except KeyError:
    pass
import pylab
import matplotlib.patches as patches

def _read_data(datafile):
    '''
    Read the data from a cpmip.output file, and returns 3 dictionaries,
    one containing the time spent in aprun and the non coupling part of the
    component models, another containing the number of processors used in
    a component, and the third containing the time spent in the coupling
    routines of the component models.
    '''
    timing_data = {'APRUN': 0, 'NEMO': 0, 'UM': 0, 'CICE': 0}
    processors = {'UM': 0, 'XIOS': 0, 'NEMO': 0}
    coupling_data = {'UM': 0, 'NEMO': 0}
    if not os.path.isfile(datafile):
        sys.stderr.write('Can not find data file %s\n' % datafile)
        sys.exit(999)
    with open(datafile, 'r') as file_handle:
        for line in file_handle.readlines():
            match = re.search(r'\D*(\d*)\D*', line)
            if 'APRUN' in line:
                timing_data['APRUN'] = int(match.group(1))
            if 'CICE' in line:
                timing_data['CICE'] = int(match.group(1))
            if 'Time' in line and 'model code' in line:
                if 'UM' in line:
                    timing_data['UM'] = int(match.group(1))
                if 'NEMO' in line:
                    timing_data['NEMO'] = int(match.group(1))
            if 'Time' in line and 'coupling code' in line:
                if 'UM' in line:
                    coupling_data['UM'] = int(match.group(1))
                if 'NEMO' in line:
                    coupling_data['NEMO'] = int(match.group(1))
            if 'Processors' in line:
                if 'XIOS' in line:
                    processors['XIOS'] = int(match.group(1))
                if 'UM' in line:
                    processors['UM'] = int(match.group(1))
                if 'NEMO' in line:
                    processors['NEMO'] = int(match.group(1))
            if 'allocated CPUS' in line:
                allocated_match = re.search(r'\(\d+/(\d+)\)', line)
                allocated_processors = int(allocated_match.group(1))
                processors['allocated'] = allocated_processors
    return timing_data, coupling_data, processors


def plot_summary(model_time, coupling_time, nproc, display=False, fname=False,
                 graph_title=''):
    '''
    Takes in 3 dictionaries determined from the function _read_data(), the
    times, coupling times, and number of processors. If the coupling times
    dictionary contains zeros, the breakdown of the overheads into coupling
    timings and general overheads wont be done. There are 3 optional paramaters
    display (True/False), where if True the graph will be presented using
    pylab.show(), and if False will be written to file. The second is
    the filename to be written, if False a default filename will be used
    containing the cycle time when used as part of a suite. Both default to
    False. The final optional variable is the graph title to be used, this
    defaults to an empty string, and if not set, and environment variable
    CYLC_TASK_CYCLE_POINT not set, no title will be used, otherwise a standard
    title will be used when running as part of a cylc suite
    '''
    try:
        cycle_point = os.environ['CYLC_TASK_CYCLE_POINT']
    except KeyError:
        if not graph_title:
            sys.stdout.write('Environment variable CYLC_TASK_CYCLE_POINT not'
                             ' loaded. Using default title and names\n')
        cycle_point = ''

    _, axis_secs = pylab.subplots()
    #UM
    axis_secs.add_patch(patches.Rectangle((0, 0),
                                          nproc['UM'], model_time['UM'],
                                          color='green',
                                          label='UM model'))
    #NEMO
    axis_secs.add_patch(patches.Rectangle((nproc['UM'], 0),
                                          nproc['NEMO'], model_time['NEMO'],
                                          color='blue',
                                          label='NEMO model'))
    # CICE
    # Remeber the NEMO time above is inclusive of CICE
    if model_time['CICE']:
        axis_secs.add_patch(patches.Rectangle((nproc['UM'], 0),
                                              nproc['NEMO'], model_time['CICE'],
                                              color='0.75',
                                              label='CICE model'))

    #XIOS
    if nproc['XIOS']:
        axis_secs.add_patch(patches.Rectangle((nproc['NEMO'] + nproc['UM'],
                                               0),
                                              nproc['XIOS'],
                                              model_time['APRUN'],
                                              color='red',
                                              label='XIOS'))
    #Overheads
    if not coupling_time['UM'] or not coupling_time['NEMO']:
        overheads_label = 'Overheads (APRUN/Coupling)'
    else:
        overheads_label = 'Overheads (APRUN)'
    #Overheads UM
    axis_secs.add_patch(patches.Rectangle((0, model_time['UM']),
                                          nproc['UM'],
                                          model_time['APRUN'] - \
                                              model_time['UM'],
                                          color='yellow',
                                          label=overheads_label))
    #Overheads NEMO
    axis_secs.add_patch(patches.Rectangle((nproc['UM'], model_time['NEMO']),
                                          nproc['NEMO'],
                                          model_time['APRUN'] - \
                                              model_time['NEMO'],
                                          color='yellow'))

    #Superimpose the coupling times if avaliable
    if coupling_time['UM'] and coupling_time['NEMO']:
        #UM
        axis_secs.add_patch(patches.Rectangle((0, model_time['UM']),
                                              nproc['UM'],
                                              coupling_time['UM'],
                                              color='lightgreen',
                                              label='UM coupling'))
        axis_secs.add_patch(patches.Rectangle((nproc['UM'], model_time['NEMO']),
                                              nproc['NEMO'],
                                              coupling_time['NEMO'],
                                              color='lightblue',
                                              label='NEMO coupling'))

    #Plot the run envelope if appropriate
    component_nproc = nproc['UM'] + nproc['NEMO'] + nproc['XIOS']
    if component_nproc < nproc['allocated']:
        axis_secs.plot([nproc['allocated'], nproc['allocated']],
                       [0, model_time['APRUN']],
                       color='0')
        axis_secs.plot([component_nproc, nproc['allocated']],
                       [model_time['APRUN'], model_time['APRUN']],
                       color='0')
    
    pylab.legend(loc='best')
    pylab.xlim([0, 1.2*(component_nproc)])
    pylab.ylim([0, 1.2*model_time['APRUN']])
    pylab.xlabel('Processor number')
    pylab.ylabel('Time (s)')
    if graph_title:
        pylab.title(graph_title)
    elif cycle_point:
        title = 'Load balancing graph for cycle %s' % cycle_point
        pylab.title(title)

    if display:
        pylab.show()
    else:
        if not fname:
            #Create the filename
            fname = 'cpmip.plot.'
            if cycle_point:
                fname = '%s%s.' % (fname, cycle_point)
            fname = '%spng' % fname
        pylab.savefig(fname, format='png')


def run_interactive():
    '''
    Parse the arguments to allow the plots to be generated in an interactive
    mode from the command line
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--display-figure",
                        dest='displayfig',
                        help="Display the plot on screen without saving for" \
                            " debug purposes. DO NOT USE when running in a" \
                            " suite",
                        action="store_true")
    parser.add_argument("--input-file",
                        dest='inputfile',
                        help="Path to the cpmip.output file produced by the" \
                            " CPMIP controller. If not specified defaults to" \
                            " ./cpmip.output",
                        default='cpmip.output')
    parser.add_argument("--filename",
                        dest='plot_filename',
                        help="Filename to save the CPMIP load balancing plot." \
                            " If left blank and --display-figure not used" \
                            " defaults to a filename containing the cycle" \
                            " time if avaliable",
                        default='')
    parser.add_argument("--title",
                        dest='graph_title',
                        help="Title for the plot. If not specified and" \
                            " environment variable CYLC_TASK_CYCLE_POINT" \
                            " not set, no title will be used. If this" \
                            " environment variable is set (for running in" \
                            " suite mode) then a standard title will be" \
                            " used",
                        default='')
    args = parser.parse_args()

    times, coupling_times, nprocs = _read_data(args.inputfile)
    plot_summary(times, coupling_times, nprocs, args.displayfig,
                 args.plot_filename, args.graph_title)

if __name__ == '__main__':
    run_interactive()
