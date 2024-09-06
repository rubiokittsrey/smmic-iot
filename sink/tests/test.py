# third-party
import asyncio
import multiprocessing
import os
import sys
import paho.mqtt.client as paho_mqtt
import logging
from typing import Any

# internal
# NOTE: for wsl development
sys.path.append('/mnt/d/projects/smmic-iot/sink/common')

import settings
sys.path.append(settings.APPConfigurations.SRC_PATH)

import mqtt.client as client
from utils import log_config, Modes, status

__log__ = log_config(logging.getLogger(__name__))

async def task_manager(queue: multiprocessing.Queue):
    __log__.debug(f"@ PID {os.getpid()} -> running test.task_manager() child process function")
    while True:
        try:
            msg: dict = queue.get()
        except Exception as e:
            __log__.error(f"@ PID {os.getpid()} -> test.task_manager() cannot get message from queue: {e}")

        if msg:
            __log__.debug(f"@ PID {os.getpid()} -> test.task_manager() received message from queue (topic: {msg["topic"]}, payload: {msg["payload"]})")

        await asyncio.sleep(0.1)

def run_task_manager(queue: multiprocessing.Queue):
    asyncio.run(task_manager(queue))

class Handler:
    def __init__(self, msg_queue: multiprocessing.Queue):
        self.msg_queue: multiprocessing.Queue = msg_queue

    def message_to_queue_callback(self, client: paho_mqtt.Client, userdata: Any, message: paho_mqtt.MQTTMessage):
        topic = message.topic
        payload = str(message.payload.decode('utf-8'))

        __log__.debug(f"@ PID {os.getpid()} -> test.message_to_queue_callback received message @ topic {topic}: {payload}")

        try:
            self.msg_queue.put({"topic": topic, "payload": payload})
        except Exception as e:
            __log__.error(f"@ PID {os.getpid()} -> test.message_to_queue_callback() error routing message ('topic': {topic}, 'payload': {payload}) to queue: {e}")

        return
    
async def main():
    __log__.debug(f"@ PID {os.getpid()} -> parent process running test.main()")
    
    # the message queue where the two processes will communicate and the process object variable
    msg_queue = multiprocessing.Queue()
    task_manager_p = None

    try:
        # first, spawn the task manager process
        task_manager_p = multiprocessing.Process(target=run_task_manager, args=(msg_queue,))
        task_manager_p.start()

        __log__.debug(f"@ PID {os.getpid()} -> running callback client task loop")

        # pass the msg_queue to the handler object
        # then create the callback_client task and pass the callback function from the handler object
        handler = Handler(msg_queue)
        callback_client_task = asyncio.create_task(client.start_client(handler.message_to_queue_callback))

        try:
            await asyncio.gather(callback_client_task)
        except asyncio.CancelledError or KeyboardInterrupt:
            __log__.debug(f"@ PID {os.getpid()} -> received KeyboardInterrupt, terminating test.run_task_manager() child process")
            task_manager_p.terminate()
            task_manager_p.join()
            
            # disconnect and shutdown the callback client properly
            await asyncio.gather(client.shutdown_client())

            raise
        
        # keep this thread alive
        while True:
            await asyncio.sleep(0.1)

    except Exception as e:
        __log__.error(f"@ PID {os.getpid()} -> error spawning test.task_manager() function process: {e}")

    except KeyboardInterrupt:
        __log__.warning(f"@ PID {os.getpid()} -> received KeyboardInterrupt, terminating test.main() process")

if __name__ == "__main__":
    try:
        Modes.debug()
        asyncio.run(main())
    except KeyboardInterrupt:
        __log__.warning(f"@ PID {os.getpid()} -> exiting test.py")