#!/usr/bin/env python2.7

import argparse
import unittest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', help='Specify test directory')
    parser.add_argument('-g', '--group', help='Specify test group',
                        action='append')
    args = parser.parse_args()

    if args.path:
        testpath = args.path
    else:
        testpath = '.'

    print testpath

    groups = {
        'all':      'test_*.py',
        'common':   'test_common_*.py',
        'suitegen': 'test_common_suitegen.py',
        'nlist':    'test_common_nlist.py',
        'utils':    'test_common_utils.py',
        'moo':      'test_common_moo.py',
        }

    if args.group:
        testgroup = args.group
    else:
        testgroup = ['all']

    for g in testgroup:
        try:
            testSuite = unittest.TestLoader().discover(testpath,
                                                       pattern=groups[g])
        except KeyError:
            print '[ERROR] UnitTest - Unknown group: {}'.format(g)
            continue
        print '[INFO] Running test group: {}'.format(g)
        testResults = unittest.TextTestRunner(buffer=True).run(testSuite)


if __name__ == '__main__':
    main()
