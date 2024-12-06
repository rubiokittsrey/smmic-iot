from paho.mqtt import client as mqtt, enums
import time
import argparse
import sys
import logging

def callback_mqtt_test(client: mqtt.Client, userdata, msg):
    print(f"payload: {str(msg.payload.decode('utf-8'))} ({msg.topic})")

def init_client() -> mqtt.Client:
    callback_client = mqtt.Client(
        callback_api_version=enums.CallbackAPIVersion.VERSION2,
        client_id = 'smmic-listener',
        protocol = mqtt.MQTTv311
    )
    return callback_client

if __name__ == "__main__":
    callback_client = init_client()

    callback_client.connect(
        host='localhost',
        port=1883,
    )

    callback_client.loop_start()

    callback_client.subscribe("#")
    callback_client.message_callback_add("#", callback_mqtt_test)

    try:
        pub = callback_client.publish(
            topic=f"smmic/user/commands/feedback",
            payload="58c6dd67-3200-4bf0-8044-a851465edd02;300;smmic/sensor/interval/58c6dd67-3200-4bf0-8044-a851465edd02",
            qos=1
        )
        pub.wait_for_publish()
        if pub.is_published():
            print('yur')
    except Exception as e:
        print(str(e))

    while True:
        time.sleep(0.5)