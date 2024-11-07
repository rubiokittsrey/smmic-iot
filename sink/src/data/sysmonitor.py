# the system monitoring module
# description -->>
# TODO: documentation
alias = 'sysmonitor'

# third-party
import os
import subprocess
import multiprocessing
import asyncio
import logging
from datetime import datetime
from typing import Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor

# internal helpers, configurations
from httpclient import api_check
from utils import logger_config, is_num, get_from_queue, status, put_to_queue
from settings import APPConfigurations, Topics, Registry

# settings configurations
alias = Registry.Modules.SystemMonitor.alias
_log = logger_config(logging.getLogger(alias))

_CONNECTED_CLIENTS : int = 0
_CLIENTS_TOTAL : int = 0
_SUB_COUNT : int = 0
_BYTES_SENT : int = 0
_BYTES_RECEIVED : int = 0
_MESSAGES_SENT : int = 0
_MESSAGES_RECEIVED : int = 0
# _FREE_MEMORY : int = 0

# the periodic check flag that is set to True when
# the periodic check method is already currently running
# and false if not
_PERIODIC_CHK_FLAG: bool = False

async def _update_values(topic : str, value : int) -> None:
    global _CONNECTED_CLIENTS, _CLIENTS_TOTAL, _SUB_COUNT, _BYTES_SENT, _BYTES_RECEIVED, _MESSAGES_SENT, _MESSAGES_RECEIVED

    if topic == Topics.SYS_CLIENTS_CONNECTED:
        _CONNECTED_CLIENTS = value
    elif topic == Topics.SYS_CLIENTS_TOTAL:
        _CLIENTS_TOTAL = value
    elif topic == Topics.SYS_SUB_COUNT:
        _SUB_COUNT = value
    elif topic == Topics.SYS_BYTES_SENT:
        _BYTES_SENT = value
    elif topic == Topics.SYS_BYTES_RECEIVED:
        _BYTES_RECEIVED = value
    elif topic == Topics.SYS_MESSAGES_SENT:
        _MESSAGES_SENT = value
    elif topic == Topics.SYS_MESSAGES_RECEIVED:
        _MESSAGES_RECEIVED = value
    else:
        _log.warning(f"Cannot assert $SYS topic of value @ sysmonitor: {topic}")

    return

# retrieval from sys queue
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

    loop = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(f"{__name__}._put_to_queue() is unabled to acquire running loop: {str(e)}")

    if not loop:
        return

    try:
        while True:
            await asyncio.sleep(300) # execute every 5 minutes
            _d = [
                    f'connected_clients:{_CONNECTED_CLIENTS}',
                    f'total_clients:{_CLIENTS_TOTAL}',
                    f'sub_count:{_SUB_COUNT}',
                    f'bytes_sent:{_BYTES_SENT}',
                    f'bytes_received:{_BYTES_RECEIVED}',
                    f'messages_sent:{_MESSAGES_SENT}',
                    f'messages_received:{_MESSAGES_RECEIVED}',
                    f'battery_level:{00}'
                ]
            data : str = ''
            for d in _d:
                data = data + f'&{d}'
            timestamp = str(datetime.now())
            payload = f'{APPConfigurations.CLIENT_ID};{timestamp};{data}'
            msg.update({'topic':Topics.SINK_DATA, 'payload':f'{payload}', 'timestamp': timestamp})

            try:
                with ThreadPoolExecutor() as pool:
                    await loop.run_in_executor(pool, put_to_queue, queue, __name__, msg)
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

# periodically check the api with the api_check() method from aiohttpclient and only return if the status
# should await on startup if init system check returned with api disconnect
# if api disconnect is triggered by the system in the middle of operation (not right after startup) no_wait_start should be True
# to allow immediate checking. wait should only apply after *that* first no wait run
async def _periodic_api_chk(triggers_q: multiprocessing.Queue, no_wait_start = False) -> int:
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(f"{alias} failed to get running event loop ({type(e).__name__}): {str(e.__cause__) if e.__cause__ else str(e)}")

    if not loop:
        return status.FAILED

    await_time = APPConfigurations.API_DISCON_WAIT # await time in seconds, 30 minutes
    mod_name = list(alias.split('.'))[len(alias.split('.')) - 1]
    chk_stat: int = status.UNVERIFIED

    _log.info(f"{mod_name} running periodic API check{' (no wait start)' if no_wait_start else ''}".capitalize())
    attempt_count = 0
    try:
        while not chk_stat == status.SUCCESS:
            # check no wait start condition
            # and always await after first attempt
            if not no_wait_start or attempt_count > 0:
                await asyncio.sleep(await_time) # every 30 minutes

            chk_stat, chk_body, chk_errs = await api_check()

            if chk_stat == status.SUCCESS:
                break
            else:
                attempt_count += 1
                _log.warning(f"{mod_name} periodic API check result -> status.DISCONNECTED ({attempt_count} attempt(s), retrying again in {await_time / 60} minutes)".capitalize())

    except (KeyboardInterrupt, asyncio.CancelledError):
        return status.UNVERIFIED

    trigger = {
        'origin': alias,
        'context': Registry.Triggers.contexts.API_CONNECTION_STATUS,
        'data': {
            'timestamp': str(datetime.now()),
            'status': status.CONNECTED if chk_stat == status.SUCCESS else status.DISCONNECTED,
            'errs': [(name, msg, cause) for name, msg, cause in chk_errs],
        }
    }
    with ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, put_to_queue, triggers_q, alias, trigger)

    _log.info(f"{mod_name} periodic API check returned with status.CONNECTED".capitalize())
    return status.CONNECTED

# start this module / coroutine
async def start(sys_queue: multiprocessing.Queue, taskmanager_q: multiprocessing.Queue, triggers_q: multiprocessing.Queue, api_init_stat: int) -> None:
    # verify existence of event loop
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(f"{alias} failed to get running event loop: {str(e.__cause__) if e.__cause__ else str(e)}")
        return

    if loop:
        _log.info(f"Coroutine {alias.split('.')[len(alias.split('.')) - 1]} active at PID {os.getpid()}")
        # use threadpool executor to run retrieval from queue in non-blocking way
        try:
            with ThreadPoolExecutor() as pool:
                #_coroutines = []
                asyncio.create_task(_put_to_queue(taskmanager_q))
                global _PERIODIC_CHK_FLAG

                if api_init_stat in [status.DISCONNECTED, status.FAILED]:
                    _PERIODIC_CHK_FLAG = True
                    init_chk = asyncio.create_task(_periodic_api_chk(triggers_q=triggers_q))
                    init_chk.add_done_callback(lambda f: globals().update({'_PERIODIC_CHK_FLAG': False}))
 
                #await loop.run_in_executor(pool, __put_to_queue__, msg_queue)
                while True:
                    item = await loop.run_in_executor(pool, get_from_queue, sys_queue, alias)

                    # if the item is an api_disconnect flag
                    if item:
                        # triggers have separate handling logic
                        if list(item.keys()).count('trigger'):
                            if item['context'] == 'api_connection_status':
                                if item['data']['status'] == status.DISCONNECTED and not _PERIODIC_CHK_FLAG:
                                    _PERIODIC_CHK_FLAG = True
                                    while_run_chk = asyncio.create_task(_periodic_api_chk(triggers_q=triggers_q, no_wait_start=True))
                                    while_run_chk.add_done_callback(lambda f: globals().update({'_PERIODIC_CHK_FLAG': False}))
                        else:
                            #__log__.debug(f"Sysmonitor @ PID {os.getpid()} received message from queue (topic: {msg['topic']})")
                            asyncio.create_task(_update_values(topic=item['topic'], value=int(item['payload'])))

                    await asyncio.sleep(0.05)

        except (KeyboardInterrupt, asyncio.CancelledError):
            return

        except Exception as e:
            _log.error(f"Unhandled exception {type(e).__name__} raised at {alias}: {str(e.__cause__)}")