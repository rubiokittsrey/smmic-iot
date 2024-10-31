import asyncio

async def process_task(name, priority):
    print(f"{name} (priority {priority}) is starting.")
    print(f"{name} (priority {priority}) is done.")

async def task_consumer(queue):
    async with asyncio.Semaphore(2):
        while True:
            priority, task_name = await queue.get()
            # Process the task
            await process_task(task_name, priority)
            queue.task_done()

async def main():
    queue = asyncio.PriorityQueue()

    # Start the consumer task
    consumer_task = asyncio.create_task(task_consumer(queue))

    # Add tasks with various priorities
    await queue.put((3, "Low-priority task"))
    await queue.put((3, "Low-priority task"))
    await queue.put((3, "Low-priority task"))
    await queue.put((1, "High-priority task"))
    await queue.put((2, "Medium-priority task"))
    await queue.put((1, "Third-degree high-priority task"))

    # Wait for all tasks to be processed
    await queue.join()
    consumer_task.cancel()  # Stop the consumer once all tasks are done

asyncio.run(main())
