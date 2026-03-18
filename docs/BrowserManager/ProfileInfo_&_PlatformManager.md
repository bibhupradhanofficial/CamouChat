# 📂 ProfileInfo & Platform

`camouchat.BrowserManager.profile_info` | `camouchat.BrowserManager.platform_manager`

---

## 🌐 Platform Enum

`Platform` is a `str`-based enum that acts as the **namespace** for all profile directories and is used throughout the SDK to route automation to the correct platform module.

```python
from camouchat.BrowserManager import Platform

# Available platforms
Platform.WHATSAPP   # → "WhatsApp"
Platform.ARATTAI    # → "Arattai"  (experimental)

# Inspect all supported platforms programmatically
print(Platform.list_platforms())  # → ['WhatsApp', 'Arattai']
```

**Why `str`-based?** Because `Platform` values are also used as directory names on disk. Making it a `str` enum means `str(Platform.WHATSAPP)` just gives you `"WhatsApp"` without extra `.value` boilerplate.

---

## 📄 ProfileInfo Dataclass

`ProfileInfo` is a **frozen snapshot** of a profile's resolved paths and runtime state. You never construct it directly — it is always returned by `ProfileManager.create_profile()` or `ProfileManager.get_profile()` via the `from_metadata()` classmethod.

```python
@dataclass
class ProfileInfo:
    profile_id: str
    platform: Platform
    version: str
    created_at: str
    last_used: str

    profile_dir: Path
    fingerprint_path: Path
    cache_dir: Path
    media_dir: Path
    media_images_dir: Path
    media_videos_dir: Path
    media_voice_dir: Path
    media_documents_dir: Path
    database_path: Path
    database_url: str

    is_active: bool
    last_active_pid: Optional[int]

    encryption: Dict
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `profile_id` | `str` | The unique name you gave the profile (e.g., `"MarketingBot"`). Used as the directory name on disk. |
| `platform` | `Platform` | The platform this profile belongs to (`Platform.WHATSAPP`, etc.). |
| `version` | `str` | SDK metadata version when the profile was created (e.g., `"0.6"`). Used for forward-compatibility checks during migrations. |
| `created_at` | `str` | UTC ISO-8601 timestamp of profile creation. |
| `last_used` | `str` | UTC ISO-8601 timestamp last updated by `activate_profile()`. |
| `profile_dir` | `Path` | Root directory of this profile on disk. All other paths are derived from this. |
| `fingerprint_path` | `Path` | Path to `fingerprint.pkl`. `BrowserForgeCompatible.get_fg()` reads/writes this file to persist a stable browser fingerprint across sessions. |
| `cache_dir` | `Path` | Camoufox's persistent browser session directory — passed as `user_data_dir`. Deleting this dir forces WhatsApp re-login. |
| `media_dir` | `Path` | Root of all downloaded media for this profile. |
| `media_images_dir` | `Path` | Subdirectory for downloaded images. |
| `media_videos_dir` | `Path` | Subdirectory for downloaded videos. |
| `media_voice_dir` | `Path` | Subdirectory for downloaded voice notes / audio. |
| `media_documents_dir` | `Path` | Subdirectory for downloaded documents and PDFs. |
| `database_path` | `Path` | Absolute path to the `messages.db` SQLite file for this profile. |
| `database_url` | `str` | Full SQLAlchemy async connection URL. For SQLite: `sqlite+aiosqlite:///...`. For remote DBs, reflects what was passed to `create_profile()`. Used directly by `SQLAlchemyStorage.from_profile()`. |
| `is_active` | `bool` | Whether this profile is currently running in a browser. Read from `metadata.json`; represents the last-known state (not guaranteed to be real-time). |
| `last_active_pid` | `int \| None` | The OS PID of the process that last activated this profile. Used by `close_profile()` to find the correct browser process. `None` if the profile was never activated or has been closed. |
| `encryption` | `dict` | Encryption block from `metadata.json`. Contains `enabled` (bool), `algorithm` (`"AES-256-GCM"`), and `created_at`. **Does not contain the actual key** — that lives exclusively in `encryption.key`. |

---

## 🔁 `from_metadata()` Classmethod

This is how `ProfileInfo` is always constructed — never directly:

```python
@classmethod
def from_metadata(cls, metadata: dict, directory: DirectoryManager) -> ProfileInfo:
    ...
```

It resolves all `Path` objects from the raw paths stored in `metadata.json` using a `DirectoryManager` instance. It also applies a backward-compatibility fallback for `database_url` — older profiles that don't have a `database.url` key in their metadata automatically get a SQLite URL derived from `database_path`.

---

## 💡 Usage Patterns

### Access profile paths

```python
profile = pm.get_profile(Platform.WHATSAPP, "MarketingBot")

print(f"Profile root:   {profile.profile_dir}")
print(f"SQLite DB:      {profile.database_path}")
print(f"Browser cache:  {profile.cache_dir}")
print(f"DB URL:         {profile.database_url}")
print(f"Is active:      {profile.is_active}")
```

### Pass to SQLAlchemyStorage

`ProfileInfo.database_url` is designed to be consumed directly by `SQLAlchemyStorage.from_profile()`:

```python
import asyncio
from camouchat.StorageDB import SQLAlchemyStorage

queue = asyncio.Queue()
storage = SQLAlchemyStorage.from_profile(profile=profile, queue=queue, log=camouchatLogger)
```

### Check encryption state

```python
enc = profile.encryption
if enc.get("enabled"):
    print(f"Encryption ON — algorithm: {enc['algorithm']}, enabled at: {enc['created_at']}")
else:
    print("Encryption is OFF for this profile.")
```

> [!NOTE]
> `ProfileInfo` is a **snapshot** — it reflects the state of `metadata.json` at the moment it was loaded. If you activate a profile or enable encryption after loading a `ProfileInfo`, that object will not automatically update. Call `pm.get_profile()` again to get a fresh snapshot.
