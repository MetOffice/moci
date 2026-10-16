# -----------------------------------------------------------------------------
# (C) Crown copyright Met Office. All rights reserved.
# The file LICENCE, distributed with this code, contains details of the terms
# under which the code may be used.
# -----------------------------------------------------------------------------

import unittest
import unittest.mock as mock

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
from mocilib import shellout


class ExecTests(unittest.TestCase):
    """Unit tests for executing shellout commands"""

    def test_called_process_error_fail(self):
        cmd = "ls peche"
        rcode, _ = shellout.exec_subprocess(cmd)
        self.assertGreater(rcode, 0)

    def test_called_process_error_pass(self):
        cmd = "ls ."
        rcode, _ = shellout.exec_subprocess(cmd)
        self.assertEqual(rcode, 0)

    def test_timeout_expired_fail(self):
        cmd = "sleep 3"
        rcode, _ = shellout.exec_subprocess(cmd, timeout=1)
        self.assertGreater(rcode, 0)

    def test_timeout_expired_pass(self):
        cmd = "sleep 3"
        rcode, _ = shellout.exec_subprocess(cmd, timeout=5)
        self.assertEqual(rcode, 0)

    def test_file_not_found_fail(self):
        cmd = "pineapple"
        rcode, _ = shellout.exec_subprocess(cmd)
        self.assertGreater(rcode, 0)

    def test_file_not_found_pass(self):
        cmd = "man sleep"
        rcode, _ = shellout.exec_subprocess(cmd)
        self.assertEqual(rcode, 0)

    def test_capture_pyvn_36(self):
        # vn3.6 pre-dates the `capture_output` kwarg
        cmd = "command"
        kw = { "cwd": os.getcwd(),
               "timeout": None,
               "check": True,
               "stdout": shellout.subprocess.PIPE,
               "stderr": shellout.subprocess.PIPE }

        with mock.patch("sys.version_info", (3,6,15)):
            with mock.patch("subprocess.run") as mock_exec:
                rcode, _ = shellout.exec_subprocess(cmd)
        mock_exec.assert_called_once_with([cmd], **kw)

    def test_capture_pyvn_37(self):
        # The `capture_output` kwarg was introduced at vn3.7
        cmd = "command"
        kw = { "cwd": os.getcwd(),
               "timeout": None,
               "check": True,
               "capture_output": True }

        with mock.patch("sys.version_info", (3,7,0)):
            with mock.patch("subprocess.run") as mock_exec:
                rcode, _ = shellout.exec_subprocess(cmd)
        mock_exec.assert_called_once_with([cmd], **kw)


if __name__ == "__main__":
    unittest.main()