import asyncio
from random import randint
from datetime import datetime
import time

async def process_task(name, priority, sem: asyncio.Semaphore):
    async with sem:
        print(f"{name} (priority {priority}) is starting.")
        await asyncio.sleep(2)

async def task_consumer(queue: asyncio.PriorityQueue):
    sem = asyncio.Semaphore(5)
    count = 0
    tasks = set()

    start = time.time()
    for _ in range(1, 16):

        # while sem.locked():
        #     await asyncio.sleep(0.01)

        while len(tasks) == 5:
           await asyncio.sleep(0.01)

        priority, task_name = await queue.get()
        # Process the task
        count += 1
        t_stamp = datetime.now()
        #print(f'received task from queue ({t_stamp.minute}:{t_stamp.second}.{t_stamp.microsecond}) with priority {priority}')
        t = asyncio.create_task(process_task(f'task #{count}', priority, sem))
        tasks.add(t)
        t.add_done_callback(tasks.discard)
        queue.task_done()
    end = time.time()

    print(f'buffer process time: {start - end}')

async def taskinflux(queue: asyncio.PriorityQueue):

    ps = [1, 1, 2, 1, 3, 1, 3, 3, 3, 2]
    for p in ps:
        title = ''
        if p == 1:
            title = 'lowest'
        elif p == 2:
            title = 'medium'
        elif p == 3:
            title = 'highest'
        queue.put_nowait((-p, title))

async def main():
    queue = asyncio.PriorityQueue()

    # Start the consumer task
    consumer_task = asyncio.create_task(task_consumer(queue))
    taskinflux_t = asyncio.create_task(taskinflux(queue))

    count = 0
    ps = [1, 2, 2, 3, 3]
    for p in ps:
        count += 1
        title = ''
        if p == 1:
            title = 'lowest'
        elif p == 2:
            title = 'medium'
        elif p == 3:
            title = 'highest'
        queue.put_nowait((-p, title))
        await asyncio.sleep(1)

    await consumer_task

asyncio.run(main())
