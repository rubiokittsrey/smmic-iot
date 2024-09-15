import asyncio
import heapq

class PrioritizedTask:
    def __init__(self, priority, task):
        self.priority = priority
        self.task = task

    def __lt__(self, other):
        return self.priority < other.priority

async def worker(name: str, duration: int, semaphore: asyncio.Semaphore):
    async with semaphore:
        print(f"Task {name} started")
        await asyncio.sleep(duration)  # Simulating a blocking task
        print(f"Task {name} completed")

async def task_scheduler(priority_queue, semaphore):
    tasks = []
    while not priority_queue.empty():
        prioritized_task = await priority_queue.get()
        tasks.append(prioritized_task.task)

    # Run tasks concurrently with semaphore limit
    await asyncio.gather(*tasks)

async def main():
    priority_queue = asyncio.PriorityQueue()
    semaphore = asyncio.Semaphore(2)  # Allow up to 2 tasks to run concurrently

    # Add tasks with different priorities
    await priority_queue.put(PrioritizedTask(2, asyncio.create_task(worker('Low Priority', 3, semaphore))))
    await priority_queue.put(PrioritizedTask(1, asyncio.create_task(worker('High Priority', 2, semaphore))))
    await priority_queue.put(PrioritizedTask(3, asyncio.create_task(worker('Very Low Priority', 1, semaphore))))
    await priority_queue.put(PrioritizedTask(1, asyncio.create_task(worker('Medium Priority', 2, semaphore))))

    # Process tasks based on priority, but with semaphore limiting concurrency
    await task_scheduler(priority_queue, semaphore)

# Run the event loop
asyncio.run(main())
