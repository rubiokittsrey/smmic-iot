# README
# this module manager everything in this entire operation
# 1. responsible for spawning the task manager child process
# 2. runs the client in an event loop
# 3. routes messages to the msg_queue
# 4. TODO: implement spawning of hardware process to manage hardware tasks in true parallelism

# third-party
import logging
import argparse
import os
import asyncio
import multiprocessing
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple

# internal core modules
from src.hardware import network
from src.mqtt import service, client
from src.data import aiohttpclient
import taskmanager

# internal helpers, configs
from utils import log_config, Modes, status, priority, set_priority
from settings import Broker

__log__ = log_config(logging.getLogger(__name__))

# runs the task_manager asyncio event loop
# this loop is important to allow concurrent task execution
def run_task_manager(msg_queue: multiprocessing.Queue, aio_queue: multiprocessing.Queue, hardware_queue: multiprocessing.Queue) -> None:
    loop: asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.new_event_loop()
    except Exception as e:
        __log__.error(f"Failed to create event loop with asyncio.new_event_loop() @ PID {os.getpid()} (child process): {str(e)}")
        os._exit(0)

    # if loop event loop is present, start taskmanager
    if loop:
        try:
            # the task manager module
            # handles the messages incoming from the queue
            loop.run_until_complete(taskmanager.run(msg_queue=msg_queue, aio_queue=aio_queue, hardware_queue=hardware_queue))
        except asyncio.CancelledError or KeyboardInterrupt:
            raise
        except Exception as e:
            __log__.error(f"Failed to run task manager loop: {str(e)}")
        finally:
            loop.close()

def run_aio_client(queue: multiprocessing.Queue) -> None:
    loop: asyncio.AbstractEventLoop | None = None

    # its very important the a new event loop is instantiated
    # if this somehow fails, exit this current process
    try:
        loop = asyncio.new_event_loop()
    except Exception as e:
        __log__.error(f"Failed to start event loop with asyncio.new_event_loop @ PID {os.getpid()} (child process): {str(e)}")
        os._exit(0)

    # TODO: implement
    if loop:
        try:
            loop.run_until_complete(aiohttpclient.start(queue))
        except asyncio.CancelledError or KeyboardInterrupt:
            raise
        except Exception as e:
            __log__.error(f"Failed to run aioClient loop: {str(e)}")
        finally:
            loop.close()

def run_hardware_p(queue: multiprocessing.Queue) -> None:
    loop: asyncio.AbstractEventLoop | None = None

    try:
        loop = asyncio.new_event_loop()
    except Exception as e:
        __log__.error(f"Failed to start event loop with asyncio.new_event_loop @ PID {os.getpid()} (child process): {str(e)}")
        os._exit(0)

    #TODO: implement

# the main function of this operation
# and the parent process of the task manager process
async def main(loop: asyncio.AbstractEventLoop) -> None:
    __log__.debug(f"Executing smmic.main() @ PID {os.getpid()}")

    # multiprocessing.Queue to communicate between task_manager and callback_client processes
    msg_queue = multiprocessing.Queue()
    aio_queue = multiprocessing.Queue()
    hardware_queue = multiprocessing.Queue()

    tsk_mngr_kwargs = {
        'msg_queue': msg_queue,
        'aio_queue': aio_queue,
        'hardware_queue': hardware_queue
    }

    task_manager_p: multiprocessing.Process | None = None

    try:
        # first, spawn and run the task manager process
        task_manager_p = multiprocessing.Process(target=run_task_manager, kwargs=tsk_mngr_kwargs)
        aio_client_p = multiprocessing.Process(target=run_aio_client, kwargs={'queue': aio_queue})

        task_manager_p.start()
        aio_client_p.start()

        # pass the msg_queue to the handler object
        # then create and run the callback_client task
        # pass the callback method of the handler object
        handler = client.Handler(msg_queue)
        callback_client_task = asyncio.create_task(client.start_client(handler.msg_callback))

        # ensures that the callback_client task is done
        # handle KeyboardInterrupt for graceful shutdown
        try:
            await asyncio.gather(callback_client_task)
        except asyncio.CancelledError or KeyboardInterrupt:
            __log__.warning(f"Main function received KeyboardInterrupt or CancelledError, shutting down operations")

            # terminate the task_manager process
            task_manager_p.terminate()
            aio_client_p.terminate()
            
            # make sure the processes are joined
            aio_client_p.join()
            task_manager_p.join()

            # disconnect and shutdown the callback client loop
            await asyncio.gather(client.shutdown_client(), callback_client_task)

            raise

        # keep the main thread alive
        while True:
            await asyncio.sleep(0.1)
        
    except Exception as e:
        __log__.error(f"Parent process called exception error: {str(e)}")
        os._exit(0)
    
    except asyncio.CancelledError or KeyboardInterrupt:
        __log__.warning(f"Main function received KeyboardInterrupt or CancelledError, shutting down operations")
        raise

# create a new event loop and then run the main process within that loop
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
            raise
        except Exception as e:
            __log__.error(f"Failed to run main loop: {str(e)}")
        finally:
            loop.close()

# runs the system checks from the network and service modules
# returns a tuple of status literals, core status and api connection status
# TODO: add an environment variables check in settings.py and call it in this method
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
    try:
        net_check = network.network_check()
    except KeyboardInterrupt:
        raise

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
            os._exit(0)
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
        try:
            core_status, api_status = sys_check()
        except KeyboardInterrupt:
            __log__.warning(f"Received KeyboardInterrupt while performing system check!")
            os._exit(0)

        if core_status == status.FAILED:
            __log__.critical(f"Core system check returned with failure, terminating main process now")
            os._exit(0)
        
        if api_status == status.FAILED:
            __log__.warning(f"Cannot establish communication with API (#TODO: handle this) <-----")

        try:
            run()
        except asyncio.CancelledError or KeyboardInterrupt:
            __log__.warning(f"Shutting down")
            os._exit(0)