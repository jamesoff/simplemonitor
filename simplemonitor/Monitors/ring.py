"""
Ring doorbell battery monitoring for SimpleMonitor
"""

import json
from pathlib import Path
from typing import Optional, cast

import ring_doorbell
from oauthlib.oauth2.rfc6749.errors import MissingTokenError

from ..Monitors.monitor import Monitor, register
from ..version import VERSION

RING_USER_AGENT = "SimpleMonitor/{}".format(VERSION)


@register
class MonitorRingDoorbell(Monitor):
    """Monitor the battery life on a Ring doorbell."""

    monitor_type = "ring_doorbell"

    def __init__(self, name: str, config_options: dict) -> None:
        if "gap" not in config_options:
            config_options["gap"] = 21600  # 6 hours
        super().__init__(name, config_options)
        self.device_name = cast(str, self.get_config_option("device_name"))
        self.device_type = cast(
            str, self.get_config_option("device_type", default="doorbell")
        )
        self.minimum_battery = cast(
            int,
            self.get_config_option("minimum_battery", required_type="int", default=25),
        )
        self.ring_username = cast(
            str, self.get_config_option("username", required=True)
        )
        self.ring_password = cast(
            str, self.get_config_option("password", required=True)
        )
        self.cache_file = Path(
            self.get_config_option("cache_file", default=".ring_token.cache")
        )
        if self.cache_file.is_file():
            self.monitor_logger.info("Using token cache file for Ring")
            self._ring_auth = ring_doorbell.Auth(
                RING_USER_AGENT,
                json.loads(self.cache_file.read_text()),
                self._token_updated,
            )
        else:
            self._ring_auth = ring_doorbell.Auth(
                RING_USER_AGENT, token_updater=self._token_updated
            )
            try:
                self.monitor_logger.info("Logging in to Ring")
                self._ring_auth.fetch_token(self.ring_username, self.ring_password)
            except MissingTokenError:
                self.monitor_logger.critical("MFA logins are not supported")
                self._ring_auth = None
        self.ring = None  # type: Optional[ring_doorbell.Ring]

    def _token_updated(self, token: str) -> None:
        self.cache_file.write_text(json.dumps(token))

    def run_test(self) -> bool:
        if self.ring is None:
            self.ring = ring_doorbell.Ring(self._ring_auth)
        self.ring.update_data()
        devices = self.ring.devices()
        # doorbots are doorbells owned by this account
        # authorized_doorbots are ones shared with this account
        # the device of interest could be in either depending on how the API
        # user we're configured with relates to it
        if self.device_type == "doorbell":
            doorbells = devices["authorized_doorbots"]
            doorbells.extend(devices["doorbots"])
        elif self.device_type == "camera":
            doorbells = devices.get("authorized_stickup_cams", [])
            doorbells.extend(devices["stickup_cams"])
        else:
            return self.record_fail(f"Unknown device type {self.device_type}")
        for doorbell in doorbells:
            if doorbell.name == self.device_name:
                battery = int(doorbell.battery_life)
                if battery < self.minimum_battery:
                    return self.record_fail(
                        f"Battery is at {battery}% (limit: {self.minimum_battery}%)"
                    )
                return self.record_success(
                    f"Battery is at {battery}% (limit: {self.minimum_battery}%)"
                )
        return self.record_fail(
            f"Could not find {self.device_type} named {self.device_name}"
        )
