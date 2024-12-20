# data module unit tests

# third-party
import argparse
import sys
import logging
import time
import os
import aiohttp
import asyncio
from typing import List, Any
from datetime import datetime

# internal
try:
    sys.path.append('mnt/d/projects/smmic-iot/sink/common')
except Exception as e:
    print(f"Exception raised: {e}")
    os._exit(0)

import settings
sys.path.append(settings.APPConfigurations.SRC_PATH)
import requests as requests
from utils import Modes, logger_config, status

__log__ = logger_config(logging.getLogger(__name__))

async def api_test_req(url: str, data: dict) -> Any:
    res: Any = None
    try:
        session = aiohttp.ClientSession()
        res = await getattr(requests, api_req_funcs[i][0])(session=session, url = url, data = data)
    except Exception as e:
        __log__.error(f"Error raised: {str(e)}")
    finally:
        await session.close()
    return res

if __name__ == "__main__":
    Modes.dev()

    parser = argparse.ArgumentParser(description="SMMIC data module unit tests")
    subparser = parser.add_subparsers(dest="submodule")

    # requests submodule parsers
    parser_api = subparser.add_parser("requests", help="Test the api_requests submodule")

    # requests subparser parsers
    api_subparser = parser_api.add_subparsers(dest="function")
    api_req_funcs : List[List[str]]  = [
        ["get_req", "Send a get request to the api"],
        ["post_req", "Send a post request to the api"],
        ["put_req", "Send a put request to the api"],
        ["patch_req", "Send a patch request to the api"],
        ["delete_req", "Send a delete request to the api"]
    ]

    for f in api_req_funcs:
        api_subparser.add_parser(f[0], help=f[1])

    args = parser.parse_args()

    if not args.submodule:
        parser.print_help()
        parser_api.print_help()

    elif args.submodule == "requests":
        # TODO: implement try - exception
        loop = asyncio.new_event_loop()
        data = {
            'SensorType' : 'soil_moisture',
            'Sensor_Node' : 'fd7b1df2-3822-425c-b4c3-e9859251728d', # id
            'timestamp' : str(datetime.now()),
            'soil_moisture' : 100,
            'humidity' : 100,
            'temperature' : 100,
            'battery_level' : 100
        }
        url = f"{settings.APIRoutes.BASE_URL}{settings.APIRoutes.SENSOR_DATA}"

        for i in range(len(api_req_funcs)):
            
            if args.function == api_req_funcs[i][0]:
                loop.run_until_complete(api_test_req(url, data))