# third-party
import os
import sys
from datetime import datetime
from random import randint
from settings import APPConfigurations

try:
    sys.path.append(f'/home/smmic/.smmic/sink/common')
    sys.path.append(APPConfigurations.SRC_PATH)
except Exception as e:
    print(f"Exception raised: {e}")
    os._exit(0)

# internal
from data import aiosqlitedb
from utils import SinkData, SensorData

if __name__ == "__main__":
    data = {
        'payload': 'raw_p',
        'timestamp': str(datetime.now()),
        'connected_clients': 25,
        'total_clients': 25,
        'sub_count': 100,
        'bytes_sent': 1000,
        'bytes_received': 1000,
        'messages_sent': 250,
        'messages_received': 250,
        'battery_level': 0,
        'device_id': 'test'
    }
    #data = SinkData('raw_p', datetime.now(), 25, 25, 100, 1000, 1000, 250, 250, 0, 'test')
    x = aiosqlitedb.Schema.SinkData.compose_insert(data)
    print(x)

    # data = {
        
    # }
    # data = SensorData('soil_moisture', 'fd7b1df2-3822-425c-b4c3-e9859251728d', str(datetime.now()), SensorData.SoilMoistureSensor(randint(60, 94), randint(60, 94), randint(20, 25), randint(50, 100)), 'yurt')
    # x = aiosqlitedb.Schema.SensorData.compose_insert(data)
    # print(x)