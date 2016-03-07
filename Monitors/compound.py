
"""compound checks (logical and of failure of multiple probes) for SimpleMonitor."""

from monitor import Monitor


class CompoundMonitor(Monitor):
    """Combine (logical-and) multiple failures for emergency escalation.

    Check most recent proble of provided monitors, if all are fail, then report fail.
    """

    type = "compound"

    def __init__(self, name, config_options):
        Monitor.__init__(self, name, config_options)
        monitors = []
        try:
            monitors = [ele.strip() for ele in config_options["monitors"].split(",")]
        except:
            raise RuntimeError("Required configuration fields missing")
        min_fail = len(monitors)
        try:
            min_fail = config_options["min_fail"]
        except:
            pass
        self.min_fail = min_fail
        self.monitors = monitors
        self.m = -1
        self.mt = None

    def run_test(self):
        # we depend on the other tests to run, just check them
        failcount = self.min_fail
        for i in self.monitors:
            if self.m[i].get_success_count() > 0 and self.m[i].tests_run > 0:
                failcount -= 1
        return (failcount > 0)

    def describe(self):
        """Explains what we do."""
        message = "Checking that %s tests both failed" % (self.url)
        return message

    def get_params(self):
        return (self.monitors)

    def set_mon_refs(self, mmm):
        """ stash a ref to the global monitor list so we can examine later """
        self.mt = mmm

    def post_config_setup(self):
        """ make a nice little dict of just the monitors we need """
        if self.m != -1:
            return
        self.m = {}
        for i in self.mt.monitors.keys():
            if i in self.monitors:
                self.m[i] = self.mt.monitors[i]
        # make sure we find all of our monitors or die during config
        for i in self.monitors:
            if i not in self.m.keys():
                raise RuntimeError("No such monitor %s in compound monitor" % i)
