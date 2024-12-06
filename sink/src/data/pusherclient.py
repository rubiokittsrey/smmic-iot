# third-party
import logging
import os
import asyncio
import multiprocessing
from typing import Any, Dict
from concurrent.futures import ThreadPoolExecutor
import pysher
import pysher.channel
import pusher
from json import (
    loads as json_decode,
    JSONDecodeError
)
from datetime import datetime

# internal helpers, configs
from settings import (
    APPConfigurations,
    Registry,
    Topics
)
from utils import (
    logger_config,
    get_from_queue,
    put_to_queue
)

# settings, configs
_log = logger_config(logging.getLogger(__name__))
alias = Registry.Modules.PusherClient.alias

# the pysher client for listening to events
_pysher_client = pysher.Pusher(
    key=APPConfigurations.PUSHER_KEY,
    cluster=APPConfigurations.PUSHER_CLUSTER,
    secret=APPConfigurations.PUSHER_SECRET,
    secure=APPConfigurations.PUSHER_SSL
)

# the pusher client for triggering events
_pusher_client = pusher.Pusher(
    app_id=APPConfigurations.PUSHER_APP_ID,
    key=APPConfigurations.PUSHER_KEY,
    cluster=APPConfigurations.PUSHER_CLUSTER,
    secret=APPConfigurations.PUSHER_SECRET,
    ssl=APPConfigurations.PUSHER_SSL
)

def _interval_event_handler(
        data: Any,
        triggers_q: multiprocessing.Queue,
        taskmanager_q: multiprocessing.Queue,
        loop: asyncio.AbstractEventLoop
        ):
    
    _log.debug(f'PysherClient received interval trigger event: {data}')

    command_data = None
    try:
        command_data = json_decode(data)
    except JSONDecodeError as e:
        _log.warning(
            f"{alias.capitalize()}._interval_event_handler() "
            f"raised JSONDecodeError on data: {data}"
        )

    if not command_data:
        return
    
    trigger = {
        'origin': alias,
        'context': Registry.Triggers.contexts.SE_INTERVAL,
        'data': command_data
    }
    
    with ThreadPoolExecutor() as pool:
        loop.run_in_executor(
            pool,
            put_to_queue,
            triggers_q,
            alias,
            trigger
        )

    return

def _irrigation_event_handler(
        data: Any,
        triggers_q: multiprocessing.Queue,
        taskmanager_q: multiprocessing.Queue,
        loop: asyncio.AbstractEventLoop
        ):
    
    _log.debug(f'PysherClient received irrigation trigger event: {data}')

    command_data = None
    try:
        command_data = json_decode(data)
    except JSONDecodeError as e:
        _log.warning(
            f"{alias.capitalize()}._irrigation_event_handler() "
            f"raised JSONDecodeError on data: {data}"
        )

    if not command_data:
        return

    trigger = {
        'origin': alias,
        'context': Registry.Triggers.contexts.SE_IRRIGATION_OVERRIDE,
        'data' : command_data
    }

    with ThreadPoolExecutor() as pool:
        loop.run_in_executor(
            pool,
            put_to_queue,
            triggers_q,
            alias,
            trigger
        )

    return

# when connected, subscribe to channel
# and bind events to handlers
def _connect_handler(
        data: Any,
        triggers_q: multiprocessing.Queue,
        taskmanager_q: multiprocessing.Queue,
        loop: asyncio.AbstractEventLoop
        ) -> pysher.channel.Channel:

    ch = _pysher_client.subscribe(APPConfigurations.PUSHER_CHANNELS[0])

    ch.bind(
        event_name = APPConfigurations.PUSHER_EVENT_INT,
        callback = _interval_event_handler,
        triggers_q = triggers_q,
        taskmanager_q = taskmanager_q,
        loop = loop
    )

    ch.bind(
        event_name = APPConfigurations.PUSHER_EVENT_IRR,
        callback = _irrigation_event_handler,
        triggers_q = triggers_q,
        taskmanager_q = taskmanager_q,
        loop = loop
    )

    return ch

async def _trigger(data: dict[str, Any]):
    unmapped_data = data['payload']
    split = unmapped_data.split(';')

    if len(split) < 2:
        _log.warning(
            f"{alias.capitalize()} received data "
            f"but lenght after split < 2, cancelling this task")
        return

    f_data = {
        'device_id': split[0],
        'command': split[1],
        'timestamp': str(datetime.now())
    }

    if 'irrigation' in split[2].split('/'):
        f_data['context'] = 'irrigation'
    elif 'interval' in split[2].split('/'):
        f_data['context'] = 'interval'

    _pusher_client.trigger(
        channels = APPConfigurations.PUSHER_CHANNELS[0],
        event_name = APPConfigurations.PUSHER_EVENT_FEEDBACK,
        data = f_data
    )

    _log.debug(f'{alias.capitalize()} trigger sent: {data}')
    pass

async def start(
        taskmanager_q: multiprocessing.Queue,
        triggers_q: multiprocessing.Queue,
        pusherclient_q: multiprocessing.Queue
        ) -> None:

    # acquire asyncio abstract event loop
    loop = None
    try:
        loop = asyncio.get_running_loop()

    except RuntimeError as e:
        _log.error(f"Failed to acquire running event loop: {e}")
        return
    
    # create pusher client obj
    # connect client
    _pysher_client.connection.bind(
        event_name = 'pusher:connection_established',
        callback = _connect_handler,
        triggers_q = triggers_q,
        taskmanager_q = taskmanager_q,
        loop = loop
    )
    _pysher_client.connect()

    _log.info(f"{alias} client connected and active".capitalize())

    tasks : set[asyncio.Task] = set()

    try:
        with ThreadPoolExecutor() as pool:
            # keep the thread alive
            while True:
                task = await loop.run_in_executor(
                    pool,
                    get_from_queue,
                    pusherclient_q,
                    alias
                )
                
                if task:
                    task = asyncio.create_task(_trigger(data=task))
                    tasks.add(task)
                    task.add_done_callback(tasks.discard)

                await asyncio.sleep(0.5)

    except (KeyboardInterrupt, asyncio.CancelledError):
        _pysher_client.disconnect()
        return
    
    except Exception as e:
        _log.error(f"Unhandled exception rasied: {e}")