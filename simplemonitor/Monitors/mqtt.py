from .monitor import Monitor, register
import paho.mqtt.client as mqtt
import random
import string

@register
class MonitorMQTT(Monitor):

    monitor_type = "mqtt_client"

    def describe(self) -> str:
        return f"checking that thing does foo"
    
    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        
        client = mqtt.Client("simplemonitor"+''.join(random.choices(string.ascii_lowercase + string.digits, k=8)))       
        broker_address= "localhost"
        port = 1883
        self.host = self.get_config_option("host", required=True,default="localhost")
        self.port = self.get_config_option("port",required_type="int", required=False,default=1883)
        self.username = self.get_config_option("username", required=False)
        self.password = self.get_config_option("password", required=False)
        self.tls = self.get_config_option("tls", required_type="bool", default=False)
        self.topic = self.get_config_option("topic", required=True)
        self.success = self.get_config_option("success", required=True)
        self.payload = ""      
        client.on_connect= self.on_connect
        client.on_message= self.on_message
        if self.tls:
            client.tls_set()
        #TODO: Credentials
        client.connect(broker_address, port=port)     
        client.loop_start()

    def on_connect(self,client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to broker on topic {self.topic}")
            client.subscribe(self.topic)

        else:
            print("Connection failed")

    def on_message(self,client, userdata, msg):
        self.payload=msg.payload.decode()
        print(f"Received {msg.payload.decode()} from {msg.topic} topic")

    def run_test(self) -> bool:
        if self.success == self.payload:
            return self.record_success("it worked")
        else:
            return self.record_fail(f"failed with message {self.payload}")