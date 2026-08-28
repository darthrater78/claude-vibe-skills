# Security Pattern Reference

This file is loaded on demand by the dev-skills skill during Gate 3 (security
scan) and audit mode. It contains bad/good code examples for every security
pattern. Use these to pattern-match against code being reviewed.

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
