# the system monitoring module
# description -->>
# TODO: documentation

# third-party
import subprocess
import multiprocessing
import asyncio
import logging
import os
from datetime import datetime
from typing import Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor

# internal helpers, configurations
from utils import log_config, is_num
from settings import APPConfigurations, Topics

_log = log_config(logging.getLogger(__name__))

__CONNECTED_CLIENTS__ : int = 0
__CLIENTS_TOTAL__ : int = 0
__SUB_COUNT__ : int = 0
__BYTES_SENT__ : int = 0
__BYTES_RECEIVED__ : int = 0
__MESSAGES_SENT__ : int = 0
__MESSAGES_RECEIVED__ : int = 0
# __FREE_MEMORY__ : int = 0

__, __sys_topics__ = Topics.get_topics()

async def _update_values(topic : str, value : int) -> None:
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
        _log.warning(f"Cannot assert $SYS topic of value @ sysmonitor: {topic}")

    return

def _from_sys_queue(queue: multiprocessing.Queue) -> dict | None:
    msg: dict | None = None

    try:
        msg = queue.get(timeout=0.1)
    except Exception as e:
        _log.error(f"Exception raised @ {os.getpid()} -> sysmonitor cannot get message from queue: {e}") if not queue.empty() else None
    except KeyboardInterrupt or asyncio.CancelledError:
        raise

    return msg

# put the current values to the aiohttp queue
# intervals of 5 minutes
async def _put_to_queue(queue: multiprocessing.Queue):
    msg: dict | None = {}

    try:
        while True:
            await asyncio.sleep(300) # execute every 5 minutes
            _d = [
                    f'connected_clients:{__CONNECTED_CLIENTS__}',
                    f'total_clients:{__CLIENTS_TOTAL__}',
                    f'sub_count:{__SUB_COUNT__}',
                    f'bytes_sent:{__BYTES_SENT__}',
                    f'bytes_received:{__BYTES_RECEIVED__}',
                    f'messages_sent:{__MESSAGES_SENT__}',
                    f'messages_received:{__MESSAGES_RECEIVED__}',
                    f'battery_level:{00}'
                ]
            data : str = ''
            for d in _d:
                data = data + f'&{d}'
            payload = f'{APPConfigurations.CLIENT_ID};{datetime.now()};{data}'
            msg.update({'topic':'smmic/sink/data', 'payload':f'{payload}'})

            try:
                queue.put(msg)
            except Exception as e:
                _log.error(f"Cannot put message to queue -> __put_to_queue__ @ PID {os.getpid()}: {str(e)}")
    except (KeyboardInterrupt, asyncio.CancelledError):
        return

# returns a list of memory usage data (in kilobytes) of the device
# 'free' docs: https://www.turing.com/kb/how-to-use-the-linux-free-command
# NOTE: not in use (as of 9/25/2024)
def mem_check() -> Tuple[List[int|float], List[int|float]]:
    mem_f : List[int | float] = []
    swap_f : List[int | float] = []

    try:
        # get output of free, decode and then split each newline
        output = subprocess.check_output(["free"])
        decoded = output.decode('utf-8')
        s_output = decoded.split("\n")

        # the mem and swap out as lists
        # assign to cache as Tuples with the final mem and swap lists
        mem_split : List[Any] = s_output[1].split(' ')
        swap_split: List[Any] = s_output[2].split(' ')
        cache = [(mem_split, mem_f), (swap_split, swap_f)]
        
        # remove any empty occurence within each split
        # and pop the first items 'Mem:' or 'Swap:'
        for split, f in cache:
            for i in range(split.count('')):
                split.remove('')

        # the final mem and swap output list
        # contains num values (int / float)
        # convert each conte nt of list to num and append to mem_f
        # then return mem_f [total, used, free, shared, buff/cache, available]
        for split, f in cache:
            for item in split:
                _t = is_num(item)
                if not _t:
                    pass
                else:
                    f.append(_t(item))

    except Exception as e:
        _log.error(f"Unhandled exception occured at sysmonitor.__mem_check__: {str(e)}")

    return mem_f, swap_f

# start this module / coroutine
async def start(sys_queue: multiprocessing.Queue, tskmngr_queue: multiprocessing.Queue) -> None:
    # verify existence of event loop
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(f"Failed to get running event loop @ PID {os.getpid()} sysmonitor module: {str(e)}")
        return

    if loop:
        _log.info(f"{__name__} coroutine active at PID {os.getpid()}")
        # use threadpool executor to run retrieval from queue in non-blocking way
        try:
            # to do handle task cancellation of this
            with ThreadPoolExecutor() as pool:
                #_coroutines = []
                asyncio.create_task(_put_to_queue(tskmngr_queue))
                #await loop.run_in_executor(pool, __put_to_queue__, msg_queue)
                try:
                    while True:
                        msg = await loop.run_in_executor(pool, _from_sys_queue, sys_queue)
                        if msg:
                            #__log__.debug(f"Sysmonitor @ PID {os.getpid()} received message from queue (topic: {msg['topic']})")
                            asyncio.create_task(_update_values(topic=msg['topic'], value=int(msg['payload'])))

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