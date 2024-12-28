import time
from logging import INFO, Logger, getLogger
from typing import Dict, List, Literal, Optional

import prefixed

from ..core import Event, ProgressHandler, get_progress_reporter

NumberFormat = Literal[None, "si", "iec"]


def format_number(x: float, format: NumberFormat):
    if format is None:
        return f"{x:.2f}"
    if format == "si":
        return f"{prefixed.Float(x):.2h}"
    if format == "iec":
        return f"{prefixed.Float(x):.2k}"

    raise ValueError(f"Unsupported format: {format!r}")


def format_interval(t):
    if t is None:
        return "??:??"

    mins, s = divmod(int(t), 60)
    h, m = divmod(mins, 60)

    if h:
        return f"{h:d}:{m:02d}:{s:02d}"

    return f"{m:02d}:{s:02d}"


class TaskLogger:
    """
    Logs the progress of an individual task at regular intervals.

    Args:
        description (str, optional): A description to prefix the log messages with, typically
            describing the task. Defaults to None.
        n_total (float, optional): The total number of items to process. If not provided,
            the logger will assume an indeterminate total. Defaults to None.
        log_interval (float, optional): The interval (in seconds) at which progress is logged.
            Defaults to 60.
        unit (str, optional): The unit of work being processed (e.g., "it" for iterations).
            Defaults to "it".
        number_format (NumberFormat, optional): The format used for displaying large numbers.
            Can be "si" for SI prefixes (k, M, G, ...) or "iec" for IEC binary prefixes (ki, Mi, Gi). Defaults to "si".
        smoothing (float, optional): The smoothing factor for the rate estimation. Must be
            between 0 and 1 (exclusive of 0, inclusive of 1). Lower values put more weight
            on recent rates. Defaults to 0.5.
        smoothing_min_n_done (float, optional): The minimum number of processed items after
            which smoothing is applied. It might make sense to use a number >0 because the
            first few objects tend to be processed slower. Defaults to 0.
    """

    def __init__(
        self,
        logger: Logger,
        level=INFO,
        *,
        description: Optional[str] = None,
        n_total: Optional[float] = None,
        log_interval: float = 60,
        unit="it",
        number_format: NumberFormat = "si",
        smoothing: float = 0.5,
        smoothing_min_n_done: float = 0,
    ) -> None:
        self.logger = logger
        self.level = level

        if smoothing <= 0.0 or smoothing > 1.0:
            raise ValueError(f"smoothing must be between 0 and 1, got {smoothing:.2f}")

        self.description = description
        self.n_total = n_total
        self.log_interval = log_interval
        self.unit = unit
        self.number_format: NumberFormat = number_format
        self.smoothing = smoothing
        self.smoothing_min_n_done = smoothing_min_n_done

        #: Total number of processed items
        self.n_done = 0
        #: Timestamp of the last update
        self.t_last_update = time.time()
        #: Elapsed seconds since the first update
        self.elapsed_since_start = 0
        #: Timestamp of the last log
        self.t_last_log: Optional[float] = None
        #: Number of processed items of the last log
        self.n_done_last_log = 0
        #: Previous rate estimate (items/second)
        self.rate_last_log: Optional[float] = None

    def update(self, n: float = 1):
        """
        Updates the progress by setting the count of processed items to `n`.
        Logs the progress if the specified log interval has passed since the last log.
        """
        t_cur = time.time()
        delta_t = t_cur - self.t_last_update
        self.t_last_update = t_cur

        self.elapsed_since_start += delta_t
        self.n_done = n

        if self.t_last_log is None or (t_cur > self.t_last_log + self.log_interval):
            if self.t_last_log is None:
                # Global rate estimate (items/second)
                rate = self.n_done / self.elapsed_since_start
            else:
                # Local rate estimate
                elapsed_since_last_log = t_cur - self.t_last_log
                n_done_since_last_log = self.n_done - self.n_done_last_log
                rate = n_done_since_last_log / elapsed_since_last_log

                # Apply smoothing if possible (items/second)
                if (
                    (self.rate_last_log is not None)
                    and (self.smoothing > 0)
                    and (self.n_done >= self.smoothing_min_n_done)
                ):
                    rate = (self.smoothing * self.rate_last_log) + (
                        (1 - self.smoothing) * rate
                    )

            self.t_last_log = t_cur
            self.n_done_last_log = self.n_done
            self.rate_last_log = rate

            if self.description is not None:
                msg = f"{self.description}: "
            else:
                msg = ""

            parts = []

            if self.n_total is not None:
                t_remaining = (self.n_total - self.n_done) / rate if rate else None

                parts.append(
                    f"{format_number(self.n_done, self.number_format)} / {format_number(self.n_total, self.number_format)}"
                )
                parts.append(f"{self.n_done / self.n_total:.2%}")

                parts.append(
                    f"{format_interval(self.elapsed_since_start)} + {format_interval(t_remaining)}"
                )
            else:
                parts.append(f"{format_number(self.n_done, self.number_format)} / ?")

                parts.append(f"{format_interval(self.elapsed_since_start)}")

            if (rate >= 1) or (rate <= 0):
                parts.append(f"{format_number(rate, self.number_format)}{self.unit}/s")
            else:
                parts.append(f"{1/rate:.2f}s/{self.unit}")

            msg += ", ".join(parts)

            self.logger.log(self.level, msg)


class LoggingHandler(ProgressHandler):
    """
    A ProgressHandler that reports progress as log messages.
    """

    def __init__(
        self,
        level=INFO,
        log_interval: float = 60,
        unit="it",
        smoothing: float = 0.5,
        smoothing_min_n_done: float = 0,
    ) -> None:
        super().__init__()

        self.level = level
        self.log_interval = log_interval
        self.unit = unit
        self.smoothing = smoothing
        self.smoothing_min_n_done = smoothing_min_n_done

        self.task_loggers: Dict[int, TaskLogger] = {}

    def handle_event(self, event: Event):
        try:
            task_logger = self.task_loggers[event.task_id]
        except KeyError:
            self.task_loggers[event.task_id] = task_logger = TaskLogger(
                getLogger(event.name),
                level=self.level,
                description=event.description,
                n_total=event.total,
                log_interval=self.log_interval,
                unit=self.unit,
                smoothing=self.smoothing,
                smoothing_min_n_done=self.smoothing_min_n_done,
            )

        task_logger.update(n=event.progress)

        if event.finished:
            del self.task_loggers[event.task_id]
