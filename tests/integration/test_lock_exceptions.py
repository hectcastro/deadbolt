import pytest

from deadbolt import AdvisoryLock


class TestExceptionPropagation:
    def test_exception_propagates_from_context(
        self, conn_params: dict, unique_lock_id: int
    ) -> None:
        """Exceptions raised in context body are not suppressed."""
        lock = AdvisoryLock(lock_id=unique_lock_id, **conn_params)

        with pytest.raises(ValueError, match="test exception"), lock:
            raise ValueError("test exception")

    def test_exception_type_preserved(self, conn_params: dict, unique_lock_id: int) -> None:
        """Original exception type is preserved."""
        lock = AdvisoryLock(lock_id=unique_lock_id, **conn_params)

        class CustomError(Exception):
            pass

        with pytest.raises(CustomError), lock:
            raise CustomError("custom")

    def test_lock_still_released_on_exception(self, conn_params: dict, unique_lock_id: int) -> None:
        """Lock is released even when exception occurs."""
        lock = AdvisoryLock(lock_id=unique_lock_id, **conn_params)

        with pytest.raises(RuntimeError), lock:
            assert lock.is_locked
            raise RuntimeError("boom")

        assert not lock.is_locked
