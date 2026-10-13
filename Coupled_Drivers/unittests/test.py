#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------
'''
NAME
    test.py

DESCRIPTION
    Top level file for running the unit tests
'''
import argparse
import unittest
import sys
import os

assert sys.version_info >= (3, 6)

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))

def main():
    '''
    Run unit tests
    '''
    groups = {
        'all': 'test*.py',
        'env_lib': 'test_env_lib.py',
        'aprun_command': 'test_aprun_command_construction.py',
        'mct': 'test_mct_driver.py',
        'lfric': 'test_lfric_driver.py',
        'xios': 'test_xios_driver.py',
        'dependency_checker': 'test_driver_dependencies.py',
        'cpmip': 'test_cpmip*py',
        'nemo_driver': 'test_nemo_driver.py',
        'um_driver': 'test_um_driver.py',
        'cice_driver': 'test_cice_driver.py',
        'si3': 'test_si3_controller.py',
        'rivers': 'test_rivers_driver.py',
        'common': 'test_common.py',
        'namcouple': 'test_update_namcouple.py',
        'link': 'test_link_drivers.py',
    }

    parser = argparse.ArgumentParser(
        description='MOCI Drivers App UnitTests',
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-g', '--group',
                        help='Specify a group of tests to run.  Default=all' \
                        ' Additional groups may be requested with further' \
                        ' --group arguments',
                        action='append')
    args = parser.parse_args()

    if args.group:
        testgroup = args.group
    else:
        testgroup = ['all']

    rtn_code = 0
    for grp in testgroup:
        try:
            test_suite = unittest.TestLoader().\
                discover(os.path.dirname(os.path.realpath(__file__)),
                         pattern=groups[grp])
        except KeyError:
            sys.stderr.write(
                '[ERROR] UnitTest - Unknown group: {}\n.  See help'.format(grp)
                )
            continue
        sys.stdout.write('[INFO] Running test group: {}\n'.format(grp))
        test_rtn = unittest.TextTestRunner(buffer=True).run(test_suite)
        rtn_code += len(test_rtn.failures) + len(test_rtn.errors)

    sys.exit(rtn_code)

if __name__ == '__main__':
    main()
