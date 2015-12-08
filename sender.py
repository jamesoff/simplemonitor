import pickle
import socket
import StringIO

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
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 4321))
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
            print "got some data"
        conn.close()
        result = pickle.loads(pickled)
        print result
        
        data = ""
        print "Finished."

if __name__ == "__main__":
    main()

