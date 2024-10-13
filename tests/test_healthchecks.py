import unittest
from unittest.mock import patch, MagicMock
from simplemonitor.Alerters import HealthchecksAlerter


class TestHealthchecksAlerter(unittest.TestCase):

    @patch("requests.post")
    def test_send_notification(self, mock_post):
        """Test sending a notification successfully."""
        # Mock the response from requests
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Instantiate the Alerter
        config_options = {"token": "123456789"}

        alerter = HealthchecksAlerter(config_options)

        # Test the send_notification method
        alerter.send_notification(
            subject="Test Subject",
            body="Test Body",
            alert_type="success",
            name="Test Monitor",
            slug="test-slug",
        )

        # Check that requests.post was called with the correct URL
        expected_url = "https://hc-ping.com/123456789/test-slug"
        mock_post.assert_called_once_with(
            expected_url,
            data="Test Body",
            headers={"User-Agent": "SimpleMonitor"},
            timeout=5,
        )

    @patch("requests.post")
    def test_send_notification_create(self, mock_post):
        """Test sending a notification with the create option set to True"""
        # Mock the response from requests
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        config_options = {"token": "123456789"}
        config_options["create"] = True

        # Instantiate the Alerter
        alerter = HealthchecksAlerter(config_options)

        # Test the send_notification method
        alerter.send_notification(
            subject="Test Subject",
            body="Test Body",
            alert_type="success",
            name="Test Monitor",
            slug="test-slug",
        )

        # Check that requests.post was called with the correct URL
        expected_url = "https://hc-ping.com/123456789/test-slug?create=1"
        mock_post.assert_called_once_with(
            expected_url,
            data="Test Body",
            headers={"User-Agent": "SimpleMonitor"},
            timeout=5,
        )

    @patch("requests.post")
    def test_send_notification_failed(self, mock_post):
        """Test sending a notification successfully."""
        # Mock the response from requests
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Instantiate the Alerter
        config_options = {"token": "123456789"}

        alerter = HealthchecksAlerter(config_options)

        # Test the send_notification method
        alerter.send_notification(
            subject="Test Subject",
            body="Test Body",
            alert_type="failed",
            name="Test Monitor",
            slug="test-slug",
        )

        # Check that requests.post was called with the correct URL
        expected_url = "https://hc-ping.com/123456789/test-slug/fail"
        mock_post.assert_called_once_with(
            expected_url,
            data="Test Body",
            headers={"User-Agent": "SimpleMonitor"},
            timeout=5,
        )

    @patch("requests.post")
    def test_send_notification_failed_create(self, mock_post):
        """Test sending a notification successfully."""
        # Mock the response from requests
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Instantiate the Alerter
        config_options = {"token": "123456789"}
        config_options["create"] = True

        alerter = HealthchecksAlerter(config_options)

        # Test the send_notification method
        alerter.send_notification(
            subject="Test Subject",
            body="Test Body",
            alert_type="failed",
            name="Test Monitor",
            slug="test-slug",
        )

        # Check that requests.post was called with the correct URL
        expected_url = "https://hc-ping.com/123456789/test-slug/fail?create=1"
        mock_post.assert_called_once_with(
            expected_url,
            data="Test Body",
            headers={"User-Agent": "SimpleMonitor"},
            timeout=5,
        )


if __name__ == "__main__":
    unittest.main()
