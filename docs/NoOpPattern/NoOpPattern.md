# 🔲 NoOpPattern

`camouchat.NoOpPattern`

CamouChat's `NoOpPattern` module provides two stub implementations that silently absorb method calls without performing any real work. They exist so that `MessageProcessor` (and any other component that accepts optional backends) can function without requiring a real database or rate-limiter to be configured.

---

## Why NoOp?

`MessageProcessor` requires `storage_obj` and `filter_obj` arguments, but neither is mandatory for simple use cases. Instead of scattering `if obj is not None:` guards throughout the message pipeline, CamouChat injects these stub objects when the real ones are not provided.

This keeps the pipeline code clean, always-callable, and trivially testable.

---

## `NoOpStorage`

`camouchat.NoOpPattern.NoOpStorage`

A no-op implementation of `StorageInterface`. Every storage method either returns immediately, returns a safe empty value, or does nothing.

```python
from camouchat.NoOpPattern import NoOpStorage

storage = NoOpStorage()

await storage.init_db()          # → None (no-op)
await storage.create_table()     # → None (no-op)
await storage.start_writer()     # → None (no-op)
await storage.enqueue_insert(msgs)  # → None (messages discarded)
await storage.close_db()         # → None (no-op)

exists = await storage.check_message_if_exists_async("msg_123")
# Always returns False — deduplication is always disabled

rows = storage.get_all_messages()
# Always returns [] — no data is ever persisted
```

> [!NOTE]
> `MessageProcessor` logs `"Storage not provided → using NoOpStorage."` at INFO level when it substitutes the NoOp. This makes it obvious in logs that persistence is disabled for a session.

---

## `NoOpMessageFilter`

`camouchat.NoOpPattern.NoOpMessageFilter`

A no-op implementation of `MessageFilter`. The `apply()` method returns the input list unchanged — every message passes through, no rate-limiting, no deferring, no state.

```python
from camouchat.NoOpPattern import NoOpMessageFilter

f = NoOpMessageFilter()
allowed = f.apply(msgs=messages)
# → returns messages unchanged (pass-all)
```

> [!NOTE]
> `MessageProcessor` logs `"Filter not provided → using NoOpMessageFilter."` at INFO level.

---

## When to Use

| Scenario | Use |
|----------|-----|
| CI / unit tests | ✅ Always — no DB setup needed |
| Quick prototyping | ✅ Skip setup, focus on logic |
| Production bots | ❌ Use `SQLAlchemyStorage` + `MessageFilter` |
| Read-only scrapers | ✅ If you don't need to persist messages |

---

## 💡 Pro Tip

You never need to import or instantiate `NoOpStorage` / `NoOpMessageFilter` directly in production code. Simply omit `storage_obj` and `filter_obj` from `MessageProcessor.__init__()` and the stubs are injected automatically:

```python
# This is all you need for an in-memory-only scraper:
msg_proc = MessageProcessor(
    chat_processor=chat_proc,
    page=page,
    ui_config=ui_config,
    # No storage_obj → NoOpStorage is used
    # No filter_obj  → NoOpMessageFilter is used
)
```
