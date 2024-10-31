# TODO: documentation
#
#
#

alias = "task-manager"

# third-party
import multiprocessing
import asyncio
import logging
import os
import random
import heapq
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, Dict, List, Tuple, Set

# internal helpers, configs
from utils import (log_config,
                   set_priority, priority,
                   get_from_queue, put_to_queue,
                   SensorAlerts,
                   status)
from settings import APPConfigurations, Topics
from src.data import sysmonitor, aiosqlitedb, aiohttpclient

_log = log_config(logging.getLogger(__name__))

# unimplemented priority class for tasks
# not sure how to implement this yet
# TODO: look into task prioritization
class _prioritized_task:
    def __init__(self, priority: int, task: Callable):
        self.priority = priority
        self.task = task

    def __lt__(self, other):
        return self.priority < other.priority

# for topic '/dev/test'
# a simple dummy function made to test concurrent task management
async def _dev_test_task(data: dict) -> None:
    # simulate task delay
    duration = random.randint(1, 10)
    await asyncio.sleep(duration)
    _log.debug(f"Task done @ PID {os.getpid()} (dev_test_task()): [timestamp: {data['timestamp']}, topic: {data['topic']}, payload: {data['payload']}] after {duration} seconds")

# - description:
# * delegates task to the proper process / function
#
# - parameters:
# * aio_queue: the message queue to send items to the aiohttp client
# * hardware_queue: the message queue to send items to the hardware process
async def _delegator(semaphore: asyncio.Semaphore,
                     data: Dict,
                     sysmonitor_q: multiprocessing.Queue,
                     aiosqlite_q: multiprocessing.Queue,
                     aiohttpclient_q: multiprocessing.Queue,
                     hardware_q: multiprocessing.Queue,
                     api_stat: int,
                     ) -> Any:
    
    # if the task is an api_disconnect trigger, forward to the correct queue
    if list(data.keys()).count('api_disconnect'):
        if data['api_disconnect']:
            _to_queue(sysmonitor_q, data)
        return

    # topics that need to be handled by the aiohttp client (http requests, api calls)
    aiohttp_queue_topics = [Topics.SENSOR_DATA, Topics.SINK_DATA, Topics.SENSOR_ALERT, Topics.SINK_ALERT]
    # topics that need to be handled by the hardware module
    hardware_queue_topics = [Topics.IRRIGATION] # TODO: implement this
    # topics handled by aiosqlitedb module
    aiosqlite_queue_topics = [Topics.SENSOR_DATA, Topics.SINK_DATA]
    # test topics
    test_topics = ['/dev/test']

    async with semaphore:
        dest: List[Tuple[multiprocessing.Queue, Any]] = []

        if data['status'] == int(status.FAILED):

            #_log.warning(f"{alias} received failed task from {aiohttpclient.alias}: {task['task_id']}".capitalize())
            if data['origin'] == aiohttpclient.alias:
                dest.append((aiosqlite_q, {**data, 'to_unsynced': True}))

        else:

            if data['topic'] in test_topics:
                await _dev_test_task(data)

            if data['topic'] in aiosqlite_queue_topics:
                dest.append((aiosqlite_q, {**data, 'to_unsynced': False}))

            if data['topic'] in aiohttp_queue_topics:
                if api_stat == status.DISCONNECTED:
                    dest.append((aiosqlite_q, {**data, 'to_unsynced': True, 'origin': alias}))
                else:
                    dest.append((aiohttpclient_q, data))

            if data['topic'] in hardware_queue_topics:
                dest.append((hardware_q, data))

            if data['topic'] == Topics.SENSOR_ALERT:
                alert = SensorAlerts.map_sensor_alert(data['payload'])

                alert_c = alert['alert_code']
                if alert_c == SensorAlerts.CONNECTED:
                    pass
                elif alert_c == SensorAlerts.DISCONNECTED:
                    dest.append((hardware_q, {**alert, 'disconnected': True}))
        
        for queue, f_task in dest:
            #_log.debug(f"Data put to queue: {queue}")
            put_to_queue(queue, __name__, f_task)

    return 

# internal helper function that handles putting messages to queue
# primarily used by the delegator
def _to_queue(queue: multiprocessing.Queue, msg: Dict[str, Any]) -> bool:    
    try:
        queue.put(msg)
        return True
    except Exception as e:
        _log.error(f"Failed to put message to queue at PID {os.getpid()} ({__name__}): {str(e)}")
        return False

# start the taskmanager process
#
# - parameters:
# * msg_queue: the message queue that the mqtt client sends messages to. items from this queue are identified and delegated in this task manager module
# * aio_queue: the queue that the task manager will send request tasks to, received by the aioclient submodule from the 'data' module
# * hardware_queue: hardware tasks are put into this queue by the task manager. received by the hardware module
#
async def start(
        taskmanager_q: multiprocessing.Queue,
        aiohttpclient_q: multiprocessing.Queue,
        hardware_q: multiprocessing.Queue,
        sysmonitor_q: multiprocessing.Queue,
        api_stat: int
        ) -> None:
    # testing out this semaphore count
    # if the system experiences delay or decrease in performance, try to lessen this amount
    semaphore = asyncio.Semaphore(APPConfigurations.GLOBAL_SEMAPHORE_COUNT)
    # TODO: look into this priority queue
    # priority_queue = asyncio.PriorityQueue()

    loop: asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError as e:
        _log.error(f"{alias} failed to get running event loop at PID {os.getpid()}: {str(e)}")
        return

    aiosqlite_q = multiprocessing.Queue()

    # api status flag
    api_status = status.DISCONNECTED
    if api_stat == status.SUCCESS:
        api_status = status.CONNECTED

    queues_kwargs = {
        'sysmonitor_q': sysmonitor_q,
        'aiohttpclient_q':aiohttpclient_q,
        'hardware_q': hardware_q,
        'aiosqlite_q': aiosqlite_q
    }

    tasks: Set[asyncio.Task] = set()
    if loop:
        _log.info(f"{alias} subprocess active at PID {os.getpid()}".capitalize())
        # use the threadpool executor to run the monitoring function that retrieves data from the queue
        try:
            aiosqlitedb_t = asyncio.create_task(aiosqlitedb.start(aiosqlite_q))
            with ThreadPoolExecutor() as pool:
                while True:
                    # run message retrieval from queue in non-blocking way
                    data = await loop.run_in_executor(pool, get_from_queue, taskmanager_q, __name__)

                    if data:
                        t_keys = list(data.keys())

                        # if the task is an api disconnect trigger
                        if 'api_disconnect' in t_keys:
                            # assign proper status value to flag
                            if data['api_disconnect']:
                                api_status = status.DISCONNECTED
                                task = asyncio.create_task(_delegator(**queues_kwargs, semaphore=semaphore, data=data, api_stat=api_status)).add_done_callback(tasks.discard)
                                tasks.add(task)
                            else:
                                if api_status != status.CONNECTED:
                                    api_status = status.CONNECTED
                                else:
                                    _log.warning(f"API disconnect trigger ({data['api_disconnect']}) received but api_status == status.CONNECTED")
                        
                        else:
                            log_msg = ''
                            if 'status' not in t_keys:
                                data.update({
                                        'status': status.PENDING,
                                        'task_id': sha256(f"{data['topic']}{data['payload']}".encode('utf-8')).hexdigest()
                                    })
                                log_msg = f"{alias} received item from queue: {data['task_id']}".capitalize()
                            elif data['status'] == status.FAILED:
                                log_msg = f"{alias} received failed item from queue: {data['task_id']}".capitalize()
                            else:
                                log_msg = f"{alias} received item from queue: {data['task_id']}".capitalize()                        
                            _log.debug(log_msg)

                            task = asyncio.create_task(_delegator(**queues_kwargs, semaphore=semaphore, data=data, api_stat=api_status)).add_done_callback(tasks.discard) # pass api status flag to delegator
                            tasks.add(task)

                    await asyncio.sleep(0.05)

        except (KeyboardInterrupt, asyncio.CancelledError):

            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            loop.run_until_complete(aiosqlitedb_t)

            return