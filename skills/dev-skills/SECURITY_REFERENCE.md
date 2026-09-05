# Security Pattern Reference

This file is loaded on demand by the dev-skills skill during Gate 3 (security
scan) and audit mode. It contains rules and bad/good code examples for every
security pattern. Use these to pattern-match against code being reviewed.

---

## Rules — flag on sight during any coding session

These rules apply as code is written, not just during Gate 3 scans.

**Secrets and credentials:**
- Never hardcode API keys, passwords, tokens in source — not even in comments
- Use environment variables or a secrets manager
- Flag `.env` files not in `.gitignore` — add immediately
- Check git history: `git log --diff-filter=D -- '*.env'`
- Rotate any accidentally exposed secret

**Dangerous execution:**
- No `eval()`, `exec()`, `Function()`, `shell=True` with user input, `os.system()` with user input
- No `Invoke-Expression`, `iex`, `& $userInput` in PowerShell
- Use parameterized commands, safe parsers, allowlisted inputs

**Input handling:**
- All external input is hostile: HTTP params, file contents, env vars, CLI args, WebSocket, IPC
- Validate type, length, format, range before use
- Sanitize for output context (HTML-encode, parameterize SQL, escape shell)

**Database access:**
- SQL string concatenation is always wrong — use parameterized queries or ORM
- App DB account should not have DROP/schema-modification rights in production

**Network and HTTP:**
- Never disable TLS: `verify=False`, `rejectUnauthorized: false`, `InsecureSkipVerify: true`
- Validate and allowlist URLs before server-side requests (SSRF prevention)
- Never reflect stack traces or internal paths to clients

**File system:**
- Validate paths against traversal — reject `../`, absolute paths from user input, null bytes
- Restrictive permissions: `0o600` (Unix) / owner-only ACLs (Windows) for secrets
- Never pass user-controlled strings directly to file open/delete

**Serialization:**
- No `pickle`/`marshal`/`ObjectInputStream`/`unserialize()` on untrusted data
- Use JSON with schema validation

**JavaScript/Node-specific:**
- Prototype pollution: check for `__proto__`, `constructor`, `prototype` in user-supplied keys
- XSS: no `innerHTML` with user data — use `textContent` or DOMPurify
- Open redirect: allowlist redirect targets, never `res.redirect(req.query.url)` raw

**Windows-specific:**
- PowerShell injection: no `Invoke-Expression`/`iex`/`& $userInput` — use parameter arrays
- UNC path injection: reject `\\` and `//` prefixed paths from user input (NTLM hash leak)
- DLL hijacking: use absolute paths for `LoadLibrary`/`ctypes.CDLL`, call `SetDllDirectory("")`
- Credential storage: use DPAPI/Credential Manager/`keyring` — never plaintext in registry or config
- Registry: use `HKCU` not `HKLM` unless needed, set restrictive ACLs, validate data read back
- Services: never run as `SYSTEM` — use dedicated service accounts, gMSA where available
- Code signing: sign with Authenticode, never bypass execution policy
- Path hazards: reject reserved names (`CON`, `PRN`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`),
  handle MAX_PATH, account for case insensitivity

**Linux-specific:**
- SUID/SGID: never set SUID casually — prefer Linux capabilities (`setcap`)
- Containers: never run as root, never `--privileged`, drop all caps and add back selectively,
  never mount Docker socket, pin base image digests not tags, use `--read-only` root filesystem
- Symlink/TOCTOU: use `mkstemp()`/`NamedTemporaryFile()`, not predictable temp paths;
  `O_NOFOLLOW` to refuse symlinks
- Systemd: add `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`,
  `CapabilityBoundingSet`; flag units running as root without hardening
- SSH keys: `0600` private / `0644` public, never commit to git, prefer Ed25519,
  avoid agent forwarding on untrusted hosts (use `ProxyJump`)
- Cron: absolute paths only, scripts not world-writable, no credentials in crontab
- SELinux/AppArmor: never `setenforce 0` or disable profiles as a fix — diagnose the policy
- Package repos: verify GPG fingerprints, reject unsigned repos, pin third-party packages

**Android-specific:**
- Exported components: never export Activities, Services, BroadcastReceivers, or
  ContentProviders without permission guards — unprotected exports let any app on
  the device invoke them
- Manifest hardening: `android:debuggable="false"`, `android:allowBackup="false"`,
  `android:usesCleartextTraffic="false"` in production
- WebView: never combine `setJavaScriptEnabled(true)` with `addJavascriptInterface()`
  on API < 17 (RCE); validate URLs loaded in WebViews, disable file access
  (`setAllowFileAccess(false)`)
- Intent security: validate all data from incoming Intents — they are external input;
  use explicit Intents for internal communication; never put secrets in Intent extras
- Storage: never store secrets in SharedPreferences (plaintext XML) — use
  EncryptedSharedPreferences or Android Keystore; never write sensitive data to
  external storage (world-readable before API 29)
- Network: use Network Security Config for certificate pinning; never override
  `onReceivedSslError` to proceed on errors
- Permissions: request only what the app needs, prefer runtime over install-time
  permissions, never request `WRITE_EXTERNAL_STORAGE` when scoped storage suffices
- Logging: never log PII, tokens, or passwords — `Log.d`/`Log.v` are readable
  by any app on rooted devices and by ADB
- ProGuard/R8: enable for release builds — prevents trivial reverse engineering
- APK signing: never ship with the default debug keystore — verify release signature
  with `apksigner verify --print-certs`; CN containing "Android Debug" = ship failure
- Keystore in `.gitignore`: verify `.gitignore` contains `*.keystore`, `*.jks`,
  `*.pk8`, `key.properties` — a committed keystore is a 🚨 Critical finding

**Cross-platform:**
- File permissions: `0o600`/`chmod` on Unix, `icacls` owner-only on Windows
- Path validation: reject UNC paths, reject Windows reserved names, check traversal
- Credential hierarchy: secrets manager > OS credential store > encrypted file > env var > never hardcode

**Python best practices:**
- Type hints on every function signature. Use `from __future__ import annotations` for Python ≤3.9.
- Context managers (`with`) for all resources. Always `encoding="utf-8"` on `open()`.
- `pathlib.Path` over string path concatenation.
- `secrets` module for tokens/nonces/session IDs — never `random`.
- No `assert` for validation — stripped by `python -O`. Use `if` + `raise`.
- No bare `except` — catch specific exceptions, log, and re-raise.
- Never log passwords, tokens, full request bodies, or PII.
- Hashing: SHA-256 minimum for integrity. bcrypt/argon2/scrypt for passwords — never MD5/SHA1.
- No mutable default arguments — use `None` + create inside the function.
- Pin exact versions in requirements. Use `pip-compile` for transitive pinning.
- Run `bandit` before committing. Add to pre-commit hooks or CI.

---

## Secrets and credentials

```python
# bad
API_KEY = "sk-abc123..."
DB_PASSWORD = "hunter2"

# good
import os
API_KEY = os.environ["API_KEY"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
```

---

## Dangerous execution

```python
# bad — command injection
import subprocess
subprocess.run(f"ls {user_input}", shell=True)
os.system(f"convert {filename}")

# good — no shell, no injection
subprocess.run(["ls", user_input], shell=False)
subprocess.run(["convert", filename])
```

---

## Input handling and SQL injection

```python
# bad — trusts input blindly
@app.route("/user/<user_id>")
def get_user(user_id):
    return db.query(f"SELECT * FROM users WHERE id = {user_id}")

# good — validates and parameterizes
@app.route("/user/<int:user_id>")
def get_user(user_id: int):
    return db.query("SELECT * FROM users WHERE id = ?", (user_id,))
```

```python
# bad — SQL injection
cursor.execute("SELECT * FROM users WHERE id = " + user_id)
cursor.execute(f"DELETE FROM orders WHERE id = '{order_id}'")

# good
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))
```

---

## Network and HTTP

```python
# bad — disables TLS, leaks internals
resp = requests.get(url, verify=False)
return {"error": traceback.format_exc()}

# good
resp = requests.get(url)  # verify=True is default
logger.exception("Request failed")
return {"error": "An internal error occurred"}, 500
```

---

## File system and path traversal

```python
# bad — path traversal
filename = request.args["file"]
with open(f"/uploads/{filename}") as f:
    return f.read()

# good
from pathlib import Path
upload_dir = Path("/uploads").resolve()
file_path = (upload_dir / filename).resolve()
if not file_path.is_relative_to(upload_dir):
    raise ValueError("Path traversal detected")
with open(file_path, "r", encoding="utf-8") as f:
    return f.read()
```

---

## Serialization

```python
# bad — RCE via pickle
import pickle
data = pickle.loads(user_uploaded_bytes)

# good
import json
data = json.loads(user_uploaded_bytes)
# then validate against a schema
```

---

## JavaScript/Node-specific

```javascript
// bad — XSS
element.innerHTML = userComment;
// bad — open redirect
res.redirect(req.query.returnUrl);

// good
element.textContent = userComment;
// good — allowlisted redirect
const allowed = ["/dashboard", "/profile", "/settings"];
const target = allowed.includes(req.query.returnUrl) ? req.query.returnUrl : "/";
res.redirect(target);
```

---

## Windows — PowerShell injection

```powershell
# bad — injection via string expansion
Invoke-Expression "Get-Content $userPath"
& "cmd /c $userCommand"
Start-Process -FilePath "cmd.exe" -ArgumentList "/c $userInput"

# good — no shell interpretation
Get-Content -LiteralPath $userPath
Start-Process -FilePath "myapp.exe" -ArgumentList @($arg1, $arg2)
```

---

## Windows — UNC path injection

```python
# bad — user controls path, UNC not checked
open(user_supplied_path)

# good
if user_path.startswith("\\\\") or user_path.startswith("//"):
    raise ValueError("UNC paths not allowed")
resolved = Path(user_path).resolve()
```

---

## Windows — credential storage

```python
# bad — plaintext in registry
import winreg
winreg.SetValueEx(key, "ApiToken", 0, winreg.REG_SZ, "sk-abc123")

# good — credential manager
import keyring
keyring.set_password("myapp", "api_token", token)
token = keyring.get_password("myapp", "api_token")
```

---

## Linux — SUID vs capabilities

```bash
# bad — full root privileges to anyone who runs it
chmod u+s /usr/local/bin/myapp

# good — only the specific capability needed
sudo setcap cap_net_bind_service=+ep /usr/local/bin/myapp
```

---

## Linux — Docker/container security

```dockerfile
# bad
FROM python:latest
# runs as root by default, unpinned tag

# good
FROM python:3.12-slim@sha256:abcd1234...
RUN useradd -r -s /bin/false appuser
USER appuser
COPY --chown=appuser:appuser . /app
```

---

## Linux — symlink/TOCTOU races

```python
# bad — predictable, race-prone
path = f"/tmp/myapp_{user_id}.txt"
if os.path.exists(path):
    with open(path) as f:
        data = f.read()

# good — atomic, unpredictable
import tempfile
with tempfile.NamedTemporaryFile(prefix="myapp_", delete=False) as f:
    f.write(data)
    safe_path = f.name
```

---

## Linux — systemd hardening

```ini
[Service]
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/myapp
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
User=myapp
Group=myapp
```

---

## Linux — cron job security

```bash
# bad — relative path, world-writable script, credential in crontab
* * * * * backup.sh --password=hunter2

# good — absolute path, restricted script
* * * * * /usr/local/bin/backup.sh --config /etc/backup/config.env
# config.env is 0600 owned by the cron user
```

---

## Android — exported components

```xml
<!-- bad — activity exported with no permission, any app can launch it -->
<activity android:name=".admin.AdminPanelActivity"
    android:exported="true" />

<!-- good — require a permission to launch -->
<activity android:name=".admin.AdminPanelActivity"
    android:exported="true"
    android:permission="com.example.app.permission.ADMIN" />

<!-- good — if only used internally, don't export -->
<activity android:name=".admin.AdminPanelActivity"
    android:exported="false" />
```

---

## Android — manifest hardening

```xml
<!-- bad — debuggable, allows backup, allows cleartext -->
<application
    android:debuggable="true"
    android:allowBackup="true"
    android:usesCleartextTraffic="true">

<!-- good — production-hardened -->
<application
    android:debuggable="false"
    android:allowBackup="false"
    android:usesCleartextTraffic="false"
    android:networkSecurityConfig="@xml/network_security_config">
```

---

## Android — WebView security

```kotlin
// bad — JavaScript + JS interface = RCE on older APIs
webView.settings.javaScriptEnabled = true
webView.addJavascriptInterface(MyJSInterface(), "Android")
webView.loadUrl(intentData)  // attacker controls the URL

// good — validate URL, restrict file access
webView.settings.javaScriptEnabled = true
webView.settings.allowFileAccess = false
webView.settings.allowContentAccess = false
val url = intent.getStringExtra("url") ?: return
if (!url.startsWith("https://example.com/")) return
webView.loadUrl(url)
```

---

## Android — Intent validation

```kotlin
// bad — trusts Intent data blindly
val userId = intent.getStringExtra("user_id")
db.query("SELECT * FROM users WHERE id = $userId")  // SQL injection + unvalidated

// good — validate and parameterize
val userId = intent.getStringExtra("user_id")
    ?.takeIf { it.matches(Regex("^[0-9]+$")) }
    ?: return
db.query("SELECT * FROM users WHERE id = ?", arrayOf(userId))
```

---

## Android — secure storage

```kotlin
// bad — secrets in plain SharedPreferences
val prefs = getSharedPreferences("auth", MODE_PRIVATE)
prefs.edit().putString("api_token", token).apply()

// good — EncryptedSharedPreferences
val masterKey = MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build()
val prefs = EncryptedSharedPreferences.create(
    context, "auth_encrypted", masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
)
prefs.edit().putString("api_token", token).apply()
```

---

## Android — network security config

```xml
<!-- res/xml/network_security_config.xml -->
<!-- good — certificate pinning + no cleartext -->
<network-security-config>
    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">api.example.com</domain>
        <pin-set expiration="2027-01-01">
            <pin digest="SHA-256">base64EncodedPin=</pin>
            <pin digest="SHA-256">base64BackupPin=</pin>
        </pin-set>
    </domain-config>
</network-security-config>
```

```kotlin
// bad — bypasses SSL errors
webView.webViewClient = object : WebViewClient() {
    override fun onReceivedSslError(view: WebView, handler: SslErrorHandler, error: SslError) {
        handler.proceed()  // accepts any certificate
    }
}

// good — reject bad certificates
webView.webViewClient = object : WebViewClient() {
    override fun onReceivedSslError(view: WebView, handler: SslErrorHandler, error: SslError) {
        handler.cancel()
    }
}
```

---

## Android — APK signing

```groovy
// bad — no signing config, Gradle uses debug keystore by default
android {
    buildTypes {
        release {
            minifyEnabled true
            // no signingConfig — APK is signed with ~/.android/debug.keystore
        }
    }
}

// good — release build uses a dedicated release keystore
android {
    signingConfigs {
        release {
            storeFile file(System.getenv("RELEASE_KEYSTORE_PATH") ?: "release.keystore")
            storePassword System.getenv("RELEASE_KEYSTORE_PASSWORD")
            keyAlias System.getenv("RELEASE_KEY_ALIAS")
            keyPassword System.getenv("RELEASE_KEY_PASSWORD")
        }
    }
    buildTypes {
        release {
            minifyEnabled true
            signingConfig signingConfigs.release
        }
    }
}
```

```bash
# Verify signing — run before every release

# bad — no verification, ship whatever Gradle produced
cp app/build/outputs/apk/release/app-release.apk ./release.apk

# good — verify the signer is NOT the debug key
apksigner verify --print-certs app-release.apk
# Check output: CN must NOT contain "Android Debug"
# SHA-256 must NOT match the debug keystore fingerprint

# alternative when apksigner is unavailable
keytool -printcert -jarfile app-release.apk
# Look for: Owner: CN=<your org or name> — NOT CN=Android Debug

# If you see any of these, the APK is debug-signed — DO NOT SHIP:
#   Owner: CN=Android Debug, O=Android, C=US
#   Signer #1 certificate DN: CN=Android Debug, O=Android, C=US
```

```bash
# Generating a release keystore (one-time setup)
keytool -genkeypair -v \
    -keystore release.keystore \
    -alias release \
    -keyalg RSA -keysize 2048 \
    -validity 10000 \
    -storepass <strong-password> \
    -keypass <strong-password> \
    -dname "CN=<Your Name>, O=<Your Org>, L=<City>, ST=<State>, C=<Country>"

# NEVER commit the keystore or its passwords to version control
# Store keystore in a secure location, passwords in a secrets manager
```

```gitignore
# bad — .gitignore missing keystore entries (or no .gitignore at all)
# Keystores, key.properties, and .pk8 files can be committed accidentally

# good — .gitignore includes all signing-related files
*.keystore
*.jks
*.pk8
*.pem
key.properties
signing.properties
```

```groovy
// bad — passwords hardcoded in build.gradle (committed to repo)
signingConfigs {
    release {
        storeFile file("release.keystore")
        storePassword "mysecretpassword"
        keyAlias "mykey"
        keyPassword "anothersecret"
    }
}

// good — passwords loaded from key.properties (which is in .gitignore)
def keystorePropertiesFile = rootProject.file("key.properties")
def keystoreProperties = new Properties()
keystoreProperties.load(new FileInputStream(keystorePropertiesFile))

signingConfigs {
    release {
        storeFile file(keystoreProperties['storeFile'])
        storePassword keystoreProperties['storePassword']
        keyAlias keystoreProperties['keyAlias']
        keyPassword keystoreProperties['keyPassword']
    }
}
```

---

## Cross-platform file permissions

```python
import os
import platform

def set_restrictive_permissions(path: str) -> None:
    if platform.system() == "Windows":
        import subprocess
        subprocess.run(
            ["icacls", path, "/inheritance:r",
             "/grant:r", f"{os.getlogin()}:(F)"],
            check=True
        )
    else:
        os.chmod(path, 0o600)
```

---

## Cross-platform path validation

```python
from pathlib import Path
import platform

def validate_user_path(user_input: str, allowed_base: Path) -> Path:
    # reject UNC paths on Windows
    if user_input.startswith("\\\\") or user_input.startswith("//"):
        raise ValueError("UNC paths not allowed")

    # reject Windows reserved names
    if platform.system() == "Windows":
        name = Path(user_input).stem.upper()
        reserved = {"CON", "PRN", "AUX", "NUL"} | {
            f"{d}{n}" for d in ("COM", "LPT") for n in range(1, 10)
        }
        if name in reserved:
            raise ValueError(f"Reserved filename: {name}")

    resolved = (allowed_base / user_input).resolve()
    if not resolved.is_relative_to(allowed_base.resolve()):
        raise ValueError("Path traversal detected")
    return resolved
```

---

## Cross-platform credential retrieval

```python
import os

def get_secret(name: str) -> str:
    # tier 2: OS credential store
    try:
        import keyring
        val = keyring.get_password("myapp", name)
        if val:
            return val
    except ImportError:
        pass
    # tier 4: environment variable (floor)
    val = os.environ.get(name)
    if val:
        return val
    raise RuntimeError(f"Secret '{name}' not found in credential store or environment")
```

---

## Python — type hints

```python
# bad
def create_user(username, role, active):
    ...

# good
def create_user(username: str, role: str, active: bool) -> dict[str, Any]:
    ...
```

---

## Python — context managers

```python
# bad
f = open("data.txt")
data = f.read()

# good
with open("data.txt", "r", encoding="utf-8") as f:
    data = f.read()
```

---

## Python — pathlib

```python
# bad
file_path = upload_dir + "/" + filename

# good
from pathlib import Path
file_path = (Path(upload_dir) / filename).resolve()
```

---

## Python — secrets module

```python
# bad
import random
token = random.randint(100000, 999999)

# good
import secrets
token = secrets.token_urlsafe(32)
```

---

## Python — assert is not validation

```python
# bad — silently disabled with -O
assert user.is_admin, "Admin required"

# good
if not user.is_admin:
    raise PermissionError("Admin required")
```

---

## Python — no bare except

```python
# bad
try:
    result = process(data)
except:
    pass

# good
try:
    result = process(data)
except ValueError as e:
    logger.warning("Invalid input: %s", e)
    raise
```

---

## Python — sensitive data logging

```python
# bad
logger.debug("Login: username=%s password=%s", username, password)

# good
logger.debug("Login attempt: username=%s", username)
```

---

## Python — hashing

```python
# bad
hashlib.md5(data).hexdigest()
hashlib.sha1(password.encode()).hexdigest()

# good — integrity
hashlib.sha256(data).hexdigest()
# good — passwords
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
```

---

## Python — mutable default arguments

```python
# bad
def add_item(item, collection=[]):
    collection.append(item)
    return collection

# good
def add_item(item, collection: list | None = None) -> list:
    if collection is None:
        collection = []
    collection.append(item)
    return collection
```

---

## Python — pinned dependencies

```
# bad
requests>=2.28.0
flask

# good
requests==2.32.3
flask==3.0.3
```

---

## "Just make it work" — loud comment pattern

```python
# SECURITY RISK: hardcoded credentials — move to env var before any real use
# TODO: os.environ['DB_PASSWORD']
DB_PASSWORD = "hunter2"
```
