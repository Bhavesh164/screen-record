from __future__ import annotations

import cProfile
import io
import pstats
import queue
import threading
import time


def _bounded_queue_simulation(iterations: int = 5000) -> None:
    frame_queue: queue.Queue[bytes] = queue.Queue(maxsize=3)
    stop_event = threading.Event()

    def producer() -> None:
        for _ in range(iterations):
            payload = b"x" * 4096
            try:
                frame_queue.put_nowait(payload)
            except queue.Full:
                try:
                    frame_queue.get_nowait()
                except queue.Empty:
                    pass
                frame_queue.put_nowait(payload)
            time.sleep(0.001)
        stop_event.set()

    def consumer() -> None:
        while not stop_event.is_set() or not frame_queue.empty():
            try:
                frame_queue.get(timeout=0.05)
            except queue.Empty:
                continue

    producer_thread = threading.Thread(target=producer)
    consumer_thread = threading.Thread(target=consumer)
    producer_thread.start()
    consumer_thread.start()
    producer_thread.join()
    consumer_thread.join()


def main() -> None:
    profiler = cProfile.Profile()
    profiler.enable()
    _bounded_queue_simulation()
    profiler.disable()

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumtime")
    stats.print_stats(15)
    print(stream.getvalue())


if __name__ == "__main__":
    main()
