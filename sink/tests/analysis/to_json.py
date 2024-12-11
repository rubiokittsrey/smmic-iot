import aiosqlite
import os
import sys
import asyncio
import json
from datetime import datetime
from typing import Any, List

from settings import APPConfigurations
from utils import SensorData

se_id = '58c6dd67-3200-4bf0-8044-a851465edd02'

async def fetch(read_semaphore, db):
    async with read_semaphore:
        sql = (
            "SELECT * FROM SENSORDATA "
            f"WHERE device_id = '{se_id}'")
        rows: Any = None
        try:
            cur = await db.execute(sql)
            rows = await cur.fetchall()
        except aiosqlite.OperationalError as e:
            print(f"raised {type(e).__name__}: {str(e)}")

        return rows
    
async def start():
    data: list
    try:
        async with aiosqlite.connect(
            f"{APPConfigurations.LOCAL_STORAGE_DIR}"
            "local_backup.db") as con:

            data = await fetch(asyncio.Semaphore(1), con)
            print(len(data))
            write_to_json(data)
    
    except Exception as e:
        print(f"{type(e).__name__} raised: {str(e)}")

def write_to_json(data: list):
    fpath = "sensor_one.json"

    mlist: list[dict] = []

    count = 0
    for row in data:
        rmap = SensorData.map_sensor_payload(row[4])
        rmap.pop('sensor_type')
        rmap.pop('battery_level')
        rmap.pop('device_id')
        #rmap.pop('payload')

        try:
            rmap['timestamp'] = datetime.strptime(
                rmap['timestamp'],
                "%Y-%m-%d %H:%M:%S"
            )
            mlist.append(rmap)
            count += 1
        except ValueError as e:
            continue
    
    sorted_mlist = sorted(mlist, key=lambda x: x['timestamp'])
    for x in sorted_mlist:
        x['timestamp'] = str(x['timestamp'])

    sorted_mlist.insert(0,{
        'device_id': se_id
    })
    with open(fpath, "w") as jsonf:
        json.dump(sorted_mlist, jsonf, indent=4)

if __name__ == "__main__":
    asyncio.run(start())