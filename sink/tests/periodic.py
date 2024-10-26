import time
import asyncio
import multiprocessing
import random
from secrets import token_urlsafe
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from utils import status

async def produce(q: multiprocessing.Queue):
    print('produce active')
    while True:
        await asyncio.sleep(5)
        try:
            q.put('yuuurt')
            print('put item to queue:')
        except Exception as e:
            print(f'failed to put item to queue: {str(e)}')

def acq_item(q: multiprocessing.Queue) -> Any:
    item: Any = None
    try:
        item = q.get(timeout=0.1)
    except Exception as e:
        if not q.empty():
            print(f'failed to get item from queue: {str(e)}')
    return item

async def mock_api_check() -> int:
    num = random.randint(1, 100)
    await asyncio.sleep(5)
    result = status.DISCONNECTED
    if num == 69:
        result = status.CONNECTED
    return result

async def main(q: multiprocessing.Queue, stat = int):
    loop = asyncio.get_running_loop()
    _stat = stat
    with ThreadPoolExecutor() as pool:
        while True:

            if _stat == status.DISCONNECTED:
                _chk_running = False

                while _stat == status.DISCONNECTED:
                    
                    item = await loop.run_in_executor(pool, acq_item, q)

                    if item:
                        print(f'item: {str(item)}, status: {_stat} (disconnected)')

                    if not _chk_running:
                        _chk_running = True
                        print('check_res running...')
                        chk_res = await loop.run_in_executor(pool, mock_api_check)

                    if chk_res == status.CONNECTED:
                        print(f'check res = status connected: {str(chk_res)}')
                        break
                    elif chk_res == status.DISCONNECTED:
                        print(f'check res = status disconnected: {str(chk_res)}')
                        _chk_running = False

                    await asyncio.sleep(0.5)

            if _stat == status.CONNECTED:

                while _stat == status.CONNECTED:

                    item = await loop.run_in_executor(pool, acq_item, q)

                    if item:
                        print(f'item: {str(item)}, status: {_stat} (connected)')

                    await asyncio.sleep(0.5)

async def run_this(q, stat):
    loop = asyncio.get_running_loop()

    loop.create_task(main(q, stat))
    loop.create_task(produce(q))

    while True:
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    queue = multiprocessing.Queue()

    _stat = status.DISCONNECTED
    asyncio.run(run_this(queue, _stat))
    
    pass