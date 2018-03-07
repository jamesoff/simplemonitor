#!/usr/bin/env
from __future__ import print_function # Only Python 2.x
import multiprocessing as mp 
import logging
import subprocess
import SimpleHTTPServer
import SocketServer
import os
import sys

PORT = int(os.environ['HTTP_PORT']) if 'HTTP_PORT' in os.environ else 8012
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitor.py")

CONFIG = "/config/monitor.ini"
HTML = "/config/html/"

print("Running monitor.py from: {}".format(SCRIPT))
print("Looking for config file at: {}".format(CONFIG))
print("Serving HTTP from: {}".format(CONFIG))


def execute(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line 
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

def run_monitor():
    print("Starting Monitor...")
    sys.stdout.flush()
    import monitor
    sys.argv = ['monitor.py', "-vH", "--config={}".format(CONFIG)]
    monitor.main()
    print("Monitor stopped.")
    sys.stdout.flush()

def run_http():
    os.chdir(HTML)
    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd = SocketServer.TCPServer(("", PORT), Handler)
    print("Displaying HTTP output on http://localhost:{}".format(PORT))
    print("Starting HTTP Server...")
    sys.stdout.flush()
    httpd.serve_forever()
    print("HTTP Server Stopped.")
    sys.stdout.flush()


# Setup monitor and http processess
mp.log_to_stderr(logging.DEBUG)
p_mon = mp.Process(target=run_monitor)
p_http = mp.Process(target=run_http)
p_http.daemon = True
p_mon.start()
p_http.start()

# Wait for Monitor to finish
while True:
    try:
        p_mon.join(timeout=2)
    except KeyboardInterrupt:
        print("Monitor service stopped.")
        sys.stdout.flush()
        break

print("Killing HTTP server.")
sys.stdout.flush()
p_http.terminate()
while True:
    try:
        p_http.join(timeout=2)
    except KeyboardInterrupt:
        print("HTTP server shutdown interrupted")
        break
