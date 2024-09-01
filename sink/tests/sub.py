# run this script to test out topics within the MQTT network
# example: python test_sub.py --topic "/topic/to/test"
# default topic (without --topic argument) will use DevTopics.TEST from configs.yaml

import paho.mqtt.client as mqtt
import time
import argparse
import sys
import logging

from settings import DevTopics, APPConfigurations
from utils import Modes

sys.path.append(APPConfigurations.SRC_PATH)

from mqtt import client
from utils import log_config

log = log_config(logging.getLogger(__name__))

topic = None

def callback_mqtt_test(client, userdata, msg):
    print(f"payload: {str(msg.payload.decode('utf-8'))} ({msg.topic})")

def init_client() -> mqtt.Client:
    callback_client = client.get_client()
    if not callback_client:
        log.error(f'src.mqtt.client.get_client() did not return with a valid client')
    return callback_client

if __name__ == "__main__":
    Modes.dev()
    
    parser = argparse.ArgumentParser(description="Run a subscribe test on the MQTT network")
    parser.add_argument("--topic", type=str, help="Specify a different topic to test subscribe (other than the default test topic)", default=DevTopics.TEST)

    args = parser.parse_args()
    topic = args.topic

    callback_client = init_client()

    callback_client.message_callback_add("#", callback_mqtt_test)

    while True:
        time.sleep(5)