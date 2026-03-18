# 📂 DirectoryManager

`camouchat.directory`

`DirectoryManager` is a centralized, OS-independent path resolver for all CamouChat data. It uses the `platformdirs` library to find the correct system directories on Linux, macOS, and Windows, and provides convenience methods for every path the SDK needs — profile roots, database files, encryption keys, media folders, cache, and logs.

---

## 🛠️ Constructor

```python
DirectoryManager()
```

No parameters. On initialization, it sets up and creates the base directory structure:

```
~/.local/share/CamouChat/         (Linux)
~/Library/Application Support/CamouChat/  (macOS)
%APPDATA%\CamouChat\              (Windows)
  └── platforms/                  # Namespace for all profile directories

~/.cache/CamouChat/               (Linux cache)
  ├── ErrorTrace.log
  └── browser.log
```

```python
from camouchat.directory import DirectoryManager

dm = DirectoryManager()
print(dm.root_dir)        # e.g., /home/user/.local/share/CamouChat
print(dm.platforms_dir)   # e.g., /home/user/.local/share/CamouChat/platforms
```

---

## 📦 Path Methods

All path methods accept `(platform: str, profile_id: str)` and return `Path` objects. Directory-returning methods also call `mkdir(parents=True, exist_ok=True)` automatically.

### Profile Structure

| Method | Returns | Creates? |
|--------|---------|---------|
| `get_platform_dir(platform)` | `.../platforms/<platform>/` | ✅ Yes |
| `get_profile_dir(platform, profile_id)` | `.../platforms/<platform>/<profile_id>/` | ❌ |
| `get_database_path(platform, profile_id)` | `.../platforms/<platform>/<profile_id>/messages.db` | ❌ |
| `get_key_file_path(platform, profile_id)` | `.../platforms/<platform>/<profile_id>/encryption.key` | ❌ |
| `get_cache_dir(platform, profile_id)` | `.../platforms/<platform>/<profile_id>/cache/` | ✅ Yes |
| `get_backup_dir(platform, profile_id)` | `.../platforms/<platform>/<profile_id>/backups/` | ✅ Yes |
| `get_media_dir(platform, profile_id)` | `.../platforms/<platform>/<profile_id>/media/` | ✅ Yes |
| `get_media_images_dir(platform, profile_id)` | `.../media/images/` | ✅ Yes |
| `get_media_videos_dir(platform, profile_id)` | `.../media/videos/` | ✅ Yes |
| `get_media_voice_dir(platform, profile_id)` | `.../media/voice/` | ✅ Yes |
| `get_media_documents_dir(platform, profile_id)` | `.../media/documents/` | ✅ Yes |

### Global Paths

| Method | Returns |
|--------|---------|
| `get_error_trace_file()` | `~/.cache/CamouChat/ErrorTrace.log` |
| `get_browser_log_file()` | `~/.cache/CamouChat/browser.log` |
| `get_cache_root()` | `~/.cache/CamouChat/` |
| `get_log_root()` | User log directory (via platformdirs) |

---

## 💡 Usage Examples

```python
dm = DirectoryManager()

# Get the SQLite database path for a profile
db_path = dm.get_database_path("WhatsApp", "MarketingBot")
print(db_path)
# → /home/user/.local/share/CamouChat/platforms/WhatsApp/MarketingBot/messages.db

# Get the encryption key path
key_path = dm.get_key_file_path("WhatsApp", "MarketingBot")
print(key_path)
# → /home/user/.local/share/CamouChat/platforms/WhatsApp/MarketingBot/encryption.key

# Get the media images directory
images_dir = dm.get_media_images_dir("WhatsApp", "MarketingBot")
print(images_dir)
# → /home/user/.local/share/CamouChat/platforms/WhatsApp/MarketingBot/media/images/
```

> [!NOTE]
> You rarely need to use `DirectoryManager` directly. `ProfileManager` creates one internally and exposes all paths through the `ProfileInfo` dataclass. Use `profile.database_path`, `profile.cache_dir`, `profile.media_images_dir`, etc.

---

## 🔒 Key File Design Note

`get_key_file_path()` returns a path **inside** the profile directory but **outside** `metadata.json`. This separation is intentional:

- `metadata.json` is general-purpose readable configuration — it should be inspectable for debugging.
- `encryption.key` is a dedicated secret. `ProfileManager.enable_encryption()` applies `chmod 600` to it (owner-read-only on Linux/macOS). The key is never embedded in `metadata.json`.

```python
# encryption.key format: a single line, base64-encoded 32-byte AES-256 key
# Example content (do not log or expose):
# dGhpcyBpcyBhIHRlc3Qga2V5IGZvciBkb2N1bWVudGF0aW9u
```

---

## 💡 Pro Tips

- **Consistent across runs**: `platformdirs` always resolves to the same OS-appropriate path for the same `appname`/`appauthor` combination. Your profiles will always be found in the same location across restarts.
- **Cross-platform deployment**: The same code works on Linux, macOS, and Windows without any path changes. `DirectoryManager` handles all OS-specific path conventions.
- **`platforms/` is lowercase**: Platform enum values are lowercased when used as directory names (via `platform.lower()` in `get_platform_dir()`). So `Platform.WHATSAPP` → directory named `whatsapp`.
