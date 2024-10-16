import threading
import time
from unittest.mock import ANY, Mock


from kymion import NonBlockingRelay, ProgressHandler, get_progress_reporter


def test_task():
    handler = Mock(wraps=ProgressHandler())

    progress_reporter = get_progress_reporter("test_reporter")
    progress_reporter.add_handler(handler)

    # Test "raw" update and finish
    t1 = progress_reporter.task(total=10)

    # Handler got an initialization event
    handler.handle_event.assert_called_with((t1.id, ANY, 0, 10, None, False))

    for _ in range(10):
        t1.update()
    t1.finish()

    # Handler got a "finished" event
    handler.handle_event.assert_called_with((t1.id, ANY, 10, 10, None, True))

    # Test context manager
    with progress_reporter.task(range(10)) as t2:
        for _ in t2:
            pass

    # Handler got an initialization and "finished" event
    handler.handle_event.assert_any_call((t2.id, ANY, 0, 10, None, False))
    handler.handle_event.assert_called_with((t2.id, ANY, 10, 10, None, True))


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
    handler.handle_event.assert_called_with((t.id, ANY, 10, 10, None, True))


def test_thread_safety():
    class VerySlowHandler(ProgressHandler):
        def handle_event(self, event):
            print(event[0])
            time.sleep(1)

    very_slow_handler = Mock(wraps=VerySlowHandler())
    relay = Mock(wraps=NonBlockingRelay())
    relay.add_handler(very_slow_handler)

    progress_reporter = get_progress_reporter("thread_safe_reporter")
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
        relay.handle_event.assert_any_call((ANY, ANY, 0, 5, str(i), False))
        relay.handle_event.assert_any_call((ANY, ANY, 5, 5, str(i), True))

    assert very_slow_handler.handle_event.call_count < relay.handle_event.call_count
