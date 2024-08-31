import paho.mqtt.client as mqtt
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from random import randint
import sys

from settings import Broker, DevTopics, SinkTopics, AdminTopics, SensorTopics, APPConfigurations
sys.path.append(APPConfigurations.SRC_PATH)

from mqtt import client

def simulated_task_with_delay(delay: int, msg: str):
    print(f'task will take {delay} seconds ({msg})')
    time.sleep(delay)
    print(f'task completed {msg}')

def on_msg(client, userdata, msg):
    print(f'payload: {msg}')
    simulated_task_with_delay(randint(1, 15), msg)
    
def subscribe(client: mqtt.Client):
    topics = [DevTopics.TEST, SinkTopics.ALERT, AdminTopics.SETTINGS, SensorTopics.ALERT, SensorTopics.DATA]
    for topic in topics:
        client.subscribe(topic=topic, qos=1)

def main():
    callback_client = client.get_client()
    callback_client.message_callback_add("#", on_msg)
    callback_client.connect(Broker.HOST, Broker.PORT)
    subscribe(callback_client)
    callback_client.loop_start()

    while True:
        if not client.CONNECTED:
            time.sleep(5)
    
if __name__ == "__main__":
    main()