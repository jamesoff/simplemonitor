import unittest
import datetime
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

    def test_MonitorConfig(self):
        config_options = {
            'test_string': 'a string',
            'test_int': '3',
            'test_[int]': '1,2, 3',
            'test_[str]': 'a, b,c',
            'test_bool1': '1',
            'test_bool2': 'yes',
            'test_bool3': 'true',
            'test_bool4': '0'
        }
        self.assertEqual(
            Monitors.monitor.Monitor.get_config_option(
                config_options,
                'test_string'),
            'a string'
        )
        self.assertEqual(
            Monitors.monitor.Monitor.get_config_option(
                config_options,
                'test_int',
                required_type='int'),
            3
        )
        self.assertEqual(
            Monitors.monitor.Monitor.get_config_option(
                config_options,
                'test_[int]',
                required_type='[int]'),
            [1, 2, 3]
        )
        self.assertEqual(
            Monitors.monitor.Monitor.get_config_option(
                config_options,
                'test_[str]',
                required_type='[str]'),
            ['a', 'b', 'c']
        )
        for bool_test in list(range(1, 4)):
            self.assertEqual(
                Monitors.monitor.Monitor.get_config_option(
                    config_options,
                    'test_bool{0}'.format(bool_test),
                    required_type='bool'),
                True
            )
        self.assertEqual(
            Monitors.monitor.Monitor.get_config_option(
                config_options,
                'test_bool4',
                required_type='bool'),
            False
        )

    def test_downtime(self):
        m = Monitors.monitor.Monitor()
        m.failed_at = datetime.datetime.utcnow()
        self.assertEqual(m.get_downtime(), (0, 0, 0, 0))

        m.failed_at = None
        self.assertEqual(m.get_downtime(), (0, 0, 0, 0))

        now = datetime.datetime.utcnow()
        two_h_thirty_m_ago = now - datetime.timedelta(hours=2, minutes=30)
        yesterday = now - datetime.timedelta(days=1)

        m.failed_at = two_h_thirty_m_ago
        self.assertEqual(m.get_downtime(), (0, 2, 30, 0))

        m.failed_at = yesterday
        self.assertEqual(m.get_downtime(), (1, 0, 0, 0))
