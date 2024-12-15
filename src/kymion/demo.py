import random
import time
from . import get_progress_reporter

progress_reporter = get_progress_reporter("kymion.demo")


def run_demo():
    for step in progress_reporter.task(
        [
            "Initialization",
            "Pre-processing",
            "Transforming",
            "Finalizing",
            "Cleaning up",
        ],
        description="Overall",
    ):
        print(f"{step}...")
        for _ in progress_reporter.task(
            range(random.randint(10, 1000)), description=step
        ):
            time.sleep(random.uniform(1e-6, 1e-3))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--tqdm", action="store_true", help="Use tqdm handler")
    parser.add_argument("--rich", action="store_true", help="Use rich handler")
    args = parser.parse_args()

    if args.tqdm:
        from kymion.handlers.tqdm import TQDMHandler

        progress_reporter.add_handler(TQDMHandler())

    if args.rich:
        from kymion.handlers.rich import RichHandler

        progress_reporter.add_handler(RichHandler())

    run_demo()
