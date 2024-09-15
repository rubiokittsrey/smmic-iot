# README
# this is the api request module that should be used to make calls to the api
# TODO: implement support for django websockets

# third-party
import aiohttp
import time
import logging
import os
from typing import Dict, Any, Callable
from decimal import Decimal

# internal helpers, configs
from settings import APIRoutes, APPConfigurations
from utils import log_config

__log__ = log_config(logging.getLogger(__name__))

# request decorator that provides request statistics and handles exception
# TODO: add other stats, store failed requests, implement failed request protocol
def __req__(func: Callable) -> Any:
    async def _wrapper(*args, **kwargs) -> Any:
        start = time.time()
        attempt = 0

        retries: int = kwargs.get('retries', APPConfigurations.NETWORK_MAX_TIMEOUT_RETRIES)

        response: Any

        while attempt < retries:
            try:
                response = await func(*args, **kwargs)
                end = time.time()
                __log__.debug(f"Request statistics -> {func.__name__} took {end-start} seconds to finish after {attempt + 1} attempts(s)")
                return response
            except aiohttp.ClientConnectionError as e:
                __log__.error(f"aiohttp.ClientConnectionError raised at requests.{func.__name__}: {str(e)}")
            except aiohttp.ClientResponseError as e:
                __log__.error(f"aiohttp.ClientResponseError raised at requests.{func.__name__}: {str(e)}")
            # except aiohttp.ClientTimeout as e:
            #     print(f"Timeout error occurred: {e}")
            except aiohttp.ClientError as e:
                __log__.error(f"aiohttp.ClientError raised at requests.{func.__name__}: {str(e)}")
            except Exception as e:
                # Catch any other exceptions
                __log__.error(f"Unhandled exception raised at requests.{func.__name__}: {str(e)}")

            attempt += 1
            __log__.debug(f"Retrying request... attempt: {attempt}")

        __log__.error(f"Request failed at requests.{func.__name__}: max attempts reached")

        end = time.time()
        __log__.debug(f"Request statistics -> {func.__name__} took {end-start} seconds to finish (failed)")
        return None
    
    return _wrapper

# TODO: create a unit test at api_test.py
@__req__
async def get_req(
    session: aiohttp.ClientSession,
    url: str,
    data: Dict[str, Any] | None,
    retries: int | None = None,
    timeout: int = APPConfigurations.NETWORK_TIMEOUT) -> Any:

    async with session.get(url, json=data, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
        response.raise_for_status()
        __log__.debug(f"Get request successful: {response.status} -> {await response.json()}")
        return response

@__req__
async def post_req(
    session: aiohttp.ClientSession,
    url: str,
    data: Dict[str, Any],
    retries: int | None = None,
    timeout: int = APPConfigurations.NETWORK_TIMEOUT) -> Any:

    async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
        response.raise_for_status()
        __log__.debug(f"Post request successful: {response.status} -> {await response.json()}")
        return response