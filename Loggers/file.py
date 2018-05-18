# coding=utf-8
from __future__ import with_statement

import os
import datetime
import time
import socket
import tempfile
import shutil
import stat
import sys
import json

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from util import format_datetime
from .logger import Logger


class FileLogger(Logger):

    filename = ""
    only_failures = False
    buffered = True
    dateformat = None

    def __init__(self, config_options=None):
        if config_options is None:
            config_options = {}
        Logger.__init__(self, config_options)
        if "filename" in config_options:
            try:
                self.filename = config_options["filename"]
                self.file_handle = open(self.filename, "a+")
            except Exception as e:
                raise RuntimeError("Couldn't open log file %s for appending: %s" % (self.filename, e))
        else:
            raise RuntimeError("Missing filename for logfile")
        self.filename = Logger.get_config_option(
            config_options,
            'filename',
            required=True,
            allow_empty=False
        )
        self.file_handle = open(self.filename, 'a+')

        self.only_failures = Logger.get_config_option(
            config_options,
            'only_failures',
            required_type='bool',
            default=False
        )

        self.buffered = Logger.get_config_option(
            config_options,
            'buffered',
            required_type='bool',
            default=True
        )

        self.dateformat = Logger.get_config_option(
            config_options,
            'dateformat'
        )

    def save_result2(self, name, monitor):
        if self.only_failures and monitor.virtual_fail_count() == 0:
            return

        dateformat = 'timestamp'
        if self.dateformat == 'iso8601':
            dateformat = 'iso8601'

        if dateformat == 'timestamp':
            datestring = str(int(time.time()))
        elif dateformat == 'iso8601':
            datestring = format_datetime(datetime.datetime.now())
        try:
            if monitor.virtual_fail_count() > 0:
                self.file_handle.write("%s %s: failed since %s; VFC=%d (%s) (%0.3fs)" % (
                    datestring,
                    name,
                    format_datetime(monitor.first_failure_time()),
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
        except Exception as e:
            self.logger_logger.exception("Error writing to logfile %s", self.filename)

    def hup(self):
        """Close and reopen log file."""
        self.file_handle.close()
        try:
            self.file_handle = open(self.filename, "a+")
        except Exception as e:
            raise RuntimeError("Couldn't reopen log file %s after HUP: %s" % (self.filename, e))

    def describe(self):
        return "Writing log file to {0}".format(self.filename)


class HTMLLogger(Logger):
    """A batching logger which writes a simple HTML page of the current state."""

    supports_batch = True
    filename = ""
    count_data = ""

    def __init__(self, config_options={}):
        Logger.__init__(self, config_options)
        self.filename = Logger.get_config_option(
            config_options,
            'filename',
            required=True,
            allow_empty=False
        )
        self.header = Logger.get_config_option(
            config_options,
            'header',
            required=True,
            allow_empty=False
        )
        self.footer = Logger.get_config_option(
            config_options,
            'footer',
            required=True,
            allow_empty=False
        )
        self.folder = Logger.get_config_option(
            config_options,
            'folder',
            required=True,
            allow_empty=False
        )

    def save_result2(self, name, monitor):
        if not self.doing_batch:
            self.logger_logger.error("HTMLLogger.save_result2() called while not doing batch.")
            return
        if monitor.virtual_fail_count() == 0:
            status = True
        else:
            status = False
        if not status:
            fail_time = format_datetime(monitor.first_failure_time())
            fail_count = monitor.virtual_fail_count()
            fail_data = monitor.get_result()
            downtime = monitor.get_downtime()
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
        except Exception:
            my_host = socket.gethostname()

        try:
            temp_file = tempfile.mkstemp()
            file_handle = os.fdopen(temp_file[0], "w")
            file_name = temp_file[1]
        except Exception:
            sys.stderr.write("Couldn't create temporary file for HTML output\n")
            return

        output_ok = StringIO()
        output_fail = StringIO()

        keys = list(self.batch_data.keys())
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
            except Exception:
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
            except Exception:
                output.write("<td>&nbsp;</td>")
            output.write("<td>%s &nbsp;</td>" % (self.batch_data[entry]["fail_data"]))
            if self.batch_data[entry]["failures"] == 0:
                output.write("<td></td><td></td>")
            else:
                output.write("""<td>%s</td>
                <td>%s</td>""" % (
                    self.batch_data[entry]["failures"],
                    format_datetime(self.batch_data[entry]["last_failure"])
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
        except Exception as e:
            self.logger_logger.exception("problem closing temporary file for HTML output")

    def parse_file(self, file_handle):
        lines = []
        for line in file_handle:
            line = line.replace("_NOW_", format_datetime(datetime.datetime.now()))
            line = line.replace("_HOST_", socket.gethostname())
            line = line.replace("_COUNTS_", self.count_data)
            line = line.replace("_TIMESTAMP_", str(int(time.time())))
            line = line.replace("_STATUS_", self.status)
            lines.append(line)
        return lines

    def describe(self):
        return "Writing HTML page to {0}".format(self.filename)


class MonitorResult(object):

    def __init__(self):
        self.virtual_fail_count = 0
        self.result = None
        self.first_failure_time = None
        self.last_run_duration = None
        self.status = "Fail"
        self.dependencies = []

    def json_representation(self):
        return self.__dict__


class MonitorJsonPayload(object):
    def __init__(self):
        self.generated = None
        self.monitors = {}

    def json_representation(self):
        return self.__dict__


class PayloadEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'json_representation'):
            return obj.json_representation()
        else:
            return json.JSONEncoder.default(self, obj.__dict__)


class JsonLogger(Logger):

    filename = ""
    supports_batch = True

    def __init__(self, config_options={}):
        Logger.__init__(self, config_options)
        self.filename = Logger.get_config_option(
            config_options,
            'filename',
            required=True,
            allow_empty=False
        )

    def save_result2(self, name, monitor):
        result = MonitorResult()
        result.first_failure_time = format_datetime(monitor.first_failure_time())
        result.virtual_fail_count = monitor.virtual_fail_count()
        result.last_run_duration = monitor.last_run_duration
        result.result = monitor.get_result()
        if hasattr(monitor, "was_skipped") and monitor.was_skipped:
            result.status = "Skipped"
        elif monitor.virtual_fail_count() <= 0:
            result.status = "OK"
        result.dependencies = monitor._dependencies

        self.batch_data[name] = result

    def process_batch(self):
        payload = MonitorJsonPayload()
        payload.generated = format_datetime(datetime.datetime.now())
        payload.monitors = self.batch_data

        with open(self.filename, 'w') as outfile:
            json.dump(payload, outfile,
                      indent=4,
                      separators=(',', ':'),
                      ensure_ascii=False,
                      cls=PayloadEncoder)
        self.batch_data = {}

    def describe(self):
        return "Writing JSON file to {0}".format(self.filename)
