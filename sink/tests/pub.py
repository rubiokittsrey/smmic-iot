# run this script to test out topics within the MQTT network
# example: python test_pub.py --topic "/topic/to/test"
# default topic (without --topic argument) will use MQTTDevTopics.TEST from configs.yaml

import time
import paho.mqtt.client as mqtt
import secrets
import argparse
import logging

from settings import Broker, DevTopics
from src.mqtt import client
from utils import log_config

log = log_config(logging.getLogger(__name__))

def on_pub(client, userdata, mid):
    print(f"data published: {msg}")

def publish(client: mqtt.Client, topic):
    global msg
    try:
        msg  = str(secrets.token_urlsafe(16))
        payload=str(msg)
        pub=client.publish(
            topic=topic,
            payload=payload.encode('utf-8'),
            qos=1)
        pub.wait_for_publish()
    except Exception as e:
        print(e)

def init_client() -> mqtt.Client:
    callback_client = client.get_client()
    if not callback_client:
        log.error('src.mqtt.client.get_client() returned empty or without a valid client')

def mqtt_loop_test(callback_client: mqtt.Client, topic) -> None:
    client.on_publish = on_pub
    client.connect(Broker.HOST, Broker.PORT)
    client.loop_start()

    while True:
        publish(client, topic)
        publish(client, DevTopics.TEST)
        time.sleep(7)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a publish test on the MQTT network")
    parser.add_argument("--topic", type=str, help="Specify a different topic to test publish (other than the default test topic)", default=DevTopics.TEST)

    args = parser.parse_args()
    callback_client = init_client()
    mqtt_loop_test(callback_client, args.topic)