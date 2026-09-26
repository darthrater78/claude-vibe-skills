# Security Pattern Reference

This file is loaded on demand by the dev-skills skill during Gate 3 (security
scan) and audit mode. It contains rules and bad/good code examples for
cross-platform and language-general security patterns. Use these to
pattern-match against code being reviewed.

Windows, Linux, and Android patterns live in their own files
(`SECURITY_WINDOWS.md`, `SECURITY_LINUX.md`, `SECURITY_ANDROID.md`) and are
loaded alongside this one only when project environment detection
(`WORKFLOW_REFERENCE.md`, Step 1) matches that platform.

---

## Audit mode

On "audit my project", "scan this codebase", "security review", or "check my
code", `SKILL.md` §9): with this file loaded, also read `QUALITY_REFERENCE.md` and every
platform file the project matches (`WORKFLOW_REFERENCE.md` Step 1 signals):
`SECURITY_WINDOWS.md`, `SECURITY_LINUX.md`, `SECURITY_ANDROID.md` (+
`QUALITY_ANDROID.md`). Then:
1. Discover source files via Glob
2. Triage: read high-risk files first (auth, login, upload, config, api,
   routes, crypto, token, secret, password)
3. Grep for dangerous patterns (`eval(`, `shell=True`, `pickle.loads`, `md5`,
   `Invoke-Expression`, `innerHTML`, hardcoded strings, `.env` files)
4. Apply every security rule from `SKILL.md` Section 4 and this file
5. Output findings by severity (🚨 Critical, ⚠️ High, 📝 Medium, 💡 Low) with
   file:line, description, and fix
6. End with a summary: files scanned, findings by severity, top 3 next steps.
   A full audit that finds `.github/workflows/` also runs the workflow audit
   (`WORKFLOW_REFERENCE.md`) and folds its findings in.

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

**Dependencies:**
- Every package must be a current release with no known Critical/High CVE —
  direct and transitive (SKILL.md Section 4.1)
- Never write a version number from memory — look up the current release before
  pinning; a remembered version is stale the day it is written
- A package or runtime with LTS lines stays on LTS — see "LTS lines" below
- Pin exact versions, and keep the lockfile committed
- A pinned version is not a safe version: pinning decides *which* CVEs you carry
- Re-audit the whole tree on every security gate, not only when the manifest
  changes — the version stands still, the advisories do not
- Flag a dependency whose upstream is abandoned: it will never ship the fix for
  its next advisory

**JavaScript/Node-specific:**
- Prototype pollution: check for `__proto__`, `constructor`, `prototype` in user-supplied keys
- XSS: no `innerHTML` with user data — use `textContent` or DOMPurify
- Open redirect: allowlist redirect targets, never `res.redirect(req.query.url)` raw

**Platform-specific:** loaded on demand alongside this file, based on the
detected project environment (`WORKFLOW_REFERENCE.md`, Step 1) — Windows
(`SECURITY_WINDOWS.md`), Linux/containers (`SECURITY_LINUX.md`), Android
(`SECURITY_ANDROID.md`). Each covers rules and bad/good examples specific to
that platform only.

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

## Platform-specific patterns

Bad/good code examples for Windows, Linux, and Android security patterns live
in `SECURITY_WINDOWS.md`, `SECURITY_LINUX.md`, and `SECURITY_ANDROID.md`
respectively — loaded alongside this file once project environment detection
(`WORKFLOW_REFERENCE.md`, Step 1) identifies the platform.

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

## Dependencies — pinned, current, and CVE-free

Three separate properties. A manifest can satisfy one and fail the others, and
each failure has its own consequence.

```
# bad — unpinned: the build is not reproducible, and today's audit
# says nothing about tomorrow's install
requests>=2.28.0
flask

# bad — pinned, reproducible, and vulnerable. Pinning froze the CVEs in
# place; this is the version a model writes from memory
requests==2.28.0        # CVE-2023-32681, fixed in 2.31.0
flask==2.0.1            # 3 majors behind current

# good — pinned to the current release, audit clean
requests==2.32.3
flask==3.0.3
```

**Look the version up; never recall it.** The check is one command per
ecosystem, and it is the difference between a project that starts current and
one that starts a year behind:

```bash
npm view <pkg> version                 # Node
pip index versions <pkg>               # Python (pip marks this experimental)
cargo search <pkg>                     # Rust
go list -m -versions <module>          # Go
dotnet package search <pkg>            # .NET (SDK 9+; else check nuget.org)
```

**LTS lines: stay on LTS, and on the newest one.** Where a package or runtime
publishes long-term-support lines (Node.js, .NET, Java, Ubuntu, Debian,
Kubernetes, Django, many databases and base images), "current" means the
newest patch of the newest *settled* LTS line, not the newest release overall.
A project picked LTS for stability, and a jump to a short-lived line trades
that away without anyone deciding to.

- **Settled** means the line has had its first patch after going LTS: Node's
  line once it is Active LTS, Ubuntu `.04.1`, .NET `x.0.1`, Java `x.0.1`. A
  brand-new LTS waits for that; the previous LTS line stays current until then.
- **New projects start on the newest settled LTS** where the ecosystem has one.
- **LTS → non-LTS** (Node Current, .NET STS, a Java feature release, an Ubuntu
  interim) is the user's call, asked and recorded, never a silent upgrade.
- **Within a line, always the newest patch.** That's where the security fixes
  land.
- **A newer LTS major is a major-version upgrade**: its own change, its own
  gates (`SKILL.md` §4.1).
- **An LTS past end of support is a High finding** (`SECURITY_GATE.md`): no
  more security fixes will ship for it. A superseded LTS still in support is a
  Low finding, and the upgrade gets planned.
- **Pin the exact version**, never a floating `lts` tag (`node:lts`,
  `lts/*` in a Dockerfile). The one exception is the CI runtime in a workflow
  template, where `lts/*` is the point.
- Ecosystems with no LTS lines (Python, most npm and PyPI libraries) keep
  "latest stable".

```
# bad — "latest stable" (as of 2026-09) moved an LTS project to Current
FROM node:26.10.0-alpine         # not LTS until 2026-10-28

# good — newest patch of the newest settled LTS, looked up the same day
FROM node:24.21.0-alpine         # Active LTS
```

Look up the LTS lines and their end-of-support dates; never recall them:

**endoflife.date's `lts` can be a date instead of `true`.** A line whose `lts`
date is still in the future is not LTS yet, so compare it with today; a truthy
check calls Node 26 LTS months early. The `jq` lines need `jq` installed.

```bash
curl -sf https://endoflife.date/api/<product>.json   # any product: lts, eol, latest
curl -sf https://nodejs.org/dist/index.json | jq -r '[.[]|select(.lts)][0].version'
curl -sf https://api.adoptium.net/v3/info/available_releases | jq .most_recent_lts
curl -sf https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json \
  | jq -r '.["releases-index"][]|select(."release-type"=="lts")|."channel-version"' | head -1
```

**Audit the tree, not the manifest.** Most advisories arrive through packages
nobody chose directly — the manifest looks clean while the lockfile carries the
vulnerability:

```bash
npm audit --audit-level=high           # Node
pip-audit                              # Python
cargo audit                            # Rust
govulncheck ./...                      # Go
dotnet list package --vulnerable --include-transitive
osv-scanner scan source .              # any ecosystem, incl. lockfiles
```

**Fixing a transitive advisory** means moving the parent to a range that pulls
the fixed child — not pinning the child behind its parent's back:

```
# bad — fights the resolver; the parent may still pull its own pinned copy,
# and the next lockfile regeneration silently undoes this
urllib3==1.26.17

# good — move the parent forward so the fixed child comes with it
requests==2.32.3        # pulls urllib3 >= 1.26.17
```

For an ecosystem that supports it, an override/resolution is the explicit form
(`overrides` in npm, `[patch]` in Cargo) — use it deliberately, with a comment
naming the advisory, and remove it once the parent ships the fix.

---

## "Just make it work" — loud comment pattern

```python
# SECURITY RISK: hardcoded credentials — move to env var before any real use
# TODO: os.environ['DB_PASSWORD']
DB_PASSWORD = "hunter2"
```
