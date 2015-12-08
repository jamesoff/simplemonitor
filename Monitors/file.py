
""" File-based monitors for SimpleMonitor. """

import os
import os.path
import time

from monitor import Monitor


class MonitorBackup(Monitor):
    filename = os.path.join("C:\\", "Program Files", "VERITAS", "Backup Exec", "status.txt")

    def run_test(self):
        if not os.path.exists(self.filename):
            self.record_fail("Status file missing")
            return False

        try:
            fh = open(self.filename, "r")
        except:
            self.record_fail("Unable to open status file")
            return False

        try:
            status = fh.readline()
            timestamp = fh.readline()
        except:
            self.record_fail("Unable to read data from status file")
            return False

        fh.close()

        status = status.strip()
        timestamp = int(timestamp.strip())

        if status not in ("ok", "running"):
            self.record_fail("Unknown status %s" % status)
            return False

        now = int(time.time())
        if timestamp > now:
            self.record_fail("Timestamp is ahead of now!")
            return False

        gap = now - timestamp
        print timestamp, now, gap
        if status == "ok":
            if gap > (3600 * 24):
                self.record_fail("OK was reported %ds ago" % gap)
                return False
        else:
            if gap > (3600 * 7):
                self.record_fail("Backup has been running for %ds" % gap)
                return False

        self.record_success()
        return True

    def describe(self):
        "Checking Backup Exec runs daily, and doesn't run for too long."
