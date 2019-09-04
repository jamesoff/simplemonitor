import unittest
import Monitors.remote_service
from tests.test_remote_monitor import TestRemoteMonitor

from Monitors.monitor import MonitorConfigurationError


class TestRemoteServiceMonitors(unittest.TestCase):

    remote_monitor_config = {
        "remote_host": "1.2.3.4",
        "user": "root",
        "port": 22,
        "password": "password123"
    }

    def get_config(self, options):
        config = dict(self.remote_monitor_config)
        config.update(options)
        return config

    def test_RemoteService_brokenConfigOne(self):
        config_options = self.get_config({})
        with self.assertRaises(MonitorConfigurationError):
            Monitors.remote_service.RemoteServiceMonitor("test", config_options)

    def test_RemoteService_brokenConfigTwo(self):
        config_options = self.get_config({"service": "sshd", "svc_cmd": "unknown_tool"})
        with self.assertRaises(MonitorConfigurationError):
            Monitors.remote_service.RemoteServiceMonitor("test", config_options)

    def test_RemoteService_correctConfigOne(self):
        config_options = self.get_config({"service": "sshd"})
        m = Monitors.remote_service.RemoteServiceMonitor("test", config_options)
        self.assertIsInstance(m, Monitors.remote_service.RemoteServiceMonitor)

    def test_RemoteService_correctConfigTwo(self):
        config_options = self.get_config({"service": "sshd", "svc_cmd": "service"})
        m = Monitors.remote_service.RemoteServiceMonitor("test", config_options)
        self.assertIsInstance(m, Monitors.remote_service.RemoteServiceMonitor)

    def test_RemoteService_correctConfigThree(self):
        config_options = self.get_config({"service": "sshd", "svc_cmd": "chkconfig"})
        m = Monitors.remote_service.RemoteServiceMonitor("test", config_options)
        self.assertIsInstance(m, Monitors.remote_service.RemoteServiceMonitor)

    def test_RemoteService_serviceUp_service(self):
        config_options = self.get_config({"service": "sshd", "srv_cmd": "service"})
        m = Monitors.remote_service.RemoteServiceMonitor("test", config_options)
        m._connection = TestRemoteMonitor.mock_connection(
            stdout="Checking for service sshd                                                             running",
            return_code=0)
        m.run_test()
        self.assertTrue(m.test_success())

    def test_RemoteService_serviceDown_service(self):
        config_options = self.get_config({"service": "sshd", "srv_cmd": "service"})
        m = Monitors.remote_service.RemoteServiceMonitor("test", config_options)
        m._connection = TestRemoteMonitor.mock_connection(
            stdout="Checking for service sshd                                                             dead",
            return_code=1)
        m.run_test()
        self.assertFalse(m.test_success())

    def test_RemoteService_serviceUp_chkconfig(self):
        config_options = self.get_config({"service": "sshd", "svc_cmd": "chkconfig"})
        m = Monitors.remote_service.RemoteServiceMonitor("test", config_options)
        m._connection = TestRemoteMonitor.mock_connection(
            stdout="sshd    on",
            return_code=0)
        m.run_test()
        self.assertTrue(m.test_success())

    def test_RemoteService_serviceDown_chkconfig(self):
        config_options = self.get_config({"service": "sshd", "svc_cmd": "chkconfig"})
        m = Monitors.remote_service.RemoteServiceMonitor("test", config_options)
        m._connection = TestRemoteMonitor.mock_connection(
            stdout="sshd    off",
            return_code=0)
        m.run_test()
        self.assertFalse(m.test_success())

    def test_RemoteService_get_params(self):
        config_options = self.get_config({"service": "sshd", "srv_cmd": "service"})
        m = Monitors.remote_service.RemoteServiceMonitor("test", config_options)
        self.assertTupleEqual(m.get_params(), ("1.2.3.4", 22, "root", "password123", "sshd", "service"))


if __name__ == "__main__":
    unittest.main()
