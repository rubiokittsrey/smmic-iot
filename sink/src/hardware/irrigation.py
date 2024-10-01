# TODO: add documentation

# third-party
import logging
import asyncio
import os
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from typing import List, Any, Dict
import RPi.GPIO as GPIO
import time

# internal helpers, configurations
from utils import log_config, get_from_queue, is_num
from settings import Channels

__log__ = log_config(logging.getLogger(__name__))

# the global irritaion queue dictionary
__QUEUE__ : Dict[str, float] = {}
# specifies how long to wait for the 'off' signal from the sensors before turning removing the id from the __QUEUE__ list
__OFF_SIGNAL_TOLERANCE__ : float = 60
__CHANNEL__ = Channels.IRRIGATION

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
    
    num_check = is_num(split[2])

    if not num_check:
        __log__.warning(f"{__name__}.map_irrigation_payload: 'signal' value of assumed irrigation payload is not num! ({str(type(split[2]))})")
    else:
        final = {
            'device_id': split[0],
            'timestamp': split[1],
            'signal': num_check(split[2])
        }

    return final

# async def __watcher__(loop: asyncio.AbstractEventLoop, queue: multiprocessing.Queue) -> None:
#     global __QUEUE__
#     while True:
#         task : Dict | None = get_from_queue(queue, __name__)

#         if task:
#             __log__.debug(f"{__name__}.__watcher__() at PID {os.getpid()} received task from queue")
#             device_id = task['device_id']
#             _expire = time.time() + 60 # 1 minute tolerance time before the system forcefully removes an item from the queue
#             if task['signal'] == 1:
#                 __QUEUE__.append(task['device_id']) if task['device_id'] not in __QUEUE__ else None
#                 __log__.debug(f"{__name__} queue: {__QUEUE__}")
#             else:
#                 __QUEUE__.remove(task['device_id'])
#                 __log__.debug(f"{__name__} queue: {__QUEUE__}")

#         await asyncio.sleep(0.01)

# the watcher function that retrieves items from the irrigation queue and 
# stores the deviced id (from the item dict) into the __QUEUE__ global variable when
# and removes the device ids on '0' signal
# TODO: implement 'OFF' signal maximum wait tolerance
# when an 'OFF' signal from a device is not received within a certain amount of time, close water pump
# NOTE: consider that the delay of the 'OFF' signal maybe because it takes time to reach ideal soil moisture level
# IDEA: use last will and testament ---> https://www.hivemq.com/blog/mqtt-essentials-part-9-last-will-and-testament/
async def __watcher__(loop: asyncio.AbstractEventLoop, queue: multiprocessing.Queue) -> None:
    global __QUEUE__
    cache: List = [] # cache for quick access

    while True:
        # get 'task' item from the queue
        task: Dict | None = get_from_queue(queue, __name__)

        if task:
            _id = task['device_id']
            _expire = time.time()
            if task['signal'] == 1:
                if _id not in cache:
                    __log__.debug(f"{__name__}.__watcher__() at PID {os.getpid()} received 'ON' signal from {_id}")
                    cache.append(_id)
                    __QUEUE__.update({_id:_expire})
                else:
                    __log__.warning(f"{__name__} received signal 'ON' from {_id} but already in queue (received another 'ON' before 'OFF')")
            else:
                try:
                    del __QUEUE__[_id]
                except KeyError:
                    __log__.warning(f"{__name__} received signal 'OFF' from {_id} but id not in queue")

        await asyncio.sleep(0.01)

# turn on the input on the water pump channel
def on(pin):
    GPIO.output(pin, GPIO.LOW)

# turn off input on the water pump channel
# not in use
def off(pin):
    GPIO.output(pin, GPIO.HIGH)

async def start(queue: multiprocessing.Queue) -> None:
    global __QUEUE__

    # get event loop
    loop: asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.get_event_loop()
    except Exception as e:
        __log__.error(f"Failed to get event loop @ PID {os.getpid()} ({__name__} submodule co-routine): {e}")
        return
    
    if loop:
        __log__.info(f"{__name__} submodule active @ PID {os.getpid()}")

        asyncio.create_task(__watcher__(loop, queue))
        try:
            while True:
                if len(__QUEUE__) > 0:
                    # GPIO setup
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(__CHANNEL__, GPIO.OUT)
                    while len(__QUEUE__) > 0:
                        try:
                            on(__CHANNEL__)
                        except KeyboardInterrupt:
                            GPIO.cleanup()
                        except Exception as e:
                            __log__.warning(f"{__name__} raised unhandled exception: {e}")
                        await asyncio.sleep(0.01)
                    GPIO.cleanup()
                else:
                    try:
                        off(__CHANNEL__)
                        GPIO.cleanup()
                    except Exception as e:
                        pass
                await asyncio.sleep(0.01)
        except (KeyboardInterrupt, asyncio.CancelledError):
            GPIO.cleanup()
            raise
        except Exception as e:
            __log__.error(f"Unhandled exception raised at {__name__} module: {e}")