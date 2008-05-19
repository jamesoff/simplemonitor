try:
    import sqlite3
    sqlite_available = True
except:
    sqlite_available = False

import time
from logger import Logger
from socket import gethostname


class DBLogger(Logger):
    """Abstract class which uses a sqlite3 backend."""

    hostname = gethostname()
    connected = False

    def __init__(self, db_path):
        """Open the database connection."""
        if not sqlite_available:
            raise RuntimeError("SQLite module not loaded.")
        self.db_handle = sqlite3.connect(db_path, isolation_level = None)
        self.connected = True


class DBFullLogger(DBLogger):
    """Logs results to a sqlite3 db."""

    def save_result(self, monitor_name, monitor_type, monitor_params, monitor_result, monitor_info, hostname = ""):
        """Write to the database."""
        if not self.connected:
            print "cannot send results, a dependency failed"
            return
        sql = "INSERT INTO results (result_id, monitor_host, monitor_name, monitor_type, monitor_params, monitor_result, timestamp, monitor_info) VALUES (null, ?, ?, ?, ?, ?, ?, ?)"
        c = self.db_handle.cursor()

        join_string = ":"
        timestamp = int(time.time())
        if hostname == "":
            hostname = self.hostname

        params = (hostname, monitor_name, monitor_type, join_string.join([str(x) for x in monitor_params]), monitor_result, timestamp, monitor_info)
        c.execute(sql, params)

    def save_result2(self, name, monitor):
        """new interface."""
        self.save_result(name, monitor.type, monitor.get_params(), monitor.get_result(), monitor.describe())


class DBStatusLogger(DBLogger):
    """Maintains status snapshot in db."""

    def clear_results(self):
        """Flush all status results."""
        c = self.db_handle.cursor()
        c.execute("DELETE FROM status")

    def save_result(self, monitor_name, monitor_type, monitor_params, monitor_result, monitor_info, hostname=""):
        if hostname == "":
            hostname = self.hostname
        c = self.db_handle.cursor()
        c.execute("DELETE FROM status WHERE monitor_host = ? AND monitor_name = ?", (self.hostname, monitor_name))
        c.execute("REPLACE INTO status (monitor_host, monitor_name, monitor_result, monitor_info) VALUES (?, ?, ?, ?)", (hostname, monitor_name, monitor_result, monitor_info))

    def save_result2(self, name, monitor):
        """new interface."""
        self.save_result(name, monitor.type, monitor.get_params(), monitor.get_result(), monitor.describe())



