#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
'''
import argparse
import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'common'))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'atmos'))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'nemocice'))


def main():
    '''Run unit tests for postproc app'''
    groups = {
        'all':      'test_*.py',
        'common':   'test_common*.py',
        'suitegen': 'test_common_suitegen.py',
        'nlist':    'test_common_nlist.py',
        'utils':    'test_common_utils.py',
        'moo':      'test_common_moo.py',
        'atmos':    'test_atmos_*.py',
        'atmbase':  'test_atmos_base.py',
        'atmutils': 'test_atmos_atmutils.py',
        'nemocice': 'test_nemocice*.py',
        'nemo':     'test_nemocice_nemo.py',
        'template': 'test_nemocice_template.py',
        }

    subgroups = [
        ' '.join(['common'] + [c for c in groups.keys() if
                               'common_' in groups[c]]),
        ' '.join(['atmos'] + [a for a in groups.keys() if
                              'atmos_' in groups[a]]),
        ' '.join(['nemocice'] + [n for n in groups.keys() if
                                 'nemocice_' in groups[n]]),
        ]

    parser = argparse.ArgumentParser(
        description='MOCI PostProcessing App UnitTests',
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-g', '--group',
                        help='''Specify a group of tests to run.  Default=all
Additional groups may be requested with further --group arguments.
Available groups: \n\t{}'''.format('\n\t'.join(subgroups)),
                        action='append')
    args = parser.parse_args()

    if args.group:
        testgroup = args.group
    else:
        testgroup = ['all']

    for grp in testgroup:
        try:
            test_suite = unittest.TestLoader().\
                discover(os.path.dirname(os.path.realpath(__file__)),
                         pattern=groups[grp])
        except KeyError:
            print '[ERROR] UnitTest - Unknown group: {}.  See help'.format(grp)
            continue
        print '[INFO] Running test group: {}'.format(grp)
        unittest.TextTestRunner(buffer=True).run(test_suite)


if __name__ == '__main__':
    main()
