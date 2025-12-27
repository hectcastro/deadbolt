import pytest

from deadbolt import AdvisoryLock


class TestLockLifecycle:
    def test_is_locked_transitions(self, conn_params: dict, unique_lock_id: int) -> None:
        """is_locked toggles on enter and resets on exit."""
        lock = AdvisoryLock(lock_id=unique_lock_id, **conn_params)

        assert lock.is_locked is False

        with lock:
            assert lock.is_locked is True

        assert lock.is_locked is False

    def test_context_manager_returns_self(self, conn_params: dict, unique_lock_id: int) -> None:
        """Context manager returns the lock instance."""
        lock = AdvisoryLock(lock_id=unique_lock_id, **conn_params)

        with lock as acquired:
            assert acquired is lock

    def test_reentrant_use_raises_error(self, conn_params: dict, unique_lock_id: int) -> None:
        """Nested use of same lock instance raises RuntimeError."""
        lock = AdvisoryLock(lock_id=unique_lock_id, **conn_params)

        with lock:  # noqa: SIM117
            with pytest.raises(RuntimeError, match="already held"):
                with lock:
                    pass
