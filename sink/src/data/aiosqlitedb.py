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
from utils import log_config, get_from_queue, SinkData, SensorData, status

_logs = log_config(logging.getLogger(__name__))

_DATABASE = f"{APPConfigurations.LOCAL_STORAGE_DIR}local.db"

# create table commands
_sk_data_t = """
    CREATE TABLE IF NOT EXISTS SinkData (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        battery_level DECIMAL(5, 2) NOT NULL,
        connected_clients INTEGER NOT NULL,
        total_clients INTEGER NOT NULL,
        sub_count INTEGER NOT NULL,
        bytes_sent INTEGER NOT NULL,
        bytes_received INTEGER NOT NULL,
        messages_sent INTEGER NOT NULL,
        messages_received INTEGER NOT NULL,
        payload TEXT NOT NULL
    ) """

_se_device_t = """
    CREATE TABLE IF NOT EXISTS SensorDevice (
        device_id VARCHAR(100) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        latitude DECIMAL(9, 6) NOT NULL,
        longitude DECIMAL(9, 6) NOT NULL,
        lastsync TEXT NOT NULL
    ) """

_se_data_t = """
    CREATE TABLE IF NOT EXISTS SensorData (
        device_id VARCHAR(100) NOT NULL,
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        battery_level DECIMAL(5, 2) NOT NULL,
        timestamp TEXT NOT NULL,
        soil_moisture DECIMAL(5, 2) NOT NULL,
        temperature DECIMAL(5, 2) NOT NULL,
        humidity DECIMAL(5, 2) NOT NULL,
        payload TEXT NOT NULL,
        CONSTRAINT fk_device FOREIGN KEY (device_id) REFERENCES SensorDevice (device_id) ON DELETE CASCADE
    ) """

_unsynced_t = """
    CREATE TABLE IF NOT EXISTS UnsyncedData (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic VARCHAR(50) NOT NULL,
        origin TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        payload TEXT NOT NULL
    ) """

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

# generates / checks schemas
# if successful, return status.SUCCESS
async def init() -> int:
    init_stat = status.UNVERIFIED

    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _logs.error(f"Unable to get running event loop {os.getpid()} ({__name__}): {str(e)}")

    # generate schemas
    try:
        async with aiosqlite.connect(_DATABASE) as db:
            # sink data table
            await db.execute(_sk_data_t)
            await db.commit()
            # sensor device table
            await db.execute(_se_device_t)
            await db.commit()
            # sensor data table
            await db.execute(_se_data_t)
            await db.commit()
            # unsyced data table
            await db.execute(_unsynced_t)
            await db.commit()
            init_stat = status.SUCCESS
            _logs.debug(f"Database initialization successful ({init.__name__})")
    except aiosqlite.Error as e:
        init_stat = status.FAILED
        _logs.error(f"Database init at {init.__name__} raised error: {str(e)}")

    return init_stat

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

            async with aiosqlite.connect(_DATABASE) as db:

                # write-ahead logging
                await db.execute("PRAGMA journal_mode=WAL;")
                await db.commit()

                while True:

                    if not flag:
                        _logs.info(f"Coroutine {__name__.split('.')[len(__name__.split('.')) - 1]} active at PID {os.getpid()}")
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