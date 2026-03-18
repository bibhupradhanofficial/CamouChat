# 📝 Logger

`camouchat.camouchat_logger`

CamouChat ships with a production-ready logging setup that provides **colored console output**, **rotating file logs**, **JSON formatting** (optional), and **profile-aware contextual logging**. All built on top of Python's standard `logging` module.

---

## 🗂️ What's Available

```python
from camouchat.camouchat_logger import (
    camouchatLogger,           # Global default logger (profile_id="GLOBAL")
    browser_logger,            # Dedicated browser-only logger
    get_profile_logger,        # Factory: returns a profile-scoped logger
    get_browser_profile_logger,# Factory: returns a browser logger for a profile
    CamouChatLoggerAdapter,    # LoggerAdapter subclass (for custom adapters)
    JSONFormatter,             # Optional JSON log formatter
)
```

---

## 🖨️ Default Loggers

### `camouchatLogger`

The global default logger. All SDK classes use this if no `log` parameter is provided. It outputs to both the **console** (colored) and a **rotating file** (`ErrorTrace.log`).

```python
from camouchat.camouchat_logger import camouchatLogger

camouchatLogger.info("Bot started.")
camouchatLogger.warning("Rate limit approaching.")
camouchatLogger.error("Failed to extract messages.", exc_info=True)
```

Log format:
```
2026-03-18 22:30:01,234 | INFO | [GLOBAL][12345] | tweakio | Bot started.
```
- `[GLOBAL]` — the `profile_id` (always `"GLOBAL"` for the default adapter).
- `[12345]` — the OS process ID.

---

### `browser_logger`

Same structure as `camouchatLogger` but writes to a separate **`browser.log`** file. Used internally by browser-related classes to separate browser lifecycle events from application events.

```python
from camouchat.camouchat_logger import browser_logger

browser_logger.info("Browser launched in headless mode.")
```

---

## 🎯 Profile-Scoped Loggers

### `get_profile_logger(profile_id) → CamouChatLoggerAdapter`

Returns a `CamouChatLoggerAdapter` with the `profile_id` field set to the given string. Use this in production when running multiple bots simultaneously so every log line is tagged with the bot's identity.

```python
from camouchat.camouchat_logger import get_profile_logger

log = get_profile_logger("MarketingBot")
log.info("Processing messages.")
# Output: 2026-03-18 | INFO | [MarketingBot][12345] | tweakio | Processing messages.
```

Results are **cached** — calling `get_profile_logger("MarketingBot")` ten times returns the same adapter instance.

---

### `get_browser_profile_logger(profile_id) → CamouChatLoggerAdapter`

Same as `get_profile_logger()` but for browser-specific logging to `browser.log`.

```python
from camouchat.camouchat_logger import get_browser_profile_logger

b_log = get_browser_profile_logger("MarketingBot")
```

---

## 🎨 Console Colors

The console handler uses `colorlog.ColoredFormatter` with this color scheme:

| Level | Color |
|-------|-------|
| `DEBUG` | Cyan |
| `INFO` | Green |
| `WARNING` | Yellow |
| `ERROR` | Red |
| `CRITICAL` | Bold Red |

---

## 📁 Log File Locations

Log files are placed in the OS-appropriate user cache directory by `DirectoryManager` (via `platformdirs`):

| File | OS Location |
|------|-------------|
| `ErrorTrace.log` | Linux: `~/.cache/CamouChat/ErrorTrace.log` |
| `browser.log` | Linux: `~/.cache/CamouChat/browser.log` |
| | macOS: `~/Library/Caches/CamouChat/...` |
| | Windows: `%LOCALAPPDATA%\CamouChat\...` |

**Rotation settings**: Max 20 MB per file, 3 backup files kept (`backupCount=3`). Uses `ConcurrentRotatingFileHandler` (from `concurrent-log-handler`) if available, falls back to the standard `RotatingFileHandler` — safe for multi-process logging.

---

## 🔧 CamouChatLoggerAdapter

`CamouChatLoggerAdapter` extends `logging.LoggerAdapter` to inject `profile_id` and `process_id` into every log record's `extra` dict. This is what powers the `[profile_id][pid]` prefix in log messages.

```python
from camouchat.camouchat_logger import CamouChatLoggerAdapter
import logging

# Custom adapter for a specific profile
my_logger = CamouChatLoggerAdapter(
    logging.getLogger("tweakio"),
    {"profile_id": "CustomBot", "process_id": 99999}
)
my_logger.info("Custom context log.")
```

---

## 🗎 JSONFormatter

`JSONFormatter` formats log records as JSON objects. Useful for log aggregation pipelines (e.g., Elasticsearch, Loki).

```python
from camouchat.camouchat_logger import JSONFormatter
import logging

handler = logging.FileHandler("structured.log")
handler.setFormatter(JSONFormatter())
logging.getLogger("tweakio").addHandler(handler)
```

Produces:
```json
{"timestamp": "2026-03-18 22:30:01,234", "level": "INFO", "logger": "tweakio", "message": "Bot started.", "profile_id": "MarketingBot", "process_id": 12345}
```

---

## 💡 Pro Tips

- **Always inject `log` into SDK classes**: Pass `get_profile_logger(profile_id)` as the `log` parameter to `ProfileManager`, `CamoufoxBrowser`, `ChatProcessor`, `MessageProcessor`, etc. This gives you per-profile log filtering in production.
- **Log level**: The default level is `INFO`. Set `logging.getLogger("tweakio").setLevel(logging.DEBUG)` early in your application if you need verbose output during development.
- **Don't create new `Logger` objects**: Always use the existing `tweakio` logger or the adapters provided. Creating a new logger breaks the shared handler setup and you'll lose file logging.
