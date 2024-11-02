import asyncio
from random import randint
from datetime import datetime

async def process_task(name, priority, sem: asyncio.Semaphore):
    if sem.locked():
        print(f'{name} awaiting semaphore acquisition')
    async with sem:
        print(f"{name} (priority {priority}) is starting.")
        await asyncio.sleep(2)

async def task_consumer(queue: asyncio.PriorityQueue):
    sem = asyncio.Semaphore(4)
    count = 0
    while True:
        priority, task_name = await queue.get()
        # Process the task
        count += 1
        t_stamp = datetime.now()
        print(f'received task from queue ({t_stamp.minute}:{t_stamp.second}.{t_stamp.microsecond}) with priority {priority}')
        asyncio.create_task(process_task(f'task #{count}', priority, sem))
        queue.task_done()

async def taskinflux(queue: asyncio.PriorityQueue):
    for _ in range(0, 10):
        p = randint(1, 3)
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
    while count != 5:
        count += 1
        p = randint(1, 3)
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
