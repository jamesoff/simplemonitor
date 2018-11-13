# coding=utf-8
"""A (fairly) simple host/service monitor."""


import os
import sys
import time
import logging

from envconfig import EnvironmentAwareConfigParser

from optparse import OptionParser, SUPPRESS_HELP

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
import Alerters.fortysixelks
import Alerters.syslogger
import Alerters.execute
import Alerters.slack
import Alerters.pushover
import Alerters.nma
import Alerters.pushbullet
import Alerters.telegram
import Alerters.nc

try:
    import colorlog
except ImportError:
    pass

VERSION = "1.7"

main_logger = logging.getLogger('simplemonitor')


def get_config_dict(config, monitor):
    options = config.items(monitor)
    ret = {}
    for (key, value) in options:
        ret[key] = value
    return ret


def load_monitors(m, filename):
    """Load all the monitors from the config file and return a populated SimpleMonitor."""
    config = EnvironmentAwareConfigParser()
    config.read(filename)
    monitors = config.sections()
    if "defaults" in monitors:
        default_config = get_config_dict(config, "defaults")
        monitors.remove("defaults")
    else:
        default_config = {}

    myhostname = gethostname().lower()

    main_logger.info('=== Loading monitors')
    for monitor in monitors:
        if config.has_option(monitor, "runon"):
            if myhostname != config.get(monitor, "runon").lower():
                main_logger.warning("Ignoring monitor %s because it's only for host %s", monitor, config.get(monitor, "runon"))
                continue
        monitor_type = config.get(monitor, "type")
        new_monitor = None
        config_options = default_config.copy()
        config_options.update(get_config_dict(config, monitor))

        try:
            cls = Monitors.monitor.get_class(monitor_type)
        except KeyError:
            main_logger.error(
                "Unknown monitor type %s; valid types are: %s",
                monitor_type, ', '.join(Monitors.monitor.all_types()))
            continue
        new_monitor = cls(monitor, config_options)

        main_logger.info("Adding %s monitor %s: %s", monitor_type, monitor, new_monitor)
        m.add_monitor(monitor, new_monitor)

    for i in list(m.monitors.keys()):
        m.monitors[i].post_config_setup()
    main_logger.info('--- Loaded %d monitors', m.count_monitors())
    return m


def load_loggers(m, config):
    """Load the loggers listed in the config object."""

    if config.has_option("reporting", "loggers"):
        loggers = config.get("reporting", "loggers").split(",")
    else:
        loggers = []

    main_logger.info('=== Loading loggers')
    for config_logger in loggers:
        logger_type = config.get(config_logger, "type")
        config_options = get_config_dict(config, config_logger)
        config_options['_name'] = config_logger
        try:
            logger_cls = Loggers.logger.get_class(logger_type)
        except KeyError:
            main_logger.error(
                "Unknown logger type %s; valid types are: %s",
                logger_type, ', '.join(Loggers.logger.all_types()))
            continue
        new_logger = logger_cls(config_options)
        main_logger.info("Adding %s logger %s: %s", logger_type, config_logger, new_logger)
        m.add_logger(config_logger, new_logger)
        del new_logger
    main_logger.info('--- Loaded %d loggers', len(m.loggers))
    return m


def load_alerters(m, config):
    """Load the alerters listed in the config object."""
    if config.has_option("reporting", "alerters"):
        alerters = config.get("reporting", "alerters").split(",")
    else:
        alerters = []

    main_logger.info('=== Loading alerters')
    for alerter in alerters:
        alerter_type = config.get(alerter, "type")
        config_options = get_config_dict(config, alerter)
        try:
            alerter_cls = Alerters.alerter.get_class(alerter_type)
        except KeyError:
            main_logger.error(
                "Unknown alerter type %s; valid types are: %s",
                alerter_type, ', '.join(Alerters.alerter.all_types()))
            continue
        new_alerter = alerter_cls(config_options)
        main_logger.info("Adding %s alerter %s", alerter_type, alerter)
        new_alerter.name = alerter
        m.add_alerter(alerter, new_alerter)
        del new_alerter
    main_logger.info('--- Loaded %d alerters', len(m.alerters))
    return m


def main():
    r"""This is where it happens \o/"""

    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help=SUPPRESS_HELP)
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet", default=False, help=SUPPRESS_HELP)
    parser.add_option("-t", "--test", action="store_true", dest="test", default=False, help="Test config and exit")
    parser.add_option("-p", "--pidfile", dest="pidfile", default=None, help="Write PID into this file")
    parser.add_option("-N", "--no-network", dest="no_network", default=False, action="store_true", help="Disable network listening socket")
    parser.add_option("-d", "--debug", dest="debug", default=False, action="store_true", help=SUPPRESS_HELP)
    parser.add_option("-f", "--config", dest="config", default="monitor.ini", help="configuration file")
    parser.add_option("-H", "--no-heartbeat", action="store_true", dest="no_heartbeat", default=False, help="Omit printing the '.' character when running checks")
    parser.add_option('-1', '--one-shot', action='store_true', dest='one_shot', default=False, help='Run the monitors once only, without alerting. Require monitors without "fail" in the name to succeed. Exit zero or non-zero accordingly.')
    parser.add_option('--loops', dest='loops', default=-1, help=SUPPRESS_HELP, type=int)
    parser.add_option('-l', '--log-level', dest="loglevel", default="warn", help="Log level: critical, error, warn, info, debug")
    parser.add_option('-C', '--no-colour', '--no-color', action='store_true', dest='no_colour', default=False, help='Do not colourise log output')
    parser.add_option('--no-timestamps', action='store_true', dest='no_timestamps', default=False, help='Do not prefix log output with timestamps')

    (options, _) = parser.parse_args()

    if options.quiet:
        print('Warning: --quiet is deprecated; use --log-level=critical')
        options.loglevel = 'critical'

    if options.verbose:
        print('Warning: --verbose is deprecated; use --log-level=info')
        options.loglevel = 'info'

    if options.debug:
        print('Warning: --debug is deprecated; use --log-level=debug')
        options.loglevel = 'debug'

    if options.no_timestamps:
        logging_timestamp = ''
    else:
        logging_timestamp = '%(asctime)s '

    try:
        log_level = getattr(logging, options.loglevel.upper())
    except AttributeError:
        print('Log level {0} is unknown'.format(options.loglevel))
        sys.exit(1)

    log_datefmt = '%Y-%m-%d %H:%M:%S'
    log_plain_format = logging_timestamp + '%(levelname)8s (%(name)s) %(message)s'
    if not options.no_colour:
        try:
            handler = colorlog.StreamHandler()
            handler.setFormatter(colorlog.ColoredFormatter(logging_timestamp + '%(log_color)s%(levelname)8s%(reset)s (%(name)s) %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
            main_logger.addHandler(handler)
        except NameError:
            logging.basicConfig(format=log_plain_format, datefmt=log_datefmt)
            main_logger.error('Could not enable colorlog')
    else:
        logging.basicConfig(format=log_plain_format, datefmt=log_datefmt)

    main_logger.setLevel(log_level)

    if not options.quiet:
        main_logger.info('=== SimpleMonitor v%s', VERSION)
        main_logger.info('Loading main config from %s', options.config)

    config = EnvironmentAwareConfigParser()
    if not os.path.exists(options.config):
        main_logger.critical('Configuration file "%s" does not exist!', options.config)
        sys.exit(1)
    try:
        config.read(options.config)
    except Exception as e:
        main_logger.critical('Unable to read configuration file')
        main_logger.critical(e)
        sys.exit(1)

    try:
        interval = config.getint("monitor", "interval")
    except Exception:
        main_logger.critical('Missing [monitor] section from config file, or missing the "interval" setting in it')
        sys.exit(1)

    pidfile = None
    try:
        pidfile = config.get("monitor", "pidfile")
    except Exception:
        pass

    if options.pidfile:
        pidfile = options.pidfile

    if pidfile:
        my_pid = os.getpid()
        try:
            with open(pidfile, "w") as file_handle:
                file_handle.write("%d\n" % my_pid)
        except Exception:
            main_logger.error("Couldn't write to pidfile!")
            pidfile = None

    if config.has_option("monitor", "monitors"):
        monitors_file = config.get("monitor", "monitors")
    else:
        monitors_file = "monitors.ini"

    main_logger.info("Loading monitor config from %s", monitors_file)

    try:
        allow_pickle = config.getboolean("monitor", "allow_pickle",
                                         fallback='true')
    except ValueError:
        main_logger.critical('allow_pickle should be "true" or "false".')
        sys.exit(1)

    m = SimpleMonitor(allow_pickle=allow_pickle)

    m = load_monitors(m, monitors_file)

    count = m.count_monitors()
    if count == 0:
        main_logger.critical("No monitors loaded :(")
        sys.exit(2)

    m = load_loggers(m, config)
    m = load_alerters(m, config)

    try:
        if config.get("monitor", "remote") == "1":
            if not options.no_network:
                enable_remote = True
                remote_port = int(config.get("monitor", "remote_port"))
            else:
                enable_remote = False
        else:
            enable_remote = False
    except Exception:
        enable_remote = False

    if not m.verify_dependencies():
        sys.exit(1)

    if options.test:
        main_logger.warning("Config test complete. Exiting.")
        sys.exit(0)

    if options.one_shot:
        main_logger.warning("One-shot mode: expecting monitors without 'fail' in the name to succeed, and with to fail. Will exit zero or non-zero accordingly.")

    try:
        key = config.get("monitor", "key")
    except Exception:
        key = None

    if enable_remote:
        if not options.quiet:
            if not allow_pickle:
                allowing_pickle = "not "
            else:
                allowing_pickle = ""
            main_logger.info("Starting remote listener thread ({0}allowing pickle data)".format(allowing_pickle))
        remote_listening_thread = Loggers.network.Listener(
            m, remote_port, key, allow_pickle=allow_pickle)
        remote_listening_thread.daemon = True
        remote_listening_thread.start()

    if not options.quiet:
        main_logger.info("=== Starting... (loop runs every %ds) Hit ^C to stop", interval)
    loop = True
    heartbeat = 0

    loops = int(options.loops)

    while loop:
        try:
            if loops > 0:
                loops -= 1
                if loops == 0:
                    main_logger.warning('Ran out of loop counter, will stop after this one')
                    loop = False
            m.run_tests()
            m.do_recovery()
            m.do_alerts()
            m.do_logs()

            if not options.quiet and not options.verbose and not options.no_heartbeat:
                heartbeat += 1
                if heartbeat == 2:
                    sys.stdout.write(".")
                    sys.stdout.flush()
                    heartbeat = 0
        except KeyboardInterrupt:

            if not options.quiet:
                print("\n--> EJECT EJECT")
            loop = False
        except Exception:
            sys.exc_info()
            main_logger.exception("Caught unhandled exception during main loop")
        if loop and enable_remote:
            if not remote_listening_thread.isAlive():
                main_logger.error("Listener thread died :(")
                remote_listening_thread = Loggers.network.Listener(
                    m, remote_port, key, allow_pickle=allow_pickle)
                remote_listening_thread.start()

        if options.one_shot:
            break

        try:
            time.sleep(interval)
        except Exception:
            main_logger.info("Quitting")
            loop = False

    if enable_remote:
        remote_listening_thread.running = False
        main_logger.info('Waiting for listener thread to exit')
        remote_listening_thread.join(0)

    if pidfile:
        try:
            os.unlink(pidfile)
        except Exception:
            main_logger.error("Couldn't remove pidfile!")

    if not options.quiet:
        main_logger.info("Finished.")

    if options.one_shot:  # pragma: no cover
        ok = True
        print('\n--> One-shot results:')
        for monitor in sorted(m.monitors.keys()):
            if "fail" in monitor:
                if m.monitors[monitor].error_count == 0:
                    print("    Monitor {0} should have failed".format(monitor))
                    ok = False
                else:
                    print("    Monitor {0} was ok (failed)".format(monitor))
            elif "skip" in monitor:
                if m.monitors[monitor].skipped():
                    print("    Monitor {0} was ok (skipped)".format(monitor))
                else:
                    print("    Monitor {0} should have been skipped".format(monitor))
                    ok = False
            else:
                if m.monitors[monitor].error_count > 0:
                    print("    Monitor {0} failed and shouldn't have".format(monitor))
                    ok = False
                else:
                    print("    Monitor {0} was ok".format(monitor))
        if not ok:
            print("Not all non-'fail' succeeded, or not all 'fail' monitors failed.")
            sys.exit(1)

    logging.shutdown()


if __name__ == "__main__":
    main()
