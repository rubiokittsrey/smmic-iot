# third-party
import time
import datetime
from random import randint
from paho.mqtt import client as mqtt, enums

# internal
from settings import Topics, Broker

client = mqtt.Client(client_id="test_pub1")
client.connect('192.168.1.25', 1883)
client.loop_start()

k = 0
while True:
    sensor_type: str = "soil_moisture"
    device_id: str = "fd7b1df2-3822-425c-b4c3-e9859251728d"
    timestamp: str = str(datetime.datetime.now())
    sm: int = randint(60, 94)
    hm: int = randint(60, 94)
    tmp: int = randint(20, 25)
    batt: int = randint(50, 100)
    data = f"soil_moisture:{sm}&humidity:{hm}&temperature:{tmp}&battery_level:{batt}"
    payload = f"{sensor_type};{device_id};{timestamp};{data}"
    try:
        msg = client.publish(
            topic=f"{Broker.ROOT_TOPIC}{Topics.SENSOR_DATA}",
            payload=payload,
            qos=1
        )
        msg.wait_for_publish()
        if msg.is_published():
            print(payload)
    
    except Exception as e:
        print(e)

    time.sleep(300)

# # third-party
# from paho.mqtt import client as paho_mqtt, enums
# from typing import Any, List
# import time

# # $SYS topics testing
# # 

# __subscribed_topics__ = []

# _topics = [
#         '$SYS/broker/clients/connected',
#         '$SYS/broker/clients/total',
#         '$SYS/broker/subscriptions/count',
#         '$SYS/broker/bytes/sent', # total number of bytes sent since the broker started
#         '$SYS/broker/bytes/received', # total number of bytes received since the broker started
#         '$SYS/broker/messages/received',
#         '$SYS/broker/messages/sent',
#     ]

# __ACTIVE_CLIENTS__ : int = 0
# __CLIENTS_TOTAL__ : int = 0
# __SUB_COUNT__ : int = 0
# __BYTES_SENT__ : int = 0
# __BYTES_RECEIVED__ : int = 0
# __MESSAGES_RECEIVED__ : int = 0
# __MESSAGES_SENT__ : int = 0

# def on_c(client: paho_mqtt.Client, userdata: Any, flags, rc, properties) -> None:
#     print(f"{client._client_id.decode('utf-8')}: connected")

# def on_msg(client: paho_mqtt.Client, userdata: Any, msg: paho_mqtt.MQTTMessage) -> None:
#     global __ACTIVE_CLIENTS__, __CLIENTS_TOTAL__, __SUB_COUNT__, __BYTES_SENT__, __BYTES_RECEIVED__, __MESSAGES_RECEIVED__, __MESSAGES_SENT__

#     if msg.topic == _topics[0]:
#         __ACTIVE_CLIENTS__ = int(msg.payload)
    
#     elif msg.topic == _topics[1]:
#         __CLIENTS_TOTAL__ = int(msg.payload)

#     elif msg.topic == _topics[2]:
#         __SUB_COUNT__ = int(msg.payload)

#     elif msg.topic == _topics[3]:
#         __BYTES_SENT__ = int(msg.payload)

#     elif msg.topic == _topics[4]:
#         __BYTES_RECEIVED__ = int(msg.payload)

#     elif msg.topic == _topics[5]:
#         __MESSAGES_RECEIVED__ = int(msg.payload)
    
#     elif msg.topic == _topics[6]:
#         __MESSAGES_SENT__ = int(msg.payload)

#     print(f"{msg.topic}: {msg.payload.decode('utf-8')}")

# def subscribe(client: paho_mqtt.Client, topics: List[str]) -> None:
#     client.subscribe("$SYS/#", qos=1)
#     #for topic in topics:
#     #    client.subscribe(topic, qos=1)

# def add_callbacks(client: paho_mqtt.Client, topics: List[str]) -> None:
#     for topic in topics:
#         print(f"{client._client_id.decode('utf-8')} subscribed to: {topic}")
#         client.message_callback_add(topic, on_msg)

# client = paho_mqtt.Client(callback_api_version=enums.CallbackAPIVersion.VERSION2, client_id="sys_test")
# client.on_connect = on_c
# add_callbacks(client, _topics)
# client.connect('192.168.1.25', 1883)
# client.loop_start()
# subscribe(client, _topics)

# def get_vals() -> str:
#     _str = f"c_active: {__ACTIVE_CLIENTS__}, c_total: {__CLIENTS_TOTAL__}, s_count: {__SUB_COUNT__}, b_sent: {__BYTES_SENT__}, b_recieved: {__BYTES_RECEIVED__}, m_sent: {__MESSAGES_SENT__}, m_received: {__MESSAGES_RECEIVED__}"

#     return _str

# # keep thread alive
# try:
#     while True:
#         time.sleep(0.5)
# except KeyboardInterrupt:
#     msg_map : dict = {
#         'active_clients': __ACTIVE_CLIENTS__,
#         'total_clients': __CLIENTS_TOTAL__,
#         'sub_count': __SUB_COUNT__,
#         'bytes_sent': __BYTES_SENT__,
#         'bytes_received': __BYTES_RECEIVED__,
#         'messages_sent': __MESSAGES_SENT__,
#         'messages_received': __MESSAGES_RECEIVED__
#     }

#     print(msg_map)
