# this module contains any and all functions and processes related to the mqtt client
# only this isntance of the client should be created in the entire application

# import packages
import paho.mqtt.client as mqtt
import time
import logging

# settings, utils
from settings import Broker, SensorTopics, SinkTopics, AdminTopics, APPConfigurations, DevTopics
from utils import log_config

CONNECTED = False

log = log_config(logging.getLogger(__name__))

__subscriptions__ = []

def __init_client__() -> mqtt.Client:
    client = None
    try:
        # intialize callback client
        client = mqtt.Client(client_id = APPConfigurations.CLIENT_ID)
        log.info(f'Callback client successfully created at client.__init_client() with id: {APPConfigurations.CLIENT_ID}')

    except Exception as e:
        log.error(f'Client module was unable to successfuly initiate a callback client at client.__init_client__(): {e}')

    return client

def __on_connected__(client, userData, flags, rc):
    global CONNECTED
    CONNECTED = True
    log.info(f'Callback client \'{APPConfigurations.CLIENT_ID}\' successfully connected to broker at {Broker.HOST}:{Broker.PORT}')

def __on_disconnected__(client, userdata, rc):
    global CONNECTED
    CONNECTED = False
    log.warning(f'Callback client \'{APPConfigurations.CLIENT_ID}\' has been disconnected from broker at {Broker.HOST}:{Broker.PORT}')

def __on_publish__(client: mqtt.Client, userdata: mqtt.Client.user_data_get, mid, granted_qos):
    log.info(f'Published data:') #TODO: add message here

def __subscribe__(client: mqtt.Client):
    topics = [SensorTopics.ALERT, SensorTopics.DATA, SinkTopics.ALERT, AdminTopics.SETTINGS, DevTopics.TEST]

    for topic in topics:
        client.subscribe(topic)

# TODO: fix this callback
def __on_subscribe__(client: mqtt.Client, userdata: mqtt.Client.user_data_set, mid, reason_code_list):
    log.info(f'Subscribed')

# main client function
# this function returns the already connected and 'loop_started' callback client for the smmic application
# NOTE: for that reason, this client should run within its own concurrent task or thread (arguably the thread option is better)
# NOTE that only one instance of **THIS** client may be used for the entire application on runtime
# calling another instance of this elsewhere while another is already up will result in race conditions
# TODO: include error handling for when another instance is called using a global counter flag
def get_client() -> mqtt.Client:
    client = __init_client__()

    # register client configurations and callbacks
    if APPConfigurations.MQTT_USERNAME and APPConfigurations.MQTT_PW: # set password and username if exists
        client.username_pw_set(username=APPConfigurations.MQTT_USERNAME, password=APPConfigurations.MQTT_PW)
    client.on_disconnect = __on_disconnected__
    client.on_connect = __on_connected__

    client.connect(Broker.HOST, Broker.PORT)
    __subscribe__(client)
    client.loop_start()
    client.on_subscribe = __on_subscribe__ #TODO: fix on_subscribe topic log bug

    return client