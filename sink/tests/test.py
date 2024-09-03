import asyncio
import multiprocessing.process
import multiprocessing.queues
from secrets import token_hex
import time
import sys
import os
import paho.mqtt.client as paho_mqtt
import logging

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

log = log_config(logging.getLogger(__name__))

# async def async_task(name, delay):
#     print(f"Task {name}: {i}")
#     await asyncio.sleep(delay)
#     print(f"Task {name} complete")
#     return f"Task {name} complete"

# async def simulated_event_loop():
#     tasks = [
#         asyncio.create_task(async_task(token_hex(8), 1)),
#         asyncio.create_task(async_task(token_hex(8), 2))
#     ]
#     results = await asyncio.gather(*tasks)

global MSG_QUEUE

def task_manager():
    log.debug(f"test.task_manager() function executing @ PID {os.getpid()}")
    log.debug(f"client status: {client.CLIENT_STAT}")
    while True:
        if client.CALLBACK_CLIENT.is_connected():
            client.CALLBACK_CLIENT.publish(settings.DevTopics.TEST, "757575757575")
        time.sleep(5)
        log.debug(f"still not publishing")

def redirect_queue(client: paho_mqtt.Client, userdata, message: paho_mqtt.MQTTMessage):
    log.debug(f"Payload received: {str(message.payload.decode('utf-8'))} from topic {message.topic}")

def callback_client():
    log.debug(f'test.callback_client() function executing @ PID {os.getpid()}')
    asyncio.run(client.start_callback_client())

    while True:
        if client.CLIENT_STAT == status.CONNECTED:
            client.CALLBACK_CLIENT.message_callback_add("#", redirect_queue)

if __name__ == "__main__":
    Modes.dev()

    MSG_QUEUE = multiprocessing.Queue()

    log.debug(f'test.py module executing @ PID {os.getpid()}')

    tsk_mngr = multiprocessing.Process(target=task_manager)
    c_client = multiprocessing.Process(target=callback_client)
    
    # start processes
    try:
        tsk_mngr.start()
        c_client.start()
    except KeyboardInterrupt:
        print(f'keyboardInterrupt raised')
        tsk_mngr.terminate()
        c_client.terminate()
        tsk_mngr.join()
        c_client.join()

    # join
    tsk_mngr.join()
    c_client.join()


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
    