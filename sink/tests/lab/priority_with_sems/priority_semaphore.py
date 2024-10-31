import asyncio
from collections import deque
from bisect import insort_right

class PrioritySortedDeque(deque):

    def __init__(self):
        super().__init__()
        self.append_priority = 0.0

    def __iter__(self):
        return (i[1] for i in super().__iter__())

    def append(self, object):
        insort_right(self, (self.append_priority, object))

    def remove(self, value):
        del self[next(i for i, v in enumerate(self) if v is value)]

    def popleft(self):
        return super().popleft()[1]

class PrioritySemaphore(asyncio.Semaphore):

    def __init__(self, *args):
        super().__init__(*args)
        self._waiters = PrioritySortedDeque()

    def priority(self, priority):
        self._waiters.append_priority = priority
        return self

    async def priority_acquire(self, priority):
        self._waiters.append_priority = priority
        return await super().acquire()
    
if __name__ == "__main__":

    sem, p_sem = None, None

    async def normal_semaphored_print(val):
        async with sem:
            await asyncio.sleep(0.0)
            print(val, end=", ")

    async def prioritized_print(val):
        async with p_sem.priority(val):
            await asyncio.sleep(0.0)
            print(val, end=", ")

    async def prioritized_print_2(val):
        await p_sem.priority_acquire(val)
        await asyncio.sleep(0.0)
        print(val, end=", ")
        p_sem.release()

    async def main():
        global sem, p_sem
        p_sem = PrioritySemaphore(4)
        sem = asyncio.Semaphore(4)
        await asyncio.gather(*map(normal_semaphored_print, range(20, 0, -1)))
        print('\n')
        await asyncio.gather(*map(prioritized_print, range(20, 0, -1)))
        print('\n')
        await asyncio.gather(*map(prioritized_print_2, range(20, 0, -1)))
        print()

    asyncio.run(main())