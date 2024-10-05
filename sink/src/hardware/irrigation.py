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
__QUEUE__ : List[str] = []
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

# the watcher function that retrieves items from the irrigation queue and 
# stores the deviced id (from the item dict) into the __QUEUE__ global variable when
# and removes the device ids on '0' signal
# TODO: implement 'OFF' signal maximum wait tolerance
# when an 'OFF' signal from a device is not received within a certain amount of time, close water pump
# NOTE: consider that the delay of the 'OFF' signal maybe because it takes time to reach ideal soil moisture level
# IDEA: use last will and testament ---> https://www.hivemq.com/blog/mqtt-essentials-part-9-last-will-and-testament/
async def __watcher__(loop: asyncio.AbstractEventLoop, queue: multiprocessing.Queue) -> None:
    global __QUEUE__

    # start loop
    while True:
        # retrieve irrigation task from queue
        i_task: Dict | None = get_from_queue(queue, __name__)

        if i_task:
            keys = list(i_task.keys())
            device_id = i_task['device_id']

            if 'signal' in keys:
                if i_task['signal'] == 1 and device_id not in __QUEUE__:
                    __QUEUE__.append(device_id)
                else:
                    __log__.warning("%s: signal 'ON' received from sensor %s but task already in __QUEUE__", __name__, device_id)

                if i_task['signal'] == 0 and device_id in __QUEUE__:
                    __QUEUE__.remove(device_id)
                else:
                    __log__.warning("%s: signal 'OFF' received from sensor %s but id not in __QUEUE__", __name__, device_id)

            if 'disconnected' in keys:
                if device_id in __QUEUE__:
                    __QUEUE__.remove(device_id)
                else:
                    pass

        await asyncio.sleep(0.01)

# sensor device disconnected panic function
# removes the sensor device from the queue if it exists
def remove_from_queue(device_id: str):
    global __QUEUE__

    if device_id in __QUEUE__:
        __QUEUE__.remove(device_id)

# turn on the input on the water pump channel
def __on__(pin):
    GPIO.output(pin, GPIO.LOW)

# turn off input on the water pump channel
# not in use
def __off__(pin):
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
                    try:
                        GPIO.setmode(GPIO.BCM)
                        GPIO.setup(__CHANNEL__, GPIO.OUT)
                    except Exception as e:
                        __log__.warning(f"Unhandled exception raised at {__name__} module: {e}")

                    while len(__QUEUE__) > 0:
                        try:
                            __on__(__CHANNEL__)
                        except KeyboardInterrupt:
                            GPIO.cleanup()
                        except Exception as e:
                            __log__.warning(f"{__name__} raised unhandled exception: {e}")
                        await asyncio.sleep(0.01)
                    GPIO.cleanup()
                else:
                    try:
                        __off__(__CHANNEL__)
                        GPIO.cleanup()
                    except Exception as e:
                        pass
                await asyncio.sleep(0.01)
        except (KeyboardInterrupt, asyncio.CancelledError):
            GPIO.cleanup()
            raise
        except Exception as e:
            __log__.error(f"Unhandled exception raised at {__name__} module: {e}")