#!/usr/bin/env python
# *****************************COPYRIGHT*******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT*******************************
#
# Code Owner: Please refer to the UM file CodeOwners.txt
# This file belongs in section: Rose test suite

"""
 CODE OWNER
   Stephen Haddad

 NAME
   comp_norms

This script compares the norms output by a UM EndGame run
The key feature of script is that it looks through the timesteps
in each output file to find those with matching time stamps and
only compares those that match. This means if you have 2 runs
over different but overlapping time periods, the scripts compares
norms for periods that overlap and ignores timesteps that do not overlap.
"""

import re
import sys
import itertools
import argparse
import validate_common

class InvalidArgumentsError(Exception):
    """Error when incorrect command line arguments are supplied."""
    pass

class AtmosNormMismatchError(Exception):
    """
    Error triggered when matching timesteps in UM pe output
    have different norm values.
    """
    def __init__(self):
        Exception.__init__(self)
        self.file_name1 = 'unknown'
        self.file_name2 = 'unknown'

    def __str__(self):
        self.message = 'Values in the following PE output files do not '\
                       'match:\n file 1 = {file_name1}\n file 2 = {file_name2}'
        self.message = self.message.format(** self.__dict__)
        return self.message

def get_command_line_arguments():
    """
    filename1, filename2 = get_command_line_arguments()
    Process command line arguments
    """
    desc_msg = 'Compare 2 norm files from 2 UM atmosphere tasks.'
    parser = argparse.ArgumentParser(description=desc_msg)
    parser.add_argument('--filename1', dest='filename1')
    parser.add_argument('--filename2', dest='filename2')
    parser.add_argument('--list-errors',
                        dest='list_errors',
                        action='store_true',
                        help=validate_common.HELP_LIST_ERRORS)
    parser.add_argument('--stop-on-error',
                        dest='stop_on_error',
                        action='store_true',
                        help=validate_common.HELP_STOP_ON_ERROR)

    return parser.parse_args()

class Timestep(object):
    """
    Represent a timestep in a model pe_output file. Stores the timestamp and
    output norms for the timestep
    """
    def __init__(self, year, month, day, hour, minute, second, number):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        self.number = number
        self.norm_list = []

    def __str__(self):
        ret_val = '{year:04}/{month:02}/{day:02} '\
                  '{hour:02}:{minute:02}:{second:02}'.format(**self.__dict__)
        return ret_val

    def add_norm(self, norm1):
        """
        Add a norm value to the timestep object
        """
        self.norm_list += [norm1]

    def compare_times(self, other):
        """Compare the timestamps of 2 Norm objects."""
        if self.year != other.year:
            return False
        if self.month != other.month:
            return False
        if self.day != other.day:
            return False
        if self.hour != other.hour:
            return False
        if self.minute != other.minute:
            return False
        if self.second != other.second:
            return False
        return True

    def compare_norms(self, other):
        """Compare the norm values of 2 Norm objects."""
        if len(self.norm_list) != len(other.norm_list):
            return False
        for norm1, norm2 in itertools.izip(self.norm_list, other.norm_list):
            if norm1 != norm2:
                return False
        return True

    def max_norm_diff(self, other):
        """Find the max difference in the norm values of 2 Norm objects."""
        if len(self.norm_list) != len(other.norm_list):
            return False
        max_diff = 0.0
        for norm1, norm2 in itertools.izip(self.norm_list, other.norm_list):
            if abs(norm1.norm - norm2.norm) > max_diff:
                max_diff = abs(norm1.norm - norm2.norm)
        return max_diff
class Norm(object):
    """
    Represents a norm value output by an UM EndGame run.
    """
    # This tolerance is based on the 8 significant figures that are used for
    # norm  output by the UM in the PE output file
    TOLERANCE = 1.0e-8

    def __init__(self, outer, inner, iterations, norm):
        self.outer = outer
        self.inner = inner
        self.iterations = iterations
        self.norm = norm

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        if self.outer != other.outer:
            return False
        if self.inner != other.inner:
            return False
        if self.iterations != other.iterations:
            return False
        if abs(self.norm  - other.norm) > self.TOLERANCE:
            return False
        return True


UNKNOWN_SECTION = -1
TIMESTEP_SECTION = 1
NORM_SECTION = 2

# Regular expression used for looking for a string in each time step with
# the timestep data and time. The RE will match a string  of the form
# "Model time:   YYYY-MM-DD HH:MM:SS"
TIMESTEP_HEADER_STRING = \
    'Model time:[ ]+([0-9]{2,4}[-]{0,1}){3}[ ]+([0-9]{2,4}[:]{0,1}){3}'

# Regular expression used for looking for a string in each time step with
# the timestep number. The RE will match a string  of the form
# "Atm_Step: Timestep        2"
TIMESTEP_NUMBER_PATTERN = 'Atm_Step: Timestep[ ]+[0-9]+'

# RE string to find the first line of a section of output from each timestep
# containing solver norms
NORM_HEADER_STRING = 'Linear solve for Helmholtz problem'

# RE string to match a line containing a model norm. There are several lines
# associated with each timestep. This pattern will match strings of the form:
# "*    1     1       16     0.100000E+01     *"
# or more generically "* int int int float(scientific) *"
NORM_VALUE_STRING = '\\*[ ]*[0-9]+[ ]+[0-9]+[ ]+[0-9]+[ ]+.*\\*'

def process_timestep_string(line,
                            timestep_header_pattern,
                            timestep_number_pattern):
    """
    Process a line of a pe_output file containg a timestep header. The header
    line looks like:
    Atm_Step: Timestep        2   Model time:   1988-09-01 00:40:00

    Usage:
    current_timestep = process_timestep_string(line, timestep_header_pattern)

    Inputs/Outputs:
    line: string containing the line to be processed
    timestep_header_pattern: string with the pattern of the timestamp to be
                           matched
    current_timestep: A Timestep object extract from line input argument
    """
    # find the timestep date/time string in the line of text
    regex_output = re.finditer(timestep_header_pattern, line)
    timestep_str = ''.join([x1.group() for x1 in regex_output])
    # process the raw string into a list of numbers representing the date
    # and time
    ts_list1 = timestep_str[11:].lstrip().rstrip().split(' ')
    date_list1 = [int(x1) for x1 in ts_list1[0].split('-')]
    time_list1 = [int(x1) for x1 in ts_list1[1].split(':')]

    # find the timestep number string in the line
    regex_output2 = re.finditer(timestep_number_pattern, line)
    ts_num = -1
    try:
        #extract the timestep number from the string
        ts_num_matches = [x for x in regex_output2][0]
        ts_num = int(ts_num_matches.group()[18:].strip(' '))
    except Exception:
        # catching all exception, because whatever the problem, assign -1 to
        # the timestep in question, which will result in it being excluded
        # from comparisons
        ts_num = -1

    current_timestep = Timestep(year=date_list1[0],
                                month=date_list1[1],
                                day=date_list1[2],
                                hour=time_list1[0],
                                minute=time_list1[1],
                                second=time_list1[2],
                                number=ts_num)
    return current_timestep

def process_norm_string(line, norm_value_pattern):
    """
    Process a line of a pe_output file containing output model norms. The line
    of text containing the norms looks like:

        *    1     1       16     0.100000E+01     *
    Usage:
    new_norm = process_norm_string(line, norm_value_pattern)

    Inputs/Outputs:
    newNorm = process_norm_string(line, norm_value_pattern)
    line: string containing the line to processed
    norm_value_pattern: string containing the pattern to be matched
    newNorm: a norm object containing the extracted norm value
    """
    # find norm string in line of text
    regex_output = re.finditer(norm_value_pattern, line)
    norm_str_raw = ''.join([x1.group() for x1 in regex_output])
    norm_str_raw = norm_str_raw[1:-1].lstrip().rstrip()

    # extract the 4 values in the form string
    norm_set1 = [s1 for s1 in norm_str_raw.split(' ') if len(s1) > 0]
    outer_val = int(norm_set1[0])
    inner_val = int(norm_set1[1])
    iterations_val = int(norm_set1[2])
    norm_val = float(norm_set1[3])

    # create a norm object from the extracted values
    new_norm = Norm(outer=outer_val,
                    inner=inner_val,
                    iterations=iterations_val,
                    norm=norm_val)
    return new_norm



def extract_norms(filename):
    """
    Process a file at the specified location

    timesteplist = extract_norms(filename)
    filename: string containing path to the pe_output file
    timesteplist: A list of Timestep objects extracted from the file
    """

    timesteplist = []
    with open(filename) as result_file:
        status = UNKNOWN_SECTION
        current_timestep = None
        for line in result_file:
            if re.findall(TIMESTEP_HEADER_STRING, line):
                if current_timestep != None and \
                    len(current_timestep.norm_list) > 0:
                    # we exclude timesteps with no norms. This is usually
                    # the first timestep of a cycle, where no calculation
                    # happens and so there is no associated norm in the output
                    timesteplist += [current_timestep]
                current_timestep = \
                    process_timestep_string(line,
                                            TIMESTEP_HEADER_STRING,
                                            TIMESTEP_NUMBER_PATTERN)
                status = TIMESTEP_SECTION
            elif re.findall(NORM_HEADER_STRING, line) \
                and status == TIMESTEP_SECTION:
                status = NORM_SECTION
            elif re.findall(NORM_VALUE_STRING, line) \
                 and status == NORM_SECTION:
                new_norm = process_norm_string(line, NORM_VALUE_STRING)
                current_timestep.add_norm(new_norm)

    return timesteplist

def compare_timestep_norms(ts_list1, ts_list2):
    """
    Compare 2 lists of Timestep objects
    The function considers all possible pairs from the 2 lists. If a pair
    of Timestep objects have the same timestamp, the norms for that pair are
    compared and if they differ, the indices of the each Timestep object is
    stored. The function returns a list of Tuples containing 2 integers, which
    refer to a Timestep in the first and second input arguments that have
    equal timestamps and unequal norms

    misMatches = compare_timestep_norms(ts_list1, ts_list2)
    ts_list1: A list of Timestep objects
    tsList2: A list of Timestep objects
    misMatches: a list of Tuples containing 2 integers, which refer to a
                Timestep in the first and second input arguments that have
                equal timestamps and unequal norms
    """
    mismatches = []
    num_comps = 0
    iter1 = ((ix1, ts1, ix2, ts2) for ix1, ts1 in enumerate(ts_list1) \
                                  for ix2, ts2 in enumerate(ts_list2))
    max_error = 0.0
    max_error_ix1 = -1
    max_error_ix2 = -1
    for ix1, ts1, ix2, ts2 in iter1:
        # We are not comparing norms for timestep 0, because none are output
        # as no calculation has been done!
        if ts1.number > 0 and ts2.number > 0 and ts1.compare_times(ts2):
            num_comps += 1
            if not ts1.compare_norms(ts2):
                mismatches += [(ix1, ix2)]
                max_ts_diff = ts1.max_norm_diff(ts2)
                if max_ts_diff > max_error:
                    max_error = max_ts_diff
                    max_error_ix1 = ix1
                    max_error_ix2 = ix2
    return (mismatches,
            num_comps,
            max_error,
            max_error_ix1,
            max_error_ix2)

def compare_norm_files(filename1,
                       filename2,
                       stop_on_error,
                       list_errors):
    """
    Main function for comparing the norms for each matching timestep in
    2 UM PE output files"
    Usage:
    compare_norm_files(filename1, filename2)

    Inputs
    filename1: Path to the first output file
    filename2: Path to the first output file
    """
    timestep_list1 = extract_norms(filename1)
    timestep_list2 = extract_norms(filename2)

    print '{0} time steps found in input 1'.format(len(timestep_list1))
    print '{0} time steps found in input 2'.format(len(timestep_list2))

    print 'comparing UM norms with tolerance {0:g}'.format(Norm.TOLERANCE)
    (mismatches,
     num_comps,
     max_error,
     max_error_ix1,
     max_error_ix2) = compare_timestep_norms(timestep_list1,
                                             timestep_list2)
    return_value = 0
    msg1 = ''
    if num_comps == 0:
        msg1 += 'no timesteps have matching dates/times.\n'
    elif len(mismatches) > 0:
        msg1 += 'Compared {0} time steps present in both input '\
               'files.\n'.format(num_comps)

        max_err_msg = 'max difference in norms {0:g} at time step {1}'
        max_err_msg = max_err_msg.format(max_error,
                                         str(timestep_list1[max_error_ix1]))
        msg1 += max_err_msg + '\n'

        if list_errors:
            msg1 += 'The following timesteps have different norms:\n'
            for ix1, _ in mismatches:
                ts_msg = 'Model time: {0}\n'.format(str(timestep_list1[ix1]))
                msg1 += ts_msg + '\n'
            msg1 += '\n'
        else:
            msg1 += '{0} mismatches found\n'.format(len(mismatches))
        return_value = 1
        if stop_on_error:
            error1 = AtmosNormMismatchError()
            error1.file_name1 = filename1
            error1.file_name2 = filename2
            raise error1
    else:
        msg1 = 'All {0} matching timesteps have equal norms.'.format(num_comps)

    print msg1
    sys.stderr.write(msg1)
    # if we reach here, all matching timesteps  have equal norms
    # so the match is a success
    return return_value

def main():
    """
    Main function for com_norms.py script.
    """
    input_args = get_command_line_arguments()

    msg1 = 'comparing contents of atmosphere (UM) norm files:\n'
    msg1 += 'file 1: {0}\nfile 2: {1}\n'
    msg1 = msg1.format(input_args.filename1,
                       input_args.filename2)
    print msg1

    exit_code = compare_norm_files(**input_args.__dict__)
    if exit_code != 0:
        exit(exit_code)

if __name__ == '__main__':
    main()
