"""
Network logging support for SimpleMonitor
"""

import hmac
import logging
import socket
import struct
from threading import Thread
from typing import Any, Dict, Union, cast

from ..Monitors.monitor import Monitor
from ..util import LoggerConfigurationError
from ..util.json_encoding import json_dumps, json_loads
from .logger import Logger, register

# From the docs:
#  Threads interact strangely with interrupts: the KeyboardInterrupt exception
#  will be received by an arbitrary thread. (When the signal module is
#  available, interrupts always go to the main thread.)

_DIGEST_NAME = "md5"


@register
class NetworkLogger(Logger):
    """Send our results over the network to another instance."""

    logger_type = "network"
    supports_batch = True

    def __init__(self, config_options: dict) -> None:
        super().__init__(config_options)

        self.host = cast(
            str, self.get_config_option("host", required=True, allow_empty=False)
        )
        self.port = cast(
            int, self.get_config_option("port", required_type="int", required=True)
        )
        self.hostname = cast(str, self.get_config_option("client_name"))
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
        if monitor.monitor_type == "unknown":
            self.logger_logger.error(
                "Cannot serialize monitor %s, has type 'unknown'.", name
            )
            return
        try:
            if monitor.monitor_type == "compound":
                self.logger_logger.error(
                    "not pickling compound monitor - currently incompatible with network loggers"
                )
            else:
                data = {
                    "cls_type": monitor.monitor_type,
                    "data": monitor.to_python_dict(),
                }
                if self.batch_data is not None:
                    self.batch_data[monitor.name] = data
                else:
                    self.batch_data = {monitor.name: data}  # type: Dict[str, dict]
        except Exception:  # pylint: disable=broad-except
            self.logger_logger.exception("Failed to serialize monitor %s", name)

    def process_batch(self) -> None:
        try:
            payload = json_dumps(
                {
                    "version": 2,
                    "name": self.hostname,
                    "monitors": self.batch_data,
                }
            )
            mac = hmac.new(self.key, payload, _DIGEST_NAME)
            send_bytes = struct.pack("B", mac.digest_size) + mac.digest() + payload
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                try:
                    sock.connect((self.host, self.port))
                except socket.error:
                    sock.close()
                    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    sock.connect((self.host, self.port))
                sock.send(send_bytes)
            finally:
                sock.close()
        except Exception as exception:  # pylint: disable=broad-except
            self.logger_logger.exception("Failed to send network data: %s", exception)


class Listener(Thread):
    """
    Handle incoming remote connections.

    This class isn't actually a Logger, but is the receiving-end
    implementation for network logging.

    Here seemed a reasonable place to put it."""

    def __init__(
        self,
        simplemonitor: Any,
        port: int,
        key: str = None,
        bind_host: str = "",
        ipv4_only: bool = False,
    ) -> None:
        """Set up the thread.

        simplemonitor is a SimpleMonitor object which we will put our results into.
        """
        if key is None or key == "":
            raise LoggerConfigurationError("Network logger key is missing")
        Thread.__init__(self, daemon=True)
        if ipv4_only:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            # try IPv6 and fallback to IPv4
            try:
                self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, False)
            except OSError:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((bind_host, port))
        self.simplemonitor = simplemonitor
        self.key = bytearray(key, "utf-8")
        self.logger = logging.getLogger("simplemonitor.logger.networklistener")
        self.running = False  # type: bool

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
                if len(serialized) == 0:
                    self.logger.debug("No data from %s", addr[0])
                    continue
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
                except IndexError as error:  # pragma: no cover
                    raise ValueError(
                        "Did not receive any or enough data from {}".format(addr[0])
                    ) from error
                if isinstance(my_digest, str):
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
                        "Mismatched MAC for network logging data from %s\n"
                        "Mismatched key? Old version of SimpleMonitor?\n" % addr[0]
                    )
                result = json_loads(bytes(serialized))  # type: dict
                version = result.get("version", 1)
                if version == 1:
                    self.logger.debug("Received version 1 data from %s", addr[0])
                    self.simplemonitor.update_remote_monitor(result, addr[0])
                elif version == 2:
                    self.logger.debug("Received version 2 data from %s", addr[0])
                    self._handle_data_v2(result, addr[0])
                else:
                    self.logger.critical(
                        "Received unknown version %s data from %s cannot process",
                        version,
                        addr[0],
                    )
            except socket.error as exception:
                if exception.errno == 4:
                    # Interrupted system call
                    self.logger.warning(
                        "Interrupted system call in thread, I think that's a ^C"
                    )
                    self.running = False
                    self.sock.close()
                if self.running:
                    self.logger.exception("Socket error caught in thread")
            except Exception:  # pylint: disable=broad-except
                self.logger.exception("Listener thread caught exception")
        self.logger.warning("Listener stopped")

    def _handle_data_v2(
        self, data: Dict[str, Union[str, int, Dict[str, dict]]], source: str
    ) -> None:
        """Handle data in v2 format

        {
            "version": 2,
            "name": "remote_instance_name",
            "monitors": [ monitor data, ... ]
        }
        """
        remote_instance_name = str(data.get("name", source))
        if not remote_instance_name or remote_instance_name == "None":
            remote_instance_name = source
        remote_monitors = data.get("monitors", None)
        if remote_monitors is None:
            self.logger.error(
                "Received empty monitors list from remote instance %s",
                remote_instance_name,
            )
        elif isinstance(remote_monitors, dict):
            self.simplemonitor.update_remote_monitor(
                remote_monitors, remote_instance_name
            )
        else:
            self.logger.error(
                "Bad data type for monitors from remote instance %s",
                remote_instance_name,
            )
