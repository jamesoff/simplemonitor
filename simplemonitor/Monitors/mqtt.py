import threading
import paho.mqtt.client as mqtt
from .monitor import Monitor, register


class MQTTBrokerManager:
    """Manager for MQTT connections and subscriptions"""
    _managers = {}  # Shared dictionary of brokers: {(broker, port): MQTTBrokerManager}

    def __new__(cls, broker, port, username=None, password=None, tls_enabled=False, ca_cert=None):
        key = (broker, port)  # Unique key based on broker and port
        if key not in cls._managers:
            # Create a new instance if it doesn't exist for this broker
            instance = super().__new__(cls)
            instance._init(broker, port, username, password, tls_enabled, ca_cert)
            cls._managers[key] = instance
        return cls._managers[key]

    def _init(self, broker, port, username, password, tls_enabled, ca_cert):
        """Initialize the MQTT client."""
        self.client = mqtt.Client()
        self.lock = threading.Lock()
        self.topic_callbacks = {}  # Map of topic -> list of callback functions
        self.received_data = {}  # Latest payload for each topic

        # Authentication
        if username and password:
            self.client.username_pw_set(username, password)

        # TLS configuration
        if tls_enabled:
            if ca_cert:
                self.client.tls_set(ca_certs=ca_cert)
                print(f"TLS enabled for {broker} with CA certificate: {ca_cert}")
            else:
                self.client.tls_set()
                print(f"TLS enabled for {broker} with default CA certificates.")
            self.client.tls_insecure_set(False)

        # MQTT event handlers
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        # Start MQTT client in a background thread
        self.thread = threading.Thread(target=self.start_client, args=(broker, port))
        self.thread.daemon = True
        self.thread.start()

    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to the broker."""
        if rc == 0:
            print("Connected to MQTT broker.")
            for topic in self.topic_callbacks:
                client.subscribe(topic)
                print(f"Subscribed to topic: {topic}")
        else:
            print(f"Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        """Callback when a message is received."""
        topic = msg.topic
        payload = msg.payload.decode()

        with self.lock:
            self.received_data[topic] = payload
            if topic in self.topic_callbacks:
                for callback in self.topic_callbacks[topic]:
                    callback(payload)

    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from the broker."""
        print("Disconnected from MQTT broker.")

    def start_client(self, broker, port):
        """Start the MQTT client loop."""
        try:
            self.client.connect(broker, port)
            self.client.loop_forever()
        except Exception as e:
            print(f"Error starting MQTT client: {e}")

    def subscribe(self, topic, callback):
        """Subscribe to a topic and register a callback."""
        with self.lock:
            if topic not in self.topic_callbacks:
                self.topic_callbacks[topic] = []
                self.client.subscribe(topic)
            self.topic_callbacks[topic].append(callback)

    def get_latest_payload(self, topic):
        """Retrieve the latest payload for a given topic."""
        with self.lock:
            return self.received_data.get(topic, None)


# Monitor for multiple brokers
@register
class MonitorMQTT(Monitor):
    """Monitor for MQTT topics using shared or unique broker connections."""
    monitor_type = "mqtt_client"

    def __init__(self, name, config_options):
        super().__init__(name, config_options)

        # Monitor configuration
        self.topic = self.get_config_option("topic", required=True)
        self.success_state = self.get_config_option("success_state", required=True)
        self.last_payload = None
        self.status = "UNKNOWN"

        # Broker configuration
        broker = self.get_config_option("broker", required=True)
        port = self.get_config_option("port", required_type="int", default=1883)
        username = self.get_config_option("username", required=False)
        password = self.get_config_option("password", required=False)
        tls_enabled = self.get_config_option("tls", required_type="bool", default=False)
        ca_cert = self.get_config_option("ca_cert", required=False)

        # Get or create the MQTT broker manager
        self.mqtt_manager = MQTTBrokerManager(broker, port, username, password, tls_enabled, ca_cert)

        # Subscribe to the topic with a callback
        self.mqtt_manager.subscribe(self.topic, self.on_message_received)

    def on_message_received(self, payload):
        print(f"[{self.name}] Received message: {payload}")
        self.last_payload = payload
        self.evaluate_payload(payload)

    def evaluate_payload(self, payload):
        """Evaluate the payload against the success_state."""
        try:
            numeric_payload = float(payload)
            condition = self.success_state.strip()
            if condition.startswith("<"):
                threshold = float(condition[1:])
                self.status = "OK" if numeric_payload < threshold else "FAILED"
            elif condition.startswith(">"):
                threshold = float(condition[1:])
                self.status = "OK" if numeric_payload > threshold else "FAILED"
            elif "<" in condition and "x" in condition:
                parts = condition.split("<")
                lower = float(parts[0].strip())
                upper = float(parts[2].strip())
                self.status = "OK" if lower < numeric_payload < upper else "FAILED"
            else:
                self.status = "OK" if numeric_payload == float(condition) else "FAILED"
        except ValueError:
            self.status = "OK" if payload == self.success_state else "FAILED"

    def run_test(self):
        if self.status == "OK":
            self.record_success(f"Payload '{self.last_payload}' matched condition '{self.success_state}'.")
        elif self.status== "UNKNOWN":
            self.record_skip(f"Topic '{self.topic}' did not received any messages yet.")
        else:
            self.record_fail(f"Payload '{self.last_payload}' did not match condition '{self.success_state}'.")
