import threading
import time
import uuid
from typing import Dict, Iterable, List, Optional


class ProgressReporter:
    root: "ProgressReporter"
    manager: "ProgressReporterManager"

    def __init__(self, parent: Optional["ProgressReporter"]) -> None:
        self.parent = parent
        self.handlers: "List[ProgressHandler]" = []

    def add_handler(self, handler: "ProgressHandler"):
        if not handler in self.handlers:
            self.handlers.append(handler)

    def notify_handlers(self, event):
        pr = self
        while pr is not None:
            for handler in pr.handlers:
                handler.handle_event(event)

            pr = pr.parent

    def task(
        self,
        iterable: Optional[Iterable] = None,
        *,
        description: Optional[str] = None,
        total: Optional[float] = None,
        initial: float = 0,
        min_diff_n: float = 0,
        min_diff_t: float = 0.1,  # 100ms
    ) -> "Task":
        return Task(self, iterable, description, total, initial, min_diff_n, min_diff_t)


class Task:
    def __init__(
        self,
        progress_reporter: ProgressReporter,
        iterable: Optional[Iterable],
        description: Optional[str],
        total: Optional[float],
        initial: float,
        min_diff_n: float,
        min_diff_t: float,
    ):
        self.progress_reporter = progress_reporter

        self.iterable = iterable

        self.description = description

        if total is None and iterable is not None:
            try:
                total = len(iterable)  # type: ignore
            except (TypeError, AttributeError):
                total = None
        if total == float("inf"):
            total = None

        self.total = total

        self.progress = initial

        self.min_diff_n = min_diff_n
        self.min_diff_t = min_diff_t

        self.id = uuid.uuid4().int
        self.last_notify_t = t = time.time()
        self.last_notify_n = initial
        self.finished = False

        # Notify handlers of the existence of this task
        self._notify(t)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()

    def _notify(self, t: float):
        self.last_notify_n = self.progress
        self.last_notify_t = t

        self.progress_reporter.notify_handlers(
            (self.id, t, self.progress, self.total, self.description, self.finished)
        )

    def update(self, amount: float = 1):
        """Increase progress by amount"""
        self.progress += amount

        if self.progress - self.last_notify_n >= self.min_diff_n:
            t = time.time()
            if t - self.last_notify_t >= self.min_diff_t:
                self._notify(t)

    def finish(self):
        self.finished = True
        self._notify(time.time())

    def __iter__(self):
        try:
            for item in self.iterable:  # type: ignore
                yield item
                self.update()

        finally:
            self.finish()


class ProgressHandler:
    def handle_event(self, event): ...


class ProgressReporterManager:
    def __init__(self, root: ProgressReporter) -> None:
        self.root = root
        self.progress_reporters: Dict[str, ProgressReporter] = {}

    def getProgressReporter(self, name: str) -> ProgressReporter:
        try:
            return self.progress_reporters[name]
        except KeyError:
            pass

        pr = self.progress_reporters[name] = ProgressReporter(self.root)

        return pr


ProgressReporter.root = root = ProgressReporter(None)
ProgressReporter.manager = manager = ProgressReporterManager(root)
get_progress_reporter = manager.getProgressReporter

del root
del manager


class NonBlockingRelay(ProgressHandler):
    """
    NonBlockingRelay is a ProgressHandler that forwards progress events to multiple handlers
    in a separate thread to prevent long-running or slow handlers from blocking the main thread.

    Events are stored in a dictionary, where the most recent event replaces the previous event
    for the same task. The relay ensures that all events are processed asynchronously.
    """

    def __init__(self, daemon=False) -> None:
        super().__init__()

        # List of handlers to forward events to
        self.handlers: List[ProgressHandler] = []

        # Condition for synchronizing the event store
        self._condition = threading.Condition()

        # Dictionary to store the most recent events for each task (keyed by task id)
        self._tasks = {}

        # Thread that processes the events
        self._worker_thread = threading.Thread(
            target=self._process_events, daemon=daemon
        )
        self._worker_thread.start()

    def _process_events(self):
        """
        The worker thread function that continuously processes events. It retrieves the most
        recent event for each task and forwards it to the registered handlers.

        The thread waits on a condition to avoid busy waiting when there are no new events.
        """

        while True:
            with self._condition:
                # Wait until a new event is available or the main thread terminates
                while True:
                    if not threading.main_thread().is_alive():
                        return

                    try:
                        # Pop one event from the _tasks dictionary
                        _, event = self._tasks.popitem()
                        # Exit the waiting loop to process the event
                        break
                    except KeyError:
                        # If no tasks are currently available, wait until notified or timeout.
                        # The timeout allows to detect the death of the main thread.
                        self._condition.wait(0.1)
                        continue

            # Forward the event to all registered handlers
            for handler in self.handlers:
                handler.handle_event(event)

    def add_handler(self, handler: ProgressHandler):
        """
        Register a new handler to receive events forwarded by this relay.
        """

        if not handler in self.handlers:
            self.handlers.append(handler)

    def handle_event(self, event):
        """
        Receive an event and add it to the task queue. If an event for the same task id
        already exists, it is replaced with the new one.

        Args:
            event (tuple): The event to be handled, which contains the task id and progress details.
        """

        with self._condition:
            self._tasks[event[0]] = event
            self._condition.notify()
