# third party
import asyncio
import time
import logging
import os
from paho.mqtt import client as paho_mqtt, enums, reasoncodes, properties
from typing import Any

# internal
from settings import Broker, APPConfigurations, get_topics
from utils import log_config, status

# internal log object
__log__ = log_config(logging.getLogger(__name__))

# **private** variable that stores subscriptions
# using this to track all subscriptions of mqtt client, not sure what to do with this yet
# but its good to have just in case its needed
__subscriptions__ = []

# global vars
__CLIENT_STAT__ = status.DISCONNECTED
__CALLBACK_CLIENT__: paho_mqtt.Client | None

# interal private function called upon to instantiate the smmic client object
def __init_client__() -> paho_mqtt.Client | None:
    client = None
    try:
        client = paho_mqtt.Client(callback_api_version=enums.CallbackAPIVersion.VERSION2,client_id = APPConfigurations.CLIENT_ID, protocol=paho_mqtt.MQTTv311)
        __log__.debug(f"Callback client successfully created: {APPConfigurations.CLIENT_ID}, {client._protocol}")

    except Exception as e:
        __log__.error(f"Client module was unable to succesffully create a callback client at __init_client(): {str(e)}")

    return client

# internal callback functions
def __on_connected__(client:paho_mqtt.Client, userData, flags, rc, properties) -> None:
    __log__.info(f"Callback client connected to broker at {Broker.HOST}:{Broker.PORT}")

def __on_disconnected__(client: paho_mqtt.Client,
                        userData: Any,
                        disconnect_flags: paho_mqtt.DisconnectFlags,
                        rc: reasoncodes.ReasonCode,
                        properties: properties.Properties) -> None:
    __log__.warning(f"Callback client has been disconnected from broker: {rc} (disregard if expected)")

def __on_publish__(client: paho_mqtt.Client, userData: Any, mid: int, rc: reasoncodes.ReasonCode, prop: properties.Properties):
    # TODO: implement on publish, not sure what to do
    return

def __on_subscribe__(client: paho_mqtt.Client, userdata, mid, reason_code_list, properties):
    #TODO: fix this shit code
    __log__.debug(f"Callback client subscribed to topic: {__subscriptions__[0]}")
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
            __log__.warning(f"Unable to subscribe callback client to topics {topic}: {str(e)}")

# connect the client
# start the loop
# subscribe to topics
# add the message handler callback function
async def __connect_loop__(_client: paho_mqtt.Client | None, _msg_handler: paho_mqtt.CallbackOnMessage) -> bool:
    if not _client: return False

    global __CLIENT_STAT__
    global __CALLBACK_CLIENT__

    try:
        __log__.debug(f"Callback client connecting to broker @ {Broker.HOST}:{Broker.PORT}")
        _client.connect(Broker.HOST, Broker.PORT)
        _client.loop_start()
    except Exception as e:
        __log__.error(f"Unable to establish successful connection with broker: {e}")
    __subscribe__(_client)
    
    __CLIENT_STAT__ = status.CONNECTED

    # assign client the global callback client
    __CALLBACK_CLIENT__ = _client

    # add the message callback handler
    _client.message_callback_add("#", _msg_handler)

    return True

# handles failed connect attempt at startup
def __on_connect_fail__(_client: paho_mqtt.Client, _userdata: Any):
    time.sleep(APPConfigurations.NETWORK_TIMEOUT)

    global __CLIENT_STAT__

    attempts = APPConfigurations.NETWORK_MAX_TIMEOUTS
    timeout = APPConfigurations.NETWORK_TIMEOUT

    while True:
        attempts = attempts - 1
        try:
            _client.connect(Broker.HOST, Broker.PORT)
            __CLIENT_STAT__ = status.CONNECTED
        except Exception as e:
            __log__.error(f"Unable to establish successful connection with broker: {e}, retrying again in {timeout} seconds (attempts remaining: {attempts})")
            time.sleep(timeout)

        if attempts == 0:
            __log__.critical(f"Callback client was unable to successfully connect with broker @ {Broker.HOST}:{Broker.PORT}, max attempts allowed reached!")
            __CLIENT_STAT__ = status.FAILED

        if __CLIENT_STAT__ == status.CONNECTED:
            break

# starts the client
# optional message callback functions can be added
# each function returns a tuple of str (the task title) and a bool (the result of the task)
async def start_client(_msg_handler: paho_mqtt.CallbackOnMessage) -> None:
    _client = __init_client__()

    if not _client:
        return
    
    # set username and password (if exists)
    _pw = APPConfigurations.MQTT_PW
    _uname = APPConfigurations.MQTT_USERNAME

    if _pw and _uname:
        _client.username_pw_set(username=_uname, password=_pw)

    _client.on_disconnect = __on_disconnected__ # type: ignore #TODO: find a workaround for this other than this dangerous ignore anotation
    _client.on_connect = __on_connected__
    _client.on_publish = __on_publish__
    _client.on_subscribe = __on_subscribe__
    _client.on_connect_fail = __on_connect_fail__

    con = await __connect_loop__(_client, _msg_handler)

    while True:
        await asyncio.sleep(0.5)

def get_client() -> paho_mqtt.Client | None:
    if __CALLBACK_CLIENT__:
        return __CALLBACK_CLIENT__
    else:
        __log__.error(f"The callback client does not exist, are you sure the client is instantiated?")
        return None

# shutdown the client, perform cleanup
# handle exceptions
async def shutdown_client() -> bool:
    global __CLIENT_STAT__
    global __CALLBACK_CLIENT__

    if not __CALLBACK_CLIENT__:
        __log__.error(f"Cannot disconnect or shutdown a callback client that does not exist!")
        return False
    
    __log__.info(f"Performing shutdown on callback client @ PID: {os.getpid()}")

    if __CLIENT_STAT__ == status.CONNECTED:
        try:
            __log__.debug(f"Disconnecting callback client {APPConfigurations.CLIENT_ID} from broker @ {Broker.HOST, Broker.PORT}")
            __CALLBACK_CLIENT__.disconnect()
        except Exception as e:
            __log__.error(f"Unable to disconnect client: {e}, forcing disconnect")
        
        try:
            __log__.debug(f"Terminating callback client loop @ PID: {os.getpid()}")
            __CALLBACK_CLIENT__.loop_stop()
        except Exception as e:
            __log__.error(f"Unable to stop client loop: {e}, forcing task termination by exiting process (os._exit(0))")
            os._exit(0) # TODO: execute thread terminate
            # NOTE: if something funny happens, its probably this ^^

    if not __CALLBACK_CLIENT__.is_connected():
        __CALLBACK_CLIENT__ = None
        return True
    
    return False

if __name__ == "__main__":
    def dummy_handler(cli, usdata, msg):
        __log__.debug(f"msg: {msg}")

    asyncio.run(start_client(dummy_handler))