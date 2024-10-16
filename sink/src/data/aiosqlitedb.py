# TODO: documentation
#
#

# third-party
import aiosqlite
import asyncio
import logging
import os
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from typing import Any

# internal helpers, configurations
from settings import APPConfigurations
from utils import log_config, get_from_queue

_logs = log_config(logging.getLogger(__name__))

async def _delegator(semaphore: asyncio.Semaphore, data: Any):
    # TODO: implement delegator
    _logs.debug(f"{__name__} received data: {data}")
    pass

async def start(queue: multiprocessing.Queue) -> None:
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _logs.error(f"Unable to get running event loop at PID {os.getpid()} ({__name__}): {str(e)}")

    if not loop:
        return
    
    semaphore = asyncio.Semaphore(APPConfigurations.GLOBAL_SEMAPHORE_COUNT)
    _logs.info(f"{__name__} coroutine active at PID {os.getpid()}")
    try:
        with ThreadPoolExecutor() as pool:
            while True:
                data = await loop.run_in_executor(pool, get_from_queue, queue, __name__)
                if data:
                    asyncio.create_task(_delegator(semaphore, data))
                await asyncio.sleep(0.05)
    except (asyncio.CancelledError, KeyboardInterrupt):
        raise