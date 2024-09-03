"""
The callback client of the SMMIC sink node application.
"""

# the module that returns the one of isntance of the client the system should use on runtime
# NOTE: this client module starts the event loop of the client, for that reason
# ----- only one instance of this client should run in the entire application

# third party
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
CLIENT_STAT = status.DISCONNECTED
CALLBACK_CLIENT = None

# internal function to initiate client creation
def __init_client__() -> paho_mqtt.Client | None:
    client = None
    try:
        client = paho_mqtt.Client(client_id = APPConfigurations.CLIENT_ID, protocol=paho_mqtt.MQTTv311)
        __log__.debug(f'Callback client successfully created: {APPConfigurations.CLIENT_ID}, {client._protocol}')

    except Exception as e:
        __log__.error(f'Client module was unable to succesffully create a callback client at __init_client(): {str(e)}')

    return client

# internal builtin callbacks for the client
def __on_connected__(client, userData, flags, rc):
    global CLIENT_STAT
    CLIENT_STAT = status.CONNECTED

    __log__.info(f'Callback client connected to broker at {Broker.HOST}:{Broker.PORT}')

def __on_disconnected__(client, userData, rc):
    global CLIENT_STAT
    CLIENT_STAT = status.DISCONNECTED

    __log__.warning(f'Callback client has been disconnected from broker: {rc} (disregard if expected)')

def __on_publish__(client: paho_mqtt.Client, userData, mid):
    # TODO: implement on publish, not sure what to do
    return

def __on_subscribe__(client: paho_mqtt.Client, userdata, mid, reason_code_list):
    #TODO: fix this shit code
    __log__.debug(f'Callback client subscribed to topic: {__subscriptions__[0]}')
    __subscriptions__.pop(0)

def __subscribe__(client: paho_mqtt.Client | None) -> None:
    app, sys = get_topics()
    topics = app + sys

    global __subscriptions__

    if not client: return
    for topic in topics:
        try:
            client.subscribe(topic=topic, qos=2)
            __subscriptions__.append(topic)
        except Exception as e:
            __log__.warning(f'Unable to subscribe callback client to topics {topic}: {str(e)}')    

async def __shutdown_disconnect__() -> None:
    global CLIENT_STAT
    global CALLBACK_CLIENT

    if not CALLBACK_CLIENT:
        return
    
    if CLIENT_STAT == status.CONNECTED:
        try:
            __log__.info(f'Disconnecting SMMIC callback client {APPConfigurations.CLIENT_ID} from broker at {Broker.HOST, Broker.PORT}')
            CALLBACK_CLIENT.disconnect()
            CLIENT_STAT = status.INACTIVE
        except Exception as e:
            __log__.error(f'Unable to disconnect client: {e}')

    if not CALLBACK_CLIENT.is_connected():
        CALLBACK_CLIENT = None

async def __loop_connect__(client: paho_mqtt.Client | None):
    if not client: return

    try:
        client.connect(Broker.HOST, Broker.PORT)
    except Exception as e:
        __log__.error(f'Unable to establish successful connection with broker: {e}')
    __subscribe__(client)
    client.loop_start()

    global CLIENT_STAT
    global CALLBACK_CLIENT
    CALLBACK_CLIENT = client

    # this while loop is important to keep the main thread alive
    # in the future, this could be another function that pings for broker information but this will do for now
    attempts = 0
    while True:
        if CLIENT_STAT == status.DISCONNECTED:
            __log__.info(f'Callback client attempting connection with broker: ({attempts} attempts)')
            attempts += 1
            if attempts == APPConfigurations.NETWORK_MAX_TIMEOUTS:
                __log__.error(f'Unable to establish successful connection with broker')
                CLIENT_STAT == status.FAILED # type: ignore
                await asyncio.sleep(10)
                break
        else:
            attempts = 0
        await asyncio.sleep(5)


async def start_callback_client() -> None:
    client = __init_client__()

    if not client:
        return

    # set the username and password (if any)
    if APPConfigurations.MQTT_USERNAME and APPConfigurations.MQTT_PW:
        client.username_pw_set(username=APPConfigurations.MQTT_USERNAME, password=APPConfigurations.MQTT_PW)

    client.on_disconnect = __on_disconnected__
    client.on_connect = __on_connected__
    client.on_publish = __on_publish__
    client.on_subscribe = __on_subscribe__

    await __loop_connect__(client)

# NOTE: sep 2 2024
# this is just trying out the pure asyncio approach, but given that the application will run
# blocking tasks (net requests, file i/o, hardware tasks, tasks that need to be awaited)
# might have to change the approach to multiprocessing