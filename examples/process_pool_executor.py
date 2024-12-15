import multiprocessing
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from kymion.core import get_progress_reporter
from kymion.handlers.queue import QueueHandler, QueueListener
from kymion.handlers.rich import RichHandler


def task(task_id):
    progress_reporter = get_progress_reporter("example.task")
    for _ in progress_reporter.task(range(5), description=f"Task {task_id}"):
        time.sleep(random.uniform(1e-2, 1e-1))
    return task_id


def executor_initializer(event_queue):
    handler = QueueHandler(event_queue)
    get_progress_reporter().add_handler(handler)


if __name__ == "__main__":
    get_progress_reporter().add_handler(RichHandler())

    mp_context = multiprocessing.get_context("spawn")
    event_queue = mp_context.Queue()

    with ProcessPoolExecutor(
        mp_context=mp_context,
        initializer=executor_initializer,
        initargs=(event_queue,),
    ) as executor, QueueListener(event_queue):
        futures = [executor.submit(task, i) for i in range(10)]
        for fut in as_completed(futures):
            print(f"Task {fut.result()} completed.")
