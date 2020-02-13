# coding=utf-8
import hmac
import logging
import pickle
import socket
import struct
from json import JSONDecodeError
from threading import Thread
from typing import Any, cast

from ..Monitors.monitor import Monitor
from ..util import LoggerConfigurationError, json_dumps, json_loads
from .logger import Logger, register

# From the docs:
#  Threads interact strangely with interrupts: the KeyboardInterrupt exception
#  will be received by an arbitrary thread. (When the signal module is
#  available, interrupts always go to the main thread.)

_DIGEST_NAME = "md5"


@register
class NetworkLogger(Logger):
    """Send our results over the network to another instance."""

    type = "network"
    supports_batch = True

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)

        self.host = cast(
            str, self.get_config_option("host", required=True, allow_empty=False)
        )
        self.port = cast(
            int, self.get_config_option("port", required_type="int", required=True)
        )
        self.hostname = socket.gethostname()
        self.key = bytearray(
            self.get_config_option("key", required=True, allow_empty=False), "utf-8"
        )

    def describe(self) -> str:
        return "Sending monitor results to {0}:{1}".format(self.host, self.port)

    def save_result2(self, name: str, monitor: Monitor) -> None:
        if not self.doing_batch:  # pragma: no cover
            self.logger_logger.error(
                "NetworkLogger.save_result2() called while not doing batch."
            )
            return
        self.logger_logger.debug("network logger: %s %s", name, monitor)
        if monitor.type == "unknown":
            self.logger_logger.error(
                "Cannot serialize monitor %s, has type 'unknown'." % name
            )
            return
        try:
            if monitor.type == "compound":
                self.logger_logger.error(
                    "not pickling compound monitor - currently incompatible with network loggers"
                )
            else:
                data = {"cls_type": monitor.type, "data": monitor.to_python_dict()}
                # TODO: why does the line below make mypy cross?
                self.batch_data[monitor.name] = data  # type: ignore
        except Exception:
            self.logger_logger.exception("Failed to serialize monitor %s", name)

    def process_batch(self) -> None:
        try:
            p = json_dumps(self.batch_data)
            mac = hmac.new(self.key, p, _DIGEST_NAME)
            send_bytes = struct.pack("B", mac.digest_size) + mac.digest() + p
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                try:
                    s.connect((self.host, self.port))
                except socket.error:
                    s.close()
                    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    s.connect((self.host, self.port))
                s.send(send_bytes)
            finally:
                s.close()
        except Exception:
            self.logger_logger.exception("Failed to send network data")


class Listener(Thread):
    """This class isn't actually a Logger, but is the receiving-end implementation for network logging.

    Here seemed a reasonable place to put it."""

    def __init__(
        self, simplemonitor: Any, port: int, key: str = None, allow_pickle: bool = True
    ) -> None:
        """Set up the thread.

        simplemonitor is a SimpleMonitor object which we will put our results into.
        """
        if key is None or key == "":
            raise LoggerConfigurationError("Network logger key is missing")
        Thread.__init__(self)
        self.allow_pickle = allow_pickle
        # try IPv6 and fallback to IPv4
        try:
            self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, False)
        except OSError:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("", port))
        self.simplemonitor = simplemonitor
        self.key = bytearray(key, "utf-8")
        self.logger = logging.getLogger("simplemonitor.logger.networklistener")
        self.running = False

    def run(self) -> None:
        """The main body of our thread.

        The loop here keeps going until we're killed by the main app.
        When the main app kills us (with join()), socket.listen throws socket.error.
        """
        self.running = True
        while self.running:
            try:
                self.sock.listen(5)
                conn, addr = self.sock.accept()
                self.logger.debug("Got connection from %s", addr[0])
                serialized = bytearray()
                while 1:
                    data = conn.recv(1024)
                    if not data:
                        break
                    serialized += data
                conn.close()
                self.logger.debug("Finished receiving from %s", addr[0])
                try:
                    # first byte is the size of the MAC
                    mac_size = serialized[0]
                    # then the MAC
                    their_digest = serialized[1 : mac_size + 1]
                    # then the rest is the serialized data
                    serialized = serialized[mac_size + 1 :]
                    mac = hmac.new(self.key, serialized, _DIGEST_NAME)
                    my_digest = mac.digest()
                except IndexError:  # pragma: no cover
                    raise ValueError(
                        "Did not receive any or enough data from %s", addr[0]
                    )
                if type(my_digest) is str:
                    self.logger.debug(
                        "Computed my digest to be %s; remote is %s",
                        my_digest,
                        their_digest,
                    )
                else:
                    self.logger.debug(
                        "Computed my digest to be %s; remote is %s",
                        my_digest.hex(),
                        their_digest.hex(),
                    )
                if not hmac.compare_digest(their_digest, my_digest):
                    raise Exception(
                        "Mismatched MAC for network logging data from %s\nMismatched key? Old version of SimpleMonitor?\n"
                        % addr[0]
                    )
                try:
                    result = json_loads(serialized)
                except JSONDecodeError:
                    result = pickle.loads(serialized)
                try:
                    self.simplemonitor.update_remote_monitor(result, addr[0])
                except Exception:
                    self.logger.exception("Error adding remote monitor")
            except socket.error as e:
                if e.errno == 4:
                    # Interrupted system call
                    self.logger.warning(
                        "Interrupted system call in thread, I think that's a ^C"
                    )
                    self.running = False
                    self.sock.close()
                if self.running:
                    self.logger.exception("Socket error caught in thread: %s")
            except Exception:
                self.logger.exception("Listener thread caught exception %s")
