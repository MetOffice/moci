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
    umdump_year.py

DESCRIPTION
    This changes the year of the validtiy time in the fixed length header
    of a Unified Model start dump

AUTHORS
    Alistair Sellar (Met Office)
    Harry Shepherd (Met Office)

REQUIRED ARGUMENTS:
    infile:      full path and filename of dump to be perturbed
    --year, -Y:  year to impose on restart dump (4 digits)

OPTIONAL ARGUMENTS:
    --outfile, -o: Full path and filename of perturbed dump
                   Default value = "<input filename>_<year>"
'''

import argparse
import re
import sys

# The script requires mule, which isn't available unless the um_tools module
# is present
try:
    import mule
except ImportError:
    sys.stderr.write('[FAIL] Unable to import mule\n'
                     '[FAIL] Please check the um_tools module is loaded by\n'
                     '[FAIL] running \'module load um_tools\'\n')
    sys.exit(999)


def set_year(infile, outfile, year):
    '''
    Use mule to set the year for time2 (validity time) in the fixed length
    header
    '''
    dump = mule.DumpFile.from_file(infile)
    dump.fixed_length_header.t2_year = year
    dump.to_file(outfile)


def parse_args():
    '''
    Parse the command line arguments
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', help='Input filename')
    parser.add_argument('--outfile', '-o', help='Output filename', default='')
    parser.add_argument('--year', '-Y', help='Year to impose in restart dump'
                        ' (4 digits)', required=True)

    args = parser.parse_args()
    return args


def main():
    '''
    Run the program
    '''
    args = parse_args()
    # check the year has four digits
    if not re.match(r'^\d{4}$', args.year):
        sys.stderr.write('[FAIL] The year must contain exactly four digits\n')
        sys.exit(999)
    # make default outfile name if needed
    if not args.outfile:
        outfile = '{}_{}'.format(args.infile, args.year)
    else:
        outfile = args.outfile

    set_year(args.infile, outfile, args.year)


if __name__ == '__main__':
    main()
