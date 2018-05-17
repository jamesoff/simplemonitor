# coding=utf-8
import pickle
import socket
import sys
import hmac
import traceback
import struct
import logging

import util

# From the docs:
#  Threads interact strangely with interrupts: the KeyboardInterrupt exception
#  will be received by an arbitrary thread. (When the signal module is
#  available, interrupts always go to the main thread.)

from threading import Thread

from .logger import Logger


class NetworkLogger(Logger):
    """Send our results over the network to another instance."""

    supports_batch = True

    def __init__(self, config_options):
        Logger.__init__(self, config_options)

        self.host = Logger.get_config_option(
            config_options,
            'host',
            required=True,
            allow_empty=False
        )
        self.port = Logger.get_config_option(
            config_options,
            'port',
            required_type='int',
            required=True
        )
        self.hostname = socket.gethostname()
        self.key = bytearray(
            Logger.get_config_option(
                config_options,
                'key',
                required=True,
                allow_empty=False),
            'utf-8'
        )

    def describe(self):
        return "Sending monitor results to {0}:{1}".format(self.host, self.port)

    def save_result2(self, name, monitor):
        if not self.doing_batch:
            self.logger_logger.error("NetworkLogger.save_result2() called while not doing batch.")
            return
        self.logger_logger.debug("network logger: %s %s", name, monitor)
        try:
            self.batch_data[monitor.name] = pickle.dumps(monitor)
        except Exception:
            self.logger_logger.exception('Failed to pickle monitor %s', name)

    def process_batch(self):
        try:
            p = pickle.dumps(self.batch_data)
            mac = hmac.new(self.key, p)
            send_bytes = struct.pack('B', mac.digest_size) + mac.digest() + p
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.host, self.port))
            s.send(send_bytes)
        except Exception as e:
            self.logger_logger.error("Failed to send network data")
        finally:
            s.close()


class Listener(Thread):
    """This class isn't actually a Logger, but is the receiving-end implementation for network logging.

    Here seemed a reasonable place to put it."""

    def __init__(self, simplemonitor, port, verbose=False, key=None):
        """Set up the thread.

        simplemonitor is a SimpleMonitor object which we will put our results into.
        """
        if key is None or key == "":
            raise util.LoggerConfigurationError("Network logger key is missing")
        Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', port))
        self.simplemonitor = simplemonitor
        self.verbose = verbose
        self.key = bytearray(key, 'utf-8')
        self.logger = logging.getLogger('simplemonitor.logger.networklistener')
        self.running = False

    def run(self):
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
                pickled = bytearray()
                while 1:
                    data = conn.recv(1024)
                    if not data:
                        break
                    pickled = pickled + data
                conn.close()
                self.logger.debug("Finished receiving from %s", addr[0])
                try:
                    # first byte is the size of the MAC
                    mac_size = pickled[0]
                    # then the MAC
                    their_digest = pickled[1:mac_size + 1]
                    # then the rest is the pickled data
                    pickled = pickled[mac_size + 1:]
                    mac = hmac.new(self.key, pickled)
                    my_digest = mac.digest()
                except IndexError:
                    raise ValueError('Did not receive any or enough data from %s', addr[0])
                self.logger.debug("Computed my digest to be %s; remote is %s", my_digest, their_digest)
                if not hmac.compare_digest(their_digest, my_digest):
                    raise Exception("Mismatched MAC for network logging data from %s\nMismatched key? Old version of SimpleMonitor?\n" % addr[0])
                result = pickle.loads(pickled)
                try:
                    self.simplemonitor.update_remote_monitor(result, addr[0])
                except Exception as e:
                    self.logger.exception('Error adding remote monitor')
            except socket.error as e:
                fail_info = sys.exc_info()
                try:
                    if fail_info[1][0] == 4:
                        # Interrupted system call
                        self.logger.warning("Interrupted system call in thread, I think that's a ^C")
                        self.running = False
                        self.sock.close()
                except IndexError:
                    pass
                if self.running:
                    self.logger.exception("Socket error caught in thread: %s")
            except Exception:
                self.logger.exception("Listener thread caught exception %s")
