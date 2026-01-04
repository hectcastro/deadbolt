use once_cell::sync::OnceCell;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use std::sync::{Arc, Mutex};
use tokio::runtime::{Handle, Runtime};
use tokio_postgres::{Client, NoTls};

static RUNTIME: OnceCell<Runtime> = OnceCell::new();

fn get_runtime() -> PyResult<&'static Runtime> {
    RUNTIME
        .get_or_try_init(Runtime::new)
        .map_err(|e| PyRuntimeError::new_err(format!("Failed to create tokio runtime: {}", e)))
}

fn get_handle() -> PyResult<Handle> {
    Ok(get_runtime()?.handle().clone())
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
    /// Timeout in seconds for lock acquisition (None = no timeout)
    timeout: Option<u64>,
    /// Active connection, only Some when lock is held
    client: Option<Client>,
    /// Shared state to track connection errors
    connection_error: Arc<Mutex<Option<String>>>,
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
    ///     timeout: Timeout in seconds for lock acquisition (optional, no timeout if not set)
    #[new]
    #[pyo3(signature = (lock_id, host, database, user=None, password=None, port=5432, timeout=None))]
    fn new(
        lock_id: i64,
        host: String,
        database: String,
        user: Option<String>,
        password: Option<String>,
        port: u16,
        timeout: Option<u64>,
    ) -> Self {
        AdvisoryLock {
            host,
            port,
            database,
            user,
            password,
            lock_id,
            timeout,
            client: None,
            connection_error: Arc::new(Mutex::new(None)),
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
        if slf.client.is_some() {
            return Err(PyRuntimeError::new_err(format!(
                "Lock is already held (lock_id={}); re-entrant use is not supported",
                slf.lock_id
            )));
        }

        let handle = get_handle()?;

        let mut config = tokio_postgres::Config::new();
        config.host(&slf.host);
        config.port(slf.port);
        config.dbname(&slf.database);
        if let Some(ref user) = slf.user {
            config.user(user);
        }
        if let Some(ref password) = slf.password {
            config.password(password);
        }

        let lock_id = slf.lock_id;
        let timeout_duration = slf.timeout;
        let error_state = Arc::clone(&slf.connection_error);

        // Release GIL while blocking on async operation.
        let client = slf.py().detach(|| {
            handle.block_on(async {
                let acquire_lock = async {
                    let task_handle = tokio::spawn(async move {
                        let (client, connection) = config.connect(NoTls).await.map_err(|e| {
                            PyRuntimeError::new_err(format!("Connection failed: {}", e))
                        })?;

                        // Spawn connection driver with error tracking
                        let error_state_clone = Arc::clone(&error_state);
                        tokio::spawn(async move {
                            if let Err(e) = connection.await {
                                let error_msg = format!("Connection lost: {}", e);
                                eprintln!("{}", error_msg);
                                if let Ok(mut err) = error_state_clone.lock() {
                                    *err = Some(error_msg);
                                }
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
                };

                // Apply timeout if specified
                if let Some(secs) = timeout_duration {
                    tokio::time::timeout(std::time::Duration::from_secs(secs), acquire_lock)
                        .await
                        .map_err(|_| {
                            PyRuntimeError::new_err(format!(
                                "Lock acquisition timed out after {} seconds",
                                secs
                            ))
                        })?
                } else {
                    acquire_lock.await
                }
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
        exc_type: Option<Py<PyAny>>,
        exc_value: Option<Py<PyAny>>,
        traceback: Option<Py<PyAny>>,
    ) -> PyResult<bool> {
        let _ = (exc_type, exc_value, traceback);

        if let Some(client) = self.client.take() {
            let handle = get_handle()?;
            let lock_id = self.lock_id;

            // Release GIL while blocking on async operation.
            py.detach(|| {
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

            // Check if connection error occurred during the lock lifetime
            if let Ok(err_lock) = self.connection_error.lock() {
                if let Some(ref error_msg) = *err_lock {
                    eprintln!(
                        "Warning: {}. Lock may have been released early by PostgreSQL.",
                        error_msg
                    );
                }
            }
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

    /// Whether a client connection handle exists.
    ///
    /// Note: This reflects whether the client handle is present, not whether
    /// the lock is definitely held on the server. If the connection drops
    /// unexpectedly, this may return True even though the server-side lock
    /// has been released.
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
