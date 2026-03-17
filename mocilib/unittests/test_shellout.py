# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir,os.pardir))
from mocilib import shellout

#TODO: Add success tests and other tests on same line

class ExecTets(unittest.TestCase):
    ''' Unit tests for executing shellout commands'''

    def test_called_process_error(self):
        cmd = f"ls peche"
        rcode,_ = shellout.exec_subprocess(cmd)
        print(f"The rcode which was returned is {rcode}")
        self.assertGreater(rcode,0)

    def test_timeout_expired(self):
        cmd = "sleep 15"
        rcode,_ = shellout.exec_subprocess(cmd,timeout=1)
        print(f"The rcode which was returned is {rcode}")
        self.assertGreater(rcode,0)

if __name__ == "__main__":
    unittest.main()
