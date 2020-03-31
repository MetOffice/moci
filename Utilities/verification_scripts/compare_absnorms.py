#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2020 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************

NAME
    compare_absnorms.py

DESCRIPTION
   Compare absolute norms from UM output
'''
import sys
import os
import re

class Timestep(object):
    '''
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Class to hold timestep attributes
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    '''
    def __init__(self, timestamp):
        self.timestamp = timestamp
        self.final_norm = None
        self.initial_norm = None
        self.iterations = None

    def add_norm(self, iterations, error):
        '''
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        Add either initial or, if initial exists,  final absolute norm
        with number of iterations
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        '''
        if self.initial_norm:
            self.final_norm = float(error)
        else:
            self.initial_norm = float(error)
        self.iterations = int(iterations)

    def get_value(self, attribute):
        '''
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        Return the value of the requested attribute
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        '''
        return getattr(self, attribute)


def generate_timestep(filename):
    '''
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Generator function for extracting norms for each timestep
    Arguments:
      filename <type str> File name including full path
    Yield:
      <type Timestep>
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    '''
    if not os.path.isfile(filename):
        raise SystemExit('[FAIL] File does not exist: {}'.format(filename))

    timestamp_regex = re.compile(
        r'Atm_Step: Timestep.*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
        )
    helmholtz_regex = re.compile(
        r'\*.*Linear solve for Helmholtz problem.*\*'
        )
    norms_regex = re.compile(r'\*\s+\d+\s+\d+\s+(\d+)\s+(\S+)\s+\*')

    with open(filename, 'r') as fhandle:
        nextstep = None
        num_calls = 0
        for line in fhandle.readlines():
            atmstep = timestamp_regex.search(line)
            if atmstep:
                nextstep = Timestep(atmstep.group(1))
            elif helmholtz_regex.search(line):
                num_calls += 1
            elif num_calls > 1:
                try:
                    iterations, error = norms_regex.search(line).groups()
                    nextstep.add_norm(iterations, error)
                except AttributeError:
                    pass
            try:
                if nextstep.final_norm is not None:
                    yield nextstep
                    nextstep = None
                    num_calls = 0
            except AttributeError:
                pass


def create_timesteps(file_path):
    '''
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Input:
        file_path <type str> -
            Full path to UM output file fort6.pe000 or fort6.stdout
    Return:
        <type dict {model data time: <type Timestep>}> }> -
            Dictionary of timesteps with associated norms
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    '''
    entries = {}
    for timestep in generate_timestep(file_path):
        entries[timestep.timestamp] = timestep

    return entries


def compare_timesteps(tsteps1, tsteps2):
    '''
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Input:
        tsteps1 <type dict: {timestamp: Timestep()}> -
                contains KGO output norms
        tsteps2 <type dict: {timestamp: Timestep()}> -
                contains norms to be compared

    Returns:
        msg <type str> - resulting message
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    '''
    count_compare = 0
    return_code = -1
    diffs = []

    if tsteps1 == {} or tsteps2 == {}:
        msg = '[ERROR] Norms data not found\n'
    else:
        for timestamp in tsteps2:
            if timestamp in tsteps1:
                count_compare += 1
                ts1 = tsteps1[timestamp]
                ts2 = tsteps2[timestamp]
                for attribute in ['initial_norm', 'final_norm', 'iterations']:
                    if ts1.get_value(attribute) != ts2.get_value(attribute):
                        diffs.append(timestamp)
                        break

        if diffs:
            msg = '[ERROR] {} differences in norms at model data times:\n{}\n'.\
                  format(len(diffs), '\n\t'.join(diffs))
        else:
            if count_compare == len(tsteps2):
                msg = '[ OK ] All {} timesteps checked and norms are OK\n'.\
                    format(count_compare)
                return_code = 0
            elif count_compare == 0:
                msg = '[ERROR] No matching timesteps between KGO and ' + \
                      'comparison file\n'
            elif count_compare < len(tsteps2):
                msg = '[ERROR] {} timestep norms not found in KGO file\n'.\
                    format(len(tsteps2) - count_compare)

    return return_code, msg


def main():
    ''' Main function for comp_absnorms.py '''
    if len(sys.argv) < 3:
        msg = 'Missing arguments.  Usage: \n\t' + \
              'python comp_absnorms.py <KGOFILE> <FILE2>\n'
        sys.stderr.write(msg)
        sys.exit(2)

    # Initialisation
    # File A - KGO, File B - pe_output with norms
    kgo_file = sys.argv[1]
    compare_file = sys.argv[2]

    return_code, output = compare_timesteps(create_timesteps(kgo_file),
                                            create_timesteps(compare_file))
    sys.stdout.write(output)
    sys.exit(return_code)


if __name__ == '__main__':
    main()
