# 💾 SQLAlchemyStorage

`camouchat.StorageDB.sqlalchemy_storage`

`SQLAlchemyStorage` is the async, queue-backed database engine for CamouChat. It persists `Message` objects to SQLite, PostgreSQL, or MySQL using SQLAlchemy's async ORM. A background writer task consumes from a queue and commits in configurable batches to maximize throughput without blocking the bot's automation loop.

---

## 🏗️ Architecture Overview

```
Bot automation loop
      │
      │  await storage.enqueue_insert(msgs)
      ▼
asyncio.Queue  ───────────────────────────────────────►  Background Writer Task
                                                              │
                                                              │ Every flush_interval seconds
                                                              │ OR every batch_size messages
                                                              ▼
                                                    SQLAlchemy AsyncSession.add_all()
                                                              │
                                                              ▼
                                                    Database (SQLite / PostgreSQL / MySQL)
```

The bot never blocks on DB writes — `enqueue_insert()` is an `await queue.put()`, which is effectively instantaneous. The writer task runs independently and commits in the background.

---

## 🛠️ Constructor

```python
SQLAlchemyStorage(
    queue: asyncio.Queue,
    log: Optional[Union[Logger, LoggerAdapter]] = None,
    database_url: str = "sqlite+aiosqlite:///messages.db",
    batch_size: int = 50,
    flush_interval: float = 2.0,
    echo: bool = False,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `queue` | `asyncio.Queue` | ✅ Yes | The shared async queue. All `enqueue_insert()` calls put messages here. Must be created externally and passed in (supports sharing a single queue across the app). |
| `log` | `Logger \| LoggerAdapter` | `camouchatLogger` | Logger for DB events, errors, and batch writes. |
| `database_url` | `str` | `"sqlite+aiosqlite:///messages.db"` | Full SQLAlchemy async connection URL. Examples below. |
| `batch_size` | `int` | `50` | Max batched messages before an auto-flush. Lower = more frequent writes. |
| `flush_interval` | `float` | `2.0` | Max seconds between flushes even if the batch isn't full. |
| `echo` | `bool` | `False` | Enable SQLAlchemy SQL query logging (verbose, for debugging only). |

**Connection URL examples**:

```python
# SQLite (default — great for single-bot setups)
"sqlite+aiosqlite:///path/to/messages.db"

# PostgreSQL (for high-scale, multi-bot deployments)
"postgresql+asyncpg://user:pass@localhost/camouchat"

# MySQL
"mysql+aiomysql://user:pass@localhost/camouchat"
```

---

## 🏭 Factory: `from_profile()`

The recommended way to create a `SQLAlchemyStorage` instance. Reads the `database_url` directly from the `ProfileInfo` object so you don't need to hardcode connection strings.

```python
import asyncio
from camouchat.StorageDB import SQLAlchemyStorage
from camouchat.camouchat_logger import camouchatLogger

queue = asyncio.Queue()

storage = SQLAlchemyStorage.from_profile(
    profile=profile,       # ProfileInfo from ProfileManager
    queue=queue,
    log=camouchatLogger,
    batch_size=50,         # Optional (default: 50)
    flush_interval=2.0,    # Optional (default: 2.0s)
)
```

---

## 🔄 Lifecycle

`SQLAlchemyStorage` implements the async context manager protocol for clean lifecycle management:

```python
async with storage:       # → init_db() + create_table() + migration + start_writer()
    # ... bot runs here, messages accumulate ...
    await storage.enqueue_insert(msgs=new_messages)

# __aexit__ → close_db() → flushes remaining queue → disposes engine
```

Or manually:

```python
await storage.init_db()             # Creates async engine + session factory
await storage.create_table()        # Runs CREATE TABLE IF NOT EXISTS
await storage._migrate_add_encryption_columns()  # Safe schema migration
await storage.start_writer()        # Starts background queue consumer task

# ... run bot ...

await storage.close_db()            # Cancels writer, flushes, disposes engine
```

> [!NOTE]
> `_migrate_add_encryption_columns()` is a safe migration step that adds `encrypted_message`, `encryption_nonce`, `encrypted_chat_name`, and `chat_name_nonce` columns to existing `messages` tables. SQLite doesn't support `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, so errors are silently swallowed — new installs always have these columns from `create_table()`.

---

## 📦 Key Methods

### `enqueue_insert(msgs) → None`

Puts all messages in the queue for background insertion. Returns immediately — does not wait for DB write.

```python
await storage.enqueue_insert(msgs=new_messages)
```

---

### `check_message_if_exists_async(msg_id) → bool`

Async deduplication check. Returns `True` if a message with `msg_id` already exists in the database. Called by `MessageProcessor.fetch_messages()` for every scraped message.

```python
already_stored = await storage.check_message_if_exists_async(msg_id="ABC123")
```

---

### `get_all_messages_async(limit=1000, offset=0) → List[Dict]`

Returns all stored messages as list of dicts, ordered by `id DESC` (newest first). When encryption is active, `raw_data` in returned rows will be empty — use `get_decrypted_messages_async()` instead.

```python
rows = await storage.get_all_messages_async(limit=100, offset=0)
```

---

### `get_messages_by_chat(chat_name, limit=100) → List[Dict]`

Filters messages by `parent_chat_name`. When encryption is enabled, pass the **HMAC digest** (from `MessageProcessor._hmac_chat_name()`) instead of the real name, since the real name is not stored in plaintext.

```python
rows = await storage.get_messages_by_chat(chat_name="MyFriend", limit=50)
```

---

### `get_decrypted_messages_async(key, limit=1000, offset=0) → List[Dict]`

Fetches all messages and decrypts `raw_data` (body) and `parent_chat_name` on-the-fly using the provided AES-256 key. The returned dicts have plaintext values — nothing is written back to the DB.

```python
key = pm.get_key(Platform.WHATSAPP, "SecureBot")
rows = await storage.get_decrypted_messages_async(key=key, limit=500)

for row in rows:
    print(f"[{row['direction']}] {row['parent_chat_name']}: {row['raw_data']}")
```

> [!TIP]
> This is the **primary way to read encrypted message data**. Pass the key from `ProfileManager.get_key()` — the same key used during storage.

---

## 🗄️ Database Schema

The `messages` table (defined in `StorageDB/models.py`):

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER` PK | Auto-increment primary key. |
| `message_id` | `VARCHAR(255)` UNIQUE | WhatsApp's unique message identifier (`data-id`). Used for deduplication. |
| `raw_data` | `TEXT` | Plaintext message body. Empty string when encryption is enabled. |
| `encrypted_message` | `TEXT` | Base64 AES-256-GCM ciphertext (only when encryption is on). |
| `encryption_nonce` | `VARCHAR(255)` | Base64 12-byte nonce for decrypting `encrypted_message`. |
| `data_type` | `VARCHAR(50)` | Message type (e.g., text, media). Optional. |
| `direction` | `VARCHAR(10)` | `"in"` or `"out"`. |
| `parent_chat_name` | `VARCHAR(255)` | Chat name (plaintext) or HMAC digest (when encryption is on). Indexed. |
| `parent_chat_id` | `VARCHAR(255)` | Chat ID identifier. Indexed. |
| `encrypted_chat_name` | `TEXT` | Base64 encrypted chat name (only when encryption is on). |
| `chat_name_nonce` | `VARCHAR(255)` | Base64 nonce for decrypting `encrypted_chat_name`. |
| `system_hit_time` | `FLOAT` | Unix timestamp when the message was scraped by the bot. |
| `created_at` | `DATETIME` | UTC timestamp of DB insertion. Indexed. |

**Composite indexes**: `(parent_chat_name, created_at)` and `(parent_chat_id, created_at)` for efficient per-chat history queries.

---

## 💡 Pro Tips

- **Singleton**: `SQLAlchemyStorage` uses a `database_url`-keyed class-level singleton. Two instances with the same `database_url` return the same object. This prevents duplicate engine and writer task creation.
- **Queue sharing**: The `asyncio.Queue` is shared between the storage instance and `MessageProcessor`. One queue per bot session is the recommended pattern.
- **`StorageType` enum**: Use `StorageType.SQLITE`, `StorageType.MYSQL`, or `StorageType.POSTGRESQL` in `ProfileManager.create_profile()` to auto-generate the correct `database_url` — no manual URL construction needed.
