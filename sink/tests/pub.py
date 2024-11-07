# run this script to test out topics within the MQTT network
# example: python test_pub.py --topic "/topic/to/test"
# default topic (without --topic argument) will use MQTTDevTopics.TEST from configs.yaml

# third-party
import time
import paho.mqtt.client as mqtt
import secrets
import argparse
import logging
import sys
import os

# internal
from settings import Broker, DevTopics, APPConfigurations
sys.path.append(APPConfigurations.SRC_PATH)
from mqtt import mqttclient
from utils import logger_config, Modes

log = logger_config(logging.getLogger(__name__))

def on_pub(client, userdata, mid):
    print(f"data published: {msg}")

def publish(client: mqtt.Client, topic) -> bool:
    global msg
    try:
        msg  = str(f'smmic.pub.py client: {secrets.token_urlsafe(16)}')
        payload=str(msg)
        pub=client.publish(
            topic=topic,
            payload=payload.encode('utf-8'),
            qos=1)
        pub.wait_for_publish()
        return True
    except Exception as e: 
        print(e)
        return False

# TODO: refactor this unit test!!!!
def init_client() -> mqtt.Client | None:
    mqttclient.start_callback_client()
    if not callback_client:
        log.error('src.mqtt.client.get_client() returned empty or without a valid client')
        return None
    return callback_client

if __name__ == "__main__":
    Modes.dev()

    parser = argparse.ArgumentParser(description="Run a publish test on the MQTT network")
    parser.add_argument("--topic", type=str, help="Specify a different topic to test publish (other than the default test topic)", default=DevTopics.TEST)

    args = parser.parse_args()
    callback_client = init_client()

    if not callback_client:
        os._exit(0)

    while True:
        time.sleep(10)
        publish(callback_client, args.topic)