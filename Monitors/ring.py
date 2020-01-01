try:
    import ring_doorbell
except ImportError:
    ring_doorbell = None


from typing import cast

from Monitors.monitor import Monitor, register


@register
class MonitorRingDoorbell(Monitor):
    """Monitor the battery life on a Ring doorbell."""

    type = "ring_doorbell"

    def __init__(self, name: str, config_options: dict) -> None:
        if "gap" not in config_options:
            config_options["gap"] = 21600  # 6 hours
        super().__init__(name, config_options)
        if ring_doorbell is None:
            self.monitor_logger.critical("ring_doorbell library is not installed")
        self.device_name = cast(
            str, self.get_config_option(config_options, "device_name")
        )
        self.minimum_battery = cast(
            int,
            self.get_config_option(
                config_options, "minimum_battery", required_type="int", default=25
            ),
        )
        self.ring_username = cast(
            str, self.get_config_option(config_options, "username")
        )
        self.ring_password = cast(
            str, self.get_config_option(config_options, "password")
        )
        self.ring = None

    def run_test(self) -> bool:
        if ring_doorbell is None:
            return self.record_fail("ring_doorbell library is not installed")
        if self.ring is None:
            self.monitor_logger.info("Logging in to ring")
            try:
                self.ring = ring_doorbell.Ring(self.ring_username, self.ring_password)
            except Exception as e:
                self.monitor_logger.exception("Failed to log in to Ring")
                return self.record_fail("Failed to log in to Ring: {}".format(e))
        else:
            self.ring.update()
        assert self.ring is not None
        for doorbell in self.ring.doorbells:
            doorbell.update()
            if doorbell.name == self.device_name:
                battery = doorbell.battery_life
                if battery < self.minimum_battery:
                    return self.record_fail(
                        "Battery is at {}% (limit: {}%)".format(
                            battery, self.minimum_battery
                        )
                    )
                else:
                    return self.record_success(
                        "Battery is at {}% (limit: {}%)".format(
                            battery, self.minimum_battery
                        )
                    )
        return self.record_fail(
            "Could not find doorbell named {}".format(self.device_name)
        )
