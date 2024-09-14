import asyncio
import heapq

class PrioritizedTask:
    def __init__(self, priority, task):
        self.priority = priority
        self.task = task

    def __lt__(self, other):
        return self.priority < other.priority

async def worker(name: str, duration: int):
    print(f"Task {name} started")
    await asyncio.sleep(duration)
    print(f"Task {name} completed")

async def task_scheduler(priority_queue):
    while not priority_queue.empty():
        prioritized_task = await priority_queue.get()
        await prioritized_task.task

async def main():
    priority_queue = asyncio.PriorityQueue()

    # Add tasks with different priorities (lower value = higher priority)
    await priority_queue.put(PrioritizedTask(2, asyncio.create_task(worker('Low Priority', 3))))
    await priority_queue.put(PrioritizedTask(1, asyncio.create_task(worker('High Priority', 1))))
    await priority_queue.put(PrioritizedTask(3, asyncio.create_task(worker('Very Low Priority', 2))))

    # Process tasks based on priority
    await task_scheduler(priority_queue)

# Run the event loop
asyncio.run(main())
