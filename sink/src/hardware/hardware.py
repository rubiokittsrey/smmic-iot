# the main hardware module of the system
# TODO: documentation
#
#

# third-party
import asyncio
import multiprocessing
import logging
import os
from typing import Dict, Any, List, Callable
from concurrent.futures import ThreadPoolExecutor

# internal helpers, configurations
from utils import (
    logger_config,
    get_from_queue
)
from settings import (
    Topics,
    APPConfigurations,
    Broker,
    Registry
)

if not APPConfigurations.DISABLE_IRRIGATION:
    import src.hardware.irrigation as irrigation

# configurations, settings
alias = Registry.Modules.Hardware.alias
_log = logger_config(logging.getLogger(alias))

# hardware workers queues
_IRRIGATION_QUEUE: multiprocessing.Queue = multiprocessing.Queue()

# hardware tasks callbacks
def irrigation_callback(signal : int) -> None:
    global __IRRIGATION_SIGNAL__
    __IRRIGATION_SIGNAL__ = signal

# lazy implementation, straight to irrigation module
# TODO: rework this when there are more hardware tasks added to project
async def _delegator(semaphore: asyncio.Semaphore, task: Dict) -> Any:

    async with semaphore:
        task_keys : List = list(task.keys())

        if 'disconnected' in task_keys:
            _IRRIGATION_QUEUE.put(task)

        if 'topic' in task_keys:
            task_payload = irrigation.map_irrigation_payload(task['payload'])
            if task_payload:
                _IRRIGATION_QUEUE.put(task_payload)

# begin the hardware module process
async def start(
        hardware_q: multiprocessing.Queue,
        taskmanager_q: multiprocessing.Queue
        ) -> None:
    
    semaphore = asyncio.Semaphore(APPConfigurations.GLOBAL_SEMAPHORE_COUNT)
    
    # acquire the current running event loop
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _log.error(
            f"{alias.capitalize()} failed to acquire running event loop: "
            f"{str(e.__cause__) if (e.__cause__) else str(e)}"
        )
        return

    if loop:
        _log.info(f"{alias.capitalize()} subprocess active")

        try:
            try:
                asyncio.create_task(irrigation.start(_IRRIGATION_QUEUE))
            
            except NameError as e:
                _log.info(f'{alias.capitalize()} starting with irrigation module disabled')
            
            with ThreadPoolExecutor() as pool:
                while True:
                    task = await loop.run_in_executor(
                        pool,
                        get_from_queue,
                        hardware_q,
                        __name__
                    )
                    
                    if task:
                        try:
                            if (task['topic'].count('irrigation') > 0
                                    and APPConfigurations.DISABLE_IRRIGATION):
                                continue
                        
                        # NOTE: this could present problmes in the future
                        # if something fucks up, theres a good chance its here
                        except KeyError:
                            pass
                        
                        asyncio.create_task(_delegator(semaphore, task))

        except (asyncio.CancelledError, KeyboardInterrupt):
            pass

        except Exception as e:
            _log.error(
                f"Unhandled exception raised at {alias.capitalize()}:"
                f"{str(e)}"
            )