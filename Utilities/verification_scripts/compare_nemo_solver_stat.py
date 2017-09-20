    #!/usr/bin/env python2.7
#
#*****************************COPYRIGHT******************************
#(C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
#*****************************COPYRIGHT******************************
"""
 CODE OWNER
   Stephen Haddad

 NAME
   compare_nemo_solver_stat.py

 Implements function to compare 2 NEMO solver.stat files
"""
import re

import test_common

class NemoTimestep(object):
    """
    Container for the values relevant to each NEMO timestep read in.
    """
    COMP_TOLERANCE = 1e-8
    REGEX_TSN = r'it:\s+\d+'
    REGEX_ITER = r'iter:\s+\d+'
    REGEX_B = r'b:\s-?\d+\.\d+E[-+]\d+'
    REGEX_R = r'r:\s-?\d+\.\d+E[-+]\d+'

    def __init__(self, text_line1, timestep_num_offset):
        """
        Constructor for NemoTimestep object.

        obj1 = NemoTimestep(text_line1, timestep_num_offset)

        Arguments:
        text_line1 - line of text from solver file to parse
        timestep_num_offset - offset to add to timestep number. This is for
                              comparing runs with different timestep numbers
                              for the same model time.
        """
        tsn_match = re.search(NemoTimestep.REGEX_TSN, text_line1)
        self.timestep_num = \
            int(text_line1[tsn_match.start():tsn_match.end()].split(':')[1])
        self.timestep_num += timestep_num_offset

        numit_match = re.search(NemoTimestep.REGEX_ITER, text_line1)
        self.num_iterations = \
            int(text_line1[numit_match.start():numit_match.end()].split(':')[1])

        b_match = re.search(NemoTimestep.REGEX_B, text_line1)
        self.b_value = \
            float(text_line1[b_match.start():b_match.end()].split(':')[1])

        offset1 = numit_match.end()
        r_match = re.search(NemoTimestep.REGEX_R, text_line1[offset1:])
        r_str = text_line1[offset1+r_match.start():offset1+r_match.end()]
        self.r_value = float(r_str.split(':')[1])

    def __str__(self):
        """
        Return human readable string description of timestep
        """
        return_str = '''
Timestep: {timestep_num}
No. of iterations: {num_iterations}
b={b_value}
r={r_value}
'''.format(**self.__dict__)
        return return_str

    def __eq__(self, other):

        if abs(self.b_value - other.b_value) > NemoTimestep.COMP_TOLERANCE:
            return False
        elif abs(self.r_value - other.r_value) > NemoTimestep.COMP_TOLERANCE:
            return False
        return True

    def __ne__(self, other):
        return not self == other

    def get_diffs(self, other):
        """
        Get diff values for the 2 norms available at each timestep
        """
        diff_b = abs(self.b_value - other.b_value)
        diff_r = abs(self.r_value - other.r_value)
        return diff_b, diff_r


def parse_solver_stat_file(path1, offset):
    """
    Parse a NEMO solver.stat file

    Inputs:
    path1 - Path to NEMO solver.stat file
    offset - Offset to add to timestep number is solver, for later comparison
             purposes. See compare_solver_stat_files() for more details.
    Outputs:
    timestep_list - list of NemoTimestep objects
    """
    timestep_list = []
    with open(path1) as solver_file:
        for line1 in solver_file:
            timestep_list += [NemoTimestep(line1, offset)]
    return timestep_list

def compare_timestep_result_lists(timestep_list1,
                                  timestep_list2,
                                  stop_on_error):
    """
    Inputs:
    timestep_list1 - List of NEMO timestep objects
    timestep_list2 - List of NEMO timestep objects
    stop_on_error - Stop comparing timesteps when an error is found.

    Return values:
    num_comps - Number of matching timesteps compared
    mismatches - Number of mismatches found

    Errors:
    NemoSolverStatMismatchError - raised if an error is found and
                                  stop_on_error is true
    """
    num_comps = 0
    mismatches = []
    #create generator to iterate through all timestep combinations
    iter1 = ((ts1, ts2) for ts1 in timestep_list1 for ts2 in timestep_list2)

    max_err_b = 0.0
    max_err_r = 0.0
    for (ts1, ts2) in iter1:
        if ts1.timestep_num == ts2.timestep_num:
            num_comps += 1
            if ts1 != ts2:
                if stop_on_error:
                    error1 = NemoSolverStatMismatchError()
                    raise error1
                mismatches += [ts1.timestep_num]
                diff_b, diff_r = ts1.get_diffs(ts2)
                if diff_b > max_err_b:
                    max_err_b = diff_b
                if diff_r > max_err_r:
                    max_err_r = diff_r

    return num_comps, mismatches, max_err_b, max_err_r

class NemoSolverStatMismatchError(Exception):
    """
    Error triggered when matching timesteps in solver.stat files
    have differing b or r values.
    """
    def __init__(self):
        Exception.__init__(self)
        self.file_name1 = 'unknown'
        self.file_name2 = 'unknown'

    def __str__(self):
        self.message = 'Value in the following solver.stat files do not '\
                       'match:\n file 1 = {file_name1}\n file 2 = {file_name2}'
        self.message = self.message.format(** self.__dict__)
        return self.message

def compare_solver_stat_files(nemo_solver_file1,
                              nemo_solver_file2,
                              list_errors,
                              stop_on_error,
                              nemo_solver_file2_offset,
                              io_manager):
    """
    Compare to NEMO solver.stat files, as given by nemo_solver_file1
    and nemo_solver_file2.

    Inputs:
    nemo_solver_file1 - Path to first solver.stat
    nemo_solver_file2 - Path to second solver.stat
    list_errors - List the timesteps where differences between the files are
                  found.
    stop_on_error - Stop on finding the first error
    nemo_solver_file2_offset - Offset the timestep number in the second
                               solver.stat file by the value in this parameter.
                               This is  to take account of the fact that the
                               same point in model time may have different
                               timestep numbers in different run, possibly
                               because the run has been restarted as an NRUN,
                               or because one run has more timesteps per day.

    Return value:
    ret_val - 0 if no errors, non-zero if errors found
    """
    if not io_manager:
        io_manager = test_common.TestIO()

    timestep_list1 = parse_solver_stat_file(nemo_solver_file1, 0)
    timestep_list2 = parse_solver_stat_file(nemo_solver_file2,
                                            nemo_solver_file2_offset)
    try:
        num_comps, mismatches, max_err_b, max_err_r = \
            compare_timestep_result_lists(timestep_list1,
                                          timestep_list2,
                                          stop_on_error)
    except NemoSolverStatMismatchError as error1:
        error1.file_name1 = nemo_solver_file1
        error1.file_name2 = nemo_solver_file2
        raise error1

    io_manager.write_out('{0:d} matching timesteps found'.format(num_comps))
    intro_msg1 = \
        'comparing norm values in solver.stat files with tolerance {0:g}'
    intro_msg1 = intro_msg1.format(NemoTimestep.COMP_TOLERANCE)
    io_manager.write_out(intro_msg1)

    ret_val = 0
    if len(mismatches) == 0:
        msg1 = 'All corresponding timesteps have equal solver values'
        io_manager.write_out(msg1)
    else:
        msg1 = '{0:d} of {1:d} corrsponding timesteps have differing '\
               'solver values'.format(len(mismatches), num_comps)
        msg1 += '\n max error b = {0:g}\nmax error r = {1:g}'.format(max_err_b,
                                                                     max_err_r)
        if list_errors:
            io_manager.write_out('List of timesteps with different '
                                 'solver values:')
            for mm1 in mismatches:
                io_manager.write_out('Timestep {0:d}'.format(mm1))
        ret_val = 1
        io_manager.write_both(msg1)


    return ret_val
