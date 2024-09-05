import asyncio
import multiprocessing.process
import multiprocessing.queues
from secrets import token_hex
import time
import sys
import os
import paho.mqtt.client as paho_mqtt
import logging
from typing import Any

# internal
# internal
try:
    sys.path.append('/mnt/d/projects/smmic-iot/sink/common')
except Exception as e:
    print(f'Exception raised: {e}')
    os._exit(0)

import settings

sys.path.append(settings.APPConfigurations.SRC_PATH)

import mqtt.client as client
from utils import log_config, Modes, status

__log__ = log_config(logging.getLogger(__name__))

async def task_manager(queue: multiprocessing.Queue):
    __log__.debug(f"test.task_manager() function process running @ PID: {os.getpid()}")
    try:
        while True:
            msg: dict = queue.get()
            if msg:
                __log__.debug(f"@ PID {os.getpid()} -> message received @ queue -> topic: {msg["topic"]}, payload: {msg["payload"]}")
    except KeyboardInterrupt or asyncio.CancelledError:
        __log__.warning(f"@ PID {os.getpid()} -> task_manager() process received KeyboardInterrupt")

def run_task_manager(queue: multiprocessing.Queue):
    asyncio.run(task_manager(queue))

# async def run_client():

# class Handler that containsthe callback function 
# to be passed to the client.start_client() function (@ the client module)
class Handler:
    def __init__(self, msg_queue: multiprocessing.Queue):
        self.msg_queue: multiprocessing.Queue = msg_queue

    def route_to_queue(self, client: paho_mqtt.Client, userdata: Any, message: paho_mqtt.MQTTMessage):

        #TODO: implement routing messages to queue
        topic = message.topic
        payload = str(message.payload.decode('utf-8'))

        __log__.debug(f"@ PID {os.getpid()} -> message received @ topic {topic}: {payload} -> routing to queue")
        self.msg_queue.put({"topic":topic, "payload": payload})

        return

async def main():

    # first, spawn the task manager process
    __log__.debug(f"executing test.py.main() at PID {os.getpid()}")
    
    # important process variables
    msg_queue = multiprocessing.Queue()
    task_manager_p = None # process object var declaration
    
    try:
        task_manager_p = multiprocessing.Process(target=run_task_manager, args=(msg_queue,))
        task_manager_p.start()

        __log__.debug(f"running client loop from client module @ PID {os.getpid()}")

        handler = Handler(msg_queue)
        callback_client_task = asyncio.create_task(client.start_client(handler.route_to_queue))

        try:
            await asyncio.gather(callback_client_task)
        except asyncio.CancelledError or KeyboardInterrupt:
            task_manager_p.terminate()
            __log__.info(f"raised KeyboardInterrupt, cancelling test.run_client() @ PID: {os.getpid()}")
            await asyncio.gather(client.shutdown_client())

        while True:
            await asyncio.sleep(0.5)

    except Exception as e:
        __log__.error(f"error spawning task_manage process from PID {os.getpid()}: {str(e)}")

    except KeyboardInterrupt:
        __log__.warning(f"@ PID {os.getpid()} received KeyboardInterrupt, terminating task_manager() process")
        if task_manager_p:
            task_manager_p.terminate()
            task_manager_p.join()

if __name__ == "__main__":
    try:
        Modes.dev()
        asyncio.run(main())
    except KeyboardInterrupt:
        __log__.warning(f"main process @ PID {os.getpid()} received KeyboardInterrupt, processes terminated")


# # no usage
# # using this file for testing ideas mainly

# import concurrent.futures
# import queue
# import threading
# import time
# import random
# from datetime import datetime


# # TODO: implement asyncio?
# # TODO: try out multiprocessing, although arguably unecessary
# # simple demo of using threadpool executor
# def process_task(task):
#     sleep_time = random.randint(1, 10)
#     print(f'processing {task} in thread {threading.current_thread().name}, will be done in {sleep_time} seconds - {datetime.now().second}')
#     time.sleep(sleep_time)
#     print(f'Task {task} in thread {threading.current_thread().name} completed execution - {datetime.now().second}')

# def worker(task_queue):
#     while True:
#         task = task_queue.get()
#         if task is None:
#             break
#         process_task(task)
#         task_queue.task_done()

# def main():
#     # create a queue for the tasks
#     task_queue = queue.Queue()

#     # fill queue with tasks
#     for i in range(10):
#         task_queue.put(f"Task={i}")

#     # create ThreadPoolExecutor with specific num of worker threads    
#     num_workers = 4
#     with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
#         #start worker threads
#         futures = [executor.submit(worker, task_queue) for _ in range(num_workers)]

#         # wait for tasks to be processed
#         task_queue.join()

#         # stop worker threads
#         for _ in range(num_workers):
#             task_queue.put(None) # signal threads to exit
#         for future in futures:
#             future.result() # wait for worker threads to exit

# if __name__ == "__main__":
#     main()
#     # the main point of this script is to test out the usage of threadpool executio nand learn about it and how it can improve concurrent
#     # task handling in the application
#     # im not sure how i would implement this just yet
#     # but this does seem cool
#     # also queues might be used for this
    