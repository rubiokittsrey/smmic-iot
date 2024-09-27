# the main hardware module of the system
# TODO: documentation

# third-party
import asyncio
import multiprocessing
import logging
import os
from concurrent.futures import ThreadPoolExecutor

# internal helpers, configurations
from utils import log_config
from settings import Topics, APPConfigurations

__log__ = log_config(logging.getLogger(__name__))

async def start(queue: multiprocessing.Queue) -> None:
    semaphore = asyncio.Semaphore(APPConfigurations.GLOBAL_SEMAPHORE_COUNT)

    # acquire the current running event loop
    loop: asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        __log__.error(f"Failed to get running event loop @ PID {os.getpid()} (hardware module child process): {e}")
        return
    
    if loop:
        __log__.info(f"Hardware module process active @ PID {os.getpid()}")
        try:
            with ThreadPoolExecutor() as pool:
                while True:
                    pass
                    # item = await loop.run_in_executor(pool, __from_queue__, queue)
        except KeyboardInterrupt:
            raise