# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
import shellout

class ExecTets(unittest.TestCase):
    ''' Unit tests for executing shellout commands'''

    def test_semicolon_commands(self):
        cmd = "echo Hello There;echo General Kenobi"
        _,rcode = shellout.exec_subprocess(cmd=cmd)
        assert rcode == 0

    def test_and_commands(self):
        cmd ="echo Hello There&&echo General Kenobi"
        _,rcode = shellout.exec_subprocess(cmd=cmd)
        assert rcode == 0

    def test_called_process_error(self,directory):
        cmd = f"ls /{directory}"
        _,rcode = shellout.exec_subprocess(cmd=cmd)
        assert rcode != 0

    def test_timeout_expired(self):
        cmd = "sleep 15"
        _,rcode = shellout.exec_subprocess(cmd=cmd,timeout=1)
        assert rcode != 0


if __name__ == "__main__":
    unittest.main()
