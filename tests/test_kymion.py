import multiprocessing
import threading
import time
from typing import Any
from unittest.mock import ANY, Mock
from kymion.handlers.queue import QueueHandler, QueueListener

from kymion.core import (
    Event,
    NonBlockingRelay,
    ProgressHandler,
    get_progress_reporter,
)


def test_task():
    handler = Mock(wraps=ProgressHandler())

    progress_reporter = get_progress_reporter("test_reporter")
    progress_reporter.add_handler(handler)

    # Test "raw" update and finish
    t1 = progress_reporter.task(total=10)

    # Handler got an initialization event
    handler.handle_event.assert_called_with(Event(ANY, t1.id, ANY, 0, 10, None, False))

    for _ in range(10):
        t1.update()
    t1.finish()

    # Handler got a "finished" event
    handler.handle_event.assert_called_with(Event(ANY, t1.id, ANY, 10, 10, None, True))

    # Test context manager
    with progress_reporter.task(range(10)) as t2:
        for _ in t2:
            pass

    # Handler got an initialization and "finished" event
    handler.handle_event.assert_any_call(Event(ANY, t2.id, ANY, 0, 10, None, False))
    handler.handle_event.assert_called_with(Event(ANY, t2.id, ANY, 10, 10, None, True))


def test_rate_limiting():
    handler = Mock(wraps=ProgressHandler())
    progress_reporter = get_progress_reporter("rate_limited_reporter")
    progress_reporter.add_handler(handler)

    t = progress_reporter.task(
        total=10, min_diff_n=1, min_diff_t=1
    )  # Only 1 update per second or per unit of progress

    # Fast updates
    for _ in range(10):
        t.update()

    # Ensure that not all updates were reported due to rate-limiting
    assert handler.handle_event.call_count < 10

    t.finish()
    # Ensure finish event is reported
    handler.handle_event.assert_called_with(Event(ANY, t.id, ANY, 10, 10, None, True))


def test_thread_safety():
    class VerySlowHandler(ProgressHandler):
        def handle_event(self, event):
            time.sleep(1)

    very_slow_handler = Mock(wraps=VerySlowHandler())
    relay = Mock(wraps=NonBlockingRelay())
    relay.add_handler(very_slow_handler)

    progress_reporter = get_progress_reporter("test_thread_safety")
    progress_reporter.add_handler(relay)

    def worker(i):
        for _ in progress_reporter.task(range(5), description=str(i)):
            time.sleep(0.01)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]

    for thread in threads:
        thread.start()

    # Ensure all threads updated correctly, and start and finish is reported
    for i, thread in enumerate(threads):
        thread.join()
        relay.handle_event.assert_any_call(Event(ANY, ANY, ANY, 0, 5, str(i), False))
        relay.handle_event.assert_any_call(Event(ANY, ANY, ANY, 5, 5, str(i), True))

    assert very_slow_handler.handle_event.call_count < relay.handle_event.call_count


def task(task_id):
    print(f"Executing task {task_id}...")
    progress_reporter = get_progress_reporter("test_ProcessPoolExecutor.task")
    for _ in progress_reporter.task(range(5), description=str(task_id)):
        time.sleep(0.1)
    return task_id


def _executor_initializer(event_queue):
    """
    Initialize a child process with a progress handler that forwards progress events to the main thread.
    """

    handler = NonBlockingRelay()
    handler.add_handler(QueueHandler(event_queue))

    get_progress_reporter().add_handler(handler)


def test_ProcessPoolExecutor():
    """
    Test the ProcessPoolExecutor wrapper to verify proper forwarding of progress events
    from child processes to the main thread.
    """

    from concurrent.futures import as_completed, ProcessPoolExecutor

    n_tasks = 10

    # Set up a multiprocessing context for the test
    # (We need "spawn", because we mix threads and processes.)
    mp_context = multiprocessing.get_context("spawn")
    event_queue = mp_context.Queue()  # type: ignore

    # Create a mocked progress handler to capture events
    handler = Mock(wraps=ProgressHandler())
    progress_reporter = get_progress_reporter()
    progress_reporter.add_handler(handler)

    with ProcessPoolExecutor(
        # Use the prepared multiprocessing context
        mp_context=mp_context,
        initializer=_executor_initializer,
        initargs=(event_queue,),
    ) as executor, QueueListener(event_queue):
        # Submit a series of tasks to the executor
        futures = [executor.submit(task, i) for i in range(n_tasks)]

        # Wait for all tasks to complete and collect their IDs
        task_ids = [fut.result() for fut in as_completed(futures)]

    # After everything had a chance to run, check for completion
    for task_id in task_ids:
        handler.handle_event.assert_any_call(
            Event(ANY, ANY, ANY, 5, 5, str(task_id), True)
        )
