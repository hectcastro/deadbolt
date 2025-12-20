from collections.abc import Callable, Generator

import pytest


@pytest.fixture
def lock_id_factory() -> Callable[[], int]:
    """Factory for generating unique lock IDs per test."""
    counter = 0

    def _factory() -> int:
        nonlocal counter
        counter += 1
        return 1_000_000_000 + counter

    return _factory


@pytest.fixture(scope="session")
def conn_params() -> Generator[dict[str, str | int], None, None]:
    """Provide PostgreSQL connection parameters for integration tests."""
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as postgres:
        yield {
            "host": postgres.get_container_host_ip(),
            "port": int(postgres.get_exposed_port(5432)),
            "user": postgres.username,
            "password": postgres.password,
            "database": postgres.dbname,
        }


@pytest.fixture
def unique_lock_id(lock_id_factory: Callable[[], int]) -> int:
    """Provide a unique lock ID for a single test."""
    return lock_id_factory()
