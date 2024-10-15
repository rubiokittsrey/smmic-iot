# third-party
import time
import datetime
import asyncio
from secrets import token_urlsafe
from random import randint
from paho.mqtt import client as mqtt, enums
from typing import List

# internal
from settings import Topics, Broker

async def run_test():
    k = 0
    loop = asyncio.get_event_loop()

    if loop:
        tasks: List[asyncio.Task] = []
        for i in range(5):
            tasks.append(asyncio.create_task(abstracted_pub()))

        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            for t in tasks:
                t.cancel()

async def abstracted_pub():
    device_id = token_urlsafe(8)
    timestamp = str(datetime.datetime.now())
    signal = 1

    client = await init_and_conn(device_id, timestamp)

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
        await __signal_off__(client, device_id)
    except Exception as e:
        print(f"err @ run_test: {e}")
    await asyncio.sleep(3)

async def init_and_conn(device_id: str, timestamp) -> mqtt.Client:
    client = mqtt.Client(client_id=device_id)
    client.will_set('smmic/sensor/alert', f"{device_id};{timestamp};0")
    client.connect(Broker.HOST, 1883)
    client.loop_start()

    return client

async def __signal_off__(client: mqtt.Client, device_id: str):
    payload = f"{device_id};{str(datetime.datetime.now())};{0}"
    sleep_time = randint(15,20)
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

    try:
        client.disconnect()
    except Exception as e:
        print(f'err @ run_test: {e}')

if __name__ == '__main__':
    asyncio.run(run_test())
