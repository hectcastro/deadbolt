from types import TracebackType
from typing import Self

class AdvisoryLock:
    """PostgreSQL advisory lock context manager.

    Provides a context manager interface for PostgreSQL session-level
    advisory locks.

    Example:
        ```python
        from deadbolt import AdvisoryLock

        lock = AdvisoryLock(
            lock_id=12345,
            host="localhost",
            database="mydb",
            user="postgres",
            password="secret",
        )
        with lock:
            do_exclusive_work()
        # Lock is released
        ```
    """

    def __init__(
        self,
        lock_id: int,
        host: str,
        database: str,
        user: str | None = None,
        password: str | None = None,
        port: int = 5432,
    ) -> None:
        """Create a new AdvisoryLock instance.

        Args:
            lock_id: Lock ID (64-bit signed integer)
            host: Database host
            database: Database name
            user: Database user (optional)
            password: Database password (optional)
            port: Database port (default: 5432)
        """
        ...

    def __enter__(self) -> Self:
        """Acquire the advisory lock.

        Connects to PostgreSQL and executes pg_advisory_lock($1).
        Blocks until the lock is acquired.

        Returns:
            Self for use in `with` statement

        Raises:
            RuntimeError: If connection fails or lock acquisition fails
        """
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """Release the advisory lock.

        Executes pg_advisory_unlock($1) and closes the connection.

        Args:
            exc_type: Exception type if an exception occurred
            exc_value: Exception value if an exception occurred
            traceback: Traceback if an exception occurred

        Returns:
            False (exceptions are not suppressed)

        Raises:
            RuntimeError: If lock release fails
        """
        ...

    @property
    def lock_id(self) -> int:
        """The lock ID."""
        ...

    @property
    def host(self) -> str:
        """The database host."""
        ...

    @property
    def port(self) -> int:
        """The database port."""
        ...

    @property
    def database(self) -> str:
        """The database name."""
        ...

    @property
    def user(self) -> str | None:
        """The database user."""
        ...

    @property
    def password(self) -> str | None:
        """The database password."""
        ...

    @property
    def is_locked(self) -> bool:
        """Whether the lock is currently held."""
        ...
