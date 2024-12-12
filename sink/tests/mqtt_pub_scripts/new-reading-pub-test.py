# third-party
import time
import datetime
from random import randint
from paho.mqtt import client as mqtt, enums

# internal
from settings import Topics, Broker

client = mqtt.Client(client_id="test_pub1")
client.connect(Broker.HOST, 1883)
client.loop_start()

k = 0
while True:
    sensor_type: str = "soil_moisture"
    device_id: str = "fd7b1df2-3822-425c-b4c3-e9859251728d"
    timestamp: str = str(datetime.datetime.now())
    sm: int = randint(5, 30)
    hm: int = randint(60, 94)
    tmp: int = randint(20, 25)
    batt: int = randint(50, 100)
    data = f"soil_moisture:{sm}&humidity:{hm}&temperature:{tmp}&battery_level:{batt}"
    payload = f"{sensor_type};{device_id};{timestamp};{data}"
    try:
        msg = client.publish(
            topic=f"{Topics.SENSOR_DATA}",
            payload=payload,
            qos=1
        )
        msg.wait_for_publish()
        if msg.is_published():
            print(payload)
    
    except Exception as e:
        print(e)

    time.sleep(300)
