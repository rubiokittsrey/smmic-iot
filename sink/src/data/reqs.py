# README
# this is the api request module that should be used to make calls to the api
# its build around the aiohttp python library that allows for concurrent requests
# TODO: implement support for django websockets

# third-party
import aiohttp
import asyncio
import time
import logging
import os
from typing import Dict, Any, Callable, List, Tuple
from decimal import Decimal

# internal helpers, configs
from settings import APPConfigurations
from utils import log_config

_log = log_config(logging.getLogger(__name__))

# internal request decorator that provides request statistics and handles exception
# TODO: add other stats, store failed requests, implement failed request protocol
# returns the response status and the response body
def _req(func: Callable) -> Any:
    async def _wrapper(*args, **kwargs) -> Tuple[int, dict | None]:
        start = time.time()
        attempt = 0

        retries: int = kwargs.get('retries', APPConfigurations.NETWORK_MAX_TIMEOUT_RETRIES)

        res_stat: int = 0
        res_body: dict | None = None
        err: List[str] = []

        while attempt < retries:
            try:
                res_stat, res_body = await func(*args, **kwargs)
                end = time.time()
                break
                #return response
            except aiohttp.ClientConnectionError as e:
                await asyncio.sleep(3) # sleep for 3 secs (non-blocking) to allow connection to establish
                err.append(f"Exception {type(e).__name__} raised at requests.{func.__name__}: {str(e)}")
            except aiohttp.ClientResponseError as e:
                err.append(f"Exception {type(e).__name__} raised at requests.{func.__name__}: {str(e)}")
            except aiohttp.ClientError as e:
                err.append(f"Exception {type(e).__name__} raised at requests.{func.__name__}: {str(e)}")
            except Exception as e:
                err.append(f"Unhandled exception {type(e).__name__} raised at requests.{func.__name__}: {str(e)}")
            # except aiohttp.ClientTimeout as e:
            #     print(f"Timeout error occurred: {e}")

            attempt += 1

        end = time.time()

        # organize similar errors into one log
        if len(err) > 0:
            _logged: List[str] = []

            for e in err:
                if e in _logged:
                    pass
                else:
                    count = err.count(e)
                    _log.error((f"({count}) " if count > 1 else "") + e + " ")
                    _logged.append(e)

        # if err length == retries, request failed
        if len(err) == retries:
            _log.warning(f"Request statistics -> {func.__name__} took {end-start} seconds to finish (failed after {retries} attempts)")
        else:
            _log.debug(f"Request statistics -> {func.__name__} took {end-start} seconds to finish after {attempt + 1} attempts(s)")
        
        return res_stat, res_body
    
    return _wrapper

# TODO: create a unit test at api_test.py
@_req
async def get_req(
    session: aiohttp.ClientSession,
    url: str,
    data: Dict[str, Any] | None = None,
    retries: int | None = None,
    timeout: int = APPConfigurations.NETWORK_TIMEOUT) -> Any:

    async with session.get(url, json=data, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
        response.raise_for_status()
        #__log__.debug(f"Post request successful: {response.status} -> {await response.json()}")
        res_stat = response.status
        res_body = await response.json()
        return res_stat, res_body

# TODO: create a unit test at api_test.py
@_req
async def post_req(
    session: aiohttp.ClientSession,
    url: str,
    data: Dict[str, Any],
    retries: int | None = None,
    timeout: int = APPConfigurations.NETWORK_TIMEOUT) -> Tuple[int, dict]:

    async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
        response.raise_for_status()
        #__log__.debug(f"Post request successful: {response.status} -> {await response.json()}")
        res_stat = response.status
        res_body = await response.json()
        return res_stat, res_body

# TODO: create a unit test at api_test.py
@_req
async def put_req(
    session: aiohttp.ClientSession,
    url: str,
    data: Dict[str, Any],
    retries: int | None = None,
    timeout: int = APPConfigurations.NETWORK_TIMEOUT) -> Any:

    async with session.put(url, json=data, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
        response.raise_for_status()
        _log.debug(f"Put request successful: {response.status} -> {await response.json()}")
        return response

# TODO: create a unit test at api_test.py
@_req
async def patch_req(
        session: aiohttp.ClientSession,
        url: str,
        data: Dict[str, Any],
        retries: int | None = None,
        timeout: int = APPConfigurations.NETWORK_TIMEOUT) -> Any:
    
    async with session.patch(url, json=data, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
        response.raise_for_status()
        _log.debug(f"Patch request successful: {response.status} -> {await response.json()}")
        return response

# TODO: create a unit test at api_test.py
@_req
async def delete_req(
        session: aiohttp.ClientSession,
        url: str,
        data: Dict[str, Any],
        retries: int | None = None,
        timeout: int = APPConfigurations.NETWORK_TIMEOUT) -> Any:
    
    async with session.delete(url, json=data, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
        response.raise_for_status()
        _log.debug(f"Delete request successful: {response.status} -> {await response.json()}")
        return response