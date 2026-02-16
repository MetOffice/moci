# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------

import unittest
from hypothesis import given, strategies as st

class ExecTets(unittest.TestCase):
    ''' Unit tests for executing shellout commands'''

    def test_semicolon_commands(self):
        cmd = "echo Hello There;echo General Kenobi"
        _,rcode = shellout._exec_subprocess(cmd=cmd)
        assert rcode == 0

    def test_and_commands(self):
        cmd ="echo Hello There&&echo General Kenobi"
        _,rcode = shellout._exec_subprocess(cmd=cmd)
        assert rcode == 0

    @given(st.text())
    def test_called_process_error(self,directory):
        cmd = f"ls /{directory}"
        _,rcode = shellout._exec_subprocess(cmd=cmd)
        assert rcode != 0

    def test_timeout_expired(self):
        cmd = "sleep 15"
        _,rcode = shellout._exec_subprocess(cmd=cmd,timeout=10)
        assert rcode != 0
