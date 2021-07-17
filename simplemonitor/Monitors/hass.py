"""
Home Automation monitors for SimpleMonitor
"""

from typing import Tuple, cast

import requests

from .monitor import Monitor, register


@register
class MonitorSensor(Monitor):
    """Monitor the existence of a HASS sensor"""

    monitor_type = "hass_sensor"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self.url = cast(str, self.get_config_option("url", required=True))
        self.sensor = cast(str, self.get_config_option("sensor", required=True))
        self.token = cast(str, self.get_config_option("token", default=None))

    def describe(self) -> str:
        return "monitor the existence of a sensor"

    def run_test(self) -> bool:
        try:
            # retrieve the status from hass API
            self.monitor_logger.debug(
                requests.get("{}/api/states/{}".format(self.url, self.sensor)).text
            )
            call = requests.get(
                "{}/api/states/{}".format(self.url, self.sensor),
                headers={
                    "Authorization": "Bearer {}".format(self.token),
                    "Content-Type": "application/json",
                },
            )
            if not call.ok:
                raise ValueError(call.text)
            response = call.json()
            self.monitor_logger.debug("retrieved JSON: %s", response)
        except requests.RequestException as error:
            # a general issue getting to the API
            # nothing special to report, this monitor should be configured to be
            # dependent of general hass API availability
            return self.record_fail("cannot get info from hass: {}".format(error))
        else:
            # we have a response from the API
            # now: is the sensor defined at all in hass? If not the answer is basically empty
            if response.get("context"):
                if response["state"] == "unavailable":
                    return self.record_fail(
                        "the sensor exists but state is 'unavailable'"
                    )
                return self.record_success()
            return self.record_fail("sensor not found in hass")

    def get_params(self) -> Tuple:
        return (self.url, self.sensor)
