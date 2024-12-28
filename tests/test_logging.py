import logging
import time
from kymion.handlers.logging import LoggingHandler
from kymion.core import get_progress_reporter


def test_logging():
    progress_handler = LoggingHandler(log_interval=0.1)
    progress_reporter = get_progress_reporter("test_logging")
    progress_reporter.add_handler(progress_handler)

    logger = logging.getLogger("test_logging")
    logger.setLevel(logging.INFO)

    class _LoggingHandler(logging.Handler):
        def __init__(self, level: int | str = 0) -> None:
            super().__init__(level)

            self.messages = []

        def emit(self, record: logging.LogRecord) -> None:
            self.messages.append(record.msg)

    logging_handler = _LoggingHandler()
    logging_handler.setLevel(logging.INFO)
    logger.addHandler(logging_handler)

    for _ in progress_reporter.task(range(10)):
        time.sleep(0.1)

    print(logging_handler.messages)

    # Ensure that the handler logged the expected messages
