"""
docs:
this is the aiohttp session module of the entire system
* hosts the aiohttp.ClientSession object
* acts as the router function for different messages received from the queue to the appropriate endpoints
* acts as the receiver for data from the api ### TODO: implement message handling to go to the 
# TODO: documentation
"""

alias = "http-client"

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
from utils import log_config, SinkData, SensorData, get_from_queue, SensorAlerts, status, put_to_queue
from settings import APPConfigurations, Topics, APIRoutes, Broker

_log = log_config(logging.getLogger(__name__))

# TODO: documentation
# TODO: implement return request response status (i.e code, status literal, etc.)
async def _router(semaphore: asyncio.Semaphore,
                  task: Dict,
                  client_session: aiohttp.ClientSession,
                  taskmanager_q: multiprocessing.Queue,
                  triggers_q: multiprocessing.Queue
                  ) -> Any:
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
            status_code, res_body, errs = await reqs.post_req(session=client_session, url=APIRoutes.SENSOR_DATA, data=req_body)
        elif task['topic'] == Topics.SINK_DATA:
            req_body = SinkData.map_sink_payload(task['payload'])
            status_code, res_body, errs = await reqs.post_req(session=client_session, url=APIRoutes.SINK_DATA, data=req_body)
        elif task['topic'] == Topics.SENSOR_ALERT:
            req_body = SensorAlerts.map_sensor_alert(task['payload'])
            status_code, res_body, errs = await reqs.post_req(session=client_session, url=APIRoutes.SENSOR_ALERT, data=req_body)

        if status_code == status.SUCCESS:
            pass
        else:
            task.update({
                    'status': status.FAILED,
                    'origin': alias,
                    'cause': [{'err_name': name, 'err_msg': msg, 'err_cause': cause} for name, msg, cause in errs]
                })
            # return task to taskmanager queue as failed task
            # run in executor to not block thread
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as pool:
                loop.run_in_executor(pool, put_to_queue, taskmanager_q, __name__, task)
                if status_code == status.DISCONNECTED:
                    # trigger api check on sys_monitor if connection error is part of the cause
                    if aiohttp.ClientConnectorError.__name__ in [err[0] for err in errs]:
                        # send trigger to taskamanager
                        trigger = {
                            'origin': alias,
                            'context': 'api-connection-status',
                            'data': {
                                'timestamp': datetime.now(),
                                'status': status_code,
                                'errs': [{'err_name': name, 'err_msg': msg, 'err_cause': cause} for name, msg, cause in errs],
                            }
                        }
                        loop.run_in_executor(pool, put_to_queue, triggers_q, __name__, trigger)

        return

# checks api health with the /health end point
# returns:
# success if no problem
# disconnected if connection cannot be established (status code == 0)
# failed if (400 - 500, etc.)
async def api_check() -> Tuple[int, Dict | None, List[Tuple[str, str, str]]]:
    chk_stat: int = status.UNVERIFIED

    # acquire running event loop for the aiohttp client
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(f"Failed to get running event loop ({__name__} at PID {os.getpid()}): {str(e)}")

    # acquire an aiohttp.ClientSession object to work with requests module aiohttp framework
    client: aiohttp.ClientSession | None = None
    try:
        client = aiohttp.ClientSession()
    except Exception as e:
        _log.error(f"Failed to create client session object ({__name__} at {os.getpid()}): {str(e)}")
        chk_stat = status.UNVERIFIED

    if loop and client:
        stat, body, errs = await reqs.get_req(session=client, url=APIRoutes.HEALTH)

        # TODO: add other status
        if stat == 200:
            chk_stat = status.SUCCESS
        elif stat == 0:
            chk_stat = status.DISCONNECTED
        else:
            chk_stat = status.FAILED

        await client.close()

    return chk_stat, body, errs

# TODO: documentation
_API_STATUS : int = status.DISCONNECTED
async def start(httpclient_q: multiprocessing.Queue, taskmanager_q: multiprocessing.Queue, triggers_q: multiprocessing.Queue) -> None:
    semaphore = asyncio.Semaphore(APPConfigurations.GLOBAL_SEMAPHORE_COUNT)

    # acquire the current running event loop
    # this is important to allow to run non-blocking message retrieval in the executor
    loop: asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(f"Failed to acquire event loop (exception: {type(e).__name__}): {str(e)}")
        return
    
    # acquire a aiohttp.ClientSession object
    # in order to allow non-blocking http requests to execute
    client: aiohttp.ClientSession | None = None
    try:
        client = aiohttp.ClientSession()
    except Exception as e:
        _log.error(f"{alias} failed to create client session object: {str(e)}")
        return

    if loop and client:
        _log.info(f"{alias} subprocess active at PID {os.getpid()}".capitalize())

        try:
            with ThreadPoolExecutor() as pool:
                while True:
                    task = await loop.run_in_executor(pool, get_from_queue, httpclient_q, __name__) # non-blocking message retrieval

                    # if an item is retrieved
                    if task:
                        asyncio.create_task(_router(semaphore, task, client, taskmanager_q, triggers_q))

                    await asyncio.sleep(0.1)

        except (asyncio.CancelledError, KeyboardInterrupt):
            # close the aiohttp session client
            await client.close()