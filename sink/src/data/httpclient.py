"""
aiohttpclient module

manages http communication with the api
- hosts a single aiohttp.ClientSession object for request handling
- routes various messages from the task to their designated api endpoints
- integrates with internal queues (taskmanager_q and triggers_q) to handle asynchronous retries and error reporting

TODOs:
- implement message handling for API responses to direct responses or retries.
- add support for priority setting based on urgency and timestamp.
"""

# third-party
import logging
import aiohttp
import asyncio
import time
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Any, Tuple, List
from datetime import datetime

# internal core modules
import reqs

# internal helpers, configurations
from utils import (
    logger_config,
    SinkData,
    SensorData,
    get_from_queue,
    SensorAlerts,
    status,
    put_to_queue
)

from settings import (
    APPConfigurations,
    Topics,
    APIRoutes,
    Broker,
    Registry
)

# configurations, settings
_log = logger_config(logging.getLogger(__name__))
alias = Registry.Modules.HttpClient.alias

# TODO: documentation
# TODO: implement return request response status (i.e code, status literal, etc.)
# routes task messages to api endpoints depending on topic
async def _router(
        semaphore: asyncio.Semaphore,
        task: Dict,
        client_session: aiohttp.ClientSession,
        taskmanager_q: multiprocessing.Queue,
        triggers_q: multiprocessing.Queue
        ) -> Dict:
    
    # NOTE:
    # ----- data keys -> {priorty, topic, payload, timestamp}
    # ----- (sensor alert) data keys -> {device_id, timestamp, alertCode}

    req_body = Dict | None
    status_code: int
    res_body: Any

    async with semaphore:

        if task['topic'] == '/dev/test':
            foo = 'foo'

        elif task['topic'] == Topics.SENSOR_DATA:
            req_body = SensorData.map_sensor_payload(payload=task['payload'])

            status_code, res_body, errs = await reqs.post_req(
                session=client_session,
                url=APIRoutes.SENSOR_DATA,
                data=req_body
            )
            
        elif task['topic'] == Topics.SINK_DATA:
            req_body = SinkData.map_sink_payload(task['payload'])

            status_code, res_body, errs = await reqs.post_req(
                session=client_session,
                url=APIRoutes.SINK_DATA,
                data=req_body
            )

        elif task['topic'] == Topics.SENSOR_ALERT:
            req_body = SensorAlerts.map_sensor_alert(task['payload'])

            status_code, res_body, errs = await reqs.post_req(
                session=client_session,
                url=APIRoutes.SENSOR_ALERT,
                data=req_body
            )

        # _log.debug(req_body)

        if status_code == status.SUCCESS:
            pass

        else:

            if 'origin' not in list(task.keys()):
                task.update({'origin': alias})

            # if the origin of the task is taskmanager, override
            elif task['origin'] == Registry.Modules.TaskManager.alias:
                task.update({'origin': alias})

            task.update({
                    'status': status.FAILED,
                    'cause': [(name, msg, cause) for name, msg, cause in errs]
                })
            
            # return task to taskmanager queue as failed task
            # run in executor to not block thread
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as pool:

                if task['origin'] != Registry.Modules.LocalStorage.origin_unsynced:
                    loop.run_in_executor(
                        pool,
                        put_to_queue,
                        taskmanager_q,
                        __name__,
                        task
                    )

                if status_code == status.DISCONNECTED:

                    # trigger api check on sys_monitor if connection error is part of the cause
                    if aiohttp.ClientConnectorError.__name__ in [err[0] for err in errs]:
                        
                        # send trigger to taskamanager
                        trigger = {
                            'origin': alias,
                            'context': Registry.Triggers.contexts.API_CONNECTION_STATUS,
                            'data': {
                                'timestamp': (str(datetime.now())),
                                'status': status_code,
                                'errs': [(name, msg, cause) for name, msg, cause in errs],
                            }
                        }

                        loop.run_in_executor(
                            pool,
                            put_to_queue,
                            triggers_q,
                            __name__,
                            trigger
                        )

        t_result = {
            'task_data': task,
            'status_code': status_code,
            'errs': [(name, msg, cause) for name, msg, cause in errs]
        }

        return t_result

# processes unsynced data tassks from the LocalStorage module
# callback added to tasks with origin 'locstorage_unsynced'
async def _from_locstrg_unsynced(task: asyncio.Task, triggers_q: multiprocessing.Queue) -> bool:

    result = False
    loop = asyncio.get_running_loop()

    try:
        task_result = await task

        with ThreadPoolExecutor() as pool:
            trg = {
                'origin': alias,
                'context': Registry.Triggers.contexts.UNSYNCED_DATA,
                'data': {
                    'task_id': task_result['task_data']['task_id'],
                    'status_code': task_result['status_code'],
                    'errs': task_result['errs']
                }
            }

            loop.run_in_executor(
                pool,
                put_to_queue,
                triggers_q,
                __name__,
                trg
            )

            result = True

    except Exception as e:
        _log.error(
            f"Unhandled unexpected {type(e).__name__} "
            f"raised at {alias}.{_from_locstrg_unsynced.__name__}: "
            f"{str(e.__cause__) if e.__cause__ else str(e)}"
        )

    return result

# manages the priority queue for tasks
# buffers in between the router and the main loop
async def _task_buffer(
        queue: asyncio.PriorityQueue,
        semaphore: asyncio.Semaphore,
        client_session: aiohttp.ClientSession,
        taskmanager_q: multiprocessing.Queue,
        triggers_q: multiprocessing.Queue
        ):

    tasks: set[asyncio.Task] = set()
    synced_items = []

    loop = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(
            f"{alias.capitalize()}._task_buffer"
            f"is unable to get running event loop:"
            f"{str(e.__cause__) if e.__cause__ else str(e)}"
        )
        return

    try:
        while True:

            # this while loop is important to keep the queue sorted
            # and to keep items in the queue while all the semaphores are acquired
            while len(tasks) == APPConfigurations.GLOBAL_SEMAPHORE_COUNT:
                await asyncio.sleep(0.05)
            # NOTE / TODO ^: because this keeps the items in the queue while tasks are executing
            # this can be utilized to immediately re-route tasks to the task manager as failed tasks
            # before tasks attempt calls with the api, in the event that an api disconnect trigger is
            # raise from any of the tasks
            # NOTE: a caveat of this strategy is that items remaining in the queue might be lost if the
            # entire program is interrupted or shuts down

            priority, t_data = await queue.get()

            task = asyncio.create_task(
                _router(
                    semaphore=semaphore,
                    task=t_data,
                    client_session=client_session,
                    taskmanager_q=taskmanager_q,
                    triggers_q=triggers_q
                )
            )
            tasks.add(task)
            task.add_done_callback(tasks.discard)

            if t_data['origin'] == Registry.Modules.LocalStorage.origin_unsynced:
                task.add_done_callback(
                    lambda f: asyncio.create_task(
                        _from_locstrg_unsynced(f, triggers_q)
                    )
                )

            await asyncio.sleep(0.1)

    except (asyncio.CancelledError, KeyboardInterrupt):
        await asyncio.gather(*tasks)

# checks api health with the /health end point
# returns:
#       success if no problem
#       disconnected if connection cannot be established (status code == 0)
#       failed if (400 - 500, etc.)
async def api_check() -> Tuple[int, Dict | None, List[Tuple[str, str, str]]]:
    chk_stat: int = status.UNVERIFIED

    # acquire running event loop for the aiohttp client
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(
            f"{alias.capitalize()} failed to get running event loop:"
            f"{str(e)}"
        )

    # acquire an aiohttp.ClientSession object to work with requests module aiohttp framework
    client = None
    try:
        client = aiohttp.ClientSession()
    except Exception as e:
        _log.error(
            f"{alias.capitalize()} failed to create client session object: "
            f"{str(e)}"
        )
        chk_stat = status.UNVERIFIED

    if loop and client:
        stat, body, errs = await reqs.get_req(
            session=client,
            url=APIRoutes.HEALTH
        )

        # TODO: add other status
        if stat == 200:
            chk_stat = status.SUCCESS

        elif stat == 0:
            chk_stat = status.DISCONNECTED

        else:
            chk_stat = status.FAILED

        await client.close()

    return chk_stat, body, errs

# main loop, manages the lifecycle of ClientSession and does queue retrieval
async def start(
        httpclient_q: multiprocessing.Queue,
        taskmanager_q: multiprocessing.Queue,
        triggers_q: multiprocessing.Queue
        ) -> None:

    semaphore = asyncio.Semaphore(APPConfigurations.GLOBAL_SEMAPHORE_COUNT)

    # acquire the current running event loop
    # this is important to allow to run non-blocking message retrieval in the executor
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(f"Failed to acquire event loop ({type(e).__name__}): {str(e)}")
        return

    # acquire a aiohttp.ClientSession object
    # in order to allow non-blocking http requests to execute
    client = None
    try:
        client = aiohttp.ClientSession()
    except Exception as e:
        _log.error(
            f"{alias.capitalize()} failed to create client session object: "
            f"{str(e)}"
        )
        return

    if loop and client:
        priority_queue = asyncio.PriorityQueue()

        _router_kwargs = {
            'semaphore': semaphore,
            'client_session': client,
            'taskmanager_q': taskmanager_q,
            'triggers_q': triggers_q
        }

        t_buffer_task = asyncio.create_task(
            _task_buffer(priority_queue, **_router_kwargs)
        )

        try:
            with ThreadPoolExecutor() as pool:

                while True:
                    task = await loop.run_in_executor(
                        pool,
                        get_from_queue,
                        httpclient_q,
                        __name__
                    )
 
                    if task:
                        priority = 0.0
                        p_multiplier = 1

                        task['timestamp']
                        parsed_dt = datetime.strptime(task['timestamp'], "%Y-%m-%d %H:%M:%S.%f")
                        unix_t = parsed_dt.timestamp()

                        priority = unix_t * -p_multiplier

                        await priority_queue.put((priority, task))

                    await asyncio.sleep(0.1)

        except (asyncio.CancelledError, KeyboardInterrupt) as e:
            await asyncio.gather(t_buffer_task)
            await client.close()
            return