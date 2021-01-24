# coding=utf-8
import json
import os
import shutil
import socket
import stat
import subprocess  # nosec
import sys
import tempfile
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

import arrow
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..Monitors.monitor import Monitor
from ..util import format_datetime, short_hostname
from ..version import VERSION
from .logger import Logger, register

if TYPE_CHECKING:
    import datetime


@register
class FileLogger(Logger):
    """Log monitor status to a file."""

    logger_type = "logfile"
    filename = ""
    only_failures = False
    buffered = True
    dateformat = None

    def __init__(self, config_options: Optional[Dict[str, Any]] = None) -> None:
        if config_options is None:
            config_options = {}
        super().__init__(config_options)
        self.filename = self.get_config_option(
            "filename", required=True, allow_empty=False
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

        self.file_handle.write(
            "{} simplemonitor starting\n".format(self._get_datestring())
        )
        if not self.buffered:
            self.file_handle.flush()

    def __del__(self) -> None:
        self.file_handle.close()

    def _get_datestring(self) -> str:
        if self.dateformat == "iso8601":
            return format_datetime(arrow.now(), self.tz)
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
                        format_datetime(monitor.first_failure_time(), self.tz),
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
        except OSError:
            self.logger_logger.exception("Error writing to logfile %s", self.filename)

    def hup(self) -> None:
        """Close and reopen log file."""
        try:
            self.file_handle.close()
            self.file_handle = open(self.filename, "a+")
        except OSError:
            self.logger_logger.exception(
                "Couldn't reopen log file %s after HUP", self.filename
            )

    def describe(self) -> str:
        return "Writing log file to {0}".format(self.filename)


@register
class HTMLLogger(Logger):
    """A batching logger which writes a simple HTML page of the current state."""

    logger_type = "html"
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
            self.logger_logger.critical("output folder %s does not exist", self.folder)
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
        self.map = cast(
            bool, self.get_config_option("map", required_type="bool", default=False)
        )
        self._resource_files = ["style.css"]  # type: List[str]
        self._my_host = short_hostname()
        self.status = ""
        self.header_class = ""
        self._env = Environment(
            loader=FileSystemLoader(self.source_folder),
            keep_trailing_newline=True,
            autoescape=select_autoescape("html"),
        )

    def save_result2(self, name: str, monitor: Monitor) -> None:
        if not self.doing_batch:
            self.logger_logger.error(
                "HTMLLogger.save_result2() called while not doing batch."
            )
            return
        if self.batch_data is None:
            self.batch_data = {}
        status = bool(monitor.virtual_fail_count() == 0)
        if not status:
            fail_time = format_datetime(monitor.first_failure_time(), self.tz)
            fail_count = monitor.virtual_fail_count()
            fail_data = monitor.get_result()
            downtime = monitor.get_downtime()
        else:
            fail_time = ""
            fail_count = 0
            fail_data = monitor.get_result()
            downtime = monitor.get_uptime()  # yes, I know
        failures = monitor.failures
        last_failure = format_datetime(monitor.last_failure, self.tz)
        gap = monitor.minimum_gap
        if gap == 0:
            # TODO: figure out a good way to know the interval value for both local and
            # remote monitors
            gap = 60

        try:
            if monitor.last_update is not None:
                age = arrow.utcnow() - monitor.last_update  # type: datetime.timedelta
                age_seconds = age.days * 3600 + age.seconds
                update = str(monitor.last_update)
            else:
                raise ValueError
        except ValueError:
            age_seconds = 0
            update = ""
        row_class = ""
        cell_class = ""
        if not monitor.enabled:
            status_text = "DISABLED"
        elif age_seconds > gap + 60:
            status_text = "OLD"
            cell_class = "table-warning"
        elif status:
            status_text = "OK"
            cell_class = "table-success"
        else:
            status_text = "FAIL"
            row_class = "table-danger"

        data_line = {
            "monitor_name": monitor.name,
            "status": status,
            "status_text": status_text,
            "row_class": row_class,
            "cell_class": cell_class,
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
            "availability": monitor.availability,
            "description": monitor.describe(),
            "link": monitor.failure_doc,
            "enabled": monitor.enabled,
            "my_host": True if monitor.running_on == self._my_host else False,
        }  # type: Dict[str, Any]
        self.batch_data[monitor.name] = data_line

    def process_batch(self) -> None:
        """Save the HTML file."""
        ok_count = 0
        fail_count = 0
        old_count = 0
        remote_count = 0
        disabled_count = 0

        try:
            temp_file = tempfile.mkstemp()
            file_handle = os.fdopen(temp_file[0], "w")
            file_name = temp_file[1]
        except OSError:
            self.logger_logger.exception(
                "Couldn't create temporary file for HTML output"
            )
            return

        fail_entries = []  # type: List[Dict[str, Any]]
        ok_entries = []  # type: List[Dict[str, Any]]

        if self.batch_data is None:
            return
        keys = list(self.batch_data.keys())
        keys.sort()
        for entry in keys:
            this_entry = self.batch_data[entry]
            this_list = ok_entries
            if not this_entry["enabled"]:
                disabled_count += 1
            elif this_entry["age"] > this_entry["gap"] + 60:
                old_count += 1
            elif this_entry["status"]:
                ok_count += 1
            else:
                fail_count += 1
                this_list = fail_entries
            if this_entry["host"] != self._my_host:
                remote_count += 1
            # output.write(self._make_html_row(entry, this_entry))
            this_list.append(this_entry)
        if old_count > 0:
            self.header_class = "border-warning"
            self.status = "OLD"
        elif fail_count > 0:
            self.header_class = "border-danger"
            self.status = "FAIL"
        else:
            self.header_class = "border-success"
            self.status = "OK"

        template = self._env.get_template("status-template.html")
        if self._global_info:
            interval = max(30, self._global_info["interval"])
        else:
            interval = 30
        file_handle.write(
            template.render(
                status=self.status,
                status_border=self.header_class,
                host=socket.gethostname(),
                interval=interval,
                timestamp=str(arrow.now().int_timestamp),
                now=format_datetime(arrow.now(), self.tz),
                version=VERSION,
                ok_count=ok_count,
                fail_count=fail_count,
                disabled_count=disabled_count,
                old_count=old_count,
                remote_count=remote_count,
                fail_entries=fail_entries,
                ok_entries=ok_entries,
            )
        )

        try:
            file_handle.flush()
            file_handle.close()
            os.chmod(
                file_name, stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IROTH
            )
            if not os.path.isdir(self.folder):
                self.logger_logger.critical(
                    "Target folder %s does not exist", self.folder
                )
                return
            shutil.move(file_name, os.path.join(self.folder, self.filename))
            if self.copy_resources:
                for filename in self._resource_files:
                    shutil.copy(os.path.join(self.source_folder, filename), self.folder)
        except OSError:
            self.logger_logger.exception(
                "problem closing/moving temporary file for HTML output"
            )
        if self.upload_command:
            try:
                subprocess.run(self.upload_command.split(" "), check=True)  # nosec
            except subprocess.SubprocessError:
                self.logger_logger.exception(
                    "Failed to run upload command for HTML files"
                )

    def describe(self) -> str:
        return "Writing HTML page to {0}".format(self.filename)


class MonitorResult(object):
    """Represent the current status of a Monitor."""

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
    def default(self, o: Any) -> Any:
        if hasattr(o, "json_representation"):
            return o.json_representation()
        return json.JSONEncoder.default(self, o.__dict__)


@register
class JsonLogger(Logger):
    """Write monitor status to a JSON file."""

    logger_type = "json"
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
        result.dependencies = monitor.dependencies

        self.batch_data[name] = result

    def process_batch(self) -> None:
        payload = MonitorJsonPayload()
        payload.generated = format_datetime(arrow.now())
        if self.batch_data is not None:
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
