# coding=utf-8
""" File-based monitors for SimpleMonitor. """

import requests
import os
import os.path
import time

from .monitor import Monitor, register


@register
class Sensor(Monitor):
    type = "hass_sensor"

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        self.url = Monitor.get_config_option(
            config_options,
            'url',
            required=True
        )
        self.sensor = Monitor.get_config_option(
            config_options,
            'sensor',
            required=True
        )
        self.token = Monitor.get_config_option(
            config_options,
            'token',
            default=None
        )

    def describe(self):
        return "monitor the existance of a sensor"

    def run_test(self):
        try:
            # retrieve the status from hass API
            self.monitor_logger.debug(requests.get(f'{self.url}/api/states/{self.sensor}').text)
            call = requests.get(f'{self.url}/api/states/{self.sensor}',
                                headers={
                                    f'Authorization': 'Bearer {self.token}',
                                    'Content-Type': 'application/json'
                                })
            if not call.ok:
                raise ValueError(call.text)
            r = call.json()
            self.monitor_logger.debug(f"retrieved JSON: {r}")
        except Exception as e:
            # a general issue getting to the API
            # nothing special to report, this monitor should be configured to be dependent of general hass API availability
            return self.record_fail(f"cannot get info from hass: {e}")
        else:
            # we have a response from the API
            # now: is the sensor defined at all in hass? If not the answer is basically empty
            if r.get('context'):
                if r['state'] == "unavailable":
                    return self.record_fail(f"the sensor exists but state is 'unavailable'")
                return self.record_success()
            else:
                return self.record_fail("sensor not found in hass")
