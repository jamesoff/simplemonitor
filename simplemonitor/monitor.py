# coding=utf-8
"""A (fairly) simple host/service monitor.

isort:skip_file
"""


import logging
import os
import signal
import sys
import time
import argparse
from socket import gethostname
from typing import Any, Optional

# fmt: off
from .Alerters import (  # noqa: F401
    alerter,
    bulksms,
    execute,
    fortysixelks,
    mail,
    nc,
    pushbullet,
    pushover,
    ses,
    slack,
    syslogger,
    telegram,
)
from .Loggers import db  # noqa: F401
from .Loggers import file as file_logger  # noqa: F401
from .Loggers import logger, mqtt  # noqa: F401
from .Loggers import network as network_logger  # noqa: F401
from .Monitors import compound  # noqa: F401
from .Monitors import file as file_monitor  # noqa: F401
from .Monitors import hass, host, monitor  # noqa: F401
from .Monitors import network as network_monitor  # noqa: F401
from .Monitors import ring, service  # noqa: F401
# fmt: on
from .simplemonitor import SimpleMonitor
from .util import get_config_dict
from .util.envconfig import EnvironmentAwareConfigParser

try:
    import colorlog
except ImportError:
    pass

from .version import VERSION

main_logger = logging.getLogger("simplemonitor")
need_hup = False
hup_timestamp = None


def setup_signals() -> None:
    _message = "Unable to trap SIGHUP... maybe it doesn't exist on this platform. Set 'hup_file' in config and touch that file to trigger a config reload."
    try:
        signal.signal(signal.SIGHUP, handle_sighup)
    except ValueError:  # pragma: no cover
        main_logger.warning(_message)
    except AttributeError:  # pragma: no cover
        main_logger.warning(_message)


def handle_sighup(sig_number: Any, stack_frame: Any) -> None:
    global need_hup
    main_logger.warning("Received SIGHUP")
    need_hup = True


def check_hup_file(path: Optional[str]) -> bool:
    """Check a file's timestamp, and if it's newer than last time, treat it
    the same as receiving SIGHUP so that a reload is triggered. This allows
    config reloading on platforms which don't support the signal (i.e.
    Windows)"""
    if path is None:
        return False
    try:
        statinfo = os.stat(path)
    except IOError:
        main_logger.debug("Could not call stat() on path %s for file-based HUP", path)
        return False
    global hup_timestamp
    modification_time = statinfo.st_mtime
    if hup_timestamp is None:
        hup_timestamp = modification_time
        return True
    if modification_time > hup_timestamp:
        hup_timestamp = modification_time
        return True
    return False


def load_everything(
    m: SimpleMonitor, config: EnvironmentAwareConfigParser
) -> SimpleMonitor:
    """Load monitors, alerters and loggers into a SimpleMonitor object."""
    monitors_file = config.get("monitor", "monitors", fallback="monitors.ini")
    m = load_monitors(m, monitors_file)
    m = load_loggers(m, config)
    m = load_alerters(m, config)
    if not m.verify_dependencies():
        sys.exit(1)
    return m


def load_config(config_file: str) -> EnvironmentAwareConfigParser:
    """Load the main configuration and return a config object."""
    config = EnvironmentAwareConfigParser()
    if not os.path.exists(config_file):
        main_logger.critical('Configuration file "%s" does not exist!', config_file)
        sys.exit(1)
    try:
        config.read(config_file)
    except Exception as e:
        main_logger.critical("Unable to read configuration file")
        main_logger.critical(e)
        sys.exit(1)
    return config


def load_monitors(m: SimpleMonitor, filename: str) -> SimpleMonitor:
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

    main_logger.info("=== Loading monitors")
    for this_monitor in monitors:
        if config.has_option(this_monitor, "runon"):
            if myhostname != config.get(this_monitor, "runon").lower():
                main_logger.warning(
                    "Ignoring monitor %s because it's only for host %s",
                    this_monitor,
                    config.get(this_monitor, "runon"),
                )
                continue
        monitor_type = config.get(this_monitor, "type")
        new_monitor = None
        config_options = default_config.copy()
        config_options.update(get_config_dict(config, this_monitor))
        if m.has_monitor(this_monitor):
            if m.monitors[this_monitor].type == config_options["type"]:
                main_logger.info("Updating configuration for monitor %s", this_monitor)
                m.update_monitor_config(this_monitor, config_options)
            else:
                main_logger.error(
                    "Cannot update monitor {} from type {} to type {}. Keeping original config for this monitor.".format(
                        this_monitor,
                        m.monitors[this_monitor].type,
                        config_options["type"],
                    )
                )
            continue

        try:
            cls = monitor.get_class(monitor_type)
        except KeyError:
            main_logger.error(
                "Unknown monitor type %s; valid types are: %s",
                monitor_type,
                ", ".join(monitor.all_types()),
            )
            continue
        new_monitor = cls(this_monitor, config_options)
        # new_monitor.set_mon_refs(m)

        main_logger.info(
            "Adding %s monitor %s: %s", monitor_type, this_monitor, new_monitor
        )
        m.add_monitor(this_monitor, new_monitor)

    for i in list(m.monitors.keys()):
        m.monitors[i].set_mon_refs(m.monitors)
        m.monitors[i].post_config_setup()
    m.prune_monitors(monitors)
    main_logger.info("--- Loaded %d monitors", m.count_monitors())
    return m


def load_loggers(
    m: SimpleMonitor, config: EnvironmentAwareConfigParser
) -> SimpleMonitor:
    """Load the loggers listed in the config object."""

    if config.has_option("reporting", "loggers"):
        loggers = config.get("reporting", "loggers").split(",")
    else:
        loggers = []

    main_logger.info("=== Loading loggers")
    for config_logger in loggers:
        logger_type = config.get(config_logger, "type")
        config_options = get_config_dict(config, config_logger)
        config_options["_name"] = config_logger
        if m.has_logger(config_logger):
            if m.loggers[config_logger].type == config_options["type"]:
                main_logger.info("Updating configuration for logger %s", config_logger)
                m.update_logger_config(config_logger, config_options)
            else:
                main_logger.error(
                    "Cannot update logger {} from type {} to type {}. Keeping original config for this logger.".format(
                        config_logger,
                        m.loggers[config_logger].type,
                        config_options["type"],
                    )
                )
            continue
        try:
            logger_cls = logger.get_class(logger_type)
        except KeyError:
            main_logger.error(
                "Unknown logger type %s; valid types are: %s",
                logger_type,
                ", ".join(logger.all_types()),
            )
            continue
        new_logger = logger_cls(config_options)
        main_logger.info(
            "Adding %s logger %s: %s", logger_type, config_logger, new_logger
        )
        m.add_logger(config_logger, new_logger)
        del new_logger
    m.prune_loggers(loggers)
    main_logger.info("--- Loaded %d loggers", len(m.loggers))
    return m


def load_alerters(
    m: SimpleMonitor, config: EnvironmentAwareConfigParser
) -> SimpleMonitor:
    """Load the alerters listed in the config object."""
    if config.has_option("reporting", "alerters"):
        alerters = config.get("reporting", "alerters").split(",")
    else:
        alerters = []

    main_logger.info("=== Loading alerters")
    for this_alerter in alerters:
        alerter_type = config.get(this_alerter, "type")
        config_options = get_config_dict(config, this_alerter)
        if m.has_alerter(this_alerter):
            if m.alerters[this_alerter].type == config_options["type"]:
                main_logger.info("Updating configuration for alerter %s", this_alerter)
                m.update_alerter_config(this_alerter, config_options)
            else:
                main_logger.error(
                    "Cannot update alerter {} from type {} to type {}. Keeping original config for this alerter.".format(
                        this_alerter,
                        m.alerters[this_alerter].type,
                        config_options["type"],
                    )
                )
            continue
        try:
            alerter_cls = alerter.get_class(alerter_type)
        except KeyError:
            main_logger.error(
                "Unknown alerter type %s; valid types are: %s",
                alerter_type,
                ", ".join(alerter.all_types()),
            )
            continue
        new_alerter = alerter_cls(config_options)
        main_logger.info("Adding %s alerter %s", alerter_type, this_alerter)
        new_alerter.name = this_alerter
        m.add_alerter(this_alerter, new_alerter)
        del new_alerter
    m.prune_alerters(alerters)
    main_logger.info("--- Loaded %d alerters", len(m.alerters))
    return m


def main() -> None:
    r"""This is where it happens \o/"""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version", action="version", version="%(prog)s {}".format(VERSION)
    )
    output_group = parser.add_argument_group(title="Output controls")
    testing_group = parser.add_argument_group(title="Test and debug tools")
    output_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        dest="verbose",
        default=False,
        help="Alias for --log-level=info",
    )
    output_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        dest="quiet",
        default=False,
        help="Alias for --log-level=critical",
    )
    testing_group.add_argument(
        "-t",
        "--test",
        action="store_true",
        dest="test",
        default=False,
        help="Test config and exit",
    )
    parser.add_argument(
        "-p", "--pidfile", dest="pidfile", default=None, help="Write PID into this file"
    )
    parser.add_argument(
        "-N",
        "--no-network",
        dest="no_network",
        default=False,
        action="store_true",
        help="Disable network listening socket (if enabled in config)",
    )
    output_group.add_argument(
        "-d",
        "--debug",
        dest="debug",
        default=False,
        action="store_true",
        help="Alias for --log-level=debug",
    )
    parser.add_argument(
        "-f",
        "--config",
        dest="config",
        default="monitor.ini",
        help="configuration file",
    )
    output_group.add_argument(
        "-H",
        "--no-heartbeat",
        action="store_true",
        dest="no_heartbeat",
        default=False,
        help="Omit printing the '.' character when running checks",
    )
    testing_group.add_argument(
        "-1",
        "--one-shot",
        action="store_true",
        dest="one_shot",
        default=False,
        help='Run the monitors once only, without alerting. Require monitors without "fail" in the name to succeed. Exit zero or non-zero accordingly.',
    )
    testing_group.add_argument(
        "--loops",
        dest="loops",
        default=-1,
        type=int,
        help="Number of iterations to run before exiting",
    )
    output_group.add_argument(
        "-l",
        "--log-level",
        dest="loglevel",
        default="warn",
        help="Log level: critical, error, warn, info, debug",
    )
    output_group.add_argument(
        "-C",
        "--no-colour",
        "--no-color",
        action="store_true",
        dest="no_colour",
        default=False,
        help="Do not colourise log output",
    )
    output_group.add_argument(
        "--no-timestamps",
        action="store_true",
        dest="no_timestamps",
        default=False,
        help="Do not prefix log output with timestamps",
    )
    testing_group.add_argument(
        "--dump-known-resources",
        action="store_true",
        dest="dump_resources",
        default=False,
        help="Print out loaded Monitor, Alerter and Logger types",
    )

    options = parser.parse_args()

    if options.dump_resources:
        import pprint

        print("Monitors:")
        pprint.pprint(sorted(monitor.all_types()), compact=True)
        print("Loggers:")
        pprint.pprint(sorted(logger.all_types()), compact=True)
        print("Alerters:")
        pprint.pprint(sorted(alerter.all_types()), compact=True)
        sys.exit(0)

    if options.quiet:
        options.loglevel = "critical"

    if options.verbose:
        options.loglevel = "info"

    if options.debug:
        options.loglevel = "debug"

    if options.no_timestamps:
        logging_timestamp = ""
    else:
        logging_timestamp = "%(asctime)s "

    try:
        log_level = getattr(logging, options.loglevel.upper())
    except AttributeError:
        print("Log level {0} is unknown".format(options.loglevel))
        sys.exit(1)

    log_datefmt = "%Y-%m-%d %H:%M:%S"
    log_plain_format = logging_timestamp + "%(levelname)8s (%(name)s) %(message)s"
    if not options.no_colour:
        try:
            handler = colorlog.StreamHandler()
            handler.setFormatter(
                colorlog.ColoredFormatter(
                    logging_timestamp
                    + "%(log_color)s%(levelname)8s%(reset)s (%(name)s) %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            main_logger.addHandler(handler)
        except NameError:
            logging.basicConfig(format=log_plain_format, datefmt=log_datefmt)
            main_logger.error("Could not enable colorlog")
    else:
        logging.basicConfig(format=log_plain_format, datefmt=log_datefmt)

    main_logger.setLevel(log_level)

    if not options.quiet:
        main_logger.info("=== SimpleMonitor v%s", VERSION)
        main_logger.info("Loading main config from %s", options.config)

    config = load_config(options.config)

    try:
        interval = config.getint("monitor", "interval")
    except Exception:
        main_logger.critical(
            'Missing [monitor] section from config file, or missing the "interval" setting in it'
        )
        sys.exit(1)

    pidfile = config.get("monitor", "pidfile", fallback=None)

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

    monitors_file = config.get("monitor", "monitors", fallback="monitors.ini")
    main_logger.info("Loading monitor config from %s", monitors_file)

    try:
        allow_pickle = config.getboolean("monitor", "allow_pickle", fallback=True)
    except ValueError:
        main_logger.critical('allow_pickle should be "true" or "false".')
        sys.exit(1)

    m = SimpleMonitor(allow_pickle=allow_pickle)
    m = load_everything(m, config)

    count = m.count_monitors()
    if count == 0:
        main_logger.critical("No monitors loaded :(")
        sys.exit(2)

    enable_remote = False
    if config.get("monitor", "remote", fallback="0") == "1":
        if not options.no_network:
            enable_remote = True
            remote_port = int(config.get("monitor", "remote_port"))
    key = config.get("monitor", "key", fallback=None)

    if options.test:
        main_logger.warning("Config test complete. Exiting.")
        sys.exit(0)

    if options.one_shot:
        main_logger.warning(
            "One-shot mode: expecting monitors without 'fail' in the name to succeed, and with to fail. Will exit zero or non-zero accordingly."
        )

    if enable_remote:
        if not options.quiet:
            if not allow_pickle:
                allowing_pickle = "not "
            else:
                allowing_pickle = ""
            main_logger.info(
                "Starting remote listener thread ({0}allowing pickle data)".format(
                    allowing_pickle
                )
            )
        remote_listening_thread = network_logger.Listener(
            m, remote_port, key, allow_pickle=allow_pickle
        )
        remote_listening_thread.daemon = True
        remote_listening_thread.start()

    if not options.quiet:
        main_logger.info(
            "=== Starting... (loop runs every %ds) Hit ^C to stop", interval
        )
    loop = True
    heartbeat = 0

    loops = int(options.loops)
    setup_signals()
    hup_file = config.get("monitor", "hup_file", fallback=None)
    if hup_file:
        main_logger.info(
            "Watching modification time of %s; increase it to trigger a config reload",
            hup_file,
        )
        check_hup_file(hup_file)

    global need_hup
    while loop:
        try:
            if loops > 0:
                loops -= 1
                if loops == 0:
                    main_logger.warning(
                        "Ran out of loop counter, will stop after this one"
                    )
                    loop = False
            if need_hup or check_hup_file(hup_file):
                try:
                    main_logger.warning("Reloading configuration")
                    config = load_config(options.config)
                    interval = config.getint("monitor", "interval")
                    m = load_everything(m, config)
                    m.hup_loggers()
                    need_hup = False
                except Exception:
                    main_logger.exception("Error while reloading configuration")
                    sys.exit(1)
            m.run_loop()

            if (
                options.loglevel in ["error", "critical", "warn"]
                and not options.no_heartbeat
            ):
                heartbeat += 1
                if heartbeat == 2:
                    sys.stdout.write(".")
                    sys.stdout.flush()
                    heartbeat = 0
        except KeyboardInterrupt:
            main_logger.info("Received ^C")
            loop = False
        except Exception:
            sys.exc_info()
            main_logger.exception("Caught unhandled exception during main loop")
        if loop and enable_remote:
            if not remote_listening_thread.isAlive():
                main_logger.error("Listener thread died :(")
                remote_listening_thread = network_logger.Listener(
                    m, remote_port, key, allow_pickle=allow_pickle
                )
                remote_listening_thread.start()

        if options.one_shot:
            break

        try:
            if loop:
                time.sleep(interval)
        except Exception:
            main_logger.info("Quitting")
            loop = False

    if enable_remote:
        remote_listening_thread.running = False
        main_logger.info("Waiting for listener thread to exit")
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
        print("\n--> One-shot results:")
        tail_info = []
        for this_monitor in sorted(m.monitors.keys()):
            if "fail" in this_monitor:
                if m.monitors[this_monitor].error_count == 0:
                    tail_info.append(
                        "    Monitor {0} should have failed".format(this_monitor)
                    )
                    ok = False
                else:
                    print("    Monitor {0} was ok (failed)".format(this_monitor))
            elif "skip" in this_monitor:
                if m.monitors[this_monitor].skipped():
                    print("    Monitor {0} was ok (skipped)".format(this_monitor))
                else:
                    tail_info.append(
                        "    Monitor {0} should have been skipped".format(this_monitor)
                    )
                    ok = False
            else:
                if m.monitors[this_monitor].error_count > 0:
                    tail_info.append(
                        "    Monitor {0} failed and shouldn't have".format(this_monitor)
                    )
                    ok = False
                else:
                    print("    Monitor {0} was ok".format(this_monitor))
        if len(tail_info):
            print()
            for line in tail_info:
                print(line)
        if not ok:
            print("Not all non-'fail' succeeded, or not all 'fail' monitors failed.")
            sys.exit(1)

    logging.shutdown()


if __name__ == "__main__":
    main()
