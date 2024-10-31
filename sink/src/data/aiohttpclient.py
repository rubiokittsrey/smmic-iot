"""
docs:
this is the aiohttp session module of the entire system
* hosts the aiohttp.ClientSession object
* acts as the router function for different messages received from the queue to the appropriate endpoints
* acts as the receiver for data from the api ### TODO: implement message handling to go to the 
# TODO: documentation
"""

alias = "aiohttp-client"

# third-party
import logging
import aiohttp
import asyncio
import time
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Any, Tuple, List

# internal core modules
import reqs

# internal helpers, configurations
from utils import log_config, SinkData, SensorData, get_from_queue, SensorAlerts, status, put_to_queue
from settings import APPConfigurations, Topics, APIRoutes, Broker

_log = log_config(logging.getLogger(__name__))

# TODO: documentation
# TODO: implement return request response status (i.e code, status literal, etc.)
async def _router(semaphore: asyncio.Semaphore, task: Dict, client_session: aiohttp.ClientSession, taskmanager_q: multiprocessing.Queue) -> Any:
    # NOTE:
    # ----- data keys -> {priorty, topic, payload, timestamp}
    # ----- (sensor alert) data keys -> {device_id, timestamp, alertCode}

    req_body = Dict | None

    if not client_session:
        _log.error(f"Error at {__name__}, client_session is empty!")
        return

    stat: int
    result: Any
    
    async with semaphore:

        if task['topic'] == '/dev/test':
            foo = 'foo'
        elif task['topic'] == Topics.SENSOR_DATA:
            req_body = SensorData.map_sensor_payload(payload=task['payload'])
            stat, result = await reqs.post_req(session=client_session, url=APIRoutes.SENSOR_DATA, data=req_body)
        elif task['topic'] == Topics.SINK_DATA:
            req_body = SinkData.map_sink_payload(task['payload'])
            stat, result = await reqs.post_req(session=client_session, url=APIRoutes.SINK_DATA, data=req_body)
        elif task['topic'] == Topics.SENSOR_ALERT:
            req_body = SensorAlerts.map_sensor_alert(task['payload'])
            stat, result = await reqs.post_req(session=client_session, url=APIRoutes.SENSOR_ALERT, data=req_body)

        if stat != status.SUCCESS:
            task.update({'status': status.FAILED, 'origin': alias, 'cause': result})

            # dont block thread
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as pool:
                loop.run_in_executor(pool, put_to_queue, taskmanager_q, __name__, task)

                # trigger api check on sys_monitor if cause is connect err
                try:
                    if aiohttp.ClientConnectorError.__name__ in list(result):
                        # send signal to taskamanager
                        loop.run_in_executor(pool, put_to_queue, taskmanager_q, __name__, {'api_disconnect': True})
                except TypeError as e:
                    _log.error(f"Request returned with failure but result is not a list of errors: {str(result)}")

        return

# checks api health with the /health end point
# returns:
# success if no problem
# disconnected if connection cannot be established (status code == 0)
# failed if (400 - 500, etc.)
async def api_check() -> int:
    result: int = status.UNVERIFIED

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
        result = status.UNVERIFIED

    if loop and client:
        stat, res_body = await reqs.get_req(session=client, url=APIRoutes.HEALTH)

        # TODO: add other status
        if stat == 200:
            result = status.SUCCESS
        elif stat == 0:
            result = status.DISCONNECTED
        else:
            result = status.FAILED

        await client.close()

    return result

# TODO: documentation
_API_STATUS : int = status.DISCONNECTED
async def start(aiohttpclient_q: multiprocessing.Queue, taskmanager_q: multiprocessing.Queue) -> None:
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
                    task = await loop.run_in_executor(pool, get_from_queue, aiohttpclient_q, __name__) # non-blocking message retrieval

                    # if an item is retrieved
                    if task:
                        asyncio.create_task(_router(semaphore, task, client, taskmanager_q))

                    await asyncio.sleep(0.1)

        except (asyncio.CancelledError, KeyboardInterrupt):
            # close the aiohttp session client
            await client.close()