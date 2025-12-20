import pytest


def test_lock_instantiation():
    """AdvisoryLock can be instantiated with connection params and lock_id."""
    from deadbolt import AdvisoryLock

    lock = AdvisoryLock(lock_id=12345, host="localhost", database="test")

    assert lock.host == "localhost"
    assert lock.database == "test"
    assert lock.port == 5432
    assert lock.lock_id == 12345
    assert lock.is_locked is False


def test_lock_properties():
    """AdvisoryLock exposes connection properties."""
    from deadbolt import AdvisoryLock

    lock = AdvisoryLock(lock_id=99999, host="localhost", database="test", user="postgres")

    assert isinstance(lock.host, str)
    assert isinstance(lock.database, str)
    assert isinstance(lock.port, int)
    assert isinstance(lock.user, str)
    assert isinstance(lock.lock_id, int)
    assert isinstance(lock.is_locked, bool)


def test_lock_connection_failure():
    """AdvisoryLock raises RuntimeError on connection failure."""
    from deadbolt import AdvisoryLock

    lock = AdvisoryLock(lock_id=1, host="invalid.host", database="test")

    with pytest.raises(RuntimeError, match="Connection failed"), lock:
        pass


def test_lock_id_types():
    """AdvisoryLock accepts various integer types for lock ID."""
    from deadbolt import AdvisoryLock

    # Small int
    lock1 = AdvisoryLock(lock_id=1, host="localhost", database="test")
    assert lock1.lock_id == 1

    # Large int (within i64 range)
    lock2 = AdvisoryLock(lock_id=9223372036854775807, host="localhost", database="test")
    assert lock2.lock_id == 9223372036854775807

    # Negative int
    lock3 = AdvisoryLock(lock_id=-1, host="localhost", database="test")
    assert lock3.lock_id == -1
