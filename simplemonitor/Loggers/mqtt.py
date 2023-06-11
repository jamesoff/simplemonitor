"""
Simplemonitor logger for MQTT

It is intended to be used with Home Assistant and its MQTT Discovery feature
(this the default topic)
but can be used in any other context
contact: dev@swtk.info
"""

import json
from typing import List, Optional, cast

import paho.mqtt.publish

from ..Monitors.monitor import Monitor
from .logger import Logger, register


@register
class MQTTLogger(Logger):
    """Log to MQTT endpoints"""

    logger_type = "mqtt"
    only_failures = False
    buffered = False
    dateformat = None

    def __init__(self, config_options: Optional[dict] = None) -> None:
        if config_options is None:
            config_options = {}
        super().__init__(config_options)

        self.host = cast(
            str, self.get_config_option("host", required=True, allow_empty=False)
        )
        self.port = cast(
            int,
            self.get_config_option(
                "port",
                required=False,
                allow_empty=False,
                required_type="int",
                default=1883,
            ),
        )
        # specif configuration for Home Assistant MQTT discovery
        # https://www.home-assistant.io/docs/mqtt/discovery/
        self.hass = cast(
            bool,
            self.get_config_option(
                "hass",
                required=False,
                allow_empty=False,
                required_type="bool",
                default=False,
            ),
        )
        # topic to send information to
        self.topic = cast(
            str,
            self.get_config_option(
                "topic",
                required=False,
                allow_empty=False,
                default="simplemonitor"
                if not self.hass
                else "homeassistant/binary_sensor",
            ),
        )
        # username for authentication
        self.username = cast(
            str,
            self.get_config_option(
                "username",
                required=False,
                allow_empty=True,
            ),
        )
        # password for authentication
        self.password = cast(
            str,
            self.get_config_option(
                "password",
                required=False,
                allow_empty=True,
            ),
        )
        self.device_class = cast(
            str,
            self.get_config_option("device_class", default=""),
        )

        if self.username and self.password:
            self.auth = {"username": self.username, "password": self.password}
        else:
            self.auth = {}

        # registry of monitors which registered with HA
        # not used if not Home Assistant context
        # also see
        # https://github.com/jamesoff/simplemonitor/issues/236#issuecomment-462481900
        # for rationale
        self.registered = []  # type: List[str]

    def save_result2(self, name: str, monitor: Monitor) -> None:
        safe_name = monitor.name
        if self.hass:
            if " " in safe_name:
                self.logger_logger.warning(
                    (
                        "replacing spaces with underscores for monitor %s as spaces are "
                        "not supported for MQTT/HASS names"
                    ),
                    monitor.name,
                )
                safe_name = monitor.name.replace(" ", "_")
            if monitor.name not in self.registered:
                self.logger_logger.info(
                    "attempting to register MQTT config topic for monitor %s", name
                )
                config_payload = {
                    "name": monitor.name,
                    "state_topic": "{root}/simplemonitor_{monitor}/state".format(
                        root=self.topic, monitor=safe_name
                    ),
                }
                if self.device_class:
                    config_payload["device_class"] = self.device_class
                try:
                    paho.mqtt.publish.single(
                        "{root}/simplemonitor_{monitor}/config".format(
                            root=self.topic,
                            monitor=safe_name,
                        ),
                        payload=json.dumps(config_payload),
                        retain=True,
                        hostname=self.host,
                        port=self.port,
                        auth=self.auth,
                        client_id="simplemonitor_{monitor}".format(
                            monitor=safe_name,
                        ),
                    )
                except Exception:
                    self.logger_logger.exception("cannot send %s to MQTT", monitor.name)
                else:
                    self.registered.append(monitor.name)
                    self.logger_logger.debug("registered %s in MQTT", safe_name)

        if self.only_failures and monitor.virtual_fail_count() == 0:
            return

        if self.hass:
            topic = "{root}/simplemonitor_{monitor}/state".format(
                root=self.topic, monitor=safe_name
            )
        else:
            topic = "{root}/{monitor}".format(root=self.topic, monitor=safe_name)
        self.logger_logger.debug(
            "%s failed %d times", monitor.name, monitor.virtual_fail_count()
        )
        payload = (
            "ON"
            if monitor.virtual_fail_count() == 0 and not monitor.was_skipped
            else "OFF"
        )
        try:
            paho.mqtt.publish.single(
                topic,
                payload=payload,
                retain=True,
                hostname=self.host,
                port=self.port,
                auth=self.auth,
                client_id="simplemonitor_{monitor}".format(monitor=safe_name),
            )
        except Exception:
            self.logger_logger.exception("cannot send state %s to %s", payload, topic)
        else:
            self.logger_logger.debug("state %s sent to %s", payload, topic)

    def describe(self) -> str:
        return "Sends monitoring status to a MQTT broker"
