import unittest
import Monitors.remote_monitor
from unittest.mock import Mock

from Monitors.monitor import MonitorConfigurationError


class TestRemoteMonitor(unittest.TestCase):

    def test_RemoteMonitor_brokenConfigOne(self):
        config_options = {}
        with self.assertRaises(MonitorConfigurationError):
            Monitors.remote_monitor.RemoteMonitorNull("test", config_options)

    def test_RemoteMonitor_brokenConfigTwo(self):
        config_options = {"remote_host": "1.2.3.4"}
        with self.assertRaises(MonitorConfigurationError):
            Monitors.remote_monitor.RemoteMonitorNull("test", config_options)

    def test_RemoteMonitor_brokenConfigThree(self):
        config_options = {"remote_host": "1.2.3.4", "user": "root"}
        with self.assertRaises(MonitorConfigurationError):
            Monitors.remote_monitor.RemoteMonitorNull("test", config_options)

    def test_RemoteMonitor_brokenConfigFour(self):
        config_options = {"remote_host": "1.2.3.4", "user": "root", "port": "22"}
        with self.assertRaises(MonitorConfigurationError):
            Monitors.remote_monitor.RemoteMonitorNull("test", config_options)

    def test_RemoteMonitor_brokenConfigFive(self):
        config_options = {"remote_host": "1.2.3.4", "user": "root", "port": 22}
        with self.assertRaises(MonitorConfigurationError):
            Monitors.remote_monitor.RemoteMonitorNull("test", config_options)

    def test_RemoteMonitor_correctConfigOne(self):
        config_options = {"remote_host": "1.2.3.4", "user": "root", "password": "password123"}
        m = Monitors.remote_monitor.RemoteMonitorNull("test", config_options)
        self.assertIsInstance(m, Monitors.remote_monitor.RemoteMonitorNull)

    def test_RemoteMonitor_correctConfigTwo(self):
        config_options = {"remote_host": "1.2.3.4", "user": "root", "key": "tests/id_rsa"}
        m = Monitors.remote_monitor.RemoteMonitorNull("test", config_options)
        self.assertIsInstance(m, Monitors.remote_monitor.RemoteMonitorNull)

    def test_RemoteMonitor_correctConfigThree(self):
        config_options = {"remote_host": "1.2.3.4", "user": "root", "key": "tests/id_rsa", "password": "password123"}
        m = Monitors.remote_monitor.RemoteMonitorNull("test", config_options)
        self.assertIsInstance(m, Monitors.remote_monitor.RemoteMonitorNull)

    def test_RemoteMonitor_MissingKeyFile(self):
        config_options = {"remote_host": "1.2.3.4", "user": "root", "port": 22, "key": "/path/to/non/existing/file"}
        with self.assertRaises(OSError):
            Monitors.remote_monitor.RemoteMonitorNull("test", config_options)

    def test_RemoteMonitor_runSuccessfulTest(self):
        config_options = {"remote_host": "1.2.3.4", "user": "root", "key": "tests/id_rsa", "password": "password123"}
        m = Monitors.remote_monitor.RemoteMonitorNull("test", config_options)
        m.run_test()
        self.assertTrue(m.test_success(), "Monitor failed")

    def test_RemoteMonitor_runFailTest(self):
        config_options = {"remote_host": "1.2.3.4", "user": "root", "key": "tests/id_rsa", "password": "password123"}
        m = Monitors.remote_monitor.RemoteMonitorFail("test", config_options)
        m.run_test()
        self.assertFalse(m.test_success(), "Monitor did not fail")

    @staticmethod
    def mock_connection(stdout: str = "", stderr: str = "", return_code: int = 0):
        connection = Mock()
        connection.open = lambda *args, **kwargs: None
        result = Mock()
        result.stdout = stdout
        result.stderr = stderr
        result.return_code = return_code
        connection.run = lambda *args, **kwargs: result

        return connection

    def test_mockConnection(self):
        expected_stdout = "command stdout"
        expected_stderr = "command stderr"
        expected_return_code = 0
        connection = self.mock_connection(stdout=expected_stdout,
                                          stderr=expected_stderr,
                                          return_code=expected_return_code)
        result = connection.run('command')
        self.assertEqual(result.stdout, expected_stdout)
        self.assertEqual(result.stderr, expected_stderr)
        self.assertEqual(result.return_code, expected_return_code)


if __name__ == "__main__":
    unittest.main()
