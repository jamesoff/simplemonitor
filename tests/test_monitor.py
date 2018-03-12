import unittest
import Monitors.monitor


class TestMonitor(unittest.TestCase):

    safe_config = {'partition': '/', 'limit': '10G'}

    one_KB = 1024
    one_MB = one_KB * 1024
    one_GB = one_MB * 1024
    one_TB = one_GB * 1024

    def test_MonitorInit(self):
        m = Monitors.monitor.Monitor(config_options={
            'depend': 'a, b',
            'urgent': 0,
            'tolerance': 2,
            'remote_alert': 1,
            'recover_command': 'true'
        })
        self.assertEqual(m.name, 'unnamed', 'Monitor did not set name')
        self.assertEqual(m.urgent, 0, 'Monitor did not set urgent')
        self.assertEqual(m.tolerance, 2, 'Monitor did not set tolerance')
        self.assertTrue(m.remote_alerting, 'Monitor did not set remote_alerting')
        self.assertEqual(m.recover_command, 'true', 'Monitor did not set recover_command')

    def test_MonitorSuccess(self):
        m = Monitors.monitor.Monitor()
        m.record_success('yay')
        self.assertEqual(m.get_error_count(), 0, 'Error count is not 0')
        self.assertEqual(m.get_success_count(), 1, 'Success count is not 1')
        self.assertEqual(m.tests_run, 1, 'Tests run is not 1')
        self.assertFalse(m.was_skipped, 'was_skipped is not false')
        self.assertEqual(m.last_result, 'yay', 'Last result is not correct')

    def test_MonitorFail(self):
        m = Monitors.monitor.Monitor()
        m.record_fail('boo')
        self.assertEqual(m.get_error_count(), 1, 'Error count is not 1')
        self.assertEqual(m.get_success_count(), 0, 'Success count is not 0')
        self.assertEqual(m.tests_run, 1, 'Tests run is not 1')
        self.assertFalse(m.was_skipped, 'was_skipped is not false')
        self.assertEqual(m.last_result, 'boo', 'Last result is not correct')

    def test_MonitorWindows(self):
        m = Monitors.monitor.Monitor()
        self.assertFalse(m.is_windows())

    def test_MonitorSkip(self):
        m = Monitors.monitor.Monitor()
        m.record_skip('a')
        self.assertEqual(m.get_success_count(), 1, 'Success count is not 1')
        self.assertTrue(m.was_skipped, 'was_skipped is not true')
        self.assertEqual(m.skip_dep, 'a', 'skip_dep is not correct')
        self.assertTrue(m.skipped(), 'skipped() is not true')

