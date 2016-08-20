
"""A (fairly) simple host/service monitor."""

from __future__ import with_statement

import os
import sys
import time

from ConfigParser import *
from optparse import *
from socket import gethostname


import Monitors.monitor
import Monitors.network
import Monitors.service
import Monitors.host
import Monitors.file
import Monitors.compound

from simplemonitor import SimpleMonitor

import Loggers.file
import Loggers.db
import Loggers.network

import Alerters.mail
import Alerters.ses
import Alerters.bulksms
import Alerters.syslogger
import Alerters.execute
import Alerters.slack
import Alerters.pushover


VERSION = "1.7"


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
    if "defaults" in monitors:
        default_config = get_config_dict(config, "defaults")
        monitors.remove("defaults")
    else:
        default_config = {}

    myhostname = gethostname().lower()

    for monitor in monitors:
        if config.has_option(monitor, "runon"):
            if myhostname != config.get(monitor, "runon").lower():
                sys.stderr.write("Ignoring monitor %s because it's only for host %s\n" % (monitor, config.get(monitor, "runon")))
                continue
        type = config.get(monitor, "type")
        new_monitor = None
        config_options = default_config.copy()
        config_options.update(get_config_dict(config, monitor))

        if type == "host":
            new_monitor = Monitors.network.MonitorHost(monitor, config_options)

        elif type == "service":
            new_monitor = Monitors.service.MonitorService(monitor, config_options)

        elif type == "tcp":
            new_monitor = Monitors.network.MonitorTCP(monitor, config_options)

        elif type == "rc":
            new_monitor = Monitors.service.MonitorRC(monitor, config_options)

        elif type == "diskspace":
            new_monitor = Monitors.host.MonitorDiskSpace(monitor, config_options)

        elif type == "http":
            new_monitor = Monitors.network.MonitorHTTP(monitor, config_options)

        elif type == "apcupsd":
            new_monitor = Monitors.host.MonitorApcupsd(monitor, config_options)

        elif type == "svc":
            new_monitor = Monitors.service.MonitorSvc(monitor, config_options)

        elif type == "backup":
            new_monitor = Monitors.file.MonitorBackup(monitor, config_options)

        elif type == "portaudit":
            new_monitor = Monitors.host.MonitorPortAudit(monitor, config_options)

        elif type == "pkgaudit":
            new_monitor = Monitors.host.MonitorPkgAudit(monitor, config_options)

        elif type == "loadavg":
            new_monitor = Monitors.host.MonitorLoadAvg(monitor, config_options)

        elif type == "eximqueue":
            new_monitor = Monitors.service.MonitorEximQueue(monitor, config_options)

        elif type == "windowsdhcp":
            new_monitor = Monitors.service.MonitorWindowsDHCPScope(monitor, config_options)

        elif type == "zap":
            new_monitor = Monitors.host.MonitorZap(monitor, config_options)

        elif type == "fail":
            new_monitor = Monitors.monitor.MonitorFail(monitor, config_options)

        elif type == "null":
            new_monitor = Monitors.monitor.MonitorNull(monitor, config_options)

        elif type == "filestat":
            new_monitor = Monitors.host.MonitorFileStat(monitor, config_options)

        elif type == "compound":
            new_monitor = Monitors.compound.CompoundMonitor(monitor, config_options)
            new_monitor.set_mon_refs(m)

        elif type == 'dns':
            new_monitor = Monitors.network.MonitorDNS(monitor, config_options)

        elif type == 'command':
            new_monitor = Monitors.host.MonitorCommand(monitor, config_options)

        else:
            sys.stderr.write("Unknown type %s for monitor %s\n" % (type, monitor))
            continue
        if new_monitor is None:
            continue

        if not quiet:
            print "Adding %s monitor %s" % (type, monitor)
        m.add_monitor(monitor, new_monitor)

    for i in m.monitors.keys():
        m.monitors[i].post_config_setup()

    return m


def load_loggers(m, config, quiet):
    """Load the loggers listed in the config object."""

    if config.has_option("reporting", "loggers"):
        loggers = config.get("reporting", "loggers").split(",")
    else:
        loggers = []

    for logger in loggers:
        type = config.get(logger, "type")
        config_options = get_config_dict(config, logger)
        if type == "db":
            l = Loggers.db.DBFullLogger(config_options)
        elif type == "dbstatus":
            l = Loggers.db.DBStatusLogger(config_options)
        elif type == "logfile":
            l = Loggers.file.FileLogger(config_options)
        elif type == "html":
            l = Loggers.file.HTMLLogger(config_options)
        elif type == "network":
            l = Loggers.network.NetworkLogger(config_options)
        else:
            sys.stderr.write("Unknown logger type %s\n" % type)
            continue
        if l is None:
            print "Creating logger %s failed!" % logger
            continue
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
            a = Alerters.mail.EMailAlerter(config_options)
        elif type == "ses":
            a = Alerters.ses.SESAlerter(config_options)
        elif type == "bulksms":
            a = Alerters.bulksms.BulkSMSAlerter(config_options)
        elif type == "syslog":
            a = Alerters.syslogger.SyslogAlerter(config_options)
        elif type == "execute":
            a = Alerters.execute.ExecuteAlerter(config_options)
        elif type == "slack":
            a = Alerters.slack.SlackAlerter(config_options)
        elif type == "pushover":
            a = Alerters.pushover.PushoverAlerter(config_options)
        else:
            sys.stderr.write("Unknown alerter type %s\n" % type)
            continue
        if not quiet:
            print "Adding %s alerter %s" % (type, alerter)
        a.name = alerter
        m.add_alerter(alerter, a)
        del(a)
    return m


def main():
    """This is where it happens \o/"""

    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="Be more verbose")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet", default=False, help="Don't output anything except errors")
    parser.add_option("-t", "--test", action="store_true", dest="test", default=False, help="Test config and exit")
    parser.add_option("-p", "--pidfile", dest="pidfile", default="", help="Write PID into this file")
    parser.add_option("-N", "--no-network", dest="no_network", default=False, action="store_true", help="Disable network listening socket")
    parser.add_option("-d", "--debug", dest="debug", default=False, action="store_true", help="Enable debug output")
    parser.add_option("-f", "--config", dest="config", default="monitor.ini", help="configuration file")

    (options, args) = parser.parse_args()

    if options.quiet and options.verbose:
        options.verbose = False

    if options.quiet and options.debug:
        options.debug = False

    if options.debug and not options.verbose:
        options.verbose = True

    if not options.quiet:
        print "SimpleMonitor v%s" % VERSION
        print "--> Loading main config from %s" % options.config

    config = ConfigParser()
    config.read(options.config)
    interval = config.getint("monitor", "interval")

    pidfile = ""
    try:
        pidfile = config.get("monitor", "pidfile")
    except:
        pass

    if options.pidfile != "":
        pidfile = options.pidfile

    if pidfile != "":
        my_pid = os.getpid()
        try:
            with open(pidfile, "w") as file_handle:
                file_handle.write("%d\n" % my_pid)
        except:
            sys.stderr.write("Couldn't write to pidfile!")

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

    try:
        if config.get("monitor", "remote") == "1":
            if not options.no_network:
                enable_remote = True
                remote_port = int(config.get("monitor", "remote_port"))
            else:
                enable_remote = False
        else:
            enable_remote = False
    except:
        enable_remote = False

    if not m.verify_dependencies():
        sys.exit(1)

    if options.test:
        print "--> Config test complete. Exiting."
        sys.exit(0)

    if not options.quiet:
        print

    try:
        key = config.get("monitor", "key")
    except:
        key = None

    if enable_remote:
        if not options.quiet:
            print "--> Starting remote listener thread"
        remote_listening_thread = Loggers.network.Listener(m, remote_port, options.verbose, key)
        remote_listening_thread.daemon = True
        remote_listening_thread.start()

    if not options.quiet:
        print "--> Starting... (loop runs every %ds) Hit ^C to stop" % interval
    loop = True
    heartbeat = 0

    m.set_verbosity(options.verbose, options.debug)

    while loop:
        try:
            m.run_tests()
            m.do_recovery()
            m.do_alerts()
            m.do_logs()

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
            sys.exc_info()
            sys.stderr.write("Caught unhandled exception during main loop: %s\n" % e)
        if loop and enable_remote:
            if not remote_listening_thread.isAlive():
                print "Listener thread died :("
                remote_listening_thread = Loggers.network.Listener(m, remote_port, options.verbose)
                remote_listening_thread.start()
        try:
            time.sleep(interval)
        except:
            print "\n--> Quitting."
            loop = False

    if enable_remote:
        remote_listening_thread.running = False
        remote_listening_thread.join(0)

    if pidfile != "":
        try:
            unlink(pidfile)
        except:
            print "Couldn't remove pidfile!"

    if not options.quiet:
        print "--> Finished."

if __name__ == "__main__":
    main()
