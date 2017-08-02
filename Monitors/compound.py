
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
            min_fail = max(int(config_options["min_fail"]), 1)
        except:
            print("could not parse min_fail. Ignoring...")
            pass
        self.min_fail = min_fail
        self.monitors = monitors
        self.m = -1
        self.mt = None

    def run_test(self):
        # we depend on the other tests to run, just check them
        failcount = self.min_fail
        # this check actually doesn't work, since the sub-monitors run AFTER the compound ones...
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

    def virtual_fail_count(self):
        failcount = self.fail_count()
        if failcount >= self.min_fail:
            # greater or equal number failed: we return the real failure count
            return failcount
        else:
            # we don't count failures if the specified min_fail isn't reached yet.
            return 0

    def fail_count(self):
        # increments the fail counter by 1 if a sub-monitor failed.
        failcount = 0
        for i in self.monitors:
            if self.m[i].virtual_fail_count() > 0:
                failcount += 1
        return failcount

    def get_result(self):
        failcount = self.fail_count()
        monitorcount = self.monitors.__len__()
        if failcount > 0:
            return "{0} of {1} services failed. Fail after: {2}".format(failcount, monitorcount, self.min_fail)
        else:
            return "All {0} services OK".format(monitorcount)

