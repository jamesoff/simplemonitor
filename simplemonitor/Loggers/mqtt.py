# coding=utf-8

# Simplemonitor logger for MQTT
# It is intended to be used with Home Assistant and its MQTT Discovery feature (this the default topic)
# but can be used in any other context
# Python 3 only
# contact: dev@swtk.info

try:
    import paho.mqtt.publish

    mqtt_available = True
except ImportError:
    mqtt_available = False
import json
from typing import List, cast

from ..Monitors.monitor import Monitor
from .logger import Logger, register


@register
class MQTTLogger(Logger):
    type = "mqtt"
    only_failures = False
    buffered = False
    dateformat = None

    def __init__(self, config_options: dict = None) -> None:
        if config_options is None:
            config_options = {}
        super().__init__(config_options)

        if not mqtt_available:
            self.logger_logger.error("Missing paho.mqtt module!")
            return

        # TODO: add configuration for authenticated calls, port, will, etc.
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

        # registry of monitors which registered with HA
        # not used if not Home Assistant context
        # also see https://github.com/jamesoff/simplemonitor/issues/236#issuecomment-462481900 for rationale
        self.registered = []  # type: List[str]

    def save_result2(self, name: str, monitor: Monitor) -> None:
        # check if monitor registred with HA
        if self.hass:
            if monitor.name not in self.registered:
                try:
                    paho.mqtt.publish.single(
                        "{root}/simplemonitor_{monitor}/config".format(
                            root=self.topic, monitor=monitor.name
                        ),
                        payload=json.dumps({"name": monitor.name}),
                        retain=True,
                        hostname=self.host,
                        client_id="simplemonitor_{monitor}".format(
                            monitor=monitor.name
                        ),
                    )
                except Exception as e:
                    self.logger_logger.error(
                        "cannot send {device} to MQTT: {e}".format(
                            device=monitor.name, e=e
                        )
                    )
                else:
                    self.registered.append(monitor.name)
                    self.logger_logger.debug(
                        "registered {device} in MQTT".format(device=monitor.name)
                    )

        if self.only_failures and monitor.virtual_fail_count() == 0:
            return

        if self.hass:
            topic = "{root}/simplemonitor_{monitor}/state".format(
                root=self.topic, monitor=monitor.name
            )
        else:
            topic = "{root}/{monitor}".format(root=self.topic, monitor=monitor.name)
        self.logger_logger.debug(
            "{monitor} failed {n} times".format(
                monitor=monitor.name, n=monitor.virtual_fail_count()
            )
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
                client_id="simplemonitor_{monitor}".format(monitor=monitor.name),
            )
        except Exception as e:
            self.logger_logger.error(
                "cannot send state {payload} to {topic}: {e}".format(
                    payload=payload, topic=topic, e=e
                )
            )
        else:
            self.logger_logger.debug(
                "state {state} sent to {topic}".format(state=payload, topic=topic)
            )

    def describe(self) -> str:
        return "Sends monitoring status to a MQTT broker"
