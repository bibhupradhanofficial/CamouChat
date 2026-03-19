# 🖼️ MediaCapable

`camouchat.WhatsApp.media_capable`

`MediaCapable` handles uploading files (images, videos, audio, and documents) to WhatsApp chats. It automates the attachment menu (`+` button), maps media type to the correct sub-menu option, and uses Playwright's file-chooser interception to bypass the OS-level file dialog entirely.

Like all WhatsApp components, it enforces **Singleton-per-Page** binding.

---

## 🛠️ Constructor

```python
MediaCapable(
    page: Page,
    UIConfig: WebSelectorConfig,
    log: Optional[Union[Logger, LoggerAdapter]] = None,
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | `Page` | ✅ Yes | The active Playwright async page for all DOM interactions. |
| `UIConfig` | `WebSelectorConfig` | ✅ Yes | Provides the `plus_rounded_icon()`, `photos_videos()`, `audio()`, and `document()` locators. Note: parameter name is `UIConfig` (PascalCase) — different from `ChatProcessor`'s `ui_config`. |
| `log` | `Logger \| LoggerAdapter` | ❌ No | Logger for sent-file debug messages. |

```python
from camouchat.WhatsApp import MediaCapable, WebSelectorConfig
from camouchat.camouchat_logger import camouchatLogger

ui_config = WebSelectorConfig(page=page, log=camouchatLogger)

media_handler = MediaCapable(
    page=page,
    UIConfig=ui_config,
    log=camouchatLogger,
)
```

---

## 📦 Data Types

### `MediaType` (Enum)

Defined in `camouchat.Interfaces.media_capable_interface`. Used to specify the type of file being uploaded.

| Value | String | Maps To |
|-------|--------|---------|
| `MediaType.TEXT` | `"text"` | Photos & Videos menu (text-over-image flow) |
| `MediaType.IMAGE` | `"image"` | Photos & Videos menu |
| `MediaType.VIDEO` | `"video"` | Photos & Videos menu |
| `MediaType.AUDIO` | `"audio"` | Audio upload menu |
| `MediaType.DOCUMENT` | `"document"` | Document upload menu (default fallback) |

---

### `FileTyped` (Dataclass)

Defined in `camouchat.Interfaces.media_capable_interface`. Wraps the file path and optional metadata for the upload.

```python
@dataclass(frozen=True)
class FileTyped:
    uri: str                        # Absolute path to the file on disk (Required)
    name: str                       # Display name for the file (Required)
    mime_type: Optional[str] = None # MIME type hint (e.g., "image/png"). Optional.
    size_bytes: Optional[int] = None # File size in bytes. Optional.
```

```python
from camouchat.Interfaces.media_capable_interface import FileTyped, MediaType

my_file = FileTyped(
    uri="/home/user/reports/summary.pdf",
    name="summary.pdf",
    mime_type="application/pdf",
)
```

> [!IMPORTANT]
> `uri` must be an **absolute path** to an existing file on disk. `MediaCapable.add_media()` validates existence before setting the file chooser. Relative paths will raise `MediaCapableError`.

---

## 📦 Methods

### `add_media(mtype, file, **kwargs) → bool`

Uploads a file to the currently open WhatsApp chat. Must be called while a chat is already open in the browser.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mtype` | `MediaType` | ✅ Yes | The type of media to upload. Determines which sub-menu option is clicked. |
| `file` | `FileTyped` | ✅ Yes | The file descriptor containing the absolute path. |

```python
success = await media_handler.add_media(
    mtype=MediaType.IMAGE,
    file=FileTyped(uri="/home/user/photos/product.jpg", name="product.jpg"),
)

if success:
    # WhatsApp opens the caption screen — press Enter to send immediately
    await page.keyboard.press("Enter")
```

#### Internal Flow

1. `menu_clicker()` — clicks the `+` (attachment) icon and waits 1.0–1.5 seconds for the menu to appear naturally.
2. `_getOperational(mtype)` — resolves the correct menu locator:
   - `IMAGE`, `VIDEO`, `TEXT` → `UIConfig.photos_videos()`
   - `AUDIO` → `UIConfig.audio()`
   - Anything else → `UIConfig.document()`
3. `page.expect_file_chooser()` — arms the file chooser interceptor.
4. Clicks the resolved menu option — this triggers WhatsApp's OS file dialog.
5. The file chooser interceptor catches the dialog event and calls `chooser.set_files(path)` — the OS dialog is never shown to the user.

> [!NOTE]
> `add_media()` returns `True` once the file path has been set in the file chooser. WhatsApp Web then loads a preview/caption screen. **The file is NOT yet sent** — you must press Enter or click the send button to complete the upload.

---

### `menu_clicker() → None` *(semi-private)*

Opens the attachment drawer by clicking the `plus_rounded_icon` locator. Incorporates a 1.0–1.5 second natural delay after clicking, and presses `Escape` to recover gracefully if the icon times out.

You don't usually call this directly — `add_media()` calls it internally.

---

## 🛡️ Stealth & Stability Details

1. **File Chooser Interception**: `page.expect_file_chooser()` is used as an async context manager. The file dialog is intercepted at the browser level — the OS dialog window **never appears on screen**. This is critical for headless operation.
2. **Natural Menu Timing**: The `menu_clicker()` waits `random.uniform(1.0, 1.5)` seconds after clicking the `+` icon, mimicking human pause time before selecting a menu option.
3. **File Validation**: Before setting the file path, `MediaCapable` checks that the path both exists (`p.exists()`) and is a regular file (`p.is_file()`), preventing stale or directory paths from silently failing mid-upload.

---

## 🔔 Error Handling

| Exception | When Raised |
|-----------|-------------|
| `MenuError` | `menu_clicker()` — the `+` icon locator returned `None`. |
| `MediaCapableError("Time out while clicking menu")` | Icon click timed out (3s). |
| `MediaCapableError("Attach option not visible")` | Sub-menu option not visible after menu opened (3s). |
| `MediaCapableError("Invalid file path: ...")` | `file.uri` doesn't exist or isn't a file. |
| `MediaCapableError("Timeout while resolving media option")` | File chooser or menu option timed out. |

```python
from camouchat.Exceptions.whatsapp import MediaCapableError, MenuError

try:
    await media_handler.add_media(
        mtype=MediaType.DOCUMENT,
        file=FileTyped(uri="/home/user/doc.pdf", name="doc.pdf"),
    )
    await page.keyboard.press("Enter")
except MenuError as e:
    print(f"Attachment menu not found: {e}")
except MediaCapableError as e:
    print(f"Media upload failed: {e}")
```

---

## 💡 Pro Tips

- **Call order matters**: Ensure `ChatProcessor._click_chat()` has been called (via `fetch_messages()` or manually) before calling `add_media()`. You must be inside a chat for the `+` icon to be visible.
- **Sending a caption**: After `add_media()` returns `True`, WhatsApp shows a preview with a caption input field. You can use `HumanInteractionController.typing()` to add a caption before pressing Enter, or just send without one.
- **Sending multiple files**: Call `add_media()` once per file. Each call opens the menu, selects the file, and loads the caption screen independently.
