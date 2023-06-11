"""
Simplemonitor logger for seq

Inspiration from
https://raw.githubusercontent.com/eifinger/appdaemon-scripts/master/seqSink/seqSink.py
"""

import datetime
import json
from typing import Optional, cast

import requests

from ..Monitors.monitor import Monitor
from .logger import Logger, register


@register
class SeqLogger(Logger):
    """Logging to seq"""

    logger_type = "seq"
    only_failures = False
    buffered = False
    dateformat = None

    def __init__(self, config_options: Optional[dict] = None) -> None:
        if config_options is None:
            config_options = {}
        super().__init__(config_options)

        # i.e. http://192.168.0.5:5341
        self.endpoint = cast(
            str, self.get_config_option("endpoint", required=True, allow_empty=False)
        )
        self.timeout = cast(
            int, self.get_config_option("timeout", required_type="int", default=5)
        )
        # Potentially, would need to add a header for ApiKey

        # Send message to indicate we have started logging
        self.log_to_seq(
            self.endpoint,
            "SeqLogger",
            "simpleMonitor",
            "__init__",
            None,
            "logging enabled for simpleMonitor",
            False,
        )

    def save_result2(self, name: str, monitor: Monitor) -> None:
        try:
            is_fail = monitor.test_success() is False

            self.log_to_seq(
                self.endpoint,
                name,
                monitor.name,
                monitor.monitor_type,
                str(monitor.get_params()),
                monitor.describe(),
                is_fail,
            )
        except Exception:
            self.logger_logger.exception("Error sending to seq in %s", monitor.name)

    def describe(self) -> str:
        return "Sends simple log to seq using raw endpoint"

    def log_to_seq(
        self, endpoint, name, app_name, monitor_type, params, description, is_fail
    ):
        """Send an event to seq"""
        event_data = {
            "Timestamp": str(datetime.datetime.now()),
            "Level": "Error" if is_fail is True else "Information",
            "MessageTemplate": str(description),
            "Properties": {
                "Type": "simpleMonitor",
                "Name": name,
                "Monitor": str(app_name),
                "MonitorType": monitor_type,
                # "Params": params
            },
        }
        if params is not None:
            event_data["Properties"]["Params"] = params

        request_body = {"Events": [event_data]}

        try:
            _ = json.dumps(request_body)  # This just checks it is valid...
        except TypeError:
            self.logger_logger.error("Could not serialise %s", request_body)
            return

        try:
            response = requests.post(
                self.endpoint, json=request_body, timeout=self.timeout
            )
            if not response.status_code == 200 and not response.status_code == 201:
                self.logger_logger.error(
                    "POST to seq failed with status code: %s", response
                )
        except requests.RequestException:
            self.logger_logger.exception("Failed to log to seq")
