import sqlite3
import pickle
import socket
import StringIO
from dblogger import *

class Sender:
    
    host = ""
    port = 0

    results = [] 

    def __init__(self, host, port):
        self.dependencies = []
        self.host = host
        self.port = port

    def set_dependencies(self, dependencies):
        self.dependencies = dependencies

    def check_dependencies(self, failed_list):
        for dependency in failed_list:
            if dependency in self.dependencies:
                self.connected = False
                return False
        self.connected = True

    def add_result(self, monitor_name, monitor_type, monitor_params, monitor_result, monitor_info):
        self.results.append({
            "monitor_name": monitor_name, 
            "monitor_type": monitor_type,
            "monitor_params": monitor_params,
            "monitor_result": monitor_result,
            "monitor_info": monitor_info})

    def send_results(self):
        p = pickle.dumps(self.results)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.host, self.port))
            s.send(p)
            s.close()
        except Exception, e:
            print e
        self.results = []

def main():
    #TODO: Config file
    print "listening on 4321 for remote reports..."
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 4321))
    dblogger = DBFullLogger("monitor.db")
    statuslogger = DBStatusLogger("monitor.db")

    while True:
        s.listen(1)
        conn, addr = s.accept()
        print "Connection from", addr
        pickled = ""
        while 1:
            data = conn.recv(1024)
            pickled += data
            if not data:
                break
        conn.close()
        result = pickle.loads(pickled)
        print result
        for row in result:
            print "saving %s" % result[0]
            dblogger.save_result(row["monitor_name"], row["monitor_type"], row["monitor_params"], row["monitor_result"], row["monitor_info"], addr[0])
            statuslogger.save_result(row["monitor_name"], row["monitor_type"], row["monitor_params"], row["monitor_result"], row["monitor_info"], addr[0])
        
        pickled = ""

if __name__ == "__main__":
    main()

