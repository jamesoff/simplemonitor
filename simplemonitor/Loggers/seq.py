# coding=utf-8

# Simplemonitor logger for seq
# Inspiration from https://raw.githubusercontent.com/eifinger/appdaemon-scripts/master/seqSink/seqSink.py
# Python 3 only

try:
    import json
    import requests
    import datetime

    from typing import cast

    from ..Monitors.monitor import Monitor
    from .logger import Logger, register

    is_available = True

except ImportError:
    is_available = False


@register
class SeqLogger(Logger):
    logger_type = "seq"
    only_failures = False
    buffered = False
    dateformat = None

    def __init__(self, config_options: dict = None) -> None:
        if config_options is None:
            config_options = {}
        super().__init__(config_options)

        if not is_available:
            self.logger_logger.error("Missing modules!")
            return

        # i.e. http://192.168.0.5:5341
        self.endpoint = cast(
            str, self.get_config_option("endpoint", required=True, allow_empty=False)
        )
        # Potentially, would need to add a header for ApiKey

        # Send message to indicate we have started logging
        self.log_to_seq(self.endpoint, 'SeqLogger', 'simpleMonitor', '__init__', None, 'logging enabled for simpleMonitor', False)

    def save_result2(self, name: str, monitor: Monitor) -> None:
        try:
            is_fail = monitor.test_success() is False

            self.log_to_seq(self.endpoint, name, monitor.name, monitor.monitor_type, str(monitor.get_params()), monitor.describe(), is_fail)
        except Exception:
            self.logger_logger.exception("Error sending to seq in %s", monitor.name)

    def describe(self) -> str:
        return "Sends simple log to seq using raw endpoint"
        # From https://raw.githubusercontent.com/eifinger/appdaemon-scripts/master/seqSink/seqSink.py

    def log_to_seq(self, endpoint, name, app_name, monitor_type, params, description, is_fail):
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
     
        print(is_fail)
        print(request_body)

        try:
            request_body_json = json.dumps(request_body)  # This just checks it is valid...
        except TypeError:
            self.log(f"Could not serialize {request_body}")
            return
    
        try:
            r = requests.post(self.endpoint, json=request_body)
            if not r.status_code == 200 and not r.status_code == 201:
                self.alerter_logger.error("POST to slack webhook failed: %s", r)
        except Exception:
            self.alerter_logger.exception("Failed to log to seq")

