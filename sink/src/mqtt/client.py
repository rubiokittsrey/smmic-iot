"""
The callback client of the SMMIC sink node application.

Because this module starts the client in a separate 
"""

# the module that returns the one of isntance of the client the system should use on runtime
# NOTE: this client module starts the event loop of the client, for that reason
# ----- only one instance of this client should run in the entire application

# third party
import paho.mqtt.client as paho_mqtt
from paho.mqtt import client as paho_mqtt, reasoncodes
import time
import logging
import asyncio

# internal
from settings import (
    # configurations
    Broker,
    APPConfigurations,

    # topics
    get_topics
)
from utils import log_config, status

# internal log object
__log__ = log_config(logging.getLogger(__name__))

# **private** variable that stores subscriptions
# using this to track all subscriptions of mqtt client, not sure what to do with this yet
# but its good to have just in case its needed
__subscriptions__ = []

# global variables
CLIENT_STAT = status.DISCONNTECTED
CALLBACK_CLIENT = None

# internal function to initiate client creation
def __init_client__():
    client = None
    try:
        client = paho_mqtt.Client(client_id = APPConfigurations.CLIENT_ID)
        __log__.info(f'Callback client successfully created: {APPConfigurations.CLIENT_ID}, {client._protocol}')

    except Exception as e:
        __log__.error(f'Client module was unable to succesffully create a callback client at __init_client(): {str(e)}')

    return client

# internal builtin callbacks for the client
def __on_connected__(client, userData, flags, rc: reasoncodes.ReasonCode):
    global CLIENT_STAT
    CLIENT_STAT = status.CONNECTED

    __log__.info(f'Callback client connected to broker at {Broker.HOST}:{Broker.PORT}')

def __on_disconnected__(client, userData, rc: reasoncodes.ReasonCode):
    global CLIENT_STAT
    CLIENT_STAT = status.DISCONNTECTED

    __log__.warning(f'Callback client has been disconnected from broker: ({rc})')

def __on_publish__(client: paho_mqtt.Client, userData, mid):
    # TODO: implement on publish, not sure what to do
    None

def __on_subscribe__(client: paho_mqtt.Client, userdata, mid, reason_code_list):
    __log__.info(f'Callback client subscribed to topic: {__subscriptions__[len(__subscriptions__) - 1]}')

def __subscribe__(client: paho_mqtt.Client | None) -> None:
    app, sys = get_topics()
    topics = app + sys

    global __subscriptions__

    if not client: return
    for topic in topics:
        __subscriptions__.append(topic)
        try:
            client.subscribe(topic=topic, qos=1)
        except Exception as e:
            __log__.warning(f'Unable to subscribe callback client to topics {topic}: {str(e)}')

async def start_callback_client() -> None:
    client = __init_client__()

    # set the username and password (if any)
    if APPConfigurations.MQTT_USERNAME and APPConfigurations.MQTT_PW:
        client.username_pw_set(username=APPConfigurations.MQTT_USERNAME, password=APPConfigurations.MQTT_PW)

    client.on_disconnect = __on_disconnected__
    client.on_connect = __on_connected__
    client.on_publish = __on_publish__
    client.on_subscribe = __on_subscribe__

    client.connect(Broker.HOST, Broker.PORT)
    __subscribe__(client)

    global CLIENT_STAT
    global CALLBACK_CLIENT
    CALLBACK_CLIENT = client
    client.loop_start()

    while True:
        await asyncio.sleep(5)