import threading
from typing import Dict, Tuple
import rich.progress

from ..core import ProgressHandler


class RichHandler(ProgressHandler):
    def __init__(self) -> None:
        super().__init__()

        self.progress = rich.progress.Progress()
        self.progress.start()

        self.rich_task_ids: Dict[int, rich.progress.TaskID] = {}

        # Stop the progress display gracefully once the main thread stops in order to leave the terminal tidy
        threading.Thread(target=self._stop_progress).start()

    def _stop_progress(self):
        # Wait for main thread to finish
        threading.main_thread().join()
        # Then stop the progress widget
        self.progress.stop()

    def handle_event(self, event):
        try:
            rich_task_id = self.rich_task_ids[event.task_id]
        except KeyError:
            self.rich_task_ids[event.task_id] = rich_task_id = self.progress.add_task(
                event.description or "", total=event.total
            )

        self.progress.update(
            rich_task_id,
            total=event.total,
            completed=event.progress,
            description=event.description,
        )

        if event.finished:
            # self.progress.remove_task(rich_task_id)
            del self.rich_task_ids[event.task_id]
