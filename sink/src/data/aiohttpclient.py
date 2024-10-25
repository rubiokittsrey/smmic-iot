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
from typing import Callable, Dict, Any

# internal core modules
import reqs as reqs

# internal helpers, configurations
from utils import log_config, SinkData, SensorData, get_from_queue, SensorAlerts, status, put_to_queue
from settings import APPConfigurations, Topics, APIRoutes, Broker

_log = log_config(logging.getLogger(__name__))

# TODO: documentation
# TODO: implement return request response status (i.e code, status literal, etc.)
async def _router(semaphore: asyncio.Semaphore, data: Dict, client_session: aiohttp.ClientSession) -> Any:
    # NOTE:
    # ----- data keys -> {priorty, topic, payload, timestamp}
    # ----- (sensor alert) data keys -> {device_id, timestamp, alertCode}

    req_body = Dict | None

    if not client_session:
        _log.error("Error at %s, client_session is empty!", __name__)
        return

    stat: int
    res_body: Any
    async with semaphore:
        if data['topic'] == '/dev/test':
            foo = 'foo'

        if data['topic'] == Topics.SENSOR_DATA:
            req_body = SensorData.map_sensor_payload(payload=data['payload'], no_payload=True)
            stat, res_body = await reqs.post_req(session=client_session, url=APIRoutes.SENSOR_DATA, data=req_body)

        if data['topic'] == Topics.SINK_DATA:
            req_body = SinkData.map_sink_payload(data['payload'])
            stat, res_body = await reqs.post_req(session=client_session, url=APIRoutes.SINK_DATA, data=req_body)

        if data['topic'] == Topics.SENSOR_ALERT:
            req_body = SensorAlerts.map_sensor_alert(data['payload'])

            if req_body:
                stat, res_body = await reqs.post_req(session=client_session, url=APIRoutes.SENSOR_ALERT, data=req_body)


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
async def start(aiohttpclient_q: multiprocessing.Queue, taskmanager_q: multiprocessing.Queue, api_init_status: int) -> None:
    semaphore = asyncio.Semaphore(APPConfigurations.GLOBAL_SEMAPHORE_COUNT)

    # acquire the current running event loop
    # this is important to allow to run non-blocking message retrieval in the executor
    loop: asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(f"Failed to acquire event loop (exception: {type(e).__name__}): {str(e)}")
        return

    # init api connection status
    global _API_STATUS
    if api_init_status == status.SUCCESS:
        _API_STATUS = status.CONNECTED
    else:
        _API_STATUS = status.DISCONNECTED

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

        check_running = False # flag if api check is currently running
        try:
            with ThreadPoolExecutor() as pool:
                while True:
                    item = await loop.run_in_executor(pool, get_from_queue, aiohttpclient_q, __name__) # non-blocking message retrieval

                    # periodic api_check
                    # if _API_STATUS != status.CONNECTED and not check_running:
                    #     check_res = await loop.run_in_executor(pool, api_check)
                    #     check_running = True
                    #     _API_STATUS = status.CONNECTED if check_res == status.SUCCESS else status.DISCONNECTED

                    # if an item is retrieved
                    if item:
                        if _API_STATUS == status.CONNECTED:
                            #_log.debug(f"aioHTTPClient @ PID {os.getpid()} received message from queue (topic: {item['topic']})")
                            asyncio.create_task(_router(semaphore, item, client))
                        else:
                            item.update({'failed': True})
                            # TODO: implement task storing and append results
                            result = loop.run_in_executor(pool, put_to_queue, taskmanager_q, __name__, item)

                    await asyncio.sleep(0.1)

        except (asyncio.CancelledError, KeyboardInterrupt):
            # close the aiohttp session client
            await client.close()