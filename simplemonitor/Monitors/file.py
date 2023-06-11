"""
File-based monitors for SimpleMonitor
"""

import os
import os.path
import time

from .monitor import Monitor, register


@register
class MonitorBackup(Monitor):
    """
    Monitor Veritas BackupExec

    May be out of date
    """

    monitor_type = "backup"
    filename = os.path.join(
        "C:\\", "Program Files", "VERITAS", "Backup Exec", "status.txt"
    )

    def run_test(self) -> bool:
        if not os.path.exists(self.filename):
            return self.record_fail("Status file missing")

        try:
            fh = open(self.filename, "r")
        except Exception:
            return self.record_fail("Unable to open status file")

        try:
            status = fh.readline()
            _timestamp = fh.readline()
        except Exception:
            return self.record_fail("Unable to read data from status file")

        fh.close()

        status = status.strip()
        timestamp = int(_timestamp.strip())

        if status not in ("ok", "running"):
            return self.record_fail("Unknown status %s" % status)

        now = int(time.time())
        if timestamp > now:
            return self.record_fail("Timestamp is ahead of now!")

        gap = now - timestamp
        if status == "ok":
            if gap > (3600 * 24):
                return self.record_fail("OK was reported %ds ago" % gap)
        else:
            if gap > (3600 * 7):
                return self.record_fail("Backup has been running for %ds" % gap)

        return self.record_success()

    def describe(self) -> str:
        return "Checking Backup Exec runs daily, and doesn't run for too long."
