 # the system monitoring module
# description -->>
# TODO: documentation

# third-party
import time
import multiprocessing
import asyncio
import logging
import os
from datetime import datetime
from typing import Any
from concurrent.futures import ThreadPoolExecutor

# internal helpers, configurations
from utils import log_config
from settings import APPConfigurations, Topics

__log__ = log_config(logging.getLogger(__name__))

__CONNECTED_CLIENTS__ : int = 0
__CLIENTS_TOTAL__ : int = 0
__SUB_COUNT__ : int = 0
__BYTES_SENT__ : int = 0
__BYTES_RECEIVED__ : int = 0
__MESSAGES_SENT__ : int = 0
__MESSAGES_RECEIVED__ : int = 0
__FREE_MEMORY__ : int = 0

__, __sys_topics__ = Topics.get_topics()

async def __update_values__(topic : str, value : int, semaphore : asyncio.Semaphore) -> None:
    global __CONNECTED_CLIENTS__, __CLIENTS_TOTAL__, __SUB_COUNT__, __BYTES_SENT__, __BYTES_RECEIVED__, __MESSAGES_SENT__, __MESSAGES_RECEIVED__

    if topic == Topics.SYS_CLIENTS_CONNECTED:
        __CONNECTED_CLIENTS__ = value
    elif topic == Topics.SYS_CLIENTS_TOTAL:
        __CLIENTS_TOTAL__ = value
    elif topic == Topics.SYS_SUB_COUNT:
        __SUB_COUNT__ = value
    elif topic == Topics.SYS_BYTES_SENT:
        __BYTES_SENT__ = value
    elif topic == Topics.SYS_BYTES_RECEIVED:
        __BYTES_RECEIVED__ = value
    elif topic == Topics.SYS_MESSAGES_SENT:
        __MESSAGES_SENT__ = value
    elif topic == Topics.SYS_MESSAGES_RECEIVED:
        __MESSAGES_RECEIVED__ = value
    else:
        __log__.warning(f"Cannot assert $SYS topic of value @ sysmonitor: {topic}")

def __from_sys_queue__(queue: multiprocessing.Queue) -> dict | None:
    msg: dict | None = None

    try:
        msg = queue.get(timeout=0.1)
    except Exception as e:
        __log__.error(f"Exception raised @ {os.getpid()} -> sysmonitor cannot get message from queue: {e}") if not queue.empty() else None
    except KeyboardInterrupt or asyncio.CancelledError:
        raise

    return msg

async def __put_to_queue__(queue: multiprocessing.Queue):
    msg: dict | None = {}

    while True:
        await asyncio.sleep(300)
        _d = [
                f'connected_clients:{__CONNECTED_CLIENTS__}',
                f'total_clients:{__CLIENTS_TOTAL__}',
                f'sub_count:{__SUB_COUNT__}',
                f'bytes_sent:{__BYTES_SENT__}',
                f'bytes_received:{__BYTES_RECEIVED__}',
                f'messages_sent:{__MESSAGES_SENT__}',
                f'messages_received:{__MESSAGES_RECEIVED__}'
            ]
        data : str = ''
        for d in _d:
            data = data + f'&{d}'
        payload = f'{APPConfigurations.CLIENT_ID};{datetime.now()};{data}'
        msg.update({'topic':'smmic/sink/data', 'payload':f'{payload}'})

        try:
            queue.put(msg)
        except Exception as e:
            __log__.error(f"Cannot put message to queue -> __put_to_queue__ @ PID {os.getpid()}: {str(e)}")

async def start(sys_queue: multiprocessing.Queue, msg_queue: multiprocessing.Queue) -> None:
    semaphore = asyncio.Semaphore(1)

    # verify existence of event loop
    loop: asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        __log__.error(f"Failed to get running event loop @ PID {os.getpid()} sysmonitor module: {str(e)}")
        return

    if loop:
        __log__.info(f"System monitor module of taskmanager sub-process active @ PID {os.getpid()}")
        # use threadpool executor to run retrieval from queue in non-blocking way
        try:
            # to do handle task cancellation of this
            with ThreadPoolExecutor() as pool:
                #_coroutines = []
                asyncio.create_task(__put_to_queue__(msg_queue))
                #await loop.run_in_executor(pool, __put_to_queue__, msg_queue)
                try:
                    while True:
                        msg = await loop.run_in_executor(pool, __from_sys_queue__, sys_queue)
                        if msg:
                            __log__.debug(f"Sysmonitor @ PID {os.getpid()} received message from queue (topic: {msg['topic']})")
                            asyncio.create_task(__update_values__(topic=msg['topic'], value=int(msg['payload']), semaphore=semaphore))

                        await asyncio.sleep(0.05)

                except KeyboardInterrupt:
                    raise
                    #await asyncio.gather(*_coroutines)
                    #await cancel_tasks(_coroutines)

                except asyncio.CancelledError:
                    raise
                    #await asyncio.gather(*_coroutines)

        except KeyboardInterrupt or asyncio.CancelledError:

            raise