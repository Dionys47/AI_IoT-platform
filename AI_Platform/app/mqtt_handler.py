# app/mqtt_handler.py
import paho.mqtt.client as mqtt
import json
import requests
import threading
import logging

logger = logging.getLogger(__name__)

API_URL = "http://api:8000"

class MQTTHandler:
    def __init__(self, broker="mqtt", port=1883):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.running = False
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"✅ MQTT connected to {self.broker}:{self.port}")
            # Subscribe to all device topics
            client.subscribe("iot/+/data")
            client.subscribe("iot/+/heartbeat")
        else:
            logger.error(f"❌ MQTT connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            topic = msg.topic
            logger.debug(f"MQTT message on {topic}: {payload}")
            
            # Extract device_id from topic (iot/{device_id}/data)
            parts = topic.split('/')
            if len(parts) >= 3:
                device_id = parts[1]
                payload["device_id"] = device_id
                
                # Forward to API
                requests.post(f"{API_URL}/sensor-data", json=payload, timeout=2)
        except Exception as e:
            logger.error(f"MQTT processing error: {e}")
    
    def start(self):
        self.running = True
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        
    def stop(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
    
    def publish(self, device_id, data):
        topic = f"iot/{device_id}/command"
        self.client.publish(topic, json.dumps(data))

mqtt_handler = MQTTHandler()
