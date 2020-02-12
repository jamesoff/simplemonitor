# coding=utf-8
import datetime
import json
import os
import shutil
import socket
import stat
import subprocess  # nosec
import sys
import tempfile
import time
from io import StringIO
from typing import Any, List, Optional, TextIO, cast

from ..Monitors.monitor import Monitor
from ..util import format_datetime, short_hostname
from .logger import Logger, register


@register
class FileLogger(Logger):
    type = "logfile"
    filename = ""
    only_failures = False
    buffered = True
    dateformat = None

    def __init__(self, config_options: dict = None) -> None:
        if config_options is None:
            config_options = {}
        super().__init__(config_options)
        self.filename = self.get_config_option(
            "filename", required=True, allow_empty=False
        )
        try:
            self.file_handle = open(self.filename, "a+")
        except Exception as e:
            raise RuntimeError(
                "Couldn't open log file %s for appending: %s" % (self.filename, e)
            )
        self.file_handle = open(self.filename, "a+")

        self.only_failures = self.get_config_option(
            "only_failures", required_type="bool", default=False
        )

        self.buffered = self.get_config_option(
            "buffered", required_type="bool", default=True
        )

        self.dateformat = cast(
            str,
            self.get_config_option(
                "dateformat",
                required_type="str",
                allowed_values=["timestamp", "iso8601"],
                default="timestamp",
            ),
        )

        self.file_handle.write("%s: simplemonitor starting" % self._get_datestring())

    def _get_datestring(self) -> str:
        if self.dateformat == "iso8601":
            return format_datetime(datetime.datetime.now())
        return str(int(time.time()))

    def save_result2(self, name: str, monitor: Monitor) -> None:
        if self.only_failures and monitor.virtual_fail_count() == 0:
            return

        try:
            if monitor.virtual_fail_count() > 0:
                self.file_handle.write(
                    "%s %s: failed since %s; VFC=%d (%s) (%0.3fs)"
                    % (
                        self._get_datestring(),
                        name,
                        format_datetime(monitor.first_failure_time()),
                        monitor.virtual_fail_count(),
                        monitor.get_result(),
                        monitor.last_run_duration,
                    )
                )
            else:
                self.file_handle.write(
                    "%s %s: ok (%0.3fs)"
                    % (self._get_datestring(), name, monitor.last_run_duration)
                )
            self.file_handle.write("\n")

            if not self.buffered:
                self.file_handle.flush()
        except Exception:
            self.logger_logger.exception("Error writing to logfile %s", self.filename)

    def hup(self) -> None:
        """Close and reopen log file."""
        self.file_handle.close()
        try:
            self.file_handle = open(self.filename, "a+")
        except Exception as e:
            raise RuntimeError(
                "Couldn't reopen log file %s after HUP: %s" % (self.filename, e)
            )

    def describe(self) -> str:
        return "Writing log file to {0}".format(self.filename)


@register
class HTMLLogger(Logger):
    """A batching logger which writes a simple HTML page of the current state."""

    type = "html"
    supports_batch = True
    filename = ""
    count_data = ""

    def __init__(self, config_options: dict = None) -> None:
        if config_options is None:
            config_options = {}
        super().__init__(config_options)
        package_data_dir = os.path.join(
            os.path.dirname(sys.modules["simplemonitor"].__file__), "html"
        )
        self.filename = cast(
            str, self.get_config_option("filename", required=True, allow_empty=False)
        )
        self.header = cast(
            str,
            self.get_config_option(
                "header", required=False, allow_empty=False, default="header.html"
            ),
        )
        self.footer = cast(
            str,
            self.get_config_option(
                "footer", required=False, allow_empty=False, default="footer.html"
            ),
        )
        self.source_folder = cast(
            str,
            self.get_config_option(
                "source_folder", required=False, default=package_data_dir
            ),
        )
        self.folder = cast(
            str, self.get_config_option("folder", required=False, default="html")
        )
        if not os.path.isdir(self.folder):
            self.logger_logger.critical(
                "output folder {} does not exist".format(self.folder)
            )
        self.copy_resources = cast(
            bool,
            self.get_config_option(
                "copy_resources", required_type="bool", default=True
            ),
        )
        self.upload_command = cast(
            str,
            self.get_config_option("upload_command", required=False, allow_empty=False),
        )
        self._resource_files = ["style.css"]  # type: List[str]

    def save_result2(self, name: str, monitor: Monitor) -> None:
        if not self.doing_batch:
            self.logger_logger.error(
                "HTMLLogger.save_result2() called while not doing batch."
            )
            return
        if self.batch_data is None:
            self.batch_data = {}
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
            downtime = (0, 0, 0, 0)
        failures = monitor.failures
        last_failure = monitor.last_failure
        gap = monitor.minimum_gap
        if gap == 0:
            gap = (
                60
            )  # TODO: figure out a good way to know the interval value for both local and remote monitors

        try:
            if monitor.last_update is not None:
                age = datetime.datetime.utcnow() - monitor.last_update
                age_seconds = age.days * 3600 + age.seconds
                update = str(monitor.last_update)
            else:
                raise ValueError
        except ValueError:
            age_seconds = 0
            update = ""

        data_line = {
            "status": status,
            "fail_time": fail_time,
            "fail_count": fail_count,
            "fail_data": fail_data,
            "downtime": downtime,
            "age": age_seconds,
            "update": update,
            "host": monitor.running_on,
            "failures": failures,
            "last_failure": last_failure,
            "gap": gap,
        }
        self.batch_data[monitor.name] = data_line

    def process_batch(self) -> None:
        """Save the HTML file."""
        ok_count = 0
        fail_count = 0
        old_count = 0
        remote_count = 0

        my_host = short_hostname()

        try:
            temp_file = tempfile.mkstemp()
            file_handle = os.fdopen(temp_file[0], "w")
            file_name = temp_file[1]
        except Exception:
            self.logger_logger.exception(
                "Couldn't create temporary file for HTML output"
            )
            return

        output_ok = StringIO()
        output_fail = StringIO()

        if self.batch_data is None:
            return
        keys = list(self.batch_data.keys())
        keys.sort()
        for entry in keys:
            if self.batch_data[entry]["age"] > self.batch_data[entry]["gap"] + 60:
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
            output.write('<tr class="%srow">' % status.lower())
            output.write(
                """
            <td class="monitor_name">%s</td>
            <td class="status %s">%s</td>
            <td>%s</td>
            <td>%s</td>
            """
                % (
                    monitor_name,
                    status.lower(),
                    status,
                    self.batch_data[entry]["host"],
                    self.batch_data[entry]["fail_time"],
                )
            )
            if self.batch_data[entry]["fail_count"] == 0:
                output.write('<td class="vfc">&nbsp;</td>')
            else:
                output.write(
                    '<td class="vfc">%s</td>' % self.batch_data[entry]["fail_count"]
                )
            try:
                output.write(
                    "<td>%d+%02d:%02d:%02d</td>"
                    % (
                        self.batch_data[entry]["downtime"][0],
                        self.batch_data[entry]["downtime"][1],
                        self.batch_data[entry]["downtime"][2],
                        self.batch_data[entry]["downtime"][3],
                    )
                )
            except Exception:
                output.write("<td>&nbsp;</td>")
            output.write("<td>%s &nbsp;</td>" % (self.batch_data[entry]["fail_data"]))
            if self.batch_data[entry]["failures"] == 0:
                output.write("<td></td><td></td>")
            else:
                output.write(
                    """<td>%s</td>
                <td>%s</td>"""
                    % (
                        self.batch_data[entry]["failures"],
                        format_datetime(self.batch_data[entry]["last_failure"]),
                    )
                )
            if self.batch_data[entry]["host"] == my_host:
                output.write("<td></td>")
            else:
                output.write("<td>%d</td>" % self.batch_data[entry]["age"])
            output.write("</tr>\n")
        count_data = '<div id="summary"'
        if old_count > 0:
            cls = "old"
        elif fail_count > 0:
            cls = "fail"
        else:
            cls = "ok"

        count_data = count_data + ' class="%s">%s' % (cls, cls.upper())
        self.count_data = (
            count_data
            + '<div id="details"><span class="ok">%d OK</span> <span class="fail">%d FAIL</span> <span class="old">%d OLD</span> <span class="remote">%d remote</span></div></div>'
            % (ok_count, fail_count, old_count, remote_count)
        )

        self.status = cls.upper()

        with open(os.path.join(self.source_folder, self.header), "r") as file_input:
            file_handle.writelines(self.parse_file(file_input))

        file_handle.write(output_fail.getvalue())
        file_handle.write(output_ok.getvalue())

        with open(os.path.join(self.source_folder, self.footer), "r") as file_input:
            file_handle.writelines(self.parse_file(file_input))

        try:
            file_handle.flush()
            file_handle.close()
            os.chmod(
                file_name, stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IROTH
            )
            if not os.path.isdir(self.folder):
                self.logger_logger.critical(
                    "Target folder {} does not exist".format(self.folder)
                )
                return
            shutil.move(file_name, os.path.join(self.folder, self.filename))
            if self.copy_resources:
                for filename in self._resource_files:
                    shutil.copy(os.path.join(self.source_folder, filename), self.folder)
        except Exception:
            self.logger_logger.exception(
                "problem closing/moving temporary file for HTML output"
            )
        if self.upload_command:
            try:
                subprocess.run(self.upload_command.split(" "))  # nosec
            except Exception:
                self.logger_logger.exception(
                    "Failed to run upload command for HTML files"
                )

    def parse_file(self, file_handle: TextIO) -> List[str]:
        lines = []  # type: List[str]
        for line in file_handle:
            line = line.replace("_NOW_", format_datetime(datetime.datetime.now()))
            line = line.replace("_HOST_", socket.gethostname())
            line = line.replace("_COUNTS_", self.count_data)
            line = line.replace("_TIMESTAMP_", str(int(time.time())))
            line = line.replace("_STATUS_", self.status)
            lines.append(line)
        return lines

    def describe(self) -> str:
        return "Writing HTML page to {0}".format(self.filename)


class MonitorResult(object):
    def __init__(self) -> None:
        self.virtual_fail_count = 0
        self.result = None  # type: Optional[str]
        self.first_failure_time = None  # type: Optional[str]
        self.last_run_duration = None  # type: Optional[int]
        self.status = "Fail"
        self.dependencies = []  # type: List[str]

    def json_representation(self) -> dict:
        return self.__dict__


class MonitorJsonPayload(object):
    def __init__(self) -> None:
        self.generated = None  # type: Optional[str]
        self.monitors = {}  # type: dict

    def json_representation(self) -> dict:
        return self.__dict__


class PayloadEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if hasattr(obj, "json_representation"):
            return obj.json_representation()
        else:
            return json.JSONEncoder.default(self, obj.__dict__)


@register
class JsonLogger(Logger):
    type = "json"
    filename = ""  # type: str
    supports_batch = True

    def __init__(self, config_options: dict = None) -> None:
        if config_options is None:
            config_options = {}
        super().__init__(config_options)
        self.filename = self.get_config_option(
            "filename", required=True, allow_empty=False
        )

    def save_result2(self, name: str, monitor: Monitor) -> None:
        if self.batch_data is None:
            self.batch_data = {}
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

    def process_batch(self) -> None:
        payload = MonitorJsonPayload()
        payload.generated = format_datetime(datetime.datetime.now())
        assert self.batch_data is not None
        payload.monitors = self.batch_data

        with open(self.filename, "w") as outfile:
            json.dump(
                payload,
                outfile,
                indent=4,
                separators=(",", ":"),
                ensure_ascii=False,
                cls=PayloadEncoder,
            )
        self.batch_data = {}

    def describe(self) -> str:
        return "Writing JSON file to {0}".format(self.filename)
