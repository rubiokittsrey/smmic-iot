# no usage
# using this file for testing ideas mainly

import concurrent.futures
import queue
import threading
import time
import random


# TODO: implement asyncio?
# TODO: try out multiprocessing, although arguably unecessary
# simple demo of using threadpool executor
def process_task(task):
    sleep_time = random.randint(5, 10)
    print(f'processing {task} in thread {threading.current_thread().name}, will be done in {sleep_time} seconds')
    time.sleep(sleep_time)

def worker(task_queue):
    while True:
        task = task_queue.get()
        if task is None:
            break
        process_task(task)
        task_queue.task_done()

def main():
    # create a queue for the tasks
    task_queue = queue.Queue()

    # fill queue with tasks
    for i in range(10):
        task_queue.put(f"Task={i}")

    # create ThreadPoolExecutor with specific num of worker threads    
    num_workers = 4
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        #start worker threads
        futures = [executor.submit(worker, task_queue) for _ in range(num_workers)]

        # wait for tasks to be processed
        task_queue.join()

        # stop worker threads
        for _ in range(num_workers):
            task_queue.put(None) # signal threads to exit
        for future in futures:
            future.result() # wait for worker threads to exit

if __name__ == "__main__":
    main()
    # the main point of this script is to test out the usage of threadpool executio nand learn about it and how it can improve concurrent
    # task handling in the application
    # im not sure how i would implement this just yet
    # but this does seem cool
    # also queues might be used for this
    