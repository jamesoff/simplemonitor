# type: ignore
import subprocess
import unittest
from unittest.mock import patch

from simplemonitor.Monitors import service


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

    @patch("subprocess.check_output")
    def test_svc_ok(self, subprocess_run_fn):
        config_options = {"path": "/var/service/thing"}
        subprocess_run_fn.return_value = b"/var/service/thing: up (pid 1234) 10 seconds"
        m = service.MonitorSvc("unittest", config_options)
        m.run_test()
        self.assertTrue(m.test_success())

    @patch("subprocess.check_output")
    def test_svc_down(self, subprocess_run_fn):
        config_options = {"path": "/var/service/thing"}
        subprocess_run_fn.return_value = (
            b"/var/service/thing: down 10 seconds, normally up"
        )
        m = service.MonitorSvc("unittest", config_options)
        m.run_test()
        self.assertFalse(m.test_success())

    @patch("subprocess.check_output")
    def test_svc_up_enough(self, subprocess_run_fn):
        config_options = {"path": "/var/service/thing", "minimum_uptime": 5}
        subprocess_run_fn.return_value = b"/var/service/thing: up (pid 1234) 10 seconds"
        m = service.MonitorSvc("unittest", config_options)
        m.run_test()
        self.assertTrue(m.test_success())

    @patch("subprocess.check_output")
    def test_svc_up_not_enough(self, subprocess_run_fn):
        config_options = {"path": "/var/service/thing", "minimum_uptime": 15}
        subprocess_run_fn.return_value = b"/var/service/thing: up (pid 1234) 10 seconds"
        m = service.MonitorSvc("unittest", config_options)
        m.run_test()
        self.assertFalse(m.test_success())


if __name__ == "__main__":
    unittest.main()
