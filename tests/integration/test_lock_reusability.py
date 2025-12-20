import pytest

from deadbolt import AdvisoryLock


class TestLockReusability:
    def test_lock_can_be_used_twice(self, conn_params: dict, unique_lock_id: int) -> None:
        """Same lock instance works for two consecutive contexts."""
        lock = AdvisoryLock(lock_id=unique_lock_id, **conn_params)

        with lock:
            assert lock.is_locked
        assert not lock.is_locked

        with lock:
            assert lock.is_locked
        assert not lock.is_locked

    def test_lock_can_be_used_many_times(self, conn_params: dict, unique_lock_id: int) -> None:
        """Same lock instance works for many consecutive contexts."""
        lock = AdvisoryLock(lock_id=unique_lock_id, **conn_params)

        for i in range(5):
            with lock:
                assert lock.is_locked, f"Failed on iteration {i}"
            assert not lock.is_locked, f"Failed after iteration {i}"

    def test_lock_reusable_after_exception(self, conn_params: dict, unique_lock_id: int) -> None:
        """Lock can be reused after an exception in previous context."""
        lock = AdvisoryLock(lock_id=unique_lock_id, **conn_params)

        with pytest.raises(RuntimeError), lock:
            raise RuntimeError("simulated failure")

        with lock:
            assert lock.is_locked

        assert not lock.is_locked
