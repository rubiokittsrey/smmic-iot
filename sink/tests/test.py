# third-party
from paho.mqtt import client as paho_mqtt, enums
from typing import Any, List
import time

# $SYS topics testing
# 

__subscribed_topics__ = []

_topics = [
        '$SYS/broker/clients/active',
        '$SYS/broker/subscriptions/count',
        '$SYS/broker/bytes/sent', # total number of bytes sent since the broker started
        '$SYS/broker/bytes/received', # total number of bytes received since the broker started
        '$SYS/broker/messages/received',
        '$SYS/broker/messages/sent',
        '$SYS/broker/version'
    ]

def on_c(client: paho_mqtt.Client, userdata: Any, flags, rc, properties) -> None:
    print(f"{client._client_id}: connected")

def on_msg(client: paho_mqtt.Client, userdata: Any, msg: paho_mqtt.MQTTMessage) -> None:
    print(f"{msg.topic}: {str(msg.payload)}")

def subscribe(client: paho_mqtt.Client, topics: List[str]) -> None:
    client.subscribe("$SYS/#", qos=1)
    #for topic in topics:
    #    client.subscribe(topic, qos=1)

def add_callbacks(client: paho_mqtt.Client, topics: List[str]) -> None:
    for topic in topics:
        print(f"{client._client_id} subscribed to: {topic}")
        client.message_callback_add(topic, on_msg)

client = paho_mqtt.Client(callback_api_version=enums.CallbackAPIVersion.VERSION2, client_id="sys_test")
client.on_connect = on_c
add_callbacks(client, _topics)
client.connect('localhost', 1883)
client.loop_start()
subscribe(client, _topics)

# keep thread alive
while True:
    time.sleep(0.5)