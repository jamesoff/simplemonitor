import sys
import time


class Logger:
    """Abstract class basis for loggers."""

    dependencies = []

    def __init__(self):
        raise NotImplementedError
        # subclasses should set self.connected to True

    def save_result(self):
        raise NotImplementedError

    def set_dependencies(self, dependency_list):
        """Record which monitors we depend on.
        If a monitor we depend on fails, it means we can't reach the database, so we shouldn't bother trying to write to it."""
        # TODO: Maybe cache the commands until connection returns

        self.dependencies = dependency_list

    def check_dependencies(self, failed_list):
        for dependency in failed_list:
            if dependency in self.dependencies:
                self.connected = False
                return False
        self.connected = True


class FileLogger(Logger):

    filename = ""
    only_failures = False
    buffered = True

    def __init__(self, filename, only_failures=False, buffered=True):
        try:
            self.file_handle = open(filename, "w+")
        except:
            print "Couldn't open %s for appending." % filename
            sys.exit(1)
        self.only_failures = only_failures
        self.buffered = buffered

    def save_result2(self, name, monitor):
        if self.only_failures and not monitor.virtual_fail_count() == 0:
            return

        if monitor.virtual_fail_count() > 0:
            self.file_handle.write("%d %s: failed since %s; VFC=%d (%s)" % (int(time.time()), name, monitor.first_failure_time().isoformat(), monitor.virtual_fail_count(), monitor.get_result()))
        else:
            self.file_handle.write("%d %s: ok" % (int(time.time()), name))
        self.file_handle.write("\n")

        if not self.buffered:
            self.file_handle.flush()
