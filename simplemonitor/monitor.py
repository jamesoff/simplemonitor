# coding=utf-8
"""A (fairly) simple host/service monitor. """


import argparse
import logging
import os
import sys

from .simplemonitor import SimpleMonitor
from .version import VERSION

try:
    import colorlog
except ImportError:
    pass


main_logger = logging.getLogger("simplemonitor")


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
        help=(
            "configuration file (this is the main config; "
            "you also need monitors.ini (default filename))"
        ),
    )
    parser.add_argument(
        "-j",
        "--threads",
        dest="threads",
        default=os.cpu_count(),  # default used by the library anyway
        type=int,
        help=(
            f"number of threads to run for checking monitors (default (cpus): {os.cpu_count()})"
        ),
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
        help=(
            "Run the monitors once only, without alerting. Require monitors without "
            '"fail" in the name to succeed. Exit zero or non-zero accordingly'
        ),
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

        import simplemonitor.Alerters.alerter as alerter
        import simplemonitor.Loggers.logger as logger
        import simplemonitor.Monitors.monitor as monitor

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

    m = SimpleMonitor(
        config_file=options.config,
        no_network=options.no_network,
        max_loops=options.loops,
        heartbeat=not options.no_heartbeat,
        one_shot=options.one_shot,
        max_workers=options.threads,
    )

    if options.test:
        main_logger.warning("Config test complete. Exiting.")
        sys.exit(0)

    if options.one_shot:
        main_logger.warning(
            "One-shot mode: expecting monitors without 'fail' in the name to succeed, "
            "and with to fail. Will exit zero or non-zero accordingly."
        )

    m.run()

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
                    tail_info.append(
                        "        {}".format(m.monitors[this_monitor].last_result)
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
                        "    Monitor {0} failed and shouldn't have: {1}".format(
                            this_monitor, m.monitors[this_monitor].last_result
                        )
                    )
                    ok = False
                    tail_info.append(
                        "        {}".format(m.monitors[this_monitor].last_result)
                    )
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
