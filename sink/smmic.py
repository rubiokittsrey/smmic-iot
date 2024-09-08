# third-party
import logging
import argparse
import os
import asyncio
import multiprocessing
import random
import paho.mqtt.client as paho_mqtt
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple

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

# for topic '/dev/test'
# a simple dummy function for testing concurrent task management
async def dev_test_task(semaphore: asyncio.Semaphore, msg: dict) -> None:
    # simulate task delay
    duration = random.randint(1, 10)
    async with semaphore:
        await asyncio.sleep(duration)
        __log__.debug(f"Task done @ PID {os.getpid()} (dev_test_task()): [mid: {msg['mid']}, topic: {msg['topic']}, payload: {msg['payload']}] after {duration} seconds")

# retrieves messages from the queue
def from_queue_msg(queue: multiprocessing.Queue) -> dict | None:
    msg: dict | None = None

    # try to get a message from the queue
    try:
        msg = queue.get(timeout=0.1)
    except Exception as e:
        __log__.error(f"@ PID {os.getpid()} -> test.task_manager() cannot get message from queue: {e}") if msg != None else None

    return msg

# the task manager function
# this is the function that should handle the messages incoming from the queue
async def queue_monitor(queue: multiprocessing.Queue) -> None:
    # testing out this semaphore count
    # if the system experiences delay or decrease in performance, try to lessen this amount
    semaphore = asyncio.Semaphore(10)

    loop: asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        __log__.error(f"Failed to get running event loop @ PID {os.getpid()} task_manager() child process: {e}")
        return

    if loop:
        # use the threadpool executor to run the monitoring function function that retrieves data from the queue
        with ThreadPoolExecutor() as pool:
            while True:
                # run message retrieval from queue in non-blocking way
                msg = await loop.run_in_executor(pool, from_queue_msg, queue)

                # if a message is retrieved, create a task to handle that message
                # TODO: implement task handling for different types of messages
                # TODO: maybe have this as a separate function
                if msg:
                    __log__.debug(f"Task manager @ PID {os.getpid()} received message from queue (topic: {msg['topic']}, payload: {msg['payload']})")

                    # /dev/test topic
                    if msg['topic'] == '/dev/test':
                        asyncio.create_task(dev_test_task(semaphore, msg))

                await asyncio.sleep(0.1)

# runs the task_manager event loop
# this loop is important to allow concurrent task execution
def run_task_manager(msg_queue: multiprocessing.Queue) -> None:
    loop: asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.new_event_loop()
    except Exception as e:
        __log__.error(f"Failed to create event loop with asyncio.new_event_loop() @ PID {os.getpid()} (child process): {str(e)}")
        os._exit(0)

    # if loop event loop is present, run main()
    if loop:
        try:
            loop.run_until_complete(queue_monitor(msg_queue))
        except asyncio.CancelledError or KeyboardInterrupt:
            __log__.error(f"Closing main() loop @ PID {os.getpid()}: KeyboardInterrupt")
        except Exception as e:
            __log__.error(f"Failed to run main loop: {str(e)}")
        finally:
            loop.close()

# necessary handler class in order to include the usage of the Queue object in the message callback of the client
class Handler:
    def __init__(self, __msg_queue__: multiprocessing.Queue) -> None:
        self.__msg_queue__: multiprocessing.Queue = __msg_queue__
    
    # the message callback function
    # generally just routes the messages received by the client on relevant topics to the queue
    # NOTE to self: can be scaled to do more tasks just in case
    def msg_callback(self, client: paho_mqtt.Client, userdata: Any, message: paho_mqtt.MQTTMessage) -> None:
        topic = message.topic
        payload = str(message.payload.decode('utf-8'))
        msg_id = message.mid

        try:
            self.__msg_queue__.put({'topic': topic, 'payload': payload, 'mid': msg_id})
        except Exception as e:
            __log__.warning(f"Failed routing message to queue (Handler.msg_callback()): ('topic': {topic}, 'payload': {payload}) - ERROR: {str(e)}")

        return

# the main function of this operation
# and the parent process of the task manager process
async def main(loop: asyncio.AbstractEventLoop) -> None:
    __log__.debug(f"Executing smmic.main() @ PID {os.getpid()}")

    # multiprocessing.Queue to communicate between task_manager and callback_client processes
    msg_queue = multiprocessing.Queue()
    task_manager_p: multiprocessing.Process | None = None

    try:
        # first, spawn and run the task manager process
        task_manager_p = multiprocessing.Process(target=run_task_manager, args=(msg_queue,))
        task_manager_p.start()

        # pass the msg_queue to the handler object
        # then create and run the callback_client task
        # pass the callback method of the handler object
        handler = Handler(msg_queue)
        callback_client_task = asyncio.create_task(client.start_client(handler.msg_callback))

        # ensures that the callback_client task is done
        # handle KeyboardInterrupt for graceful shutdown
        try:
            await asyncio.gather(callback_client_task)
        except asyncio.CancelledError or KeyboardInterrupt:
            __log__.warning(f"Main function received KeyboardInterrupt or CancelledError, shutting down operations")

            # terminate the task_manager process
            task_manager_p.terminate()
            task_manager_p.join()

            # disconnect and shutdown the callback client loop
            await asyncio.gather(client.shutdown_client())

            raise

        # keep the main thread alive
        while True:
            await asyncio.sleep(0.1)
        
    except Exception as e:
        __log__.error(f"Parent process called exception error: {str(e)}")
        os._exit(0)
    
    except asyncio.CancelledError or KeyboardInterrupt:
        __log__.warning(f"Main function received KeyboardInterrupt or CancelledError, shutting down operations")

def run():
    loop: asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.new_event_loop()
    except Exception as e:
        __log__.error(f"Failed to create event loop with asyncio.new_event_loop() @ PID {os.getpid()} (main process): {str(e)}")
        os._exit(0)

    # if loop event loop is present, run main()
    if loop:
        try:
            loop.run_until_complete(main(loop))
        except asyncio.CancelledError or KeyboardInterrupt:
            __log__.error(f"Closing main() loop @ PID {os.getpid()}: KeyboardInterrupt")
        except Exception as e:
            __log__.error(f"Failed to run main loop: {str(e)}")
        finally:
            loop.close()

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

        try:
            run()
        except asyncio.CancelledError or KeyboardInterrupt:
            __log__.warning(f"Shutting down")