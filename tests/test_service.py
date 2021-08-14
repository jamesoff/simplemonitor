# type: ignore
import unittest
import subprocess
from simplemonitor.Monitors import service
from unittest.mock import patch


class TestUnixServiceMonitors(unittest.TestCase):
    @patch("subprocess.run")
    def test_UnixService_ok(self, subprocess_run_fn):
        config_options = {"service": "unittest"}

        subprocess_run_fn.return_value = subprocess.CompletedProcess(
            ["service", config_options.get("service"), "status"], returncode=1
        )
        m = service.MonitorUnixService("unittest", config_options)

        m.run_test()
        self.assertFalse(m.test_success())
        self.assertEqual(m.error_count, 1)

        m.run_test()
        self.assertFalse(m.test_success())
        self.assertEqual(m.error_count, 2)

    @patch("subprocess.run")
    def test_UnixService_raiseFileNotFoundError(self, subprocess_run_fn):
        config_options = {"service": "unittest"}

        subprocess_run_fn.side_effect = FileNotFoundError(
            "[Errno 2] No such file or directory: 'service'"
        )
        m = service.MonitorUnixService("unittest", config_options)

        self.assertRaises(FileNotFoundError, m.run_test)

    @patch("subprocess.run")
    def test_UnixService_raiseSubprocessError(self, subprocess_run_fn):
        config_options = {"service": "unittest"}

        subprocess_run_fn.side_effect = subprocess.SubprocessError(
            ["service", config_options.get("service"), "status"]
        )
        m = service.MonitorUnixService("unittest", config_options)

        m.run_test()
        self.assertFalse(m.test_success())
        self.assertEqual(m.error_count, 1)

        m.run_test()
        self.assertFalse(m.test_success())
        self.assertEqual(m.error_count, 2)


if __name__ == "__main__":
    unittest.main()
