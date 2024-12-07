from paho.mqtt import client as mqtt, enums
from datetime import datetime
import time

DEVICE_ID = "86db1aee-6d62-42f4-ae89-8ed8d839cd53"
SE_DATA = "smmic/sensor/data"
SE_ALERTS = "smmic/sensor/alert"
SE_INTERVAL = f"smmic/sensor/triggers/interval/{DEVICE_ID}"
SE_IRRIGATON = f"smmic/irrigation"
SE_IRRIGATION_TRIGGER = f"smmic/sensor/triggers/irrigation/{DEVICE_ID}"
USR_COMMANDS_FEEDBACK = f"smmic/user/commands/feedback"

mqttclient = mqtt.Client(
    client_id=DEVICE_ID,
)
mqttclient.connect('localhost', 1883)
mqttclient.loop_start()

def on_msg_callback(
        client: mqtt.Client,
        userdata,
        msg: mqtt.MQTTMessage):
    
    print(f"payload: {str(msg.payload.decode('utf-8'))} ({msg.topic})")

    reply_payload = ""
    topic = ""

    if msg.topic == SE_IRRIGATION_TRIGGER:
        reply_payload = f"{DEVICE_ID};{str(datetime.now())};{msg.payload.decode('utf-8')}"
    elif msg.topic == SE_INTERVAL:
        reply_payload = f"{DEVICE_ID};{msg.payload};{msg.topic}"

    try:
        pub = mqttclient.publish(
            topic = SE_IRRIGATON,
            payload = reply_payload.encode('utf-8'),
            qos = 1
        )
    
    except Exception as e:
        print(str(e))

mqttclient.subscribe(SE_INTERVAL)
mqttclient.subscribe(SE_IRRIGATION_TRIGGER)
mqttclient.message_callback_add("smmic/#", on_msg_callback)

while True:
    time.sleep(0.25)