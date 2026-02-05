# type: ignore
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from simplemonitor.Monitors import gmirror

DEFAULT_CONFIG_OPTIONS = {"array_device": "gm0", "expected_disks": 2}

MOCK_OUTPUT_GOOD = """gm0  COMPLETE  ada0 (ACTIVE)
gm0  COMPLETE  ada1 (ACTIVE)
"""
MOCK_OUTPUT_SYNCHRONIZING = """gm0  DEGRADED  ada0 (ACTIVE)
gm0  DEGRADED  ada1 (SYNCHRONIZING, 7%)
"""
MOCK_OUTPUT_BAD = """gm0  DEGRADED  ada0 (ACTIVE)
"""


class TestGmirrorStatusMonitors(unittest.TestCase):
    @patch("subprocess.run")
    def test_GmirrorStatus_success(self, mock_run):
        """Success / happy path tests."""

        mock_stdout = MagicMock()
        mock_stdout.configure_mock(**{"stdout.decode.return_value": MOCK_OUTPUT_GOOD})
        mock_run.return_value = mock_stdout

        m = gmirror.MonitorGmirrorStatus("test", DEFAULT_CONFIG_OPTIONS)

        m.run_test()

        mock_run.assert_called_with(
            ["gmirror", "status", "-gs", DEFAULT_CONFIG_OPTIONS.get("array_device")],
            capture_output=True,
            check=True,
        )
        self.assertEqual("Array gm0 is in state COMPLETE with 2 disks", m.get_result())
        self.assertTrue(m.test_success())
        self.assertEqual(m.error_count, 0)

        m.run_test()

        self.assertTrue(m.test_success())
        self.assertEqual(m.error_count, 0)

    @patch("subprocess.run")
    def test_GmirrorStatus_failedSynchronizing(self, mock_run):
        """Check failure test cases."""

        mock_stdout = MagicMock()
        mock_stdout.configure_mock(
            **{"stdout.decode.return_value": MOCK_OUTPUT_SYNCHRONIZING}
        )
        mock_run.return_value = mock_stdout

        m = gmirror.MonitorGmirrorStatus("test", DEFAULT_CONFIG_OPTIONS)

        m.run_test()

        mock_run.assert_called()
        self.assertEqual(m.get_result(), "Array gm0 is in state DEGRADED with 2 disks")
        self.assertFalse(m.test_success())
        self.assertEqual(m.error_count, 1)

        m.run_test()

        self.assertFalse(m.test_success())
        self.assertEqual(m.error_count, 2)

    @patch("subprocess.run")
    def test_GmirrorStatus_failedMissingDisk(self, mock_run):
        """Check failure test cases."""

        mock_stdout = MagicMock()
        mock_stdout.configure_mock(**{"stdout.decode.return_value": MOCK_OUTPUT_BAD})
        mock_run.return_value = mock_stdout

        m = gmirror.MonitorGmirrorStatus("test", DEFAULT_CONFIG_OPTIONS)

        m.run_test()

        mock_run.assert_called()
        self.assertEqual(m.get_result(), "Array gm0 is in state DEGRADED with 1 disks")
        self.assertFalse(m.test_success())
        self.assertEqual(m.error_count, 1)

    @patch("subprocess.run")
    def test_GmirrorStatus_raiseFileNotFoundError(self, mock_run):
        """Make sure the program raises if the binary isn't present at all."""

        mock_run.side_effect = FileNotFoundError(
            "[Errno 2] No such file or directory: 'gmirror'"
        )
        m = gmirror.MonitorGmirrorStatus("test", DEFAULT_CONFIG_OPTIONS)
        self.assertRaises(FileNotFoundError, m.run_test)

    @patch("subprocess.run")
    def test_GmirrorStatus_failureSubprocessFailure(self, mock_run):
        """Handle failure based on command failing with non-0 exit code."""

        mock_run.side_effect = subprocess.CalledProcessError(
            1,
            ["gmirror", "status", "-gs", DEFAULT_CONFIG_OPTIONS.get("array_device")],
        )
        m = gmirror.MonitorGmirrorStatus("test", DEFAULT_CONFIG_OPTIONS)
        m.run_test()
        self.assertFalse(m.test_success())
        self.assertEqual(m.error_count, 1)


if __name__ == "__main__":
    unittest.main()
