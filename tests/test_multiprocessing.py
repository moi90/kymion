import multiprocessing
import time
from unittest.mock import ANY, Mock

from kymion.core import Event, NonBlockingRelay, ProgressHandler, get_progress_reporter
from kymion.handlers.queue import QueueHandler, QueueListener


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

    from concurrent.futures import ProcessPoolExecutor, as_completed

    n_tasks = 10

    # Set up a multiprocessing context for the test
    # (We need "spawn", because we mix threads and processes.)
    mp_context = multiprocessing.get_context("spawn")
    event_queue = mp_context.Queue()  # type: ignore

    # Create a mocked progress handler to capture events
    handler = Mock(wraps=ProgressHandler())
    progress_reporter = get_progress_reporter()
    progress_reporter.add_handler(handler)

    with (
        ProcessPoolExecutor(
            # Use the prepared multiprocessing context
            mp_context=mp_context,
            initializer=_executor_initializer,
            initargs=(event_queue,),
        ) as executor,
        QueueListener(event_queue),
    ):
        # Submit a series of tasks to the executor
        futures = [executor.submit(task, i) for i in range(n_tasks)]

        # Wait for all tasks to complete and collect their IDs
        task_ids = [fut.result() for fut in as_completed(futures)]

    # After everything had a chance to run, check for completion
    for task_id in task_ids:
        handler.handle_event.assert_any_call(
            Event(ANY, ANY, ANY, 5, 5, str(task_id), True)
        )
