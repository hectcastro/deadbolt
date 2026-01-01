from collections.abc import Generator

import pytest
from testcontainers.postgres import PostgresContainer

from deadbolt import AdvisoryLock


class TestSpecialCharacters:
    @pytest.fixture(scope="class")
    def postgres_with_special_user(self) -> Generator[dict[str, str | int], None, None]:
        """Provide PostgreSQL with a user that has special characters in password."""
        special_password = "my pass'word\\test"
        special_user = "testuser_special"

        with PostgresContainer("postgres:16-alpine") as postgres:
            sql_password = special_password.replace("'", "''")
            exit_code, output = postgres.exec(
                f"psql -U {postgres.username} -d {postgres.dbname} -c "
                f'"DROP USER IF EXISTS {special_user}; '
                f"CREATE USER {special_user} WITH PASSWORD '{sql_password}'\""
            )

            if exit_code != 0:
                raise RuntimeError(f"Failed to create user: {output.decode()}")

            yield {
                "host": postgres.get_container_host_ip(),
                "port": int(postgres.get_exposed_port(5432)),
                "user": special_user,
                "password": special_password,
                "database": postgres.dbname,
            }

    def test_password_with_all_special_chars(
        self, postgres_with_special_user: dict, lock_id_factory
    ) -> None:
        """Password containing space, single quote, and backslash works correctly."""
        lock_id = lock_id_factory()
        lock = AdvisoryLock(lock_id=lock_id, **postgres_with_special_user)

        with lock:
            assert lock.is_locked is True

        assert lock.is_locked is False
