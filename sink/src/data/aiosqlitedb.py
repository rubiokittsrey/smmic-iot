# TODO: documentation
# 
# 

# third-party
import aiosqlite
import asyncio
import logging
import os
import multiprocessing
import inspect
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Union

# internal helpers, configurations
from settings import APPConfigurations, Topics, Broker
from utils import log_config, get_from_queue, SinkData, SensorData, status

_logs = log_config(logging.getLogger(__name__))

_DATABASE = f"{APPConfigurations.LOCAL_STORAGE_DIR}local.db"

# schema tables
class Schema:
    
    class SinkData:
        # static method that takes in a dictionary or SinkData Object
        # composes an SQL insert statement from the data
        @staticmethod
        def compose_insert(data: Union[Dict, SinkData]) -> Union[str, None]:
            sk_data_obj: Union[SinkData, None] = None
            fields: List[str] = Schema.SinkData.fields

            # create a SinkData instance from the dictionary
            if isinstance(data, dict):
                try:
                    skdata_params = inspect.signature(SinkData).parameters
                    skdata_kwargs = {}
                    for f, _ in skdata_params.items():
                        if f == 'self':
                            continue
                        skdata_kwargs.update({f: data[f]})
                    sk_data_obj = SinkData(**skdata_kwargs)
                except KeyError as e:
                    _logs.error(f"KeyError raised at {__name__}: {str(e)}")
                    return None
                except TypeError as e:
                    _logs.error(f"TypeError raised at {__name__}: {str(e)}")
            elif isinstance(data, SinkData):
                sk_data_obj = data
            else:
                _logs.warning(f"Provided data is neither of type dict or SinkData: {type(data)}")
                return None

            if not sk_data_obj:
                return

            cols = ", ".join(fields)
            # iterate over fields and compose VALUES part of the INSERT statement
            values = ", ".join([repr(getattr(sk_data_obj, field)) for field in fields])

            # join the list into one command
            c_final = f"INSERT INTO SinkData ({cols}) VALUES ({values});"

            return c_final

        @staticmethod
        def create_table() -> str:
            c_final = """
                CREATE TABLE IF NOT EXISTS SinkData (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL UNIQUE,
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
            
            return c_final
        
        fields = [
            'timestamp',
            'battery_level',
            'connected_clients',
            'total_clients',
            'sub_count',
            'bytes_sent',
            'bytes_received',
            'messages_sent',
            'messages_received',
            'payload'
        ]

    class SensorDevice:

        @staticmethod #TODO
        def compose_insert(data: Dict) -> Union[str, None]:
            pass

        @staticmethod
        def create_table() -> str:
            c_final = """
                CREATE TABLE IF NOT EXISTS SensorDevice (
                    device_id VARCHAR(100) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    latitude DECIMAL(9, 6),
                    longitude DECIMAL(9, 6),
                    lastsync TEXT NOT NULL
                ) """

            return c_final
        
        fields = [
            'device_id',
            'name',
            'latitude',
            'longitude',
            'lastsync'
        ]

    class SensorData:
        # static method that takes a dict or SensorData object parameter
        # and composes and returns an insert statement from the data
        @staticmethod #TODO: implement
        def compose_insert(data: Union[Dict, SensorData]) -> Union[str, None]:
            pass
            # se_data_obj: Union[SinkData, None] = None
            # fields: List[str] = Schema.SensorData.fields

            # # create a SensorData instance from the dictionary
            # if isinstance(data, dict):
            #     try:
            #         sedata_params = inspect.signature(SensorData).parameters
            #         sedata_kwargs  = {}
            #         for f, _ in sedata_params.items():
            #             if f == 'self':
            #                 continue
            #             sedata_kwargs.update({f: data[f]})
            #         se_data_obj = SensorData(**sedata_kwargs)
            #     except KeyError as e:
            #         _logs.error(f"TypeError raised at {__name__}: {str(e)}")
            #     except TypeError as e:
            #         _logs.error(f"TypeError raised at {__name__}: {str(e)}")
            # elif isinstance(data, SensorData):
            #     se_data_obj = data
            # else:
            #     _logs.warning(f"Provided data is neither of type dict or SensorData: {type(data)}")
            #     return None

            # if not se_data_obj:
            #     return

            # #create a hash id from device_id and the timestamp of the data
            # raw_str = f'{se_data_obj.device_id}{se_data_obj.timestamp}'
            # hash_id = sha256(raw_str.encode('utf-8')).hexdigest()

            # # iterate over fields and compose VALUES pat of the INSERT statement
            # val_arr = []
            # for f in fields:
            #     if f == 'hash_id':
            #         val_arr.append(hash_id)
            #     else:
            #         val_arr.append(repr(getattr(se_data_obj, f)))
            # values = ", ".join(values)
            # cols = ", ".join(fields)

            # c_final = f"INSERT INTO SensorData ({cols}) VALUES ({values})"

            # return c_final

        @staticmethod
        def create_table() -> str:
            c_final = """
                CREATE TABLE IF NOT EXISTS SensorData (
                    hash_id TEXT PRIMARY KEY,
                    device_id VARCHAR(100) NOT NULL,
                    battery_level DECIMAL(5, 2) NOT NULL,
                    timestamp TEXT NOT NULL,
                    soil_moisture DECIMAL(5, 2) NOT NULL,
                    temperature DECIMAL(5, 2) NOT NULL,
                    humidity DECIMAL(5, 2) NOT NULL,
                    payload TEXT NOT NULL,
                    CONSTRAINT fk_device FOREIGN KEY (device_id) REFERENCES SensorDevice (device_id) ON DELETE CASCADE
                ) """

            return c_final

        fields = [
            'hash_id',
            'device_id',
            'battery_level',
            'timestamp',
            'soil_moisture',
            'temperature',
            'humidity',
            'payload'
        ]

    class Unsynced:

        @staticmethod #TODO
        def serialize_from_map(data: Dict):
            pass
        
        @staticmethod
        def create_table() -> str:
            c_final = """
                CREATE TABLE IF NOT EXISTS UnsyncedData (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic VARCHAR(50) NOT NULL,
                    origin TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT NOT NULL
                ) """
            
            return c_final

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
            await db.execute(Schema.SinkData.create_table())
            await db.commit()
            # sensor device table
            await db.execute(Schema.SensorDevice.create_table())
            await db.commit()
            # sensor data table
            await db.execute(Schema.SensorData.create_table())
            await db.commit()
            # unsyced data table
            await db.execute(Schema.Unsynced.create_table())
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