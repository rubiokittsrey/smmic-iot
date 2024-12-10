import aiosqlite
import os
import sys
import asyncio
from typing import Any

# internal
from settings import APPConfigurations

async def fetch(read_semaphore, connection):
    async with read_semaphore:
        sql = "SELECT * FROM SENSORDATA"

        rows : Any = None
        try:
            cursor = await connection.execute(sql)
            rows = await cursor.fetchall()
        except aiosqlite.OperationalError as e:
            print(f"raised {type(e).__name__}: {str(e.__cause__)}")
            #_log.error(f"Unhandled {type(e).__name__} raised at {__name__}: {str(e.__cause__)}")

        return rows

async def run2():
    await asyncio.sleep(2)
    try:
        async with aiosqlite.connect(f"{APPConfigurations.LOCAL_STORAGE_DIR}local_backup.db") as connection:
            data = await fetch(asyncio.Semaphore(APPConfigurations.GLOBAL_SEMAPHORE_COUNT), connection)
            for r in data:
                print(r)
    except Exception as e:
        print(f"{type(e).__name__} raised: {str(e.__doc__)}")

    return 'yyyyuuuuuurttttt'

async def run():
    f = asyncio.create_task(run2())
    f.add_done_callback(lambda f: print('done'))
    while True:
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(run())