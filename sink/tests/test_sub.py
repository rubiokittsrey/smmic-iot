# run this script to test out topics within the MQTT network
# example: python test_sub.py --topic "/topic/to/test"
# default topic (without --topic argument) will use DevTopics.TEST from configs.yaml

import paho.mqtt.client as mqtt
import time
import argparse
import settings

from settings import Broker, DevTopics

topic = None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a subscribe test on the MQTT network")
    parser.add_argument("--topic", type=str, help="Specify a different topic to test subscribe (other than the default test topic)", default=DevTopics.TEST)

    args = parser.parse_args()
    topic = args.topic

def on_connect(client, userData, flags, rc):
    global connected # connected flag
    connected = 1
    print("connected to mqtt server... subscribing")

def on_disconnect(client, userdata, rc):
    global connected
    connected = 0
    print("disconnected from mqtt server")

def callback_mqtt_test(client, userdata, msg):
    print(f"payload: {str(msg.payload.decode('utf-8'))}")

client = mqtt.Client("test-sub")
connected = 0

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.message_callback_add(topic, callback_mqtt_test)
client.connect(Broker.HOST, Broker.PORT)
client.loop_start()
client.subscribe(topic)
client.subscribe(settings.DevTopics.SENSOR_ONE)

while True:
    time.sleep(5)
    if (connected != 1):
        print("attempting connection with mqtt server")