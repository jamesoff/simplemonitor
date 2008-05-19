
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

VERSION = "1.2"

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

def get_config_dict(config, monitor):
    options = config.items(monitor)
    ret = {}
    for (key, value) in options:
        ret[key] = value
    return ret

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
        config_options = get_config_dict(config, monitor)

        if type == "host":
            new_monitor = MonitorHost(monitor, config_options)

        elif type == "service":
            new_monitor = MonitorService(monitor, config_options)

        elif type == "tcp":
            new_monitor = MonitorTCP(monitor, config_options)

        elif type == "rc":
            new_monitor = MonitorRC(monitor, config_options)

        elif type == "diskspace":
            new_monitor = MonitorDiskSpace(monitor, config_options)

        elif type == "http":
            new_monitor = MonitorHTTP(monitor, config_options)

        elif type == "apcupsd":
            new_monitor = MonitorApcupsd(monitor, config_options)
        
        elif type == "svc":
            new_monitor = MonitorSvc(monitor, config_options)

        elif type == "fail":
            new_monitor = MonitorFail(monitor)
        
        else:
            sys.stderr.write("Unknown type %s for monitor %s\n" % (type, monitor))
            continue
        if new_monitor == None:
            continue

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
        config_options = get_config_dict(config, alerter)
        if type == "email":
            a = EMailAlerter(config_options)
        elif type == "bulksms":
            a = BulkSMSAlerter(config_options)
        else:
            sys.stderr.write("Unknown alerter type %s\n" % type)
            continue
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
        time.sleep(interval)
    if not options.quiet:
        print "--> Finished."

if __name__ == "__main__":
    main()

