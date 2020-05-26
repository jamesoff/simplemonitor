try:
    import pyarlo

    pyarlo_available = True
except ImportError:
    pyarlo_available = False

from typing import Optional, cast

from ..Monitors.monitor import Monitor, register


@register
class MonitorArloCamera(Monitor):
    """Monitor the battery life on an Arlo camera."""

    monitor_type = "arlo_camera"

    def __init__(self, name: str, config_options: dict) -> None:
        if "gap" not in config_options:
            config_options["gap"] = 21600  # 6 hours
        super().__init__(name, config_options)
        if not pyarlo_available:
            self.monitor_logger.critical("pyarlo library is not installed")
            self.monitor_logger.critical("Try: pip install pyarlo")
            self.monitor_logger.critical("     or pip install simplemonitor[arlo]")
        self.device_name = cast(str, self.get_config_option("device_name"))
        self.minimum_battery = cast(
            int,
            self.get_config_option("minimum_battery", required_type="int", default=25),
        )
        self.arlo_username = cast(
            str, self.get_config_option("username", required=True)
        )
        self.arlo_password = cast(
            str, self.get_config_option("password", required=True)
        )
        self.base_station_id = cast(
            int,
            self.get_config_option("base_station_id", required_type="int", default=0),
        )
        self.arlo = None  # type: Optional[pyarlo.PyArlo]
        self.arlo_base = None  # type: Optional[pyarlo.ArloBaseStation]
        self.camera = None  # type: Optional[pyarlo.ArloCamera]

    def run_test(self) -> bool:
        if not pyarlo_available:
            return self.record_fail("pyarlo library is not installed")
        if self.arlo is None:
            self.monitor_logger.info("logging in to Arlo")
            try:
                self.arlo = pyarlo.PyArlo(
                    username=self.arlo_username, password=self.arlo_password
                )
            except Exception:
                self.monitor_logger.exception("arlo login failed")
                return self.record_fail("could not log in to Arlo")
        if self.arlo is None:
            return self.record_fail("failed to get Arlo object")
        if self.arlo_base is None:
            try:
                self.arlo_base = self.arlo.base_stations[self.base_station_id]
            except Exception:
                self.monitor_logger.exception("arlo base station fetch failed")
                return self.record_fail("could not fetch base station")
        if self.arlo_base is None:
            return self.record_fail("failed to get ArloBaseStation object")
        if self.camera is None:
            for camera in self.arlo.cameras:
                if camera.name == self.device_name:
                    self.camera = camera
            if camera is None:
                return self.record_fail(
                    "could not find camera named {}".format(self.device_name)
                )
        else:
            self.monitor_logger.info("Updating Arlo camera")
            try:
                camera.update()
            except Exception:
                return self.record_fail("failed to update Arlo camera")
        battery = camera.battery_level  # type: int
        if battery < self.minimum_battery:
            return self.record_fail(
                "Battery is at {}% (limit: {}%)".format(battery, self.minimum_battery)
            )
        else:
            return self.record_success(
                "Battery is at {}% (limit: {}%)".format(battery, self.minimum_battery)
            )

    def describe(self) -> str:
        return "Checking Arlo camera {} has battery level of at least {}%".format(
            self.device_name, self.minimum_battery
        )
