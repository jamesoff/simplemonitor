import logging
import multiprocessing as mp
import os
import socket
import sys
from typing import Any

import win32event
import win32service
import win32serviceutil

from simplemonitor import monitor

r"""
Notes:

This service expects the 'monitor.ini' file to exist in the same directory.

If you receive an error "The service did not respond to the start
or control request in a timely fashion", it is likely/possible you need to
include the python and pywin32 binaries in your path:

e.g. (from an administrator prompt)
setx /M PATH "%PATH%;c:\Python;c:\Python\scripts;c:\Python\Lib\site-packages\pywin32_system32;c:\Python\Lib\site-packages\win32"
"""

# Change this to the location of your config file, if required
APP_PATH = os.path.realpath(os.path.dirname(__file__))
CONFIG = os.path.join(APP_PATH, "monitor.ini")
LOGFILE = os.path.join(APP_PATH, "simplemonitor.log")


# Setup Logging
def configure_logger(
    logger: logging.Logger, level: int = logging.DEBUG
) -> logging.Logger:
    logger.setLevel(level)
    fh = logging.FileHandler(LOGFILE)
    fh.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def setup_logger(level: int = logging.DEBUG) -> logging.Logger:
    return configure_logger(mp.get_logger(), level)


LOGGER = setup_logger(logging.INFO)


class AppServerSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "SimpleMonitor"
    _svc_display_name_ = "SimpleMonitor"
    _svc_description_ = "A service wrapper for the python SimpleMonitor program"

    def __init__(self, args: Any) -> None:
        # Initialise service
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

        # Setup logger
        self.logger = LOGGER
        self.logger.info("Initialised %s service", self._svc_display_name_)

    def SvcStop(self) -> None:
        self.logger.info("Stopping %s service", self._svc_display_name_)
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self) -> None:
        self.logger.info("Starting %s service", self._svc_display_name_)
        import servicemanager

        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name, ""),
        )

        # Start monitor
        p_mon = mp.Process(target=run_monitor)
        p_mon.start()
        self.logger.info("Started %s service", self._svc_display_name_)

        # Wait for Monitor to finish
        while True:
            try:
                # Watch monitor process for 2 seconds
                p_mon.join(timeout=2)
                if not p_mon.is_alive():
                    self.logger.warning("Service stopped prematurely.")
                    self.SvcStop()

                # Check if we've received a stop command
                rc = win32event.WaitForSingleObject(self.hWaitStop, 500)
                if rc == win32event.WAIT_OBJECT_0:
                    p_mon.terminate()
                    p_mon.join()
                    break
                self.logger.debug("Still running...")
            except KeyboardInterrupt:
                self.logger.warning("Interrupted %s service", self._svc_display_name_)
                break

        self.logger.info("Stopped %s service", self._svc_display_name_)


def run_monitor() -> None:
    sys.argv = ["monitor.py", "-vH", "--config={}".format(CONFIG)]
    monitor.main()


def main() -> None:
    win32serviceutil.HandleCommandLine(AppServerSvc)


if __name__ == "__main__":
    main()
