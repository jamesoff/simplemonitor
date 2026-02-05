"""
Gmirror array checks for simplemonitor.
"""

import subprocess

from .monitor import Monitor, register


@register
class MonitorGmirrorStatus(Monitor):
    """
    Check gmirror status for specified device.
    """

    monitor_type = "gmirror_status"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self.array_device = self.get_config_option(
            "array_device", required_type="str", required=True
        )
        self.expected_disks = self.get_config_option(
            "expected_disks", required_type="int", required=True
        )

    def run_test(self) -> bool:
        """
        Run `gmirror status` for the specified device. Keep the logic simpler
        by requiring each device and the # of expected disks to be specified
        separately.
        """

        run_cmd = ["gmirror", "status", "-gs", self.array_device]
        try:
            result = subprocess.run(run_cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError:
            return self.record_fail("gmirror command failed")

        status_lines = result.stdout.decode("utf-8").rstrip("\n").split("\n")

        # Status should be same for the array, so just grab first line
        status = status_lines[0].split()[1]

        # Infer # of disks based on the number of lines
        disk_count = len(status_lines)

        msg = f"Array {self.array_device} is in state {status} with {disk_count} disks"

        if status == "COMPLETE" and disk_count == self.expected_disks:
            return self.record_success(msg)

        return self.record_fail(msg)

    def describe(self) -> str:
        return f"Check RAID status of {self.array_device}."
