# third-party
import logging
import multiprocessing
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Tuple

# internal helpers, configs
from settings import Topics, Registry, APPConfigurations
from utils import logger_config

# configs, settings
_log = logger_config(logging.getLogger(__name__))
alias = Registry.Modules.telemetrymanager

# def _init_se_conf_yaml():
#     conf_path = os.path.join(os.path.dirname(__file__), '../../sensor_confs.yaml')
#     with open(conf_path, 'r') as conf_file:
#         _conf_yaml = 

async def start(
        taskmanager_q: multiprocessing.Queue,
        triggers_q: multiprocessing.Queue,
        telemetrymanager_q: multiprocessing.Queue
        ) -> None:

    semaphore = asyncio.Semaphore(APPConfigurations.GLOBAL_SEMAPHORE_COUNT)

    # first, load the interval configuration from sensor_conf.yaml file

    # acquire loop abstraact loop obj
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError as e:
        _log.error(f"Failed to get running event loop: {e}")
        return

    if loop:
        _log.info(f"{alias} submodule coroutine active")

    

    # run while loop
    # initially, trigger sensor telemetry


    pass