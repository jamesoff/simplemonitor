# coding=utf-8
""" File-based monitors for SimpleMonitor. """

import os
import os.path
import time
import datetime

import util
from .monitor import Monitor


class MonitorBackup(Monitor):
    filename = os.path.join("C:\\", "Program Files", "VERITAS", "Backup Exec", "status.txt")

    def run_test(self):
        if not os.path.exists(self.filename):
            return self.record_fail("Status file missing")

        try:
            fh = open(self.filename, "r")
        except Exception:
            return self.record_fail("Unable to open status file")

        try:
            status = fh.readline()
            timestamp = fh.readline()
        except Exception:
            return self.record_fail("Unable to read data from status file")

        fh.close()

        status = status.strip()
        timestamp = int(timestamp.strip())

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

    def describe(self):
        "Checking Backup Exec runs daily, and doesn't run for too long."


class MonitorFileUpdate(Monitor):
    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        self.path = Monitor.get_config_option(config_options, 'path', required=True)
        max_age = Monitor.get_config_option(config_options, 'max_age', required_type='int', default=60*60*24)
        self.max_age = datetime.timedelta(seconds=max_age)

    def run_test(self):
        if not os.path.exists(self.path):
            return self.record_fail("File {0} is missing".format(self.path))

        if not os.path.isfile(self.path):
            return self.record_fail("{0} is not a file".format(self.path))

        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(self.path))
        now = datetime.datetime.now()
        age = now - mtime

        if age < datetime.timedelta(0):
            return self.record_fail("File {0} was modified in the future ({1})!".format(self.path, util.format_datetime(mtime)))
        elif age > self.max_age:
            return self.record_fail("File {0} was last modified at {1}, which was {2} ago (max {3})".format(
                self.path, util.format_datetime(mtime),
                util.format_timedelta(age), util.format_timedelta(self.max_age)))
        return self.record_success()

    def describe(self):
        "Checking file is not too old (useful for backups)."
