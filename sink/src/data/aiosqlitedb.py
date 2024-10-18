# TODO: documentation
# 
# 

# third-party
import aiosqlite
import asyncio
import logging
import os
import multiprocessing
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Any

# internal helpers, configurations
from settings import APPConfigurations, Topics, Broker
from utils import log_config, get_from_queue, SinkData, SensorData

_logs = log_config(logging.getLogger(__name__))

# sql writer
def _composer(data: Any) -> str:

    sql_command = None
    if data['topic'] == f'{Broker.ROOT_TOPIC}{Topics.SINK_DATA}':
        sk_data = SinkData.from_payload(data['payload'])

    elif data['topic'] == f'{Broker.ROOT_TOPIC}{Topics.SENSOR_DATA}':
        se_data = SensorData.from_payload(data['payload'])

    return 'f'

# sql executor
async def _executor(read_semaphore: asyncio.Semaphore, write_lock: asyncio.Lock, db_connection: aiosqlite.Connection, data: Any):
    if data['topic'].count('data') > 0:
        async with write_lock:
            for _ in range (3):
                try:
                    _composer(data)
                    # await db_connection.execute(_compose(data))
                    # await db_connection.commit()
                    break
                except aiosqlite.OperationalError as e:
                    _logs.warning(f"Unhandled OperationalError exception raised at {__name__}: {str(e)}")
                    await asyncio.sleep(0.5)
            # TODO: implement dumping data to a dump file when the sql command fails
    else:
        async with read_semaphore:
            pass
            # TODO: implement read

#
async def start(queue: multiprocessing.Queue) -> None:
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _logs.error(f"Unable to get running event loop at PID {os.getpid()} ({__name__}): {str(e)}")
        return

    read_semaphore = asyncio.Semaphore(APPConfigurations.GLOBAL_SEMAPHORE_COUNT)
    write_lock = asyncio.Lock()
    tasks: set[asyncio.Task] = set()

    try:
        flag = False
        with ThreadPoolExecutor() as pool:

            async with aiosqlite.connect('storage/local.db') as db:

                # write-ahead logging
                await db.execute("PRAGMA journal_mode=WAL;")
                await db.commit()

                while True:

                    if not flag:
                        _logs.info(f"{__name__} coroutine active at PID {os.getpid()}")
                        flag = not flag

                    try:
                        data = await loop.run_in_executor(pool, get_from_queue, queue, __name__)

                        if data:
                            t = asyncio.create_task(_executor(read_semaphore, write_lock, db, data))
                            tasks.add(t)
                            t.add_done_callback(tasks.discard)

                    except Exception as e:
                        _logs.error(f"Unhandled exception at {__name__} loop: {str(e)}")

                    await asyncio.sleep(0.5)

    except (asyncio.CancelledError, KeyboardInterrupt):
        _logs.debug(f"Shutting down {__name__} at PID {os.getpid()}")

        # cleanup
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        raise