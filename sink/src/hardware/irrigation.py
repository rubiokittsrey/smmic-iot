# TODO: add documentation

# third-party
import logging
import asyncio
import os
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from typing import List, Any, Dict
from blinker import Signal

# internal helpers, configurations
from utils import log_config, get_from_queue, is_num

__log__ = log_config(logging.getLogger(__name__))
__irrigation_queue__ : List[str] = []

SIGNAL : Signal = Signal()

# helper funciton to map a payload from the 'smmic/irrigation' topic into a list
# assuming that the payload (as a string) is:
# -----
# device_id;
# timestamp;
# signal
# -----
def map_irrigation_payload(payload: str) -> Dict | None:
    final: Dict | None = None
    
    split: List[str] = payload.split(";")
    
    _num_check = is_num([split[2]])

    if not _num_check:
        __log__.warning(f"{__name__}.map_irrigation_payload: 'signal' value of assumed irrigation payload is not num! ({str(type(split[2]))})")
    else:
        final = {
            'device_id': split[0],
            'timestamp': split[1],
            'signal': split[2]
        }

    return final

# watches the irrigation asyncio queue and puts items into the __irrigation_queue__ list
async def __watcher__(loop: asyncio.AbstractEventLoop, queue: multiprocessing.Queue):
    global __irrigation_queue__
    while True:
        # _t shape:
        # [
        #  'signal' (1 for requires irrigation, 0 if not),
        #  'device_id' (sensor device unique identifier)
        #  'timestamp' (timestamp)
        # ]
        _t : Dict | None = get_from_queue(queue, __name__)

        if _t:
            __log__.debug(f"{__name__}.__watcher__() at PID {os.getpid()} received task from queue")

            if _t['signal'] == 1:
                __irrigation_queue__.append(_t[1])
                __log__.debug(f"Irrigation queue: {__irrigation_queue__}")
            else:
                __log__.debug(f"Irrigation queue: {__irrigation_queue__}")
                __irrigation_queue__.remove(_t[1])
        
        await asyncio.sleep(0.05)
            
async def start(irr_queue: multiprocessing.Queue) -> None:
    global __irrigation_queue__
    SIGNAL.send(1)

    # get the event loop
    loop : asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.get_event_loop()
    except Exception as e:
        __log__.error(f"Failed to get event loop @ PID {os.getpid()} (irrigation submodule coroutine): {e}")
        return
    
    if loop:
        __log__.info(f"Irrigation submodule active @ PID {os.getpid()}")

        asyncio.create_task(__watcher__(loop, irr_queue))
        try:
            for i in range(2):
                with ThreadPoolExecutor() as pool:
                    while len(__irrigation_queue__) > 0:
                        # TODO: code to turn on water pump here
                        await asyncio.sleep(0.05)
                    await asyncio.sleep(30)
            SIGNAL.send(0)
        except KeyboardInterrupt or asyncio.CancelledError:
            raise
        except Exception as e:
            __log__.error(f"Unhandled exception raised at {__name__} module: {e}")