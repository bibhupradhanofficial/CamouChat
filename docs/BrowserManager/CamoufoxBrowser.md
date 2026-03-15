# 🦊 CamoufoxBrowser: Your stealthy window to the web

The `CamoufoxBrowser` is the heart of the SDK's browser interaction. It’s built on top of **Camoufox** (a modified Firefox) to provide elite-level fingerprinting and anti-detection capabilities. 

When you use `CamoufoxBrowser`, you're not just opening a browser; you're opening a **stealthy, sandboxed environment** that looks like a real human user.

---

### 🛠️ Setting up the Browser

To start the browser, you need three things: a `BrowserConfig`, a `ProfileInfo`, and a `Logger`.

```python
from camouchat.BrowserManager import CamoufoxBrowser, BrowserConfig, Platform

# 1. Setup the Config
config = BrowserConfig(
    platform=Platform.WHATSAPP,
    locale="en-US",
    headless=False,      # Set to True if you want the browser to be invisible
    enable_cache=True,   # Keeps you logged in across sessions
    fingerprint_obj=my_fingerprint_manager  # Usually your BrowserForgeCompatible instance
)

# 2. Get your Profile
profile = pm_obj.get_profile(Platform.WHATSAPP, "MyBot")

# 3. Create the Browser
browser = CamoufoxBrowser(config=config, profile=profile, log=my_logger)
```

---

### 📦 Key Functions

#### 1. `get_instance()`
This method launches the browser (if it's not already running) and returns the Playwright `BrowserContext`.
- **Note**: It automatically handles fingerprints and IP retries for you!
```python
context = await browser.get_instance()
```

---

#### 2. `get_page()`
This is the method you'll use most often. It returns a `Page` object that you can use to navigate websites.
- **Smart Logic**: If there's already a blank page open, it reuses it. Otherwise, it opens a fresh one.
```python
page = await browser.get_page()
await page.goto("https://web.whatsapp.com")
```

---

### ⚙️ BrowserConfig: Fine-tuning your Stealth

The `BrowserConfig` class lets you customize how your browser behaves:

| Attribute | Type | Description |
| :--- | :--- | :--- |
| `platform` | `Platform` | **Required.** e.g., `Platform.WHATSAPP`. |
| `locale` | `str` | Language headers for the browser (default: `"en-US"`). |
| `headless` | `bool` | `True` = Invisible, `False` = Visible window. |
| `enable_cache` | `bool` | Whether to store cookies and session data (Highly recommended!). |
| `prefs` | `dict` | Custom Firefox preferences (for advanced users). |
| `addons` | `list` | List of paths to `.xpi` extensions you want to load. |

---

### 🛡️ Why Camoufox?
*   **Anti-Detection**: Built-in protection against bot-detection scripts used by major sites.
*   **Humanization**: Automatically moves the mouse and types in a way that looks human.
*   **Auto-Cleanup**: When you close the browser, it syncs its state back to the profile automatically.

---

### 💡 Pro Tip
If you are running multiple bots on the same machine, the SDK will **automatically** force `headless=True` for any additional browsers to save your computer's RAM and keep things stable! 🚀
