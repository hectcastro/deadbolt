use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use std::sync::OnceLock;
use tokio::runtime::{Handle, Runtime};
use tokio_postgres::{Client, NoTls};

static RUNTIME: OnceLock<Runtime> = OnceLock::new();

fn get_runtime() -> &'static Runtime {
    RUNTIME.get_or_init(|| Runtime::new().expect("Failed to create tokio runtime"))
}

fn get_handle() -> Handle {
    get_runtime().handle().clone()
}

/// PostgreSQL advisory lock context manager.
///
/// Provides a context manager interface for PostgreSQL session-level
/// advisory locks.
#[pyclass]
pub struct AdvisoryLock {
    /// Database host
    host: String,
    /// Database port
    port: u16,
    /// Database name
    database: String,
    /// Database user
    user: Option<String>,
    /// Database password
    password: Option<String>,
    /// Lock ID (PostgreSQL bigint)
    lock_id: i64,
    /// Active connection, only Some when lock is held
    client: Option<Client>,
}

#[pymethods]
impl AdvisoryLock {
    /// Create a new AdvisoryLock instance.
    ///
    /// Args:
    ///     lock_id: Lock ID (64-bit integer)
    ///     host: Database host
    ///     database: Database name
    ///     user: Database user (optional)
    ///     password: Database password (optional)
    ///     port: Database port (default: 5432)
    #[new]
    #[pyo3(signature = (lock_id, host, database, user=None, password=None, port=5432))]
    fn new(
        lock_id: i64,
        host: String,
        database: String,
        user: Option<String>,
        password: Option<String>,
        port: u16,
    ) -> Self {
        AdvisoryLock {
            host,
            port,
            database,
            user,
            password,
            lock_id,
            client: None,
        }
    }

    /// Context manager entry: acquire the advisory lock.
    ///
    /// Connects to PostgreSQL and executes pg_advisory_lock($1).
    /// Blocks until the lock is acquired.
    ///
    /// Returns:
    ///     self for use in with statement
    ///
    /// Raises:
    ///     RuntimeError: If connection fails or lock acquisition fails
    fn __enter__(mut slf: PyRefMut<'_, Self>) -> PyResult<PyRefMut<'_, Self>> {
        let handle = get_handle();
        let mut parts = vec![
            format!("host={}", slf.host),
            format!("port={}", slf.port),
            format!("dbname={}", slf.database),
        ];
        if let Some(ref user) = slf.user {
            parts.push(format!("user={}", user));
        }
        if let Some(ref password) = slf.password {
            parts.push(format!("password={}", password));
        }
        let dsn = parts.join(" ");
        let lock_id = slf.lock_id;

        // Release GIL while blocking on async operation.
        let client = slf.py().allow_threads(|| {
            handle.block_on(async {
                let task_handle = tokio::spawn(async move {
                    let (client, connection) =
                        tokio_postgres::connect(&dsn, NoTls).await.map_err(|e| {
                            PyRuntimeError::new_err(format!("Connection failed: {}", e))
                        })?;

                    tokio::spawn(async move {
                        if let Err(e) = connection.await {
                            eprintln!("connection error: {}", e);
                        }
                    });

                    client
                        .execute("SELECT pg_advisory_lock($1)", &[&lock_id])
                        .await
                        .map_err(|e| {
                            PyRuntimeError::new_err(format!("Lock acquisition failed: {}", e))
                        })?;

                    Ok::<_, PyErr>(client)
                });

                task_handle
                    .await
                    .map_err(|e| PyRuntimeError::new_err(format!("Task join failed: {}", e)))?
            })
        })?;

        slf.client = Some(client);
        Ok(slf)
    }

    /// Context manager exit: release the advisory lock.
    ///
    /// Executes pg_advisory_unlock($1) and closes the connection.
    ///
    /// Args:
    ///     exc_type: Exception type if an exception occurred
    ///     exc_value: Exception value if an exception occurred
    ///     traceback: Traceback if an exception occurred
    ///
    /// Returns:
    ///     False (do not suppress exceptions)
    ///
    /// Raises:
    ///     RuntimeError: If lock release fails
    #[pyo3(signature = (exc_type=None, exc_value=None, traceback=None))]
    fn __exit__(
        &mut self,
        py: Python<'_>,
        exc_type: Option<PyObject>,
        exc_value: Option<PyObject>,
        traceback: Option<PyObject>,
    ) -> PyResult<bool> {
        let _ = (exc_type, exc_value, traceback);

        if let Some(client) = self.client.take() {
            let handle = get_handle();
            let lock_id = self.lock_id;

            // Release GIL while blocking on async operation.
            py.allow_threads(|| {
                handle.block_on(async {
                    let task_handle = tokio::spawn(async move {
                        client
                            .execute("SELECT pg_advisory_unlock($1)", &[&lock_id])
                            .await
                            .map_err(|e| {
                                PyRuntimeError::new_err(format!("Lock release failed: {}", e))
                            })?;

                        Ok::<_, PyErr>(())
                    });

                    task_handle
                        .await
                        .map_err(|e| PyRuntimeError::new_err(format!("Task join failed: {}", e)))?
                })
            })?;
        }

        Ok(false)
    }

    #[getter]
    fn lock_id(&self) -> i64 {
        self.lock_id
    }

    #[getter]
    fn host(&self) -> &str {
        &self.host
    }

    #[getter]
    fn port(&self) -> u16 {
        self.port
    }

    #[getter]
    fn database(&self) -> &str {
        &self.database
    }

    #[getter]
    fn user(&self) -> Option<&str> {
        self.user.as_deref()
    }

    #[getter]
    fn password(&self) -> Option<&str> {
        self.password.as_deref()
    }

    #[getter]
    fn is_locked(&self) -> bool {
        self.client.is_some()
    }
}

#[pymodule]
fn _deadbolt(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<AdvisoryLock>()?;
    Ok(())
}
