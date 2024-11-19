# third-party
import pysher
import logging
import os
import asyncio
import multiprocessing
from typing import Any
from concurrent.futures import ThreadPoolExecutor

import pysher.channel

# internal helpers, configs
from settings import APPConfigurations, Topics, Registry
from utils import logger_config

# settings, configs
_log = logger_config(logging.getLogger(__name__))
alias = Registry.Modules.PysherClient.alias

_pysher_client = pysher.Pusher(
    key=APPConfigurations.PUSHER_KEY,
    cluster=APPConfigurations.PUSHER_CLUSTER
    )

def _interval_event_handler(data: Any):
    print(data)
    pass

def _irrigation_event_handler(data: Any):
    print(data)
    pass

# when connected, subscribe to channel
# and bind events to handlers
def _connect_handler(
        data: Any) -> pysher.channel.Channel:

    for c in APPConfigurations.PUSHER_CHANNELS:
       ch : pysher.channel.Channel = _pysher_client.subscribe(c)

    ch.bind(APPConfigurations.PUSHER_EVENT_INT, _interval_event_handler)
    ch.bind(APPConfigurations.PUSHER_EVENT_IRR, _irrigation_event_handler)

    return ch

async def start(
        # taskamanager_q: multiprocessing.Queue,
        # triggers_q: multiprocessing.Queue,
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
    _pysher_client.connection.bind('pusher:connection_established', _connect_handler)
    _pysher_client.connect()

    _log.info(f"{alias} client connected and active".capitalize())

    try:
        # keep the thread alive
        while True:
            await asyncio.sleep(0.5)

    except (KeyboardInterrupt, asyncio.CancelledError):
        _pysher_client.disconnect()
        return
    
    except Exception as e:
        _log.error(f"Unhandled exception rasied: {e}")

if __name__ == "__main__":
    asyncio.run(start());