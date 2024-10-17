# TODO: documentation
# 
# 

# third-party
import aiosqlite
import asyncio
import logging
import os
import multiprocessing
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Any

# internal helpers, configurations
from settings import APPConfigurations
from utils import log_config, get_from_queue

_logs = log_config(logging.getLogger(__name__))

#
async def _delegator(read_semaphore: asyncio.Semaphore, write_lock: asyncio.Lock, db_connection: aiosqlite.Connection, data: Any):
    # TODO: implement delegator
    _logs.debug(f"{__name__} received data: {data}")
    await asyncio.sleep(random.randint(1, 10))
    pass

# 
async def start(queue: multiprocessing.Queue) -> None:
    try:
        loop = asyncio.get_running_loop()
    except Exception as e:
        _logs.error(f"Unable to get running event loop at PID {os.getpid()} ({__name__}): {str(e)}")
        return

    read_semaphore = asyncio.Semaphore(APPConfigurations.GLOBAL_SEMAPHORE_COUNT)
    write_lock = asyncio.Lock()
    tasks: set[asyncio.Task] = set()

    try:
        flag = False
        with ThreadPoolExecutor() as pool:
            
            async with aiosqlite.connect('local.db') as db:
                
                # write-ahead logging
                await db.execute("PRAGMA journal_mode=WAL;")
                await db.commit()

                while True:

                    if not flag:
                        _logs.info(f"{__name__} coroutine active at PID {os.getpid()}")
                        flag = not flag

                    try:
                        data = await loop.run_in_executor(pool, get_from_queue, queue, __name__)

                        if data:
                            t = asyncio.create_task(_delegator(read_semaphore, write_lock, db, data))
                            tasks.add(t)
                            t.add_done_callback(tasks.discard)

                    except Exception as e:
                        _logs.error(f"Unhandled exception at {__name__} loop: {str(e)}")

                    await asyncio.sleep(0.5)

    except (asyncio.CancelledError, KeyboardInterrupt):
        _logs.debug(f"Shutting down {__name__} at PID {os.getpid()}")

        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        raise