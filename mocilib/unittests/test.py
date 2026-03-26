#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------
import argparse
import unittest
import sys
import os

assert sys.version_info >= (3, 6)

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


def main():
    """
    Runs all mocilib unit tests
    """
    groups = {"all": "test*.py", "shellouts": "test_shellouts.py"}

    parser = argparse.ArgumentParser(
        description="MOCIlib UnitTests", formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "-g",
        "--group",
        help="Specify a group of tests to run.  Default=all"
        " Additional groups may be requested with further"
        " --group arguments",
        action="append",
    )
    args = parser.parse_args()

    if args.group:
        testgroup = args.group
    else:
        testgroup = ["all"]

    rcode = 0
    for grp in testgroup:
        try:
            test_suite = unittest.TestLoader().discover(
                os.path.dirname(os.path.realpath(__file__)), pattern=groups[grp]
            )
        except KeyError:
            sys.stderr.write(
                "[ERROR] UnitTest - Unknown group: {}\n.  See help".format(grp)
            )
            continue
        sys.stdout.write("[INFO] Running test group: {}\n".format(grp))
        test_rtn = unittest.TextTestRunner(buffer=True).run(test_suite)
        rcode += len(test_rtn.failures) + len(test_rtn.errors)

    sys.exit(rcode)


if __name__ == "__main__":
    main()
