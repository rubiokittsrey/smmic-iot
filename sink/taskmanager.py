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
from typing import Callable, Any, Dict

# internal helpers, configs
from utils import log_config, set_priority, priority, get_from_queue, SensorAlerts, status
from settings import APPConfigurations, Topics, Broker
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
                     task: Dict,
                     sysmonitor_q: multiprocessing.Queue,
                     aiosqlite_q: multiprocessing.Queue,
                     aiohttpclient_q: multiprocessing.Queue,
                     hardware_q: multiprocessing.Queue,
                     api_stat: int = status.UNVERIFIED,
                     ) -> Any:
    # topics that need to be handled by the aiohttp client (http requests, api calls)
    aiohttp_queue_topics = [Topics.SENSOR_DATA, Topics.SINK_DATA, Topics.SENSOR_ALERT]
    # topics that need to be handled by the hardware module
    hardware_queue_topics = [Topics.IRRIGATION] # TODO: implement this
    # topics handled by aiosqlitedb module
    aiosqlite_queue_topics = [Topics.SENSOR_DATA, Topics.SINK_DATA]
    # test topics
    test_topics = ['/dev/test']

    async with semaphore:

        # if the task is an api_disconnect trigger, forward to the correct queue
        if list(task.keys()).count('api_disconnect'):
            if task['api_disconnect']:
                _to_queue(sysmonitor_q, task)
            return

        # check if it is a failed item
        if task['status'] == int(status.FAILED):
            #_log.warning(f"{alias} received failed task from {aiohttpclient.alias}: {task['task_id']}".capitalize())

            # if the topic is from the aiohttp client, it is unsynced data
            if task['origin'] == aiohttpclient.alias:
                _to_queue(aiosqlite_q, {**task, 'to_unsynced': True})
            # if task['origin'] == aiohttpclient.alias:
            #     return

        else:
            if task['topic'] in test_topics:
                await _dev_test_task(task)

            if task['topic'] in aiosqlite_queue_topics:
                _to_queue(aiosqlite_q, {**task, 'to_unsynced': False})

            if task['topic'] in aiohttp_queue_topics:
                if api_stat == status.DISCONNECTED:
                    _to_queue(aiosqlite_q, {**task, 'to_unsynced': True, 'origin': aiohttpclient.alias})
                else:
                    _to_queue(aiohttpclient_q, task)

            if task['topic'] in hardware_queue_topics:
                _to_queue(hardware_q, task)
        
            # sensor alert handling
            if task['topic'] == Topics.SENSOR_ALERT:
                alert_mapped = SensorAlerts.map_sensor_alert(task['payload'])
                if not alert_mapped:
                    # TODO: handle error scenario
                    return

                #TODO: handle alert code == 0 (DISCONNECTED)
                if alert_mapped['alert_code'] == SensorAlerts.CONNECTED:
                    pass
                
                if alert_mapped['alert_code'] == SensorAlerts.DISCONNECTED:
                    _se_disconn_handler(alert_mapped, hardware_q)

# args:
# data - mapped alert data from mqtt message
# hardware_queue - the hardware queue
def _se_disconn_handler(data: Dict, hardware_queue: multiprocessing.Queue) -> bool:
    # send an irrigation 'off' signal to the hardware queue
    se_disconnect = {
        'device_id': data['device_id'],
        'disconnected': True
    }
    try:
        hardware_queue.put(se_disconnect)
        return True
    except Exception as e:
        _log.error(f"Failed to put message to queue at PID {os.getpid()} ({__name__}): {str(e)}")
        return False

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

    if loop:
        _log.info(f"{alias} subprocess active at PID {os.getpid()}".capitalize())
        # use the threadpool executor to run the monitoring function that retrieves data from the queue
        try:
            aiosqlitedb_t = asyncio.create_task(aiosqlitedb.start(aiosqlite_q))
            with ThreadPoolExecutor() as pool:
                while True:
                    # run message retrieval from queue in non-blocking way
                    task = await loop.run_in_executor(pool, get_from_queue, taskmanager_q, __name__)

                    # if a message is retrieved, create a task to handle that message
                    # TODO: implement task handling for different types of messages
                    if task:

                        # if the task is an api disconnect trigger
                        if 'api_disconnect' in list(task.keys()):
                            # assign proper status value to flag
                            if task['api_disconnect']:
                                api_status = status.DISCONNECTED
                                asyncio.create_task(_delegator(**queues_kwargs, semaphore=semaphore, task=task))
                                continue
                            else:
                                api_status = status.CONNECTED
                                continue

                        if 'status' not in list(task.keys()):
                            task.update({
                                    'status': status.PENDING,
                                    'task_id': sha256(f"{task['topic']}{task['payload']}".encode('utf-8')).hexdigest()
                                })
                            _log.debug(f"{alias} received item from queue: {task['task_id']}".capitalize())
                        elif task['status'] == status.FAILED:
                            _log.debug(f"{alias} received failed item from queue: {task['task_id']}".capitalize())
                        else:
                            _log.debug(f"{alias} received item from queue: {task['task_id']}".capitalize())

                        # NOTE: this block of code currently serves no purpose (unimplemented)
                        # assign a priority for the task
                        assigned_p = set_priority(task['topic'])
                        # if not priority set to moderate
                        if not assigned_p:
                            #_log.debug(f"Cannot assert priority of message from topic: {task['topic']}, setting priority to moderate instead")
                            assigned_p = priority.MODERATE

                        asyncio.create_task(_delegator(**queues_kwargs, semaphore=semaphore, task=task, api_stat=api_status)) # pass api status flag to delegator

                    await asyncio.sleep(0.05)
                    
        except (KeyboardInterrupt, asyncio.CancelledError):
            # enable await of aiosqlitedb_t
            loop.run_until_complete(aiosqlitedb_t)
