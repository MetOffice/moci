#!/usr/bin/env python

'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2016 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    verify_metrics.py

DESCRIPTION
    Validate that the metrics are within some given norms to ensure that
    changes to the suite only produces understandable changes to performance
    indicators
'''

from __future__ import absolute_import
import os
import re
import sys


class Metric(object):
    ''' Class to contain a description and value for various metrics'''

    def __init__(self, label):
        '''Initialise the class with a description'''
        self.label = label
        self.val = None

    def add_val(self, value):
        '''Adder to add the value for the metric'''
        self.val = value


def _read_envar(varname):
    '''
    Load environment variable. Takes the variable name and returns its
    value.
    '''
    try:
        value = os.environ[varname]
    except KeyError:
        sys.stderr.write('Attempting to read environment variable %s.'
                         ' This is unavaliable\n' % varname)
        sys.exit()
    return value


def _gather_metrics(cpmip_output_file):
    '''
    Load the metrics. Takes an argument to the cpmip.output file. Returns
    a dictionary of metric name environment variable root with it's
    associated Metric object
    '''
    metrics = {'IO_COST_UM' : Metric('IO cost UM'),
               'IO_COST_NEMO' : Metric('IO_cost NEMO'),
               'DATA_VOLUME' : Metric('Data Volume'),
               'DATA_INTENSITY' : Metric('Data Intensity'),
               'CPMIP_ANALYSIS' : Metric('Load balancing metric'),
               'COMPLEXITY_UM' : Metric('UM complexity'),
               'COMPLEXITY_NEMO' : Metric('NEMO complexity'),
               'COMPLEXITY_CICE' : Metric('CICE complexity')}

    with open(cpmip_output_file) as f_h:
        for line in f_h.readlines():
            if 'CPMIP coupling metric' in line:
                metric = float(line.split(' ')[-1])
                metrics['CPMIP_ANALYSIS'].add_val(metric)
            if 'UM' and 'IO' in line:
                metric = float(re.search(r'(\d+)', line).group(0))
                metrics['IO_COST_UM'].add_val(metric)
            if 'NEMO' and 'IO' in line:
                metric = float(re.search(r'(\d+)', line).group(0))
                metrics['IO_COST_NEMO'].add_val(metric)
            if 'This cycle produces' in line:
                metric = float(re.search(r'(\d+.\d+)', line).group(0))
                metrics['DATA_VOLUME'].add_val(metric)
            if 'The data intensity metric' in line:
                metric = float(re.search(r'(\d+.\d+)', line).group(0))
                metrics['DATA_INTENSITY'].add_val(metric)
            if 'UM complexity' in line and 'Unable to calculate' not in line:
                metric = float(re.search(r'(\d+)', line).group(1))
                metrics['COMPLEXITY_UM'].add_val(metric)
            if 'NEMO complexity' in line:
                metric = float(re.search(r'(\d+)', line).group(1))
                metrics['COMPLEXITY_NEMO'].add_val(metric)
            if 'CICE complexity' in line:
                metric = float(re.search(r'(\d+)', line).group(1))
                metrics['COMPLEXITY_CICE'].add_val(metric)
    return metrics



def _compare(name, measured_val, reference_val, tolerance=0.1):
    '''
    Compare a metric. Takes a metric name measured value, reference value,
    and a tolerance to be applied +/- the reference value.
    Returns an error code of 0 if the test passes, and 1 if not
    '''
    min_accepted = reference_val - tolerance
    max_accepted = reference_val + tolerance
    if min_accepted <= measured_val <= max_accepted:
        return_code = 0
    else:
        error_msg = '\n[FAIL] Metric %s hasnt passed validation\n' \
            '  Measured value is %.4f\n' \
            '  Expected value is %.4f with tolerance of %.2f\n' \
            '    Should be in range [%.4f, %.4f]\n' % \
            (name, measured_val, reference_val, tolerance, \
                 min_accepted, max_accepted)
        sys.stderr.write(error_msg)
        return_code = 1
    return return_code

def perform_comparison(cpmip_file):
    '''
    Compare the metrics against the reference value and tolerances
    '''
    metrics = _gather_metrics(cpmip_file)
    number_metrics = 0
    number_failed = 0
    number_unavailable = 0
    msg_unavailable = ''
    for key, info in metrics.items():
        if info.val:
            expected_val = float(_read_envar('%s_EXPECTED' % key))
            tolerance = float(_read_envar('%s_TOL' % key))
            did_fail = _compare(info.label, info.val, expected_val,
                                tolerance)
            note = ['Passed', 'Failed - See STDERR for details'][did_fail]
            sys.stdout.write('[INFO] Testing %s metric: %s. Value is %.4f\n' %
                             (info.label, note, info.val))
            number_metrics += 1
            number_failed += did_fail
        else:
            msg_unavailable += '[INFO] %s metric not avaliable for this run\n' \
                % info.label
            number_unavailable += 1
    if number_unavailable:
        sys.stdout.write(msg_unavailable)
    sys.stdout.write('\n[INFO] %i/%i metric tests succeeded\n' %
                     (number_metrics-number_failed, number_metrics))
    if number_failed > 0:
        sys.exit(9)

if __name__ == '__main__':
    perform_comparison(sys.argv[1])
