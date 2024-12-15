import multiprocessing
import queue
import threading

from ..core import ProgressHandler, Event, get_progress_reporter


class QueueHandler(ProgressHandler):
    """
    A ProgressHandler that forwards progress events to a multiprocessing.Queue.

    Args:
        queue (multiprocessing.Queue): The queue to forward events to.

    Note:
        This is analogous to `logging.handlers.QueueHandler`.
    """

    def __init__(self, queue: multiprocessing.Queue) -> None:
        super().__init__()

        self.queue = queue

    def handle_event(self, event: Event):
        self.queue.put(event)


class QueueListener:
    """
    A receiver that processes events from a multiprocessing.Queue and forwards them to
    the specified ProgressReporter.

    Args:
        queue (multiprocessing.Queue): The queue to read events from.
        daemon (bool): Whether the processing thread should be a daemon thread.

    Note:
        This is analogous to `logging.handlers.QueueListener`, but also inspired by
        the networking example in the `logging cookbook <https://docs.python.org/3/howto/logging-cookbook.html#sending-and-receiving-logging-events-across-a-network>`_.
    """

    def __init__(
        self,
        queue: multiprocessing.Queue,
    ) -> None:
        self.queue = queue

        # Thread that processes the events
        self._worker_thread = threading.Thread(target=self._process_events, daemon=True)
        self._worker_thread.start()

    def __enter__(self):
        return self

    def __exit__(self, *_, **__):
        self.shutdown(wait=True)

    def shutdown(self, wait: bool = True):
        """
        Signal the receiver to shut down.
        """

        self.queue.put(None, False)

        if wait:
            self._worker_thread.join()

    def _process_events(self):
        """
        Continuously process events from the queue and forwards them to the progress reporter.

        Stops processing if the main thread terminates or a `None` event is encountered.
        """

        while True:
            # Exit if the main thread terminates
            if not threading.main_thread().is_alive():
                return

            try:
                event: Event | None = self.queue.get(False, 0.1)
            except queue.Empty:
                continue

            if event is None:
                return

            # Forward the event to the correct progress reporter
            get_progress_reporter(event.name).handle_event(event)
