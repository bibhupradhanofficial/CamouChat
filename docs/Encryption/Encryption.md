# 🔐 Encryption Module

`camouchat.Encryption`

The Encryption module provides out-of-the-box **AES-256-GCM** message and chat-name encryption. It is composed of three classes: `MessageEncryptor`, `MessageDecryptor`, and `KeyManager`. All three are designed to work together as part of the CamouChat privacy pipeline.

---

## Architecture: How All Three Work Together

```
ProfileManager.enable_encryption()
        │
        │  KeyManager.generate_random_key()  →  32 raw bytes
        │  KeyManager.encode_key_for_storage()  →  base64 string
        │  Saved to encryption.key (chmod 600)
        │
        ▼
ProfileManager.get_key()
        │
        │  KeyManager.decode_key_from_storage()  →  32 raw bytes
        │
        ▼
MessageProcessor.__init__(encryption_key=key)
        │
        │  MessageEncryptor(key)  →  encryptor instance
        │  del encryption_key     →  key wiped from namespace
        │
        ▼
MessageProcessor.fetch_messages() — for each new message:
        │
        │  encryptor.encrypt_message(raw_data, message_id)
        │  base64(nonce), base64(ciphertext)  →  stored in DB
        │  msg.raw_data = ""                  →  plaintext wiped
        │
        ▼
SQLAlchemyStorage.get_decrypted_messages_async(key)
        │
        │  MessageDecryptor(key)
        │  decryptor.decrypt_message(nonce_bytes, cipher_bytes, message_id)
        │  →  plaintext restored for reading
```

---

## 🔑 KeyManager

`camouchat.Encryption.key_manager`

Handles both random key generation (what CamouChat uses by default) and PBKDF2-based password-derived key generation (for applications that want a user password instead of a random secret).

### `generate_random_key() → bytes` *(static)*

Generates a cryptographically secure random 32-byte AES-256 key using `os.urandom(32)`. This is what `ProfileManager.enable_encryption()` calls internally.

```python
from camouchat.Encryption import KeyManager

key = KeyManager.generate_random_key()
# 32 raw bytes — store securely, never log this
```

---

### `encode_key_for_storage(key) → str` *(static)*

Base64-encodes a raw key for safe storage in the `encryption.key` file.

```python
encoded = KeyManager.encode_key_for_storage(key)
# → "base64string..."
# Written to encryption.key
```

---

### `decode_key_from_storage(encoded_key) → bytes` *(static)*

Decodes a base64-encoded key back to raw bytes. Called by `ProfileManager.get_key()`.

```python
raw_key = KeyManager.decode_key_from_storage(encoded)
```

Raises `ValueError` if the encoded string is malformed.

---

### `derive_key_and_salt(password, salt=None) → Tuple[bytes, bytes]`

For applications that want password-based encryption (not the default CamouChat flow). Derives a 32-byte key from a password using **PBKDF2-HMAC-SHA256** with 480,000 iterations (OWASP 2023 recommendation).

```python
km = KeyManager(iterations=480_000)  # Default — matches OWASP recommendation
salt, key = km.derive_key_and_salt(password="my-secret-password")
# store salt alongside encrypted data for re-derivation
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `password` | `str` | Required | User password (must be non-empty). |
| `salt` | `bytes` | `None` | 16-byte salt. Auto-generated if not provided. |

Returns `(salt, key)` — always store the `salt` alongside encrypted data. Same password + same salt = same key.

---

### `derive_key(password, salt) → bytes`

Same as `derive_key_and_salt()` but only returns the key. Use this to re-derive a key from a stored salt.

```python
key = km.derive_key(password="my-secret-password", salt=stored_salt)
```

---

## 🔒 MessageEncryptor

`camouchat.Encryption.encryptor`

Encrypts plaintext using AES-256-GCM. Every call generates a fresh random 12-byte nonce — nonce reuse with the same key would be a critical security vulnerability.

### Constructor

```python
MessageEncryptor(key: bytes)
# Raises ValueError if key is not exactly 32 bytes
```

---

### `encrypt(plaintext, associated_data=None) → Tuple[bytes, bytes]`

Encrypts a string or bytes value.

```python
encryptor = MessageEncryptor(key)

nonce, ciphertext = encryptor.encrypt("Hello, World!")
# nonce: 12 random bytes (new each call)
# ciphertext: encrypted data with 16-byte auth tag appended
```

The `associated_data` parameter provides **Additional Authenticated Data (AAD)**. AAD is authenticated but not encrypted — it binds extra context (like a message ID) to the ciphertext so decryption fails if the wrong context is provided.

---

### `encrypt_message(message, message_id=None) → Tuple[bytes, bytes]`

Convenience wrapper over `encrypt()` that uses `message_id.encode()` as the `associated_data`.

```python
nonce, ciphertext = encryptor.encrypt_message(
    message="Sensitive text",
    message_id="msg_123abc"   # Binds the ciphertext to this specific message ID
)
```

> [!IMPORTANT]
> When `message_id` is used as `associated_data`, you **must** provide the same `message_id` to `decrypt_message()`. Decryption with the wrong or missing ID will fail with `InvalidTag`. CamouChat always passes the same `message_id` from the `Message` object to both encrypt and decrypt.

---

### `encrypt_bytes(data, associated_data=None) → Tuple[bytes, bytes]`

Encrypts raw bytes instead of a string.

---

### `generate_key() → bytes` *(static)*

Alternative way to generate a 256-bit key via `AESGCM.generate_key(bit_length=256)`.

---

## 🔓 MessageDecryptor

`camouchat.Encryption.decryptor`

Decrypts ciphertext produced by `MessageEncryptor`. Authentication is **automatic** — GCM includes a 16-byte auth tag that is verified before decryption. Tampered ciphertext raises `InvalidTag`.

### Constructor

```python
MessageDecryptor(key: bytes)
# Raises ValueError if key is not exactly 32 bytes
```

---

### `decrypt(nonce, ciphertext, associated_data=None) → str`

Decrypts and returns the plaintext as a UTF-8 string. Always verifies the GCM authentication tag first.

```python
decryptor = MessageDecryptor(key)
plaintext = decryptor.decrypt(nonce, ciphertext)
```

---

### `decrypt_message(nonce, ciphertext, message_id=None) → str`

Decrypts a message that was encrypted with `encrypt_message()`. Pass the same `message_id` used during encryption.

```python
plaintext = decryptor.decrypt_message(
    nonce=nonce_bytes,
    ciphertext=cipher_bytes,
    message_id="msg_123abc"  # Must match the ID used during encryption
)
```

---

### `decrypt_bytes(nonce, ciphertext, associated_data=None) → bytes`

Returns decrypted raw bytes instead of a UTF-8 string.

---

### `decrypt_safe(nonce, ciphertext, associated_data=None) → Optional[str]`

Catches `InvalidTag` and `ValueError` internally and returns `None` on failure instead of raising. Useful for batch decryption where you want to skip corrupted records gracefully.

```python
plaintext = decryptor.decrypt_safe(nonce, ciphertext)
if plaintext is None:
    print("Decryption failed — record may be corrupted or key mismatch")
```

---

## 💡 Security Notes

> [!IMPORTANT]
> - **Never reuse a nonce with the same key.** Every `encrypt()` call generates a fresh `os.urandom(12)` nonce. Do not serialize and re-use nonces.
> - **The key is wiped from `MessageProcessor` memory** (`del encryption_key` in a `finally` block) immediately after the encryptor is initialized. The key never lives longer in RAM than strictly necessary.
> - **`encryption.key` has `chmod 600` on Linux/macOS**. Never commit this file to source control or include it in backups alongside the database.
> - **AES-256-GCM provides confidentiality + integrity**. You cannot decrypt a modified ciphertext — `InvalidTag` is raised. This prevents database-level bit-flip attacks.
