# coding=utf-8

# Simplemonitor logger for MQTT
# It is intended to be used with Home Assistant and its MQTT Discovery feature (this the default topic)
# but can be used in any other context
# Python 3 only
# contact: dev@swtk.info

import sys
import paho.mqtt.publish
import json

from .logger import Logger, register


@register
class MQTTLogger(Logger):
    type = "mqtt"
    only_failures = False
    buffered = False
    dateformat = None

    def __init__(self, config_options=None):
        if config_options is None:
            config_options = {}
        Logger.__init__(self, config_options)

        # early check for Python version, only 3.x is supported (by me at least :))
        if sys.version_info[0] != 3:
            self.logger_logger.error("only supported on Python 3")
            return

        # TODO: add configuration for authenticated calls, port, will, etc.
        self.host = Logger.get_config_option(
            config_options,
            'host',
            required=True,
            allow_empty=False
        )
        self.port = Logger.get_config_option(
            config_options,
            'port',
            required=False,
            allow_empty=False,
            required_type='int',
            default=1883
        )
        # specif configuration for Home Assistant MQTT discovery
        # https://www.home-assistant.io/docs/mqtt/discovery/
        self.hass = Logger.get_config_option(
            config_options,
            'hass',
            required=False,
            allow_empty=False,
            required_type='bool',
            default=False
        )
        # topic to send information to
        self.topic = Logger.get_config_option(
            config_options,
            'topic',
            required=False,
            allow_empty=False,
            default="simplemonitor" if not self.hass else "homeassistant/binary_sensor"
        )

        # registry of monitors which registered with HA
        # not used if not Home Assistant context
        # also see https://github.com/jamesoff/simplemonitor/issues/236#issuecomment-462481900 for rationale
        self.registered = []

    def save_result2(self, name, monitor):
        # check if monitor registred with HA
        if self.hass:
            if monitor.name not in self.registered:
                try:
                    paho.mqtt.publish.single("{root}/simplemonitor_{monitor}/config".format(root=self.topic, monitor=monitor.name),
                                             payload=json.dumps({"name": monitor.name}),
                                             retain=True,
                                             hostname=self.host,
                                             client_id="simplemonitor_{monitor}".format(monitor=monitor.name)
                                             )
                except Exception as e:
                    self.logger_logger.error("cannot send {device} to MQTT: {e}".format(device=monitor.name, e=e))
                else:
                    self.registered.append(monitor.name)
                    self.logger_logger.debug("registered {device} in MQTT".format(device=monitor.name))

        if self.only_failures and monitor.virtual_fail_count() == 0:
            return

        topic = "{root}/simplemonitor_{monitor}/state".format(root=self.topic, monitor=monitor.name)
        self.logger_logger.debug("{monitor} failed {n} times".format(monitor=monitor.name, n=monitor.virtual_fail_count()))
        payload = 'ON' if monitor.virtual_fail_count() == 0 and not monitor.was_skipped else 'OFF'
        try:
            paho.mqtt.publish.single(topic, payload=payload, retain=True, hostname=self.host, client_id="simplemonitor_{monitor}".format(monitor=monitor.name))
        except Exception as e:
            self.logger_logger.error("cannot send state {payload} to {topic}: {e}").format(payload=payload, topic=topic,
                                                                                           e=e)
        else:
            self.logger_logger.debug("state {state} sent to {topic}".format(state=payload, topic=topic))

    def describe(self):
        return "Sends monitoring status to a MQTT broker"
