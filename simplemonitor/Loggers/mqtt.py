# coding=utf-8

# Simplemonitor logger for MQTT
# It is intended to be used with Home Assistant and its MQTT Discovery feature
# (this the default topic)
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
    logger_type = "mqtt"
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
            str, self.get_config_option("username", required=False, allow_empty=True,),
        )
        # password for authentication
        self.password = cast(
            str, self.get_config_option("password", required=False, allow_empty=True,),
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
                        auth=self.auth,
                        client_id="simplemonitor_{monitor}".format(
                            monitor=monitor.name
                        ),
                    )
                except Exception as e:
                    self.logger_logger.error(
                        "cannot send %s to MQTT: %s", monitor.name, e
                    )
                else:
                    self.registered.append(monitor.name)
                    self.logger_logger.debug(
                        "registered %s in MQTT", device=monitor.name
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
                auth=self.auth,
                client_id="simplemonitor_{monitor}".format(monitor=monitor.name),
            )
        except Exception as e:
            self.logger_logger.error("cannot send state %s to %s %s", payload, topic, e)
        else:
            self.logger_logger.debug("state %s sent to %s", payload, topic)

    def describe(self) -> str:
        return "Sends monitoring status to a MQTT broker"
