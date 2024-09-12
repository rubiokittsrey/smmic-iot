# third-party
import requests
import time
import logging
from requests.exceptions import HTTPError, Timeout
from typing import Dict, Any, Callable
from decimal import Decimal

# internal helpers, configs
from settings import APIRoutes, APPConfigurations
from utils import log_config

__log__ = log_config(logging.getLogger(__name__))

# send request decorator that provides request statistics
# and handles exceptions
# TODO: add other stats
# TODO: store failed requests
def __req__(func: Callable):
    def _wrapper(*args, **kwargs):
        start = time.time()
        attempt = 0

        retries = kwargs.get('retries', APPConfigurations.NETWORK_MAX_TIMEOUT_RETRIES)
        timeout = kwargs.get('timeout', APPConfigurations.NETWORK_TIMEOUT)
        
        response: requests.Response

        while attempt < retries:
            try:
                response = func(*args, **kwargs)
                end = time.time()
                __log__.debug(f"Request statistics -> {func.__name__} took {end-start} seconds to finish after {attempt + 1} attempt(s)")
                return response
            except HTTPError as http_err:
                __log__.error(f"HTTP error raised at api.{func.__name__}: {http_err}")

            except Timeout as timeout_err:
                __log__.error(f"Request timed out at api.{func.__name__}: {timeout_err}")
            
            except Exception as err:
                __log__.error(f"Error raised at api.{func.__name__}: {err}")

            attempt += 1
            __log__.debug(f"Retrying request... attempt: {attempt}")

        __log__.error(f"Max attempts reached, request failed at api.{func.__name__}")

        end = time.time()
        __log__.debug(f"Request statistics -> {func.__name__} took {end-start} seconds to finish (failed)")
        return None
    
    return _wrapper

# TODO: add the unit test at api_test.py
@__req__
def get_req(url: str, data: Dict[str, Any] | None, retries: int = APPConfigurations.NETWORK_MAX_TIMEOUT_RETRIES, timeout: int = APPConfigurations.NETWORK_TIMEOUT) -> requests.Response:
    response = requests.get(url, json=data, timeout=timeout)
    response.raise_for_status()
    __log__.debug(f"Get request successful: {response.status_code} -> {response.json()}")
    return response

@__req__
def post_req(url: str, data: Dict[str, Any], retries: int = APPConfigurations.NETWORK_MAX_TIMEOUT_RETRIES, timeout: int = APPConfigurations.NETWORK_TIMEOUT) -> requests.Response:
    response = requests.post(url, json=data, timeout=timeout)
    response.raise_for_status()
    __log__.debug(f"Post request successful: {response.status_code}")
    return response

# TODO: add the unit test at api_test.py
@__req__
def put_req(url: str, data: Dict[str, Any], retries: int = APPConfigurations.NETWORK_MAX_TIMEOUT_RETRIES, timeout: int = APPConfigurations.NETWORK_TIMEOUT) -> requests.Response:
    response = requests.put(url, json=data, timeout=timeout)
    response.raise_for_status()
    __log__.debug(f"Put request successful: {response.status_code}")
    return response

# TODO: add the unit test at api_test.py
@__req__
def patch_req(url: str, data: Dict[str, Any], retries: int = APPConfigurations.NETWORK_MAX_TIMEOUT_RETRIES, timeout: int = APPConfigurations.NETWORK_TIMEOUT) -> requests.Response:
    response = requests.patch(url, json=data, timeout=timeout)
    response.raise_for_status()
    __log__.debug(f"Patch request successful: {response.status_code} -> {response.json()}")
    return response

# TODO: add the unit test at api_test.py
@__req__
def delete_req(url: str, data: Dict[str, Any], retries: int = APPConfigurations.NETWORK_MAX_TIMEOUT_RETRIES, timeout: int = APPConfigurations.NETWORK_TIMEOUT) -> requests.Response:
    response = requests.delete(url, json=data, timeout=timeout)
    response.raise_for_status()
    __log__.debug(f"Delete request successful: {response.status_code}")
    return response