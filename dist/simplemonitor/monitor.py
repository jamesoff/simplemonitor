
"""A (fairly) simple host/service monitor."""

import socket
import re
import os
import platform
import sys
import datetime

from socket import gethostname
from ConfigParser import *
from optparse import *

from monitors import *
from simplemonitor import SimpleMonitor
from logger import *
from dblogger import *
from alerter import *

VERSION = "1.1"

def get_list(config, section, key, want_ints=False):
    """Get a list of items back from a command-separated list."""
    if config.has_option(section, key):
        list = config.get(section, key).split(",")
        list = [x.strip() for x in list]
        if want_ints:
            list = [int(i) for i in list]
        return list
    else:
        return []

def get_dependencies(config, monitor):
    """Convenience method to get the dependency list for a monitor.
    Used while parsing the config file."""
    return get_list(config, monitor, "depend")

def get_optional_int(config, monitor, key, default=0):
    if config.has_option(monitor, key):
        value = config.getint(monitor, key)
    else:
        value = default 
    return value

def get_tolerance(config, monitor):
    """Convenience method to get the tolerance for a monitor.
    Used while parsing the config file."""
    return get_optional_int(config, monitor, "tolerance")

def load_monitors(m, filename, quiet):
    """Load all the monitors from the config file and return a populated SimpleMonitor."""
    config = ConfigParser()
    config.read(filename)
    monitors = config.sections()
    myhostname = gethostname().lower()
    
    for monitor in monitors:
        if config.has_option(monitor, "runon"):
            if myhostname != config.get(monitor, "runon").lower():
                sys.stderr.write("Ignoring monitor %s because it's only for host %s\n" % (monitor, config.get(monitor, "runon")))
                continue
        type = config.get(monitor, "type")
        new_monitor = None

        if type == "host":
            hostname = config.get(monitor, "host")
            new_monitor = MonitorHost(hostname)

        elif type == "service":
            service = config.get(monitor, "service")
            if config.has_option(monitor, "host"):
                host = config.get(monitor, "host")
            else:
                host = "."
            if config.has_option(monitor, "state"):
                state = config.get(monitor, "state")
            else:
                state = "RUNNING"
            new_monitor = MonitorService(service, state, host)

        elif type == "tcp":
            hostname = config.get(monitor, "host")
            port = config.getint(monitor, "port")
            new_monitor = MonitorTCP(hostname, port)

        elif type == "rc":
            #TODO: Finish this monitor loading
            service = config.get(monitor, "service")
            new_monitor = MonitorRC(service)

        elif type == "diskspace":
            partition = config.get(monitor, "partition")
            limit = config.get(monitor, "limit")
            new_monitor = MonitorDiskSpace(partition, limit)

        elif type == "http":
            url = config.get(monitor, "url")
            if config.has_option(monitor, "regexp"):
                regexp = config.get(monitor, "regexp")
            else:
                regexp = ""
            allowed_codes = get_list(config, monitor, "allowed_codes", True)
            new_monitor = MonitorHTTP(url, regexp, allowed_codes)

        elif type == "apcupsd":
            path = ""
            if config.has_option(monitor, "path"):
                path = config.get(monitor, "path")
            new_monitor = MonitorApcupsd(path)
        
        elif type == "svc":
            new_monitor = MonitorSvc(config.get(monitor, "path"))

        elif type == "fail":
            new_monitor = MonitorFail()
        
        else:
            sys.stderr.write("Unknown type %s for monitor %s\n" % (type, monitor))
            continue
        if new_monitor == None:
            continue
        dependencies = get_dependencies(config, monitor)
        new_monitor.set_dependencies(dependencies)

        tolerance = get_tolerance(config, monitor)
        new_monitor.set_tolerance(tolerance)

        urgency = get_optional_int(config, monitor, "urgent", 1)
        new_monitor.set_urgency(urgency)

        gap = get_optional_int(config, monitor, "gap", 0)
        new_monitor.set_gap(gap)

        if not quiet:
            print "Adding %s monitor %s" % (type, monitor)
        m.add_monitor(monitor, new_monitor)

    return m

def load_loggers(m, config, quiet):
    """Load the loggers listed in the config object."""

    if config.has_option("reporting", "loggers"):
        loggers = config.get("reporting", "loggers").split(",")
    else:
        loggers = []

    for logger in loggers:
        type = config.get(logger, "type")
        if type == "db":
            l = DBFullLogger(config.get(logger, "path"))
        elif type == "dbstatus":
            l = DBStatusLogger(config.get(logger, "path"))
        elif type == "logfile":
            only_failures = get_optional_int(config, logger, "only_failures", 0)
            buffered = get_optional_int(config, logger, "buffered", 0)
            l = FileLogger(config.get(logger, "filename"), only_failures, buffered)
        else:
            sys.stderr.write("Unknown logger type %s\n" % type)
            continue
        dependencies = get_dependencies(config, logger)
        l.set_dependencies(dependencies)
        if not quiet:
            print "Adding %s logger %s" % (type, logger)
        m.add_logger(logger, l)
        del(l)
    return m

def load_alerters(m, config, quiet):
    """Load the alerters listed in the config object."""
    if config.has_option("reporting", "alerters"):
        alerters = config.get("reporting", "alerters").split(",")
    else:
        alerters = []

    for alerter in alerters:
        type = config.get(alerter, "type")
        if type == "email":
            limit = get_optional_int(config, alerter, "limit", 1)
            if limit <= 0:
                limit = 1
            a = EMailAlerter(config.get(alerter, "host"), config.get(alerter, "from"), config.get(alerter, "to"), limit)
        elif type == "bulksms":
            limit = get_optional_int(config, alerter, "limit", 1)
            if limit <= 0:
                limit = 1
            if config.has_option(alerter, "sender"):
                sender = config.get(alerter, "sender")
            else:
                sender = "SmplMntr"
            a = BulkSMSAlerter(config.get(alerter, "username"), config.get(alerter, "password"), config.get(alerter, "target"), sender, limit)
        else:
            sys.stderr.write("Unknown alerter type %s\n" % type)
            continue
        dependencies = get_dependencies(config, alerter)
        a.set_dependencies(dependencies)
        if not quiet:
            print "Adding %s alerter %s" % (type, alerter)
        m.add_alerter(alerter, a)
        del(a)
    return m

def main():
    """This is where it happens \o/"""

    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="Be more verbose")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet", default=False, help="Don't output anything except errors")

    (options, args) = parser.parse_args()

    if options.quiet and options.verbose:
        options.verbose = False

    if not options.quiet:
        print "SimpleMonitor v%s" % VERSION 
        print "--> Loading main config"

    config = ConfigParser()
    config.read("monitor.ini")
    interval = config.getint("monitor", "interval")
    if config.has_option("monitor", "monitors"):
        monitors_file = config.get("monitor", "monitors")
    else:
        monitors_file = "monitors.ini"

    if not options.quiet:
        print "--> Loading monitor config from %s" % monitors_file

    m = SimpleMonitor()

    m = load_monitors(m, monitors_file, options.quiet)

    count = m.count_monitors()
    if count == 0:
        sys.stderr.write("No monitors loaded :(\n")
        sys.exit(2)

    if not options.quiet:
        print "--> Loaded %d monitors.\n" % count

    m = load_loggers(m, config, options.quiet)
    m = load_alerters(m, config, options.quiet)

    if not options.quiet:
        print "\n--> Starting... (loop runs every %ds) Hit ^C to stop" % interval
    loop = True
    heartbeat = 0
    while loop:
        try:
            m.run_tests(options.verbose)
            m.do_alerts()
            m.do_logs()
            m.do_status()
            time.sleep(interval)

            if not options.quiet and not options.verbose:
                heartbeat += 1
                if heartbeat == 2:
                    sys.stdout.write(".")
                    sys.stdout.flush()
                    heartbeat = 0
        except KeyboardInterrupt:
            if not options.quiet:
                print "\n--> EJECT EJECT"
            loop = False
        except Exception, e:
            sys.stderr.write("Caught unhandled exception during main loop: %s\n" % e)
    if not options.quiet:
        print "--> Finished."

if __name__ == "__main__":
    main()

