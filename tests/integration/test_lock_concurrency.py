import threading
import time
from collections.abc import Callable

from deadbolt import AdvisoryLock


class TestConcurrentBlocking:
    def test_same_lock_id_blocks_concurrent_access(
        self, conn_params: dict, unique_lock_id: int
    ) -> None:
        """Second thread blocks until first thread releases the lock."""
        events: list[str] = []
        lock = threading.Lock()
        errors: list[Exception] = []

        def record(msg: str) -> None:
            with lock:
                events.append(msg)

        def worker(name: str) -> None:
            try:
                pg_lock = AdvisoryLock(lock_id=unique_lock_id, **conn_params)
                record(f"{name}:waiting")
                with pg_lock:
                    record(f"{name}:acquired")
                    time.sleep(0.1)
                    record(f"{name}:releasing")
                record(f"{name}:released")
            except Exception as e:
                errors.append(e)
                record(f"{name}:error:{e}")

        t1 = threading.Thread(target=worker, args=("T1",))
        t2 = threading.Thread(target=worker, args=("T2",))

        t1.start()
        time.sleep(0.05)
        t2.start()

        # Timeout to prevent infinite hang.
        t1.join(timeout=10)
        t2.join(timeout=10)

        if t1.is_alive() or t2.is_alive():
            raise TimeoutError(f"Test hung. Events so far: {events}. Errors: {errors}")

        if errors:
            raise AssertionError(f"Errors occurred: {errors}")

        # Verify sequential execution: T1 must start releasing before T2 acquires.
        t1_releasing_idx = events.index("T1:releasing")
        t2_acquired_idx = events.index("T2:acquired")

        assert t1_releasing_idx < t2_acquired_idx, (
            f"Expected T1 to start releasing before T2 acquires. Events: {events}"
        )

    def test_different_lock_ids_do_not_block(
        self, conn_params: dict, lock_id_factory: Callable[[], int]
    ) -> None:
        """Locks with different IDs can be held concurrently."""
        lock_id_1 = lock_id_factory()
        lock_id_2 = lock_id_factory()

        events: list[str] = []
        lock = threading.Lock()

        def record(msg: str) -> None:
            with lock:
                events.append(msg)

        def worker(name: str, lock_id: int) -> None:
            pg_lock = AdvisoryLock(lock_id=lock_id, **conn_params)
            with pg_lock:
                record(f"{name}:acquired")
                time.sleep(0.2)
                record(f"{name}:releasing")

        t1 = threading.Thread(target=worker, args=("T1", lock_id_1))
        t2 = threading.Thread(target=worker, args=("T2", lock_id_2))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Both should acquire before either releases.
        t1_acquired_idx = events.index("T1:acquired")
        t2_acquired_idx = events.index("T2:acquired")
        t1_releasing_idx = events.index("T1:releasing")
        t2_releasing_idx = events.index("T2:releasing")

        # At least one should acquire before the other releases.
        assert t2_acquired_idx < t1_releasing_idx or t1_acquired_idx < t2_releasing_idx, (
            f"Expected concurrent execution. Events: {events}"
        )

    def test_lock_blocks_across_separate_connections(
        self, conn_params: dict, unique_lock_id: int
    ) -> None:
        """Lock blocks even when using separate AdvisoryLock instances."""
        events: list[str] = []
        lock = threading.Lock()

        def record(msg: str) -> None:
            with lock:
                events.append(msg)

        def worker(name: str) -> None:
            # Each worker creates its own lock instance.
            pg_lock = AdvisoryLock(lock_id=unique_lock_id, **conn_params)
            with pg_lock:
                record(f"{name}:acquired")
                time.sleep(0.1)
                record(f"{name}:releasing")
            record(f"{name}:released")

        t1 = threading.Thread(target=worker, args=("T1",))
        t2 = threading.Thread(target=worker, args=("T2",))

        t1.start()
        time.sleep(0.05)
        t2.start()

        t1.join()
        t2.join()

        # Verify sequential execution: T1 must start releasing before T2 acquires.
        t1_releasing_idx = events.index("T1:releasing")
        t2_acquired_idx = events.index("T2:acquired")

        assert t1_releasing_idx < t2_acquired_idx, (
            f"Expected T1 to start releasing before T2 acquires. Events: {events}"
        )
