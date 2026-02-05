import unittest
from unittest.mock import Mock, patch

from requests import Response
from requests.auth import HTTPBasicAuth

from simplemonitor.Monitors import MonitorHTTP
from simplemonitor.util import MonitorState


class TestMonitorHTTP(unittest.TestCase):
    def test_get_ok_default_params(self):
        response_mock = Mock(spec=Response)
        response_mock.status_code = 200

        monitor = MonitorHTTP(
            name="test_http_monitor",
            config_options={
                "url": "http://example.com",
                "urgent": 0,
                "tolerance": 1,
                "remote_alert": 1,
            },
        )

        with patch("requests.request", return_value=response_mock) as mock:
            monitor.run_test()

        result = monitor.get_result()
        state = monitor.state()

        mock.assert_called_once_with(
            "GET",
            "http://example.com",
            headers=None,
            timeout=5,
            verify=True,
            allow_redirects=True,
            auth=None,
            cert=None,
            data=None,
            json=None,
        )
        self.assertEqual(state, MonitorState.OK)
        self.assertIn("200", result)

    def test_get_ok_non_default_params(self):
        response_mock = Mock(spec=Response)
        response_mock.status_code = 200

        monitor = MonitorHTTP(
            name="test_http_monitor",
            config_options={
                "url": "http://example.com",
                "urgent": 0,
                "tolerance": 1,
                "remote_alert": 1,
                "verify_hostname": False,
                "allow_redirects": False,
                "username": "test",
                "password": "pass",
                "headers": '{"test": "header"}',
                "timeout": 10,
            },
        )

        with patch("requests.request", return_value=response_mock) as mock:
            monitor.run_test()

        result = monitor.get_result()
        state = monitor.state()

        mock.assert_called_once_with(
            "GET",
            "http://example.com",
            headers={"test": "header"},
            timeout=10,
            verify=False,
            allow_redirects=False,
            auth=HTTPBasicAuth("test", "pass"),
            cert=None,
            data=None,
            json=None,
        )
        self.assertEqual(state, MonitorState.OK)
        self.assertIn("200", result)
        pass
