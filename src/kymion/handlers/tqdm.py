from typing import Dict
import tqdm.auto
import tqdm

from ..core import ProgressHandler


class TQDMHandler(ProgressHandler):
    def __init__(self) -> None:
        super().__init__()

        self.instances: Dict[int, tqdm.tqdm] = {}

    def handle_event(self, event):
        try:
            instance = self.instances[event.task_id]
        except KeyError:
            instance = self.instances[event.task_id] = tqdm.auto.tqdm()

        instance.n = event.progress
        instance.total = event.total
        instance.desc = event.description
        instance.refresh()

        if event.finished:
            instance.close()
            del self.instances[event.task_id]
