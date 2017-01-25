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
   comp_norms

Compare 2 UM dump files using the MULE API and the CUMF UM util based on MULE.
"""
import sys
import textwrap
import argparse

import mule
import um_utils.cumf

# The "lbegin" parameter of the lookup must be ignored for comparing the
# output of an NRUN with an equivalent CRUN. See Section 4.2 of UMDP F03 for
# more info
NRUN_NRUN_IGNORE_INDICES = [29]

def select_valid_lbrel(input_path, output_path):
    """
    Preprocessing step to remove any invalid fields that MULE cannot cope
    with.
    """
    raw_file = mule.UMFile.from_file(input_path)
    original_number_of_fields = len(raw_file.fields)
    valid_fields = [field1 for field1 in raw_file.fields if field1.lbrel > 0]
    number_of_valid_fields = len(valid_fields)
    raw_file.fields = valid_fields

    raw_file.to_file(output_path)

    message1 = 'select {0} valid fields from {1} fields in {2} '\
               'and wrote to new file {3}'.format(number_of_valid_fields,
                                                  original_number_of_fields,
                                                  input_path,
                                                  output_path)
    print '\n'.join(textwrap.wrap(message1))

def compare_files(fields_file_path_1, fields_file_path_2):
    """
    Main function to compare 2 UM dump files.
    """
    fields_file_1 = mule.FieldsFile.from_file(fields_file_path_1)
    fields_file_2 = mule.FieldsFile.from_file(fields_file_path_2)

    #these fields are important to ignore for nrun + nrun comparisons, as
    # they will differ in that case
    um_utils.cumf.COMPARISON_SETTINGS['ignore_templates']['lookup'] = \
        NRUN_NRUN_IGNORE_INDICES

    comparison12 = um_utils.cumf.UMFileComparison(fields_file_1,
                                                  fields_file_2)

    number_of_fields = len(comparison12.field_comparisons)
    number_of_mismatches = \
        sum([1 for fc1 in comparison12.field_comparisons if not fc1.match])
    status_code = 0
    if number_of_mismatches > 0:
        msg = '{0} of {1} fields do not match!\n'
        msg = msg.format(number_of_mismatches,
                         number_of_fields)
        status_code = 1
    else:
        msg = 'All {0} fields match!\n'.format(number_of_fields)

    sys.stderr.write(msg)
    return status_code

def get_command_line_arguments():
    """
    input_path1, input_path2 = get_command_line_arguments()
    Process command line arguments
    """
    desc_msg = 'Compare dump files from 2 GA7 tasks.'
    parser = argparse.ArgumentParser(description=desc_msg)
    parser.add_argument('--input-path1', dest='input_path1')
    parser.add_argument('--input-path2', dest='input_path2')
    args1 = parser.parse_args()
    return (args1.input_path1, args1.input_path2)

def main():
    """Main function for mule_compare_dump_files.py."""
    print 'comparing data in dump files\n'
    input_path1, input_path2 = get_command_line_arguments()
    status_code = compare_files(input_path1, input_path2)
    exit(status_code)

if __name__ == '__main__':
    main()
