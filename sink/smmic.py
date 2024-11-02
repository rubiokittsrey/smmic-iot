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
from setproctitle import setproctitle
# import sys
# from typing import Any
# from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, List, Callable

# internal core modules
import taskmanager
from src.hardware import hardware, network
from src.mqtt import service, client
from src.data import sysmonitor, locstorage, httpclient

# internal helpers, configs
from utils import log_config, Modes, status, ExceptionsHandler # priority, set_priority
# from settings import Broker

_log = log_config(logging.getLogger(__name__))

# abstract function to run sub processes
# TODO: fix KeyboardInterrupt handling for graceful termination
def run_sub_p(*args, **kwargs):
    pretty_alias: str
    sub_p: Callable

    try:
        sub_p = kwargs.pop('sub_proc')
    except KeyError:
        _log.error(f"Failed to run sub process: kwargs missing 'sub_proc' key ({__name__} at {os.getpid()})")
        raise

    try:
        pretty_alias = kwargs.pop('pretty_alias')
    except KeyError:
        _log.warning(f"Kwargs missing 'pretty_alias' key ({__name__}) at {os.getpid()}")
        pretty_alias = sub_p.__name__
    
    setproctitle(pretty_alias)

    loop = None
    try:
        loop = asyncio.new_event_loop()
    except Exception as e:
        _log.error(f"Failed to start event loop")

    if not loop:
        return

    proc_t = loop.create_task(sub_p(**kwargs))
    try:
        loop.run_until_complete(proc_t)
    except KeyboardInterrupt:
        _log.debug(f"Terminating {pretty_alias} sub process and exiting at PID {os.getpid()}")
        proc_t.cancel()

        # cleanup
        try:
            loop.run_until_complete(proc_t)
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        except RuntimeError as e:
            if str(e) == 'This event loop is already running':
                pass
            else:
                _log.error(f"Unhandled RuntimeError raised at {run_sub_p.__name__}: {str(e)}")
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
        raise

    except Exception as e:
        _log.error(f"Unhandled exception while attempting loop.run_forver(): {str(e)}")
    finally:
        loop.close()

# the main function of this operation
# and the parent process of the task manager process
async def main(loop: asyncio.AbstractEventLoop, api_status: int) -> None:
    #_log.info(f"SMMIC Main process running")

    # multiprocessing.Queue to communicate between task_manager and callback_client processes
    task_queue = multiprocessing.Queue()
    httpclient_queue = multiprocessing.Queue()
    hardware_queue = multiprocessing.Queue()
    sys_queue = multiprocessing.Queue()
    triggers_queue = multiprocessing.Queue()

    task_manager_kwargs = {
        'pretty_alias': taskmanager.alias,
        'sub_proc': taskmanager.start,
        'taskmanager_q': task_queue,
        'httpclient_q': httpclient_queue,
        'hardware_q': hardware_queue,
        'sysmonitor_q': sys_queue,
        'triggers_q': triggers_queue,
        'api_stat': api_status
    }

    httpclient_kwargs = {
        'pretty_alias': httpclient.alias,
        'sub_proc': httpclient.start,
        'httpclient_q': httpclient_queue,
        'taskmanager_q': task_queue,
        'triggers_q': triggers_queue
    }

    hardware_kwargs = {
        'pretty_alias': hardware.alias,
        'sub_proc': hardware.start,
        'hardware_q': hardware_queue,
        'taskmanager_q': task_queue
    }

    kwargs_list = [task_manager_kwargs, httpclient_kwargs, hardware_kwargs]

    try:
        # first, spawn and run the task manager process
        processes : List[multiprocessing.Process] = []
        for p_kwargs in kwargs_list:
            processes.append(multiprocessing.Process(target=run_sub_p, kwargs=p_kwargs, name=p_kwargs['pretty_alias']))

        for proc in processes:
            proc.start()

        # sub-second delay ensure that all sub-processes are already spawned before starting the callback_client coroutine of this process
        await asyncio.sleep(0.5)

        # main process co-routines
        coroutines = []

        # pass the msg_queue to the handler object
        # then create and run the callback_client task
        # pass the callback method of the handler object
        handler = client.Handler(task_queue=task_queue, sys_queue=sys_queue)
        coroutines.append(asyncio.create_task(client.start_client(handler.msg_callback)))
        # start the system monitor queue
        sysmonitor_args = {
            'sys_queue': sys_queue,
            'taskmanager_q': task_queue,
            'triggers_q': triggers_queue,
            'api_init_stat': api_status
        }
        coroutines.append(asyncio.create_task(sysmonitor.start(**sysmonitor_args)))

        # shutdown and cleanup
        try:
            await asyncio.gather(*coroutines)
        except (asyncio.CancelledError, KeyboardInterrupt) as e:
            _log.warning(f"Main process received {type(e).__name__}, shutting down operations")

            for proc in processes:
                proc.terminate()

            # short wait to ensure proc termination
            await asyncio.sleep(0.5)
            for proc in processes:
                proc.join()

            await asyncio.gather(client.shutdown_client(), *coroutines)
            raise

        # keep main thread alive
        while True:
            await asyncio.sleep(0.1)

    except Exception as e:
        _log.error(f"Parent process called {type(e).__name__} exception: {str(e.__cause__)}")
        raise SystemExit()

# create a new event loop and then run the main process within that loop
def run(core_status: int, api_status: int):
    if api_status == status.DISCONNECTED:
        _log.warning("Cannot establish connection with API, proceeding with API disconnect protocols")
    elif api_status == status.FAILED:
        _log.warning("Connection with API established but health check returned with failure")

    loop: asyncio.AbstractEventLoop | None = None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except Exception as e:
        ExceptionsHandler.event_loop.unhandled(__name__, os.getpid(), str(e))
        os._exit(0)
    # if loop event loop is present, run main()
    if loop:
        main_t = loop.create_task(main(loop, api_status))
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            main_t.cancel()
            try:
                loop.run_until_complete(main_t)
            except asyncio.CancelledError:
                pass
            raise
        except Exception as e:
            _log.error(f"Failed to run main loop: {str(e)}")
        finally:
            _log.debug(f"Closing main() loop at PID {os.getpid()}")
            loop.close()
    else:
        return

# runs the system checks from the network and service modules
# returns a tuple of status literals, core status and api connection status
# TODO: add an environment variables check in settings.py and call it in this method
def sys_check() -> Tuple[int, int]:
    # the core functions status, excluding the api connection status
    core_status: int
    # the api status
    # NOTE: that if the api status is unsuccessful the system should still operate under limited functionalities
    # i.e. store data locally (and only until uploaded to api)
    api_status: int = 0
    # the local storage status

    _log.info(f"Performing core system checks")

    # perform the network check function from the network module
    # check interface status, ping gateway to verify connectivity
    try:
        net_check = network.network_check()
    except KeyboardInterrupt:
        raise

    if net_check == status.SUCCESS:
        _log.debug(f'Network check successful, checking mosquitto service status')

        # check mosquitto service status
        # if mosquitto service check returns status.SUCCESS, proceed with api connection check
        mqtt_status = service.mqtt_status_check()
        if mqtt_status == status.ACTIVE:
            _log.debug('MOSQUITTO Broker status: active')
            core_status = status.SUCCESS
        else:
            core_status = status.FAILED

        # check api connection and health
        # if the check fails, implement no api connection protocol
        # TODO: create no connection to api system protocols
        loop: asyncio.AbstractEventLoop | None = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        except Exception as e:
            ExceptionsHandler.event_loop.unhandled(__name__, os.getpid(), str(e))
            os._exit(0)

        if loop:
            # local storage as part of core status
            storage_status = loop.run_until_complete(locstorage.init())
            if storage_status != status.SUCCESS:
                core_status = status.FAILED
            else:
                api_status, _b, _e = loop.run_until_complete(httpclient.api_check())
    else:
        _log.critical('Network check returned with critical errors, cannot proceed with operation')
        core_status = status.FAILED


    return core_status, api_status

if __name__ == "__main__":

    multiprocessing.current_process().name = 'smmic-main'
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
            _log.info('Starting in development mode - VERBOSE logging enabled, logging to file disabled')
        elif args.mode == 'normal' or not args.mode:
            _log.info('Starting in normal mode with WARNING level logging and logging to file enabled')
            Modes.normal()
        elif args.mode == 'info':
            _log.info('Starting in normal mode with INFO level logging and logging to file enabled')
            Modes.info()
        elif args.mode == 'debug':
            _log.info('Starting in debug mode with DEBUG level logging and logging to file enabled')
            Modes.debug()

        # first, perform system checks
        try:
            core_status, api_status = sys_check()
        except KeyboardInterrupt:
            _log.warning("Received KeyboardInterrupt while performing system check!")
            os._exit(0)

        if core_status == status.FAILED:
            _log.critical("Core system check returned with failure, terminating main process now")
            os._exit(0)

        try:
            run(core_status, api_status)
        except KeyboardInterrupt:
            _log.warning("Shutting down")
            os._exit(0)