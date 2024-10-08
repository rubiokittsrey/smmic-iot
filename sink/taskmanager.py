# TODO: documentation
#
#
#

PRETTY_ALIAS = "Task Manager"

# third-party
import multiprocessing
import asyncio
import logging
import os
import random
import heapq
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, Dict

# internal helpers, configs
from utils import log_config, set_priority, priority, get_from_queue, SensorAlerts
from settings import APPConfigurations, Topics, Broker
import src.data.sysmonitor as sysmonitor

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
async def _delegator(semaphore: asyncio.Semaphore, data: Dict, aio_queue: multiprocessing.Queue, hardware_queue: multiprocessing.Queue) -> Any:
    # topics that need to be handled by the aiohttp client (http requests, api calls)
    aio_queue_topics = [f'{Broker.ROOT_TOPIC}{Topics.SENSOR_DATA}', f'{Broker.ROOT_TOPIC}{Topics.SINK_DATA}', f'{Broker.ROOT_TOPIC}{Topics.SENSOR_ALERT}']
    # topics that need to be handled by the hardware module
    hardware_queue_topics = [f'{Broker.ROOT_TOPIC}{Topics.IRRIGATION}'] # TODO: implement this
    test_topics = ['/dev/test']

    async with semaphore:

        if data['topic'] in test_topics:
            await _dev_test_task(data)

        if data['topic'] in aio_queue_topics:
            _to_queue(aio_queue, data)
                # TODO: refactor to implement proper return value

        if data['topic'] in hardware_queue_topics:
            _to_queue(hardware_queue, data)
    
        # sensor alert handling
        if data['topic'] == f'{Broker.ROOT_TOPIC}{Topics.SENSOR_ALERT}':
            alert_mapped = SensorAlerts.map_sensor_alert(data['payload'])
            if not alert_mapped:
                # TODO: handle error scenario
                return
            
            #TODO: handle alert code == 0 (DISCONNECTED)
            if alert_mapped['alert_code'] == SensorAlerts.CONNECTED:
                pass
            
            if alert_mapped['alert_code'] == SensorAlerts.DISCONNECTED:
                _se_disconn_handler(alert_mapped, hardware_queue)

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
        task_queue: multiprocessing.Queue,
        c_queue: multiprocessing.Queue,
        aio_queue: multiprocessing.Queue,
        hardware_queue: multiprocessing.Queue,
        sys_queue: multiprocessing.Queue
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
        _log.error(f"{PRETTY_ALIAS} failed to get running event loop at PID {os.getpid()}: {str(e)}")
        return

    if loop:
        _log.info(f"{PRETTY_ALIAS} subprocess active at PID {os.getpid()}")
        # use the threadpool executor to run the monitoring function that retrieves data from the queue
        try:
            # start the sysmonitor coroutine
            sysmonitor_t = loop.create_task(sysmonitor.start(sys_queue=sys_queue, msg_queue=task_queue))
            with ThreadPoolExecutor() as pool:
                while True:
                    # run message retrieval from queue in non-blocking way
                    task = await loop.run_in_executor(pool, get_from_queue, task_queue, __name__)

                    # if a message is retrieved, create a task to handle that message
                    # TODO: implement task handling for different types of messages
                    if task:
                        _log.debug(f"{PRETTY_ALIAS} received item from queue: {task}")

                        # NOTE: this block of code currently serves no purpose (unimplemented)
                        # assign a priority for the task
                        assigned_p = set_priority(task['topic'])
                        # if not priority set to moderate
                        if not assigned_p:
                            _log.debug(f"Cannot assert priority of message from topic: {task['topic']}, setting priority to moderate instead")
                            assigned_p = priority.MODERATE

                        asyncio.create_task(_delegator(semaphore=semaphore, data=task, aio_queue=aio_queue, hardware_queue=hardware_queue))

                    await asyncio.sleep(0.05)
                    
        except (KeyboardInterrupt, asyncio.CancelledError):
            sysmonitor_t.cancel()
            try:
                loop.run_until_complete(sysmonitor_t)
            except asyncio.CancelledError:
                pass
            raise