# third-party
import time
import datetime
import asyncio
from secrets import token_urlsafe
from random import randint
from paho.mqtt import client as mqtt, enums

# internal
from settings import Topics, Broker

async def run_test():
    client = mqtt.Client(client_id="irr_test1")
    client.connect('192.168.1.9', 1883)
    client.loop_start()

    k = 0
    loop = asyncio.get_event_loop()

    if loop:
        tasks = []
        for i in range(2):
            device_id = token_urlsafe(8)
            timestamp = str(datetime.datetime.now())
            signal = 1
            payload = f"{device_id};{timestamp};{str(signal)}"
            try:
                msg = client.publish(
                    topic=f"{Broker.ROOT_TOPIC}{Topics.IRRIGATION}",
                    payload=payload,
                    qos=1
                )
                msg.wait_for_publish()
                if msg.is_published():
                    print(f"signal on sent: {payload}")
                tasks.append(asyncio.create_task(__signal_off__(client, device_id)))
            except Exception as e:
                print(f"err @ run_test: {e}")
            await asyncio.sleep(10)
        await asyncio.gather(*tasks)

async def __signal_off__(client: mqtt.Client, device_id: str):
    payload = f"{device_id};{str(datetime.datetime.now())};{0}"
    sleep_time = randint(5,10)
    await asyncio.sleep(sleep_time)
    try:
        msg = client.publish(
            topic=f"{Broker.ROOT_TOPIC}{Topics.IRRIGATION}",
            payload=payload,    
            qos=1
        )
        msg.wait_for_publish()
        if msg.is_published():
            print(f"signal off sent: {payload} after wait time {sleep_time}")
    except Exception as e:
        print(f"err @ __signal_off__: {e}")

if __name__ == '__main__':
    asyncio.run(run_test())
