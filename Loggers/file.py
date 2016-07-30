from __future__ import with_statement

import os
import datetime
import time
import socket
import tempfile
import shutil
import stat
import cStringIO
import sys


from logger import Logger


class FileLogger(Logger):

    filename = ""
    only_failures = False
    buffered = True
    dateformat = None

    def __init__(self, config_options={}):
        Logger.__init__(self, config_options)
        if "filename" in config_options:
            try:
                self.filename = config_options["filename"]
                self.file_handle = open(self.filename, "w+")
            except Exception, e:
                raise RuntimeError("Couldn't open log file %s for appending: %s" % (self.filename, e))
        else:
            raise RuntimeError("Missing filename for logfile")

        if "only_failures" in config_options:
            if config_options["only_failures"] == "1":
                self.only_failures = True

        if "buffered" in config_options:
            if config_options["buffered"] == "0":
                self.buffered = False

        if "dateformat" in config_options:
            self.dateformat = config_options['dateformat']

    def save_result2(self, name, monitor):
        if self.only_failures and monitor.virtual_fail_count() == 0:
            return

        dateformat = 'timestamp'
        if self.dateformat == 'iso8601':
            dateformat = 'iso8601'

        if dateformat == 'timestamp':
            datestring = str(int(time.time()))
        elif dateformat == 'iso8601':
            datestring = self.format_datetime(datetime.datetime.now())
        try:
            if monitor.virtual_fail_count() > 0:
                self.file_handle.write("%s %s: failed since %s; VFC=%d (%s) (%0.3fs)" % (
                    datestring,
                    name,
                    self.format_datetime(monitor.first_failure_time()),
                    monitor.virtual_fail_count(),
                    monitor.get_result(),
                    monitor.last_run_duration
                ))
            else:
                self.file_handle.write("%s %s: ok (%0.3fs)" % (
                    datestring,
                    name,
                    monitor.last_run_duration
                ))
            self.file_handle.write("\n")

            if not self.buffered:
                self.file_handle.flush()
        except Exception, e:
            print "Error writing to logfile %s: %s" % (self.filename, e)

    def hup(self):
        """Close and reopen log file."""
        self.file_handle.close()
        try:
            self.file_handle = open(self.filename, "w+")
        except Exception, e:
            raise RuntimeError("Couldn't reopen log file %s after HUP: %s" % (self.filename, e))


class HTMLLogger(Logger):
    """A batching logger which writes a simple HTML page of the current state."""

    supports_batch = True
    filename = ""
    count_data = ""

    def __init__(self, config_options={}):
        Logger.__init__(self, config_options)
        try:
            self.filename = config_options["filename"]
            self.header = config_options["header"]
            self.footer = config_options["footer"]
            self.folder = config_options["folder"]
        except Exception:
            print "Missing required value for HTML Logger"

    def save_result2(self, name, monitor):
        if not self.doing_batch:
            print "HTMLLogger.save_result2() called while not doing batch."
            return
        if monitor.virtual_fail_count() == 0:
            status = True
        else:
            status = False
        if not status:
            fail_time = self.format_datetime(monitor.first_failure_time())
            fail_count = monitor.virtual_fail_count()
            fail_data = monitor.get_result()
            downtime = self.get_downtime(monitor)
        else:
            fail_time = ""
            fail_count = 0
            fail_data = monitor.get_result()
            downtime = ""
        failures = monitor.failures
        last_failure = monitor.last_failure

        try:
            age = datetime.datetime.utcnow() - monitor.last_update
            age = age.days * 3600 + age.seconds
            update = monitor.last_update
        except Exception:
            age = 0
            update = ""

        data_line = {
            "status": status,
            "fail_time": fail_time,
            "fail_count": fail_count,
            "fail_data": fail_data,
            "downtime": downtime,
            "age": age,
            "update": update,
            "host": monitor.running_on,
            "failures": failures,
            "last_failure": last_failure
        }
        self.batch_data[monitor.name] = data_line

    def process_batch(self):
        """Save the HTML file."""
        ok_count = 0
        fail_count = 0
        old_count = 0
        remote_count = 0

        try:
            my_host = socket.gethostname().split(".")[0]
        except:
            my_host = socket.gethostname()

        try:
            temp_file = tempfile.mkstemp()
            file_handle = os.fdopen(temp_file[0], "w")
            file_name = temp_file[1]
        except:
            sys.stderr.write("Couldn't create temporary file for HTML output\n")
            return

        output_ok = cStringIO.StringIO()
        output_fail = cStringIO.StringIO()

        keys = self.batch_data.keys()
        keys.sort()
        for entry in keys:
            if self.batch_data[entry]["age"] > 120:
                status = "OLD"
                old_count += 1
            elif self.batch_data[entry]["status"]:
                status = "OK"
                ok_count += 1
            else:
                status = "FAIL"
                fail_count += 1
            if self.batch_data[entry]["host"] != my_host:
                remote_count += 1
            try:
                monitor_name = entry.split("/")[1]
            except:
                monitor_name = entry
            if status == "FAIL":
                output = output_fail
            else:
                output = output_ok
            output.write("<tr class=\"%srow\">" % status.lower())
            output.write("""
            <td class="monitor_name">%s</td>
            <td class="status %s">%s</td>
            <td>%s</td>
            <td>%s</td>
            """ % (
                monitor_name,
                status.lower(), status,
                self.batch_data[entry]["host"],
                self.batch_data[entry]["fail_time"],
            )
            )
            if self.batch_data[entry]["fail_count"] == 0:
                output.write("<td class=\"vfc\">&nbsp;</td>")
            else:
                output.write("<td class=\"vfc\">%s</td>" % self.batch_data[entry]["fail_count"])
            try:
                output.write("<td>%d+%02d:%02d:%02d</td>" % (self.batch_data[entry]["downtime"][0], self.batch_data[entry]["downtime"][1], self.batch_data[entry]["downtime"][2], self.batch_data[entry]["downtime"][3]))
            except:
                output.write("<td>&nbsp;</td>")
            output.write("<td>%s &nbsp;</td>" % (self.batch_data[entry]["fail_data"]))
            if self.batch_data[entry]["failures"] == 0:
                output.write("<td></td><td></td>")
            else:
                output.write("""<td>%s</td>
                <td>%s</td>""" % (
                    self.batch_data[entry]["failures"],
                    self.format_datetime(self.batch_data[entry]["last_failure"])
                )
                )
            if self.batch_data[entry]["host"] == my_host:
                output.write("<td></td>")
            else:
                output.write("<td>%d</td>" % self.batch_data[entry]["age"])
            output.write("</tr>\n")
        count_data = "<div id=\"summary\""
        if old_count > 0:
            cls = "old"
        elif fail_count > 0:
            cls = "fail"
        else:
            cls = "ok"

        count_data = count_data + " class=\"%s\">%s" % (cls, cls.upper())
        self.count_data = count_data + "<div id=\"details\"><span class=\"ok\">%d OK</span> <span class=\"fail\">%d FAIL</span> <span class=\"old\">%d OLD</span> <span class=\"remote\">%d remote</span></div></div>" % (ok_count, fail_count, old_count, remote_count)

        self.status = cls.upper()

        with open(os.path.join(self.folder, self.header), "r") as file_input:
            file_handle.writelines(self.parse_file(file_input))

        file_handle.write(output_fail.getvalue())
        file_handle.write(output_ok.getvalue())

        with open(os.path.join(self.folder, self.footer), "r") as file_input:
            file_handle.writelines(self.parse_file(file_input))

        try:
            file_handle.flush()
            file_handle.close()
            os.chmod(file_name, stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IROTH)
            shutil.move(file_name, os.path.join(self.folder, self.filename))
        except Exception, e:
            print "problem closing temporary file for HTML output", e

    def parse_file(self, file_handle):
        lines = []
        for line in file_handle:
            line = line.replace("_NOW_", self.format_datetime(datetime.datetime.now()))
            line = line.replace("_HOST_", socket.gethostname())
            line = line.replace("_COUNTS_", self.count_data)
            line = line.replace("_TIMESTAMP_", str(int(time.time())))
            line = line.replace("_STATUS_", self.status)
            lines.append(line)
        return lines
