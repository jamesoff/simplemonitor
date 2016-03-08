import pickle
import socket
import sys
import hmac

# From the docs:
#  Threads interact strangely with interrupts: the KeyboardInterrupt exception
#  will be received by an arbitrary thread. (When the signal module is
#  available, interrupts always go to the main thread.)

from threading import Thread

from logger import Logger


class NetworkLogger(Logger):
    """Send our results over the network to another instance."""

    supports_batch = True

    def __init__(self, config_options):
        Logger.__init__(self, config_options)

        try:
            self.host = config_options["host"]
            self.port = int(config_options["port"])
            self.hostname = socket.gethostname()
            self.key = config_options["key"]
        except:
            raise RuntimeError("missing config options for network monitor")

    def save_result2(self, name, monitor):
        if not self.doing_batch:
            print "NetworkLogger.save_result2() called while not doing batch."
            return
        # id = "%s_%s" % (self.hostname, monitor.name)
        # data_line = {
        #        "id": id,
        #        "name": self.hostname + "/" + monitor.name,
        #        "type": monitor.type,
        #        "host": self.hostname,
        #        "vfc": monitor.virtual_fail_count(),
        #        "failed_at": monitor.first_failure_time(),
        #        "more_info": monitor.get_result(),
        #        "just_recovered": monitor.all_better_now(),
        #        "urgent": monitor.is_urgent()
        #        }

        # self.batch_data[monitor.name] = data_line
        self.batch_data[monitor.name] = pickle.dumps(monitor)

    def process_batch(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.host, self.port))
            p = pickle.dumps(self.batch_data)
            mac = hmac.new(self.key, p)
            # print "My MAC is %s" % mac.hexdigest()
            s.send("%s\n%s" % (mac.hexdigest(), p))
        except Exception, e:
            print "Failed to send data: %s" % e
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
            raise Exception("Network logger key is missing")
        Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', port))
        self.simplemonitor = simplemonitor
        self.verbose = verbose
        self.key = key

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
                if self.verbose:
                    print "--> Got connection from %s" % addr[0]
                pickled = ""
                while 1:
                    data = conn.recv(1024)
                    pickled += data
                    if not data:
                        break
                conn.close()
                if self.verbose:
                    print "--> Finished receiving from %s" % addr[0]
                # compute our own HMAC and compare
                bits = pickled.split("\n", 1)
                their_digest = bits[0]
                pickled = bits[1]
                mac = hmac.new(self.key, pickled)
                my_digest = mac.hexdigest()
                if self.verbose:
                    print "Computed my digest to be %s" % my_digest
                    print "Remote digest is %s" % their_digest
                if not hmac.compare_digest(their_digest, my_digest):
                    raise Exception("Mismatched MAC for network logging data from %s\nMismatched key? Old version of SimpleMonitor?\n" % addr[0])
                result = pickle.loads(pickled)
                try:
                    self.simplemonitor.update_remote_monitor(result, addr[0])
                except Exception, e:
                    fail_info = sys.exc_info()
                    sys.stderr.write("Error adding remote monitor %s" % e)

            except socket.error, e:
                fail_info = sys.exc_info()
                try:
                    if fail_info[1][0] == 4:
                        # Interrupted system call
                        print "Interrupted system call in thread, I think that's a ^C"
                        self.running = False
                        self.sock.close()
                except:
                    pass
                if self.running:
                    print "Socket error caught in thread: %s" % e
            except Exception, e:
                # fail_info = sys.exc_info()
                # print fail_info
                # print traceback.print_tb(fail_info[2])
                sys.stderr.write("Listener thread caught exception %s" % e)
