# deadbolt

PostgreSQL advisory lock context manager for Python, implemented in Rust using PyO3 and `tokio-postgres`.

## Usage

```python
from deadbolt import AdvisoryLock

# Create a lock instance.
lock = AdvisoryLock(
    lock_id=12345,
    host="localhost",
    database="mydb",
    user="postgres",
    password="secret",
)

with lock:
    # Critical section - lock is held
    do_exclusive_work()
# Lock is released automatically
```
