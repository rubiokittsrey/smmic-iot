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
from typing import Dict, Any, Callable, List, Tuple, Any
from decimal import Decimal

# internal helpers, configs
from settings import APPConfigurations, Registry
from utils import logger_config, status

# settings, configuration
alias = Registry.Modules.Requests.alias
_log = logger_config(logging.getLogger(__name__))

# internal request decorator that provides request statistics and handles exception
# TODO: add other stats, store failed requests, implement failed request protocol
# returns the response status and the response body
def _req_decorator(func: Callable) -> Any:
    async def _wrapper(*args, **kwargs) -> Tuple[int, Dict[str, Any] | None, List[Tuple[str, str, str]]]:
        start = time.time()
        attempt = 0

        retries: int = kwargs.get('retries', APPConfigurations.NETWORK_MAX_TIMEOUT_RETRIES)

        status: int = 0
        body: Any | None = None
        err_logs: List[str] = []
        errs : List[Tuple[str, str, str]] = [] # Tuple[err_name, err_msg, err_cause (if provided)]

        while attempt < retries:

            try:
                status, body = await func(*args, **kwargs)
                end = time.time()
                break
                #return response

            except (aiohttp.ClientConnectorError, aiohttp.ClientResponseError, aiohttp.ClientError, aiohttp.ClientConnectionError) as e:
                err_msg = e.__cause__

                # connection error handling
                if type(e) in [aiohttp.ClientConnectorError, aiohttp.ClientConnectionError]:
                    await asyncio.sleep(3) # sleep for 3 secs (non-blocking) to allow connection to establish
                    status = 0

                # response error handling
                elif type(e) == aiohttp.ClientResponseError:
                    status = e.status
                    err_msg = e.message

                # logging logic
                err_logs.append(f"Exception {type(e).__name__} raised at {__name__}.{func.__name__}: {str(err_msg) if err_msg else str(e)}")
                errs.append((type(e).__name__, str(e), f"{str(err_msg) if err_msg else ''}"))

                if type(e) == aiohttp.ClientResponseError:
                    break

            except Exception as e:
                err_logs.append(f"Unhandled exception {type(e).__name__} raised at {__name__}.{func.__name__}: {str(e.__cause__)}")
            # except aiohttp.ClientTimeout as e:
            #     print(f"Timeout error occurred: {e}")

            attempt += 1

        end = time.time()

        # organize similar errors into one log
        if len(err_logs) > 0:
            logged: List[str] = []

            for e in err_logs:
                if e in logged:
                    pass
                else:
                    count = err_logs.count(e)
                    _log.error((f"({count}) " if count > 1 else "") + e + " ")
                    logged.append(e)

        # if err length == retries, request failed
        # put err names into the list and assign to result
        if len(err_logs) == retries or 'ClientResponseError' in [name for name, msg, cause in errs]:
            _log.warning(f"Request statistics -> {func.__name__} took {end-start} seconds to finish (failed after {attempt + 1} attempt(s))")
        else:
            _log.debug(f"Request statistics -> {func.__name__} took {end-start} seconds to finish after {attempt + 1} attempts(s)")

        return status, body, errs
    
    return _wrapper

# TODO: create a unit test at api_test.py
@_req_decorator
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
@_req_decorator
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
@_req_decorator
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
@_req_decorator
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
@_req_decorator
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
