# third party
import asyncio
import time
import logging
import os
import multiprocessing
from paho.mqtt import client as paho_mqtt, enums, reasoncodes, properties
from typing import Any
from datetime import datetime

# internal
from settings import Broker, APPConfigurations, Topics, DevTopics, DEV_MODE
from utils import log_config, status, priority, set_priority

# internal log object
_log = log_config(logging.getLogger(__name__))

# **private** variable that stores subscriptions
# using this to track all subscriptions of mqtt client, not sure what to do with this yet
# but its good to have just in case its needed
_subscriptions = []

# global vars
_CLIENT_STAT: int = status.DISCONNECTED
_CALLBACK_CLIENT: paho_mqtt.Client | None = None

# interal private function called upon to instantiate the smmic client object
def _init_client() -> paho_mqtt.Client | None:
    client = None
    try:
        client = paho_mqtt.Client(callback_api_version=enums.CallbackAPIVersion.VERSION2,client_id = APPConfigurations.CLIENT_ID, protocol=paho_mqtt.MQTTv311)
        _log.debug(f"Callback client successfully created: {APPConfigurations.CLIENT_ID}, {client._protocol}")

    except Exception as e:
        _log.error(f"Client module was unable to succesffully create a callback client at __init_client(): {str(e)}")

    return client

# internal callback functions
def _on_connected(client:paho_mqtt.Client, userData, flags, rc, properties) -> None:
    _log.debug(f"Callback client connected to broker at {Broker.HOST}:{Broker.PORT}")

def _on_disconnected(client: paho_mqtt.Client,
                        userData: Any,
                        disconnect_flags: paho_mqtt.DisconnectFlags,
                        rc: reasoncodes.ReasonCode,
                        properties: properties.Properties) -> None:
    _log.warning(f"Callback client has been disconnected from broker: {rc}")

def _on_pub(client: paho_mqtt.Client, userData: Any, mid: int, rc: reasoncodes.ReasonCode, prop: properties.Properties):
    # TODO: implement on publish, not sure what to do
    return

def _on_sub(client: paho_mqtt.Client, userdata, mid, reason_code_list, properties):
    #TODO: fix this shit code
    _log.debug(f"Callback client subscribed to topic: {_subscriptions[0]}")
    _subscriptions.pop(0)

def _subscribe(client: paho_mqtt.Client | None) -> None:
    smmic_t, sys_t = Topics.get_topics()
    topics = smmic_t + sys_t

    topics.append(DevTopics.TEST)

    global _subscriptions

    if not client: return
    for topic in topics:
        if topic.count('/') == 0:
            continue
        try:
            client.subscribe(topic=topic, qos=2)
            _subscriptions.append(topic)
        except Exception as e:
            _log.warning(f"Unable to subscribe callback client to topic {topic}: {str(e)}")

# connect the client
# start the loop
# subscribe to topics
# add the message handler callback function
async def _connect_loop(client: paho_mqtt.Client | None, _msg_handler: paho_mqtt.CallbackOnMessage) -> bool:
    if not client: return False

    global _CLIENT_STAT
    global _CALLBACK_CLIENT

    try:
        client.connect(Broker.HOST, Broker.PORT)
        client.loop_start()
    except Exception as e:
        _log.error(f"Unable to establish successful connection with broker: {e}")
        return False
    
    # 1 second wait to ensure client is connected
    await asyncio.sleep(1)
    _subscribe(client)
    
    _CLIENT_STAT = status.SUCCESS

    # assign client the global callback client
    _CALLBACK_CLIENT = client

    # add the message callback handler
    client.message_callback_add(DevTopics.TEST, _msg_handler)

    smmic_t, sys_t = Topics.get_topics()
    topics = smmic_t + sys_t

    for topic in topics:
        if topic.count('/') == 0:
            continue
        client.message_callback_add(topic, _msg_handler)

    return True

# handles failed connect attempt at startup
def _on_connect_f(_client: paho_mqtt.Client, _userdata: Any):
    _log.error(f"Attempting reconnect with broker")

    global _CLIENT_STAT

    attempts = APPConfigurations.NETWORK_MAX_TIMEOUT_RETRIES
    timeout = APPConfigurations.NETWORK_TIMEOUT

    while True:
        attempts = attempts - 1
        try:
            _client.connect(Broker.HOST, Broker.PORT)
            _CLIENT_STAT = status.SUCCESS
        except Exception as e:
            _log.error(f"Unable to establish successful connection with broker: {e}, retrying again in {timeout} seconds (attempts remaining: {attempts})")
            time.sleep(timeout)

        if attempts == 0:
            _log.critical(f"Callback client was unable to successfully connect with broker at {Broker.HOST}:{Broker.PORT}, max attempts allowed reached!")
            _CLIENT_STAT = status.FAILED

        if _CLIENT_STAT == status.SUCCESS:
            break

# starts the client
# optional message callback functions can be added
# each function returns a tuple of str (the task title) and a bool (the result of the task)
async def start_client(_msg_handler: paho_mqtt.CallbackOnMessage) -> None:
    _client = _init_client()

    if not _client:
        return
    
    # set username and password (if exists)
    _pw = APPConfigurations.MQTT_PW
    _uname = APPConfigurations.MQTT_USERNAME

    if _pw and _uname:
        _client.username_pw_set(username=_uname, password=_pw)

    _client.on_disconnect = _on_disconnected # type: ignore #TODO: find a workaround for this other than this dangerous ignore anotation
    _client.on_connect = _on_connected
    _client.on_publish = _on_pub
    _client.on_subscribe = _on_sub
    #_client.on_connect_fail = __on_connect_fail__ #TODO fix on connect not executing (?)

    con = await _connect_loop(_client, _msg_handler)
    if con:
        _log.info(f"Callback client running and connected at PID: {os.getpid()}")

    # keep this client thread alive
    while True:
        await asyncio.sleep(0.5)

def get_client() -> paho_mqtt.Client | None:
    if _CALLBACK_CLIENT:
        return _CALLBACK_CLIENT
    else:
        _log.error(f"The callback client does not exist, are you sure the client is instantiated?")
        return None

# shutdown the client, perform cleanup
# handle exceptions
async def shutdown_client() -> bool:
    global _CLIENT_STAT
    global _CALLBACK_CLIENT

    if not _CALLBACK_CLIENT:
        _log.error(f"Cannot disconnect or shutdown a callback client that does not exist!")
        return False
    
    _log.info(f"Shutting down SMMIC callback client at PID: {os.getpid()}")

    if _CLIENT_STAT == status.SUCCESS:
        # disconnect client
        try:
            _log.debug(f"Disconnecting callback client {APPConfigurations.CLIENT_ID} from broker at {Broker.HOST, Broker.PORT}")
            _CALLBACK_CLIENT.disconnect()
        except Exception as e:
            _log.error(f"Unable to disconnect client: {e}, forcing disconnect")
        
        # stop client
        try:
            _log.debug(f"Terminating callback client loop at PID: {os.getpid()}")
            _CALLBACK_CLIENT.loop_stop()
        except Exception as e:
            _log.error(f"Unable to stop client loop: {e}, forcing task termination by exiting process (os._exit(0))")
            os._exit(0) # TODO: execute thread terminate
            # NOTE: if something funny happens, its probably this ^^

    if not _CALLBACK_CLIENT.is_connected():
        _CALLBACK_CLIENT = None
        return True

    return False

# necessary handler class in order to include the usage of the Queue object in the message callback of the client
class Handler:
    def __init__(self, task_queue: multiprocessing.Queue, sys_queue: multiprocessing.Queue) -> None:
        self._task_queue: multiprocessing.Queue = task_queue
        self._sys_queue: multiprocessing.Queue = sys_queue

    # the message callback function
    # routes the messages received by the client on relevant topics to the queue
    # sets the priority for each task
    # NOTE to self: can be scaled to do more tasks just in case
    def msg_callback(self, client: paho_mqtt.Client, userdata: Any, message: paho_mqtt.MQTTMessage) -> None:

        # -->
        # {priority: the priority of the message
        # topic: topic message was published ,
        # payload: the message contents,
        # timestamp: the message timestamp #NOTE: either when it was sent or received (idk yet)}
        # --->
        topic = message.topic
        timestamp = str(datetime.now())
        payload = str(message.payload.decode('utf-8'))
        try:
            if topic.startswith("$SYS"):
                self._sys_queue.put({'topic': topic, 'payload': payload, 'timestamp': timestamp})
            else:
                self._task_queue.put({'topic': topic, 'payload': payload, 'timestamp': timestamp})
        except Exception as e:
            _log.warning(f"Error routing message to queue (Handler.msg_callback()): ('topic': {topic}, 'payload': {payload}) - ERROR: {str(e)}")

        return