"""Type stubs for the internal _deadbolt Rust extension module."""

from types import TracebackType
from typing import Self

class AdvisoryLock:
    def __init__(
        self,
        lock_id: int,
        host: str,
        database: str,
        user: str | None = None,
        password: str | None = None,
        port: int = 5432,
    ) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool: ...
    @property
    def lock_id(self) -> int: ...
    @property
    def host(self) -> str: ...
    @property
    def port(self) -> int: ...
    @property
    def database(self) -> str: ...
    @property
    def user(self) -> str | None: ...
    @property
    def password(self) -> str | None: ...
    @property
    def is_locked(self) -> bool: ...
