# third party
import requests
import time
import logging
from requests.exceptions import HTTPError, Timeout
from typing import Dict, Any, Callable
from decimal import Decimal

# internal helper modules, configs
from settings import APIRoutes
from utils import log_config

__log__ = log_config(logging.getLogger(__name__))

reading_to_api_url = f"{APIRoutes.BASE_URL}/createSNreadings/"

test_data = {
    'Sensor_Node' : 'fd7b1df2-3822-425c-b4c3-e9859251728d',
    'soil_moisture' : 75,
    'humidity' : 68,
    'temperature' : 24,
    'battery_level' : 98
}

# task statistics decorator
def __stats__(func: Callable):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()

        __log__.debug(f"Request statistics -> {func.__name__} took {end - start} seconds to execute")

        return result
    
    return wrapper

@__stats__
def testReadingToApi(data: Dict[str, Any]):
    response = requests.post(reading_to_api_url, json=data)

    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"failed: {response.json()}")


if __name__ == "__main__":
    testReadingToApi(test_data)