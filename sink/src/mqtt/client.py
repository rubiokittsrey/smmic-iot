# this module contains any and all functions and processes related to the mqtt client
# only this isntance of the client should be created in the entire application

# import packages
import paho.mqtt.client as mqtt
import time
import logging

# settings, utils
from settings import Broker, SensorTopics, SinkTopics, AdminTopics, APPConfigurations, DevTopics
import settings
from utils import log_config, Modes

CONNECTED = False
__curent_topic__ = None

log = log_config(logging.getLogger(__name__))

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

# TODO: fix this callback
def __on_subscribe__(client: mqtt.Client, userdata: mqtt.Client.user_data_set, mid, granted_qos):
    log.info(f'Subscribed to topic {__curent_topic__}')

# main client function
def get_client() -> mqtt.Client:
    client = __init_client__()

    # register client configurations and callbacks
    if APPConfigurations.MQTT_USERNAME and APPConfigurations.MQTT_PW: # set password and username if exists
        client.username_pw_set(username=APPConfigurations.MQTT_USERNAME, password=APPConfigurations.MQTT_PW)
    client.on_connect = __on_connected__
    client.on_disconnect = __on_disconnected__
    
    ### client.on_subscribe = __on_subscribe__ #TODO: fix on_subscribe topic log bug

    ## connect the client
    # client.connect(Broker.HOST, Broker.PORT)
    # __subscribe__(client=client)

    return client