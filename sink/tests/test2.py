# third-party
from paho.mqtt import client as paho_mqtt, enums
from typing import Any, List
from secrets import token_urlsafe
import time

__subscribed_topics__ = []

_topics = [
        '$SYS/broker/clients/active',
    ]

def on_c(client: paho_mqtt.Client, userdata: Any, flags, rc, properties) -> None:
    print(f"{client._client_id}: connected")

def on_msg(client: paho_mqtt.Client, userdata: Any, msg: paho_mqtt.MQTTMessage) -> None:
    print(f"{msg.topic}: {msg.payload.decode('utf-8')}")

def subscribe(client: paho_mqtt.Client, topics: List[str]) -> None:
    for topic in topics:
        client.subscribe(topic, qos=1)

def add_callbacks(client: paho_mqtt.Client, topics: List[str]) -> None:
    for topic in topics:
        client.message_callback_add(topic, on_msg)

client = paho_mqtt.Client(callback_api_version=enums.CallbackAPIVersion.VERSION2, client_id="sys_test2")
client.on_connect = on_c
add_callbacks(client, _topics)
client.connect('localhost', 1883)
client.loop_start()
subscribe(client, _topics)

# keep thread alive
while True:
    payload = token_urlsafe(8)
    try:
        pub = client.publish(topic='/dev/test', payload=payload.encode('utf-8'), qos=1)
        pub.wait_for_publish()
        print(f"{client._client_id} published: {payload}")
    except Exception as e:
        print(f"error publishing message: {str(e)}")

    time.sleep(10)