# the main hardware module of the system
# TODO: documentation

# third-party
import asyncio
import multiprocessing
import logging
import os
from typing import Dict, Any, List, Callable
from concurrent.futures import ThreadPoolExecutor

# internal helpers, configurations
from utils import log_config, get_from_queue
from settings import Topics, APPConfigurations, Broker
if not APPConfigurations.DISABLE_IRRIGATION:
    import src.hardware.irrigation as irrigation

__log__ = log_config(logging.getLogger(__name__))

__IRRIGATION_QUEUE__: multiprocessing.Queue = multiprocessing.Queue()

# hardware tasks callbacks
def irrigation_callback(signal : int) -> None:
    global __IRRIGATION_SIGNAL__
    __IRRIGATION_SIGNAL__ = signal

async def __delegator__(semaphore: asyncio.Semaphore, task: Dict) -> Any:
    async with semaphore:

        if task['topic'] == f"{Broker.ROOT_TOPIC}{Topics.IRRIGATION}":
            task_payload = irrigation.map_irrigation_payload(task['payload'])
            if task_payload:
                __IRRIGATION_QUEUE__.put(task_payload)

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
            asyncio.create_task(irrigation.start(__IRRIGATION_QUEUE__))
            with ThreadPoolExecutor() as pool:
                while True:
                    task = await loop.run_in_executor(pool, get_from_queue, queue, __name__)
                    if task:
                        __log__.debug(f"Module {__name__} at PID {os.getpid()} received message from queue (topic: {task['topic']})")
                        asyncio.create_task(__delegator__(semaphore, task))
        except KeyboardInterrupt:
            raise
        except Exception as e:
            __log__.error(f"Unhandled exception raised @ PID {os.getpid()} ({__name__}): {str(e)}")