# ⚡ Quick Start

This guide covers basic and advanced examples to help you get started with the new **CamouChat** architecture featuring Profile Manager, Sandboxing, and Async DB integrations.

For detailed module-specific guides, check out:
- [BrowserManager QuickStart 🚀](./BrowserManager/quickstart.md) - Learn about profile creation and stealth browsers.
- [WhatsApp QuickStart 💬](./WhatsApp/quickstart.md) - Build your first WhatsApp bot.

---

## Basic: Fetch Visible Chats

This example shows how to launch a stealth browser, login to WhatsApp (QR), and list your active conversations.

```python
import asyncio
from camouchat.BrowserManager import ProfileManager, BrowserConfig, CamoufoxBrowser, Platform
from camouchat.BrowserManager.browserforge_manager import BrowserForgeCompatible
from camouchat.WhatsApp import Login, ChatProcessor, WebSelectorConfig
from camouchat.camouchat_logger import camouchatLogger as logger

async def main():
    # 1. Initialize Profile Manager and Create/Load Profile
    pm = ProfileManager()
    profile = pm.create_profile(Platform.WHATSAPP, "marketing_bot")

    # 2. Configure Browser Stealth (Fingerprints matched to your hardware)
    fg_manager = BrowserForgeCompatible(log=logger)
    config_data = {
        "platform": Platform.WHATSAPP,
        "locale": "en-US",
        "enable_cache": True,
        "headless": False,
        "fingerprint_obj": fg_manager.get_fg(profile=profile)
    }
    config = BrowserConfig.from_dict(config_data)

    # 3. Launch the Camoufox Stealth Browser
    browser = CamoufoxBrowser(config=config, profile=profile, log=logger)
    page = await browser.get_page()

    # 4. Initialize WhatsApp UI config and Login
    ui_config = WebSelectorConfig(page=page, log=logger)
    login = Login(page=page, UIConfig=ui_config, log=logger)

    # method=0 for QR login (Scan the terminal/browser code!)
    await login.login(method=0)

    # 5. Fetch visible chats
    chat_processor = ChatProcessor(page=page, UIConfig=ui_config, log=logger)
    chats = await chat_processor.fetch_chats(limit=5)
    
    for chat in chats:
        print(f"📂 Chat Found: {chat.chat_name}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Advanced: Secure Message Processing

Demonstrates fetching messages from a specific chat and storing them into an **encrypted** local SQLite database.

```python
import asyncio
from camouchat.BrowserManager import ProfileManager, BrowserConfig, CamoufoxBrowser, Platform, BrowserForgeCompatible
from camouchat.WhatsApp import Login, ChatProcessor, MessageProcessor, WebSelectorConfig
from camouchat.StorageDB import SQLAlchemyStorage
from camouchat.camouchat_logger import camouchatLogger as logger

async def main():
    # 1. Setup sandboxed profile
    pm = ProfileManager()
    profile = pm.create_profile(Platform.WHATSAPP, "secure_vault")

    # 2. Retrieve AES-256 Key (Automatic creation if missing)
    if not pm.is_encryption_enabled(Platform.WHATSAPP, "secure_vault"):
        encryption_key = pm.enable_encryption(Platform.WHATSAPP, "secure_vault")
    else:
        encryption_key = pm.get_key(Platform.WHATSAPP, "secure_vault")

    # 3. Launch stealth browser
    fg_manager = BrowserForgeCompatible(log=logger)
    config = BrowserConfig(
        platform=Platform.WHATSAPP,
        fingerprint_obj=fg_manager.get_fg(profile=profile),
        headless=True  # Run in background
    )
    browser = CamoufoxBrowser(config=config, profile=profile, log=logger)
    page = await browser.get_page()

    # 4. Initialize Processors & Database
    ui_config = WebSelectorConfig(page=page, log=logger)
    queue = asyncio.Queue()
    storage = SQLAlchemyStorage.from_profile(profile=profile, queue=queue, log=logger)

    async with storage:
        chat_proc = ChatProcessor(page=page, UIConfig=ui_config, log=logger)
        msg_proc = MessageProcessor(
            storage_obj=storage,
            filter_obj=None,
            chat_processor=chat_proc,
            page=page,
            log=logger,
            UIConfig=ui_config,
            encryption_key=encryption_key
        )

        # 5. Fetch and Save!
        chats = await chat_proc.fetch_chats(limit=2)
        for chat in chats:
            print(f"\n📂 Archiving: {chat.chat_name}")
            messages = await msg_proc.Fetcher(chat=chat, retry=3)
            print(f"   ✅ Saved {len(messages)} messages to encrypted DB.")

if __name__ == "__main__":
    asyncio.run(main())
```
