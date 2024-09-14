# third-party
import multiprocessing
import asyncio
import logging
import os
import random
from concurrent.futures import ThreadPoolExecutor

# internal helpers, configs
from utils import log_config

__log__ = log_config(logging.getLogger(__name__))

# retrieves messages from the queue
def __from_queue__(queue: multiprocessing.Queue) -> dict | None:
    msg: dict | None = None

    # try to get a message from the queue
    try:
        msg = queue.get(timeout=0.1)
    except Exception as e:
        __log__.error(f"Exception raised @ {os.getpid()} -> test.task_manager() cannot get message from queue: {e}") if msg != None else None
    except KeyboardInterrupt or asyncio.CancelledError:
        raise

    return msg

# for topic '/dev/test'
# a simple dummy function for testing concurrent task management
async def __dev_test_task__(semaphore: asyncio.Semaphore, msg: dict) -> None:
    # simulate task delay
    duration = random.randint(1, 10)
    async with semaphore:
        await asyncio.sleep(duration)
        __log__.debug(f"Task done @ PID {os.getpid()} (dev_test_task()): [timestamp: {msg['timestamp']}, topic: {msg['topic']}, payload: {msg['payload']}] after {duration} seconds")

# routes messsage to the right task
# async def __worker__(*args, **kwargs):
#     asfasd

# async def __executor__(p_queue: asyncio.PriorityQueue):
    

async def start(queue: multiprocessing.Queue) -> None:
    # testing out this semaphore count
    # if the system experiences delay or decrease in performance, try to lessen this amount
    semaphore = asyncio.Semaphore(10)
    priority_queue = asyncio.PriorityQueue()

    loop: asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        __log__.error(f"Failed to get running event loop @ PID {os.getpid()} task_manager() child process: {e}")
        return

    if loop:
        # use the threadpool executor to run the monitoring function function that retrieves data from the queue
        try:
            with ThreadPoolExecutor() as pool:
                while True:
                    # run message retrieval from queue in non-blocking way
                    msg = await loop.run_in_executor(pool, __from_queue__, queue)

                    # if a message is retrieved, create a task to handle that message
                    # TODO: implement task handling for different types of messages
                    # TODO: maybe have this as a separate function
                    if msg:
                        __log__.debug(f"Task manager @ PID {os.getpid()} received message from queue (topic: {msg['topic']}, payload: {msg['payload']}, timestamp: {msg['timestamp']})")

                        #/dev/test topic
                        if msg['topic'] == '/dev/test':
                            asyncio.create_task(__dev_test_task__(semaphore, msg))

                    await asyncio.sleep(0.1)
                    
        except KeyboardInterrupt or asyncio.CancelledError:
            raise
