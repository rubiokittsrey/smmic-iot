# third-party
import logging
import argparse
import os
import asyncio
from typing import Tuple
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
import random
import paho.mqtt.client as paho_mqtt
from typing import Any

# internal core modules
from src.hardware import network
from src.mqtt import service, client

# internal helpers, configs
from utils import log_config, set_logging_configuration, Modes, status
from settings import Broker

__log__ = log_config(logging.getLogger(__name__))

# runs the system checks from the network and service modules
# returns a tuple of status literals, core status and api connection status
def sys_check() -> Tuple[int, int | None]:
    # the core functions status, excluding the api connection status
    core_status: int
    # the api status
    # NOTE: that if the api status is unsuccessful the system should still operate under limited functionalities
    # i.e. store data locally (and only until uploaded to api)
    api_status: int | None = None

    __log__.info(f"Performing core system checks")

    # perform the network check function from the network module
    # check interface status, ping gateway to verify connectivity
    net_check = network.network_check()
    if net_check == status.SUCCESS:
        __log__.debug(f'Network check successful, checking mosquitto service status')
        
        # check mosquitto service status
        # if mosquitto service check returns status.SUCCESS, proceed with api connection check
        mqtt_status = service.mqtt_status_check()
        if mqtt_status == status.ACTIVE:
            # TODO: implement api connection function
            # TODO: create no connection to api system protocols
            core_status = status.SUCCESS
            api_status = status.SUCCESS
        else:
            core_status = status.FAILED

    else:
        __log__.critical(f'Network check returned with errors, cannot proceed with operation')
        core_status = status.FAILED

    return core_status, api_status

async def worker(payload: str):
    sleep_time = random.randint(1, 10)
    await asyncio.sleep(sleep_time)
    __log__.debug(f"@ PID {os.getpid()} -> test.worker() done with: {payload} after {sleep_time} seconds")

def get_msg_from_queue(queue: multiprocessing.Queue):
    msg: dict | None = None
    try:
        msg = queue.get(timeout=0.1)
    except Exception as e:
        __log__.error(f"@ PID {os.getpid()} -> test.task_manager() cannot get message from queue: {e}") if msg != None else None

    return msg

async def task_manager(queue: multiprocessing.Queue):
    loop = asyncio.get_running_loop()

    __log__.debug(f"@ PID {os.getpid()} -> running test.task_manager() child process function")
    with ThreadPoolExecutor() as pool:
        while True:
            msg = await loop.run_in_executor(pool, get_msg_from_queue, queue)
            
            if msg:
                __log__.debug(f"@ PID {os.getpid()} -> test.task_manager() received message from queue (topic: {msg["topic"]}, payload: {msg["payload"]})")
                asyncio.create_task(worker(msg["payload"]))

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
    if os.system('cls') != 0:
        os.system('clear')

    parser = argparse.ArgumentParser(description="The main module of the SMMIC application for the Raspberry Pi 4")
    subparser = parser.add_subparsers(dest='command')

    # subparsers
    start = subparser.add_parser('start', help='Start the SMMIC MQTT application.')

    # start subparser parsers
    start_subparser = start.add_subparsers(dest='mode', help='Set the application mode. The default mode sets the logging level to WARNING with logging to file enabled.')
    dev = start_subparser.add_parser('dev', help='Start the application in development mode using verbose logging to terminal and with logging to file disabled.')
    normal = start_subparser.add_parser('normal', help='Start the application in normal mode with \'warning\' level logging.')
    info = start_subparser.add_parser('info', help='Start the application in info mode with \'info\' level logging')
    debug = start_subparser.add_parser('debug', help='Start the application in debug mode, uses verbose logging.')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        start.print_help()
    elif args.command == 'start':
        if not args.mode:
            start.print_help()
        elif args.mode == 'dev':
            Modes.dev()
            __log__.info('Starting in development mode - VERBOSE logging enabled, logging to file disabled')
        elif args.mode == 'normal' or not args.mode:
            __log__.info('Starting in normal mode with WARNING level logging and logging to file enabled')
            Modes.normal()
        elif args.mode == 'info':
            __log__.info('Starting in normal mode with INFO level logging and logging to file enabled')
            Modes.info()
        elif args.mode == 'debug':
            __log__.info('Starting in debug mode with DEBUG level logging and logging to file enabled')
            Modes.debug()

        # first, perform system checks
        core_status, api_status = sys_check()

        if core_status == status.FAILED:
            __log__.critical(f"Core system check returned with failure, terminating main process now")
            os._exit(0)
        
        if api_status == status.FAILED:
            __log__.warning(f"Cannot establish communication with API (#TODO: handle this) <-----")

        asyncio.run(main())