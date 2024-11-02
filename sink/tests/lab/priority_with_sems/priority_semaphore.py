import asyncio
from collections import deque
from bisect import insort_right
from random import randint

class PrioritySortedDeque(deque):

    def __init__(self):
        super().__init__()
        self.append_priority : float = 0.0

    def __iter__(self):
        return (i[1] for i in super().__iter__())

    def append(self, object):
        insort_right(self, (self.append_priority, object))

    def remove(self, value):
        del self[next(i for i, v in enumerate(self) if v is value)]

    def popleft(self):
        return super().popleft()[1]


class PrioritySemaphore(asyncio.Semaphore):

    def __init__(self, *_):
        super().__init__(*_)
        self._waiters = PrioritySortedDeque()

    def priority(self, priority):
        self._waiters.append_priority = priority
        return self

    async def priority_acquire(self, priority: float):
        self._waiters.append_priority = priority
        return await super().acquire()
    
if __name__ == "__main__":

    
    p_sem = PrioritySemaphore(2)
    sem = asyncio.Semaphore(2)

    async def normal_semaphored_print(val):
        async with sem:
            await asyncio.sleep(0.0)
            print(val, end=", ")

    async def prioritized_print(val):
        async with p_sem.priority(-val):
            await asyncio.sleep(0.0)
            print(-val, end=", ")

    async def prioritized_print_2(val):
        await p_sem.priority_acquire(-val)
        await asyncio.sleep(0.0)
        print(-val, end=", ")
        p_sem.release()

    async def main():

        numlist = []
        while len(numlist) < 20:
            n = randint(1, 40)
            if n in numlist:
                pass
            else:
                numlist.append(n)
            if len(numlist) > 0:
                asyncio.create_task(prioritized_print_2(numlist))

        print(numlist)
        await asyncio.gather(*map(normal_semaphored_print, numlist))
        print()
        await asyncio.gather(*map(prioritized_print, numlist))
        print()
        await asyncio.gather(*map(prioritized_print_2, numlist))
        print()

    asyncio.run(main())