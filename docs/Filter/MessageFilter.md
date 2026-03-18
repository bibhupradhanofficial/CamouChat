# 🔍 MessageFilter

`camouchat.Filter.message_filter`

`MessageFilter` is an independent, stateful message rate-limiter. It protects your bot from being overwhelmed by high-message-volume chats and implements a three-tier **deliver / defer / drop** state machine per chat.

`MessageFilter` is not tied to any specific platform — it works with any `MessageInterface` implementation.

---

## 🛠️ Constructor

```python
MessageFilter(
    LimitTime: int = 3600,
    Max_Messages_Per_Window: int = 10,
    Window_Seconds: int = 60,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `LimitTime` | `int` | `3600` | Seconds before a **deferred** chat's messages are hard-dropped and the state is reset (1 hour). A chat deferred for longer than this limit is considered permanently unresponsive and its queued messages are discarded. |
| `Max_Messages_Per_Window` | `int` | `10` | Maximum messages allowed from a single chat within `Window_Seconds` before rate-limiting kicks in. |
| `Window_Seconds` | `int` | `60` | Duration in seconds of the rolling rate-limit window. Resets every 60 seconds by default. |

```python
from camouchat.Filter import MessageFilter

msg_filter = MessageFilter(
    LimitTime=3600,               # Drop deferred messages after 1 hour
    Max_Messages_Per_Window=10,   # Allow up to 10 messages per 60 seconds per chat
    Window_Seconds=60,
)
```

---

## 📦 Methods

### `apply(msgs) → List[T]`

The core filter method. Takes a list of messages (all from the **same chat**) and returns only the messages that are allowed to pass under the current rate-limit state.

| Parameter | Type | Description |
|-----------|------|-------------|
| `msgs` | `List[T]` where `T: MessageInterface` | Messages to filter. All must belong to the same chat (same `parent_chat`). |

```python
# After fetch_messages(), pass to filter
allowed = msg_filter.apply(msgs=new_messages)

# Use allowed messages for your bot logic
for msg in allowed:
    process(msg)
```

> [!NOTE]
> `apply()` raises `MessageFilterError` if messages from more than one chat are mixed in the input list. Always call `apply()` on messages from a single chat.

---

## 🔄 State Machine

Each chat has its own `State` object in `MessageFilter.StateMap`. The state machine has three outcomes per `apply()` call:

### 1. ✅ Deliver
All messages pass when `state.count + batch_size ≤ Max_Messages_Per_Window`.

```
state.count  →  incremented by batch_size
state.last_seen  →  updated
→  returns the full msgs list
```

### 2. ⏳ Defer
Rate limit hit: `state.count + batch_size > Max_Messages_Per_Window`.

```
state.defer_since  →  set to now (if not already set)
msgs  →  pushed to MessageFilter.Defer_queue
→  returns []  (empty, nothing delivered this cycle)
```

The messages are held in `Defer_queue` for potential future processing by the application.

### 3. 🗑️ Drop
Chat has been in deferred state for longer than `LimitTime`:  
`now - state.defer_since > LimitTime`

```
state.reset()  →  clears count, defer_since, last_seen
→  returns the full msgs list (hard-reset — messages pass through to avoid starvation)
```

The hard-drop+reset clears the backlog and lets the chat "start fresh." This prevents a single very-active chat from permanently blocking the filter queue.

---

## 📊 Internal Data Classes

### `State`

Per-chat rate-limit state:

| Field | Type | Description |
|-------|------|-------------|
| `defer_since` | `float \| None` | Unix timestamp when this chat first entered deferred state. `None` if not deferred. |
| `last_seen` | `float \| None` | Unix timestamp of the last successful delivery. |
| `window_start` | `float` | Unix timestamp when the current rate-limit window started. |
| `count` | `int` | Number of messages delivered in the current window. |

`state.reset()` zeroes all fields and resets `window_start` to `time.time()`.

---

### `BindData`

Used internally to structure deferred messages in `Defer_queue`:

| Field | Type | Description |
|-------|------|-------------|
| `chat` | `ChatInterface` | The chat this batch belongs to. |
| `Messages` | `Sequence[MessageInterface]` | The deferred message batch. |
| `seen` | `float` | Unix timestamp when this batch was deferred. |

---

## 🗃️ Class-Level State Storage

Both `StateMap` and `Defer_queue` are **class-level** (shared across all instances):

```python
class MessageFilter:
    StateMap: dict[str, State] = {}     # chat_key → State
    Defer_queue: Queue[BindData] = Queue()
```

This means all `MessageFilter` instances share the same state — even if you create two filter objects, they reference the same `StateMap`. In practice, one filter instance per bot session is the standard pattern.

> [!NOTE]
> Chat identity is determined by `chat._chat_key()`, which is defined on the `ChatInterface` base class. For WhatsApp, this is typically a combination of the chat name and ID.

---

## 💡 NoOp Alternative

If you don't need rate-limiting, pass `None` as `filter_obj` in `MessageProcessor`. It automatically substitutes `NoOpMessageFilter`, which passes all messages through without any state management.

```python
from camouchat.NoOpPattern import NoOpMessageFilter

# Equivalent to not passing filter_obj to MessageProcessor
pass_all = NoOpMessageFilter()
allowed = pass_all.apply(msgs=messages)  # Always returns messages unchanged
```

---

## 💡 Pro Tips

- **Tune for your use case**: A support bot handling high-volume group chats should use a looser filter (`Max_Messages_Per_Window=50, Window_Seconds=30`). A monitoring bot should use a tighter one (`Max_Messages_Per_Window=5, Window_Seconds=60`).
- **`Defer_queue` is not auto-processed**: The deferred messages sit in `MessageFilter.Defer_queue` indefinitely unless your application explicitly reads and re-processes them. For simple bots, you can ignore the defer queue — deferred messages will eventually be hard-dropped after `LimitTime` seconds and released on the next `apply()` cycle.
- **Window resets automatically**: After `Window_Seconds` has elapsed since `window_start`, the next `apply()` call resets `count` to zero and starts a fresh window.
