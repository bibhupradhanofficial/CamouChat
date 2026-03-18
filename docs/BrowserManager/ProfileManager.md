# 🏢 ProfileManager

`camouchat.BrowserManager.profile_manager`

`ProfileManager` is the central coordinator for all profile operations. It creates sandboxed profile directories, manages the `metadata.json` configuration file, handles AES-256 encryption key lifecycle, and controls browser activation / deactivation across concurrent profiles.

Think of it as the **filesystem-backed registry** for all your virtual browser identities.

---

## 📁 What Lives Inside a Profile Directory?

When you call `create_profile()`, the following structure is created under the OS-specific user data directory (resolved by `DirectoryManager` via `platformdirs`):

```text
~/.local/share/CamouChat/platforms/<platform>/<profile_id>/
├── metadata.json       # Profile configuration (no secrets stored here)
├── fingerprint.pkl     # Pickled BrowserForge Fingerprint — unique to this profile
├── messages.db         # SQLAlchemy SQLite database (default)
├── encryption.key      # AES-256 base64 key — ONLY present when encryption is enabled
├── .lock               # PID file written on activation, deleted on deactivation
├── cache/              # Camoufox persistent browser session (cookies, local storage)
└── media/
    ├── images/
    ├── videos/
    ├── voice/
    └── documents/
```

> [!NOTE]
> `encryption.key` is intentionally **not** inside `metadata.json`. Metadata is a general-purpose readable JSON; the key file is a dedicated secret with `chmod 600` permissions (owner read-only on Linux/macOS).

---

## 🛠️ Constructor

```python
ProfileManager(log: Optional[Union[LoggerAdapter, Logger]] = None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `log` | `Logger \| LoggerAdapter` | `camouchatLogger` | Injected logger. Use `get_profile_logger(profile_id)` for profile-scoped logging. |

```python
from camouchat.BrowserManager import ProfileManager
from camouchat.camouchat_logger import get_profile_logger

pm = ProfileManager(log=get_profile_logger("MyBot"))
```

---

## 📦 Profile Lifecycle Methods

### `create_profile(platform, profile_id, storage_type, database_url) → ProfileInfo`

Creates a new sandboxed profile directory with all subdirectories, an empty `fingerprint.pkl`, and a `metadata.json` with default settings. **If the profile already exists, it returns the existing profile without modifying it.**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `platform` | `Platform` | ✅ Yes | — | The platform this profile belongs to (`Platform.WHATSAPP`, etc.). Determines the directory namespace. |
| `profile_id` | `str` | ✅ Yes | — | Unique human-readable name for this profile (e.g., `"MarketingBot"`). Used as the directory name. |
| `storage_type` | `StorageType` | ❌ No | `StorageType.SQLITE` | Backend database type. Affects the auto-generated `database_url`. |
| `database_url` | `str` | ❌ No | `None` | Override the auto-generated SQLAlchemy connection URL (e.g., for PostgreSQL). |

```python
from camouchat.BrowserManager import ProfileManager, Platform

pm = ProfileManager()

# Creates the profile (or returns existing one if already created)
profile = pm.create_profile(
    platform=Platform.WHATSAPP,
    profile_id="MarketingBot",
)
print(f"Profile at: {profile.profile_dir}")
```

> [!TIP]
> `create_profile` is **idempotent** — safe to call every time your bot starts. It only creates the directory structure on the first call; subsequent calls return the existing `ProfileInfo`.

---

### `get_profile(platform, profile_id) → ProfileInfo`

Loads an existing profile from disk and returns a fresh `ProfileInfo` instance. Raises `ValueError` if the profile does not exist.

```python
profile = pm.get_profile(Platform.WHATSAPP, "MarketingBot")
```

---

### `is_profile_exists(platform, profile_id) → bool`

Returns `True` if the profile directory exists on disk without raising.

```python
if pm.is_profile_exists(Platform.WHATSAPP, "MarketingBot"):
    profile = pm.get_profile(Platform.WHATSAPP, "MarketingBot")
```

---

### `list_profiles(platform=None) → Dict[str, List[str]]`

Returns a dictionary mapping platform name strings to a list of profile IDs saved on disk.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `platform` | `Platform` | `None` | If given, scopes the listing to that platform only. If `None`, returns all platforms. |

```python
# All platforms
all_profiles = pm.list_profiles()
# → {"WhatsApp": ["MarketingBot", "SupportBot"], "Arattai": ["TestBot"]}

# Single platform
wa_profiles = pm.list_profiles(platform=Platform.WHATSAPP)
# → {"WhatsApp": ["MarketingBot", "SupportBot"]}
```

---

### `delete_profile(platform, profile_id, force=False)`

Permanently wipes the entire profile directory (including the database, fingerprint, cache, and key file). **This operation is irreversible.**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `platform` | `Platform` | — | Target platform. |
| `profile_id` | `str` | — | Target profile name. |
| `force` | `bool` | `False` | If `True`, deletes even when `metadata.json` marks the profile as active. Use with caution — the running browser will become orphaned. |

```python
pm.delete_profile(Platform.WHATSAPP, "OldBot")
```

> [!CAUTION]
> Deleting a profile wipes all stored messages, the session cache (you'll need to log in again), and the encryption key. Decrypt all messages **before** deleting if you need the plaintext.

---

## 🔐 Encryption Key Management

### `enable_encryption(platform, profile_id) → bytes`

Generates a fresh random 32-byte AES-256 key, writes it base64-encoded to `encryption.key` with `chmod 600` permissions, and marks `"encryption.enabled": true` in `metadata.json`. The key is never stored in `metadata.json`.

Returns the **raw key bytes** so you can pass them directly to `MessageProcessor` without re-reading the file.

```python
# One-time setup — call this once, then store the key in memory
key = pm.enable_encryption(Platform.WHATSAPP, "SecureBot")

# Pass the key to MessageProcessor to enable real-time encryption
msg_processor = MessageProcessor(..., encryption_key=key)
```

> [!IMPORTANT]
> Calling `enable_encryption()` a second time on the same profile raises `ValueError`. You must call `disable_encryption()` first. This prevents accidental key rotation that would render existing ciphertext in the database permanently unreadable.

---

### `get_key(platform, profile_id) → bytes`

Reads the existing `encryption.key` file and returns the raw 32-byte key. Use this when **resuming a session** to re-initialize `MessageProcessor` with the same key as the previous run.

```python
# On subsequent bot runs — load the persisted key
key = pm.get_key(Platform.WHATSAPP, "SecureBot")
```

Raises `ValueError` if encryption is not enabled, and `FileNotFoundError` if the key file is missing (indicating profile corruption).

---

### `is_encryption_enabled(platform, profile_id) → bool`

A quick read of `metadata.json` to check whether encryption is currently active for the profile.

```python
if pm.is_encryption_enabled(Platform.WHATSAPP, "SecureBot"):
    key = pm.get_key(Platform.WHATSAPP, "SecureBot")
```

---

### `disable_encryption(platform, profile_id)`

Wipes the `encryption.key` file (overwriting with zeros before unlinking for forensic resistance) and sets `"encryption.enabled": false` in `metadata.json`.

> [!WARNING]
> Any messages already stored as ciphertext in the database are **irrecoverable** after disabling encryption. Decrypt them using `SQLAlchemyStorage.get_decrypted_messages_async()` before calling this.

---

## ⚡ Profile Activation / Deactivation

### `activate_profile(platform, profile_id, browser_obj)`

Marks the profile as active in `metadata.json`, creates a `.lock` file containing the current PID, and ensures the browser reference is recorded in memory. If another profile is already active (class-level `p_count >= 1`), this method **forces `browser_obj.config.headless = True`** to prevent multiple visible browser windows from consuming display resources.

```python
pm.activate_profile(Platform.WHATSAPP, "MarketingBot", browser_obj=browser)
```

> [!NOTE]
> `activate_profile` handles stale sessions gracefully: if the last recorded PID is no longer alive, it clears the stale lock and proceeds as if the profile was fresh.

---

### `close_profile(platform, profile_id, force=False)`

Gracefully shuts down the browser for this profile (via `CamoufoxBrowser.close_browser_by_pid`), marks the profile as inactive in `metadata.json`, and removes the `.lock` file.

```python
await pm.close_profile(Platform.WHATSAPP, "MarketingBot")

# Force-kill a stuck session
await pm.close_profile(Platform.WHATSAPP, "MarketingBot", force=True)
```

---

## 💡 Pro Tips

- **One `ProfileManager` for your entire application**: The class itself is lightweight (just a `DirectoryManager` and a logger). Create a single instance at startup and share it across all your bot threads/processes.
- **Profile-scoped logger**: Use `get_profile_logger(profile_id)` from `camouchat.camouchat_logger` so every log line is tagged with the profile name — invaluable when running 10+ bots simultaneously.
- **Encryption workflow**:
  1. First run: `enable_encryption()` → pass returned key to `MessageProcessor`.
  2. Subsequent runs: `get_key()` → pass to `MessageProcessor`.
  3. To read stored messages: `SQLAlchemyStorage.get_decrypted_messages_async(key)`.
