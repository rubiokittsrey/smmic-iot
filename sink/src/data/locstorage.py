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
from typing import Any, Dict, List, Union, Callable
from datetime import datetime

# internal helpers, configurations
from settings import APPConfigurations, Topics, Broker, Registry
from utils import (
    logger_config,
    get_from_queue,
    put_to_queue,
    SinkData,
    SensorData,
    status
    )

# settings, configurations
alias = Registry.Modules.LocalStorage.alias
_log = logger_config(logging.getLogger(alias))

_DATABASE = f"{APPConfigurations.LOCAL_STORAGE_DIR}local.db"

# schema tables
class Schema:
    
    class SinkData:
        # static method that takes in a dictionary or SinkData Object
        # composes an SQL insert statement from the data
        @staticmethod
        def compose_insert(data: Union[Dict, SinkData]) -> Union[str, None]:
            data_obj: Union[SinkData, None] = None
            fields: List[str] = Schema.SinkData.fields

            # create a SinkData instance from the dictionary
            if isinstance(data, dict):
                try:
                    params = inspect.signature(SinkData).parameters
                    kwargs = {}
                    for f, _ in params.items():
                        if f == 'self':
                            continue
                        kwargs.update({f: data[f]})
                    data_obj = SinkData(**kwargs)

                except (KeyError, TypeError) as e:
                    _log.error(f"{type(e).__name__} raised at {__name__}: {str(e)}")
                    return

                except Exception as e:
                    _log.error(f"Unhandled exception {type(e).__name__} raised at {__name__}: {str(e)}")
                    return

            elif isinstance(data, SinkData):
                data_obj = data

            else:
                _log.warning(f"Provided data is neither of type dict or SinkData: {type(data)}")
                return None

            if not data_obj:
                return

            cols = ", ".join(fields)
            # iterate over fields and compose VALUES part of the INSERT statement
            values = ", ".join([repr(getattr(data_obj, field)) for field in fields])

            # join the list into one command
            c_final = f"INSERT INTO SinkData ({cols}) VALUES ({values})"

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
            data_obj: Union[SensorData, None] = None
            fields: List[str] = Schema.SensorData.fields

            # create a SinkData instance from the dictionary
            if isinstance(data, dict):
                try:
                    params = inspect.signature(SensorData).parameters
                    kwargs = {}
                    for field, _ in params.items():
                        if field == 'self':
                            continue
                        elif field == 'readings':
                            # NOTE: this part just immediately assumes soilmoisturesensor
                            # because we have no other sensors in development
                            # TODO: fix
                            sm_params = inspect.signature(SensorData.soil_moisture).parameters
                            sm_kwargs = {}
                            for x, _ in sm_params.items():
                                if field != 'self':
                                    sm_kwargs.update({x: data[x]})
                            sm_obj = SensorData.soil_moisture(**sm_kwargs)
                            kwargs.update({field: sm_obj})
                        else:
                            kwargs.update({field: data[field]})
                    data_obj = SensorData(**kwargs)

                except (KeyError, TypeError) as e:
                    _log.error(f"{type(e).__name__} raised at {__name__}: {str(e)}")
                    return

                except Exception as e:
                    _log.error(f"Unhandled exception {type(e).__name__} raised at {__name__}: {str(e)}")
                    return

            elif isinstance(data, SensorData):
                data_obj = data

            else:
                _log.warning(f"Provided data is neither of type dict or SinkData: {type(data)}")
                return None

            if not data_obj:
                return

            # generate hash id from composite of device id and timestamp
            raw_str = f'{data_obj.device_id}{data_obj.timestamp}'
            hash_id = sha256(raw_str.encode('utf-8')).hexdigest()

            val_arr = []
            for field in fields:
                if field == 'hash_id':
                    val_arr.append(hash_id)
                elif field == 'readings':
                    params = inspect.signature(type(data_obj.readings)).parameters
                    readings_arr = []
                    for x, _ in params.items():
                        if field != 'self':
                            readings_arr.append(f'{x}:{getattr(data_obj.readings, x)}')
                    val_arr.append('&'.join(readings_arr))
                else:
                    val_arr.append(getattr(data_obj, field))

            values = ", ".join([repr(value) for value in val_arr])
            cols = ", ".join(fields)

            c_final = f"INSERT INTO SensorData ({cols}) VALUES ({values})"

            return c_final

        @staticmethod
        def create_table() -> str:
            c_final = """
                CREATE TABLE IF NOT EXISTS SensorData (
                    hash_id TEXT PRIMARY KEY,
                    device_id VARCHAR(100) NOT NULL,
                    timestamp TEXT NOT NULL,
                    readings TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    CONSTRAINT fk_device FOREIGN KEY (device_id) REFERENCES SensorDevice (device_id) ON DELETE CASCADE
                ) """

            return c_final

        fields = [
            'hash_id',
            'device_id',
            'timestamp',
            'readings',
            'payload'
        ]

    class Unsynced:

        @staticmethod #TODO
        def compose_insert(data: Dict) -> str:
            fields = Schema.Unsynced.fields
            val_arr = []

            for field in fields:
                if field == 'task_id':
                    val_arr.append(data['task_id'])
                elif field == 'timestamp':
                    val_arr.append(data['timestamp'])
                else:
                    val_arr.append(data[field])

            c_final = f"INSERT INTO UnsyncedData ({', '.join(fields)}) VALUES ({', '.join([repr(value) for value in val_arr])})"

            return c_final

        @staticmethod
        def create_table() -> str:
            c_final = """
                CREATE TABLE IF NOT EXISTS UnsyncedData (
                    task_id TEXT PRIMARY KEY,
                    topic VARCHAR(50) NOT NULL,
                    origin TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT NOT NULL
                ) """

            return c_final

        fields = [
            'task_id',
            'topic',
            'origin',
            'timestamp',
            'payload'
        ]

# sql writer
def _composer(data: Any) -> str | None:

    sql = None
    if data['to_unsynced']:

        if data['origin'] == Registry.Modules.LocalStorage.origin_unsynced:
            sql = None
        else:
            sql = Schema.Unsynced.compose_insert(data)

    elif data['topic'] == Topics.SINK_DATA:
        sql = Schema.SinkData.compose_insert(SinkData.from_payload(data['payload']))

    elif data['topic'] == Topics.SENSOR_DATA:
        sql = Schema.SensorData.compose_insert(SensorData.from_payload(data['payload']))

    return sql

# sql executor
async def _executor(write_lock: asyncio.Lock, db_conn: aiosqlite.Connection, data: Any = None, command: str | None = None):

    sql = ''
    if command:
        sql = command
    elif data:
        sql = _composer(data)

    if not sql:
        return

    # if topic contains 'data'
    # use write_lock
    # TODO: this condition could be better
    err: List[str] = []
    #_log.debug(f"{__name__} executing: {sql}".capitalize())
    async with write_lock:
        for _ in range (3):
            try:
                await db_conn.execute(sql)
                await db_conn.commit()
                break
            except aiosqlite.OperationalError as e:
                err.append(f"Unhandled OperationalError exception raised at {__name__}: {str(e.__cause__) if e.__cause__ else str(e)}")
                await asyncio.sleep(1)
            except Exception as e:
                err.append(f"Unhandled exception {type(e).__name__} raised at {__name__}: {str(e)}")

    # organize similar errors into one log
    if len(err) > 0:
        logged: List[str] = []
        for e in err:
            if e in logged:
                pass
            else:
                count = err.count(e)
                _log.error((f"({count}) " if count > 1 else "") + e + " ")
                logged.append(e)

# generates / checks schemas
# if successful, return status.SUCCESS
async def init() -> int:
    init_stat = status.UNVERIFIED

    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(f"{__name__} failed to acquire event loop: {str(e)}".capitalize())

    # generate schemas
    try:
        async with aiosqlite.connect(_DATABASE) as db_conn:
            tables = [
                Schema.SinkData.create_table(),
                Schema.SensorDevice.create_table(),
                Schema.SensorData.create_table(),
                Schema.Unsynced.create_table()
            ]

            # execute and append to results
            results = []
            for c in tables:
                results.append(await db_conn.execute(c))
            # then commit
            await db_conn.commit()

            init_stat = status.SUCCESS
            _log.debug(f"Database initialization successful ({init.__name__})")
            
    except aiosqlite.Error as e:
        await db_conn.rollback()
        _log.error(f"Database init at {init.__name__} raised error: {str(e)}")
        init_stat = status.FAILED

    return init_stat

# pushes unsynced data from sqlite to the api
# puts the unsynced data to the taskamanger queue
# this should be run as a coroutine and should put items into the queue in chunks
async def _push_unsynced(read_semaphore: asyncio.Semaphore,
                        write_lock: asyncio.Lock,
                        taskmanager_q: multiprocessing.Queue,
                        db_conn: aiosqlite.Connection,
                        async_q: asyncio.Queue,
                        locstorage_q: multiprocessing.Queue,
                        chunks: int = 5) -> Any:

    sql = "SELECT * FROM UnsyncedData"

    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(f"Unable to get running event loop (exception: {type(e).__name__}): {str(e.__cause__) if e.__cause__ else str(e)}")
        return

    async with read_semaphore:
        try:
            cursor = await db_conn.execute(sql)
        except aiosqlite.OperationalError as e:
            _log.error(f"{type(e).__name__} raised at {__name__}: {str(e.__cause__) if e.__cause__ else str(e)}")
        except Exception as e:
            _log.error(f"Unhandled unexpected {type(e).__name__} at {__name__}: {str(e.__cause__) if e.__cause__ else str(e)}")

    proceed_fetch = True
    count = 0
    taskid_cache = []
    with ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, put_to_queue, locstorage_q, __name__, {'signal': 'push_unsynced_running'})
        try:
            while proceed_fetch:

                rows = []
                if not taskid_cache:
                    rows = await cursor.fetchmany(size=chunks)

                    if not rows:
                        # break if rows is empty
                        # TODO: implement re-query db for redundancy (?)
                        break

                    # NOTE item: [task_id, topic, origin, timestamp, payload]
                    for item in rows:
                        task_dict = {
                            'task_id': item[0],
                            'topic': item[1],
                            'origin': Registry.Modules.LocalStorage.origin_unsynced,
                            'timestamp': item[3],
                            'payload': item[4]
                        }
                        await loop.run_in_executor(pool, put_to_queue, taskmanager_q, __name__, task_dict)
                        taskid_cache.append(item[0])

                # chunk done await
                # receive the hash id of the items that are done and to be deleted
                signal = await async_q.get()

                if signal['signal'] == Registry.Triggers.contexts.UNSYNCED_DATA:

                    if signal['data']['task_id'] in taskid_cache:
                        taskid_cache.remove(signal['data']['task_id'])
                    else:
                        _log.warning(f"""{alias}._push_unsynced received
                                     {Registry.Triggers.contexts.UNSYNCED_DATA}
                                     signal but provided task_id is not in current taskid_cache:
                                     {signal['data']['task_id']}""")

                    sql = f"DELETE FROM UnsyncedData WHERE task_id = '{signal['data']['task_id']}'"
                    await _executor(
                        write_lock=write_lock,
                        db_conn=db_conn,
                        command=sql
                    )
                    count += 1

                elif signal['signal'] == 'abandon_task' and signal['cause'] == 'api_disconnect':
                    proceed_fetch = False
                    for hash_id in signal['data']['hash_ids']:
                        sql = f"DELETE FROM UnsyncedData WHERE task_id = '{hash_id}'"
                        await _executor(
                                write_lock=write_lock,
                                db_conn=db_conn,
                                command=sql
                            )
                        count += 1
                    _log.warning(f"Syncing of unsynced data to API cancelled by signal: {signal['signal']} with cause \'{signal['cause']}\'")

            await loop.run_in_executor(pool, put_to_queue, locstorage_q, __name__, {'signal': 'push_unsynced_done'})

        except (KeyboardInterrupt, asyncio.CancelledError) as e:
            _log.warning(f"{__name__}.push_unsynced task received {type(e).__name__}, cancelling execution of task")
            remaining = await cursor.fetchall()
            _log.info(f"Uploaded {count} items from local storage unsynced data with {len(list(remaining))} remaining items")
            return

        except Exception as e:
            _log.error(f"Unhandled exception {type(e).__name__} raised at {__name__}.push_unsynced(): {str(e.__cause__) if e.__cause__ else str(e)}")

    remaining = await cursor.fetchall()
    _log.info(f"Uploaded {count} items from local storage unsynced data with {len(list(remaining))} remaining items")

# this modules internal trigger handler
async def _trigger_handler(
        trigger: Dict,
        read_semaphore: asyncio.Semaphore,
        write_lock: asyncio.Lock,
        db_conn: aiosqlite.Connection,
        push_unsynced_q: asyncio.Queue,
        locstorage_q: multiprocessing.Queue,
        taskmanager_q: multiprocessing.Queue,
        running_ts: List[Callable]) -> Any:

    task = None
    if trigger['context'] == Registry.Triggers.contexts.API_CONNECTION_STATUS:

        if trigger['data']['status'] == status.CONNECTED:
            if _push_unsynced in running_ts:
                pass
            else:
                _log.info(f"Connection to API restored, uploading unsynced data from local storage")
                await _push_unsynced(
                    read_semaphore=read_semaphore,
                    write_lock=write_lock,
                    taskmanager_q=taskmanager_q,
                    db_conn=db_conn,
                    async_q=push_unsynced_q,
                    locstorage_q=locstorage_q
                )

        elif trigger['data']['status'] == status.DISCONNECTED:
            signal = {
                'signal': 'abandon_task',
                'cause': 'api_disconnect',
                'data': {}
            }
            await push_unsynced_q.put(signal)

    elif trigger['context'] == Registry.Triggers.contexts.UNSYNCED_DATA:
        signal = {
            'origin': trigger['origin'],
            'signal': trigger['context'],
            'data': trigger['data']
        }
        await push_unsynced_q.put(signal)

    return

#
async def start(locstorage_q: multiprocessing.Queue, taskmanager_q: multiprocessing.Queue, httpclient_q: multiprocessing.Queue) -> None:
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(f"Unable to get running event loop (exception: {type(e).__name__}): {str(e)}")
        return

    # vars
    write_lock = asyncio.Lock()
    read_semaphore = asyncio.Semaphore(4)
    tasks: set[asyncio.Task] = set()
    push_unsynced_q = asyncio.Queue()
    running_ts = []

    try:
        flag = False
        with ThreadPoolExecutor() as pool:

            async with aiosqlite.connect(_DATABASE) as db_conn:

                # write-ahead logging
                await db_conn.execute("PRAGMA journal_mode=WAL;")
                await db_conn.commit()

                while True:

                    if not flag:
                        _log.info(f"Coroutine {__name__.split('.')[len(__name__.split('.')) - 1]} active at PID {os.getpid()}")
                        flag = not flag

                    try:
                        data = await loop.run_in_executor(pool, get_from_queue, locstorage_q, __name__)

                        if data and list(data.keys()).count('trigger'):
                            task = asyncio.create_task(_trigger_handler(
                                trigger=data,
                                read_semaphore=read_semaphore,
                                write_lock=write_lock,
                                db_conn=db_conn,
                                push_unsynced_q=push_unsynced_q,
                                locstorage_q=locstorage_q,
                                taskmanager_q=taskmanager_q,
                                running_ts=running_ts
                            ))
                            tasks.add(task)
                            task.add_done_callback(tasks.discard)

                        elif data and list(data.keys()).count('signal'):
                            if data['signal'] == 'push_unsynced_running':
                                running_ts.append(_push_unsynced)
                            if data['signal'] == 'push_unsynced_done':
                                running_ts.remove(_push_unsynced)

                        elif data:
                            task = asyncio.create_task(_executor(
                                write_lock=write_lock, 
                                db_conn=db_conn,
                                data=data
                            ))
                            tasks.add(task)
                            task.add_done_callback(tasks.discard)

                    except Exception as e:
                        _log.error(f"Unhandled exception at {__name__} loop: {str(e)}")

                    await asyncio.sleep(0.5)

    except (asyncio.CancelledError, KeyboardInterrupt):
        _log.debug(f"Shutting down {__name__} at PID {os.getpid()}")

        # cleanup
        for task in tasks:
            # TODO: implement dump to file
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        return
    
    except Exception as e:
        _log.error(f"Unhandled exception {type(e).__name__} raised at {__name__}: {str(e.__cause__) if e.__cause__ else str(e)}")