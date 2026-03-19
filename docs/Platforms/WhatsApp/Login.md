# 🔐 Login

`camouchat.WhatsApp.login`

The `Login` class is the authentication gateway to WhatsApp Web. It supports two methods: scanning a **QR code** or linking via a **phone number pairing code**. Once authenticated, the Camoufox persistent context saves the session in your profile's `cache_dir`, so you only need to log in **once per profile**.

Like all WhatsApp components, `Login` enforces a **Singleton-per-Page pattern** — the same page will always return the same `Login` instance.

---

## 🛠️ Constructor

```python
Login(
    page: Page,
    UIConfig: WebSelectorConfig,
    log: Optional[Union[Logger, LoggerAdapter]] = None,
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | `Page` | ✅ Yes | The active async Playwright page. All interaction happens through this object. Async-only. |
| `UIConfig` | `WebSelectorConfig` | ✅ Yes | The selector configuration object for this page. Provides locators for QR canvas, chat list, country selector, phone input, etc. |
| `log` | `Logger \| LoggerAdapter` | ❌ No | Logger for login status messages and the pairing code printout. |

```python
from camouchat.WhatsApp import Login, WebSelectorConfig
from camouchat.camouchat_logger import camouchatLogger

# Always create UIConfig first — it is the single source of DOM locators
ui_config = WebSelectorConfig(page=page, log=camouchatLogger)

login_obj = Login(
    page=page,
    UIConfig=ui_config,
    log=camouchatLogger,
)
```

---

## 📦 Methods

### `login(**kwargs) → bool`

The main authentication method. Navigates to WhatsApp Web and orchestrates the chosen login flow. The browser session is automatically persisted to disk by Camoufox's `persistent_context`.

| kwarg | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `method` | `int` | ✅ Yes | — | `0` = QR code login. `1` = Phone number pairing code login. |
| `wait_time` | `int` | ❌ No | `180_000` | Maximum wait in milliseconds for the QR scan or code confirmation. |
| `url` | `str` | ❌ No | `"https://web.whatsapp.com"` | WhatsApp Web URL to navigate to. Override only if you need a staging/proxy URL. |
| `number` | `int` | ⚠️ Required if `method=1` | — | Your phone number **without** the country code (e.g., `9876543210`). |
| `country` | `str` | ⚠️ Required if `method=1` | — | Country name as it appears in WhatsApp's dropdown (e.g., `"India"`, `"United States"`). |

#### QR Code Login (method=0)

The simplest method. Navigate to WhatsApp Web, then scan the QR code that appears with your phone.

```python
success = await login_obj.login(
    method=0,
    wait_time=150_000,   # 150 seconds to scan the QR
)

if success:
    print("✅ QR login successful!")
```

**How it works internally**: The SDK waits for the `chat-list` element to become visible. Once visible, it confirms the QR code is gone (if WhatsApp still shows a QR, it raises `LoginError`).

#### Phone Number / Pairing Code Login (method=1)

Fills in the country selector and phone number, then waits for WhatsApp to display an 8-character pairing code. The code is printed to your terminal via the logger.

```python
success = await login_obj.login(
    method=1,
    number=9876543210,     # Local number without country code
    country="India",       # Must match WhatsApp's country dropdown exactly
    wait_time=180_000,
)
```

> [!NOTE]
> When `method=1` is used, check your terminal for the pairing code output. It will look like:
> ```
> INFO | WhatsApp Login Code: ABCD-1234
> ```
> Open WhatsApp on your phone → **Linked Devices** → **Link a Device** → enter the code.

---

### `is_login_successful(**kwargs) → bool`

Verifies that login succeeded by waiting for the chat list sidebar to become visible. Call this after `login()` to confirm before proceeding with automation.

| kwarg | Type | Default | Description |
|-------|------|---------|-------------|
| `timeout` | `int` | `10_000` | Milliseconds to wait for the chat list (default: 10 seconds). |

```python
if await login_obj.is_login_successful(timeout=15_000):
    print("✅ Connected to WhatsApp Web!")
else:
    print("❌ Login verification timed out.")
```

---

## 🚪 Logging Out

`Login` intentionally has **no `logout()` method**. Sessions are tied to Camoufox's persistent browser context, not a simple cookie. Two ways to log out:

1. **Delete the profile** (wipes all data — use for complete cleanup):
   ```python
   pm.delete_profile(Platform.WHATSAPP, "MarketingBot")
   ```

2. **Via WhatsApp mobile app** (preferred — preserves profile data):  
   WhatsApp → **Linked Devices** → tap the device → **Log Out**.  
   The next time your bot runs, `login()` will prompt you to authenticate again.

---

## 🛡️ Error Handling

All login failures raise subclasses of `LoginError` from `camouchat.Exceptions.whatsapp`:

| Exception | When Raised |
|-----------|-------------|
| `LoginError("Timeout while loading WhatsApp Web")` | Page navigation timed out (60s). |
| `LoginError("Invalid login method.")` | `method` is not `0` or `1`. |
| `LoginError("QR login timeout.")` | User did not scan QR within `wait_time`. |
| `LoginError("Login-with-phone-number button not found.")` | WhatsApp UI changed or page not loaded. |
| `LoginError("Country '...' not selectable.")` | Country name not found in the dropdown — check spelling. |
| `LoginError("Timeout while waiting for login code.")` | WhatsApp did not produce the pairing code in time. |

```python
from camouchat.Exceptions.whatsapp import LoginError

try:
    await login_obj.login(method=1, number=9876543210, country="India")
except LoginError as e:
    print(f"Login failed: {e}")
```

---

## 💡 Pro Tips

- **Humanized typing**: Country name and phone number are typed with randomized per-keystroke delays (80–120 ms) to avoid bot-detection during the login flow.
- **Session reuse**: After the first login, you do **not** need to call `login()` on subsequent runs. The persistent context saved in `profile.cache_dir` keeps you connected until you log out or the session expires.
- **Headless login**: Avoid logging in for the first time in headless mode — scanning QR codes or confirming pairing codes requires visual access. Set `headless=True` only in `BrowserConfig` after the initial authenticated session is established.
