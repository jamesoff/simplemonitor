"""
Compound checks (logical and of failure of multiple probes) for SimpleMonitor
"""

import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, cast
from weakref import WeakValueDictionary

from .monitor import Monitor, register

if TYPE_CHECKING:
    from ..simplemonitor import SimpleMonitor


@register
class CompoundMonitor(Monitor):
    """
    Combine (logical-and) multiple failures for emergency escalation

    Check most recent proble of provided monitors, if all are fail, then report fail.
    """

    monitor_type = "compound"
    m: Optional[WeakValueDictionary[str, Monitor]] = None
    mt: Optional[WeakValueDictionary[str, Monitor]] = None

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self.monitors = cast(
            List[str],
            self.get_config_option(
                "monitors", required_type="[str]", required=True, default=[]
            ),
        )
        self.min_fail = cast(
            int,
            self.get_config_option(
                "min_fail", required_type="int", default=len(self.monitors), minimum=1
            ),
        )

    def run_test(self) -> bool:
        # we depend on the other tests to run, just check them
        failcount = self.min_fail
        # this check actually doesn't work, since the sub-monitors run AFTER the compound ones...
        if self.m is not None:
            for i in self.monitors:
                if self.m[i].get_success_count() > 0 and self.m[i].tests_run > 0:
                    failcount -= 1
        if failcount < self.min_fail:
            return self.record_success(
                "{} monitors failed (min: {})".format(failcount, self.min_fail)
            )
        return self.record_fail(
            "{} monitors failed (min: {})".format(failcount, self.min_fail)
        )

    def describe(self) -> str:
        """Explains what we do."""
        return "Checking that these monitors all succeeded: {0}".format(
            ", ".join(self.monitors)
        )

    def get_params(self) -> Tuple:
        return (self.monitors,)

    def set_mon_refs(self, mmm: Dict[str, Monitor]) -> None:
        """stash a ref to the global monitor list so we can examine later"""
        self.all_monitors = WeakValueDictionary(mmm)

    def post_config_setup(self) -> None:
        """make a nice little dict of just the monitors we need"""
        if self.m is not None:
            return
        self.m = WeakValueDictionary()
        for i in list(self.all_monitors.keys()):
            if i in self.monitors:
                self.m[i] = self.all_monitors[i]
        # make sure we find all of our monitors or die during config
        for i in self.monitors:
            if i not in list(self.m.keys()):
                raise RuntimeError("No such monitor %s in compound monitor" % i)

    def fail_count(self) -> int:
        """increments the fail counter by 1 if a sub-monitor failed"""
        failcount = 0
        if self.m is not None:
            for i in self.monitors:
                if self.m[i].virtual_fail_count() > 0:
                    failcount += 1
        return failcount

    def get_result(self) -> str:
        failcount = self.fail_count()
        monitorcount = self.monitors.__len__()
        if failcount > 0:
            return "{0} of {1} services failed. Fail after: {2}".format(
                failcount, monitorcount, self.min_fail
            )
        else:
            return "All {0} services OK".format(monitorcount)


@register
class RemoteHostsMonitor(Monitor):
    """A Monitor which checks for remote hosts sending us data."""

    monitor_type = "remotehosts"
    m = None  # type: Optional[WeakValueDictionary[str, Monitor]]
    mt = None  # type: Optional[WeakValueDictionary[str, Monitor]]

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self.hosts = cast(
            List[str],
            self.get_config_option(
                "hosts", required_type="[str]", required=True, default=[]
            ),
        )
        self.max_age = cast(
            int,
            self.get_config_option(
                "max_age", required_type="int", default=300, minimum=0
            ),
        )
        self._max_age = datetime.timedelta(seconds=self.max_age)

    def set_sm_ref(self, sm: "SimpleMonitor") -> None:
        self.simplemonitor = sm

    def run_test(self) -> bool:
        known_remotes = set(self.simplemonitor.remote_hosts.keys())
        expected_remotes = set(self.hosts)
        missing_remotes = expected_remotes - known_remotes
        surprise_remotes = known_remotes - expected_remotes
        old_remotes = [
            host
            for host, props in self.simplemonitor.remote_hosts.items()
            if host in expected_remotes
            and props["last_seen"] + self._max_age < datetime.datetime.now()
        ]

        errors = []
        if len(old_remotes):
            errors.append(f"out-of-date remotes: {', '.join(old_remotes)}")
        if len(missing_remotes):
            errors.append(f"missing remotes: {', '.join(missing_remotes)}")
        if len(surprise_remotes):
            errors.append(f"unexpected remotes: {', '.join(surprise_remotes)}")

        if len(errors):
            return self.record_fail("; ".join(errors))
        return self.record_success(f"{len(expected_remotes)} remote hosts reporting")

    def describe(self) -> str:
        return f"checking for remotes: {', '.join(self.hosts)} with max age {self.max_age}s"
