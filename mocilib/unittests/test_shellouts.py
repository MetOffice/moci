# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
import shellouts

class ExecTets(unittest.TestCase):
    ''' Unit tests for executing shellout commands'''

    def test_semicolon_commands(self):
        cmd = "echo Hello;echo World"
        _,rcode = shellouts.exec_subprocess(cmd)
        print(f"The rcode which was returned is {rcode}")
        self.assertEqual(rcode,0)

    def test_and_commands(self):
        cmd ="echo Hello&&echo World"
        _,rcode = shellouts.exec_subprocess(cmd)
        print(f"The rcode which was returned is {rcode}")
        self.assertEqual(rcode,0)

    def test_called_process_error(self):
        cmd = f"ls peche"
        _,rcode = shellouts.exec_subprocess(cmd)
        print(f"The rcode which was returned is {rcode}")
        self.assertGreater(rcode,0)

    def test_timeout_expired(self):
        cmd = "sleep 15"
        _,rcode = shellouts.exec_subprocess(cmd,timeout=1)
        print(f"The rcode which was returned is {rcode}")
        self.assertGreater(rcode,0)


if __name__ == "__main__":
    unittest.main()
