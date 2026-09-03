# Code Quality Pattern Reference

This file is loaded on demand by the dev-skills skill during Gate 3 and quality
review. It contains rules and bad/good code examples for structure and
performance patterns.

---

## Rules — apply as code is written

These rules apply while writing code, not just during Gate 3 quality review.
Clean structure and good performance are not separate concerns from security —
tangled code hides bugs and makes audits harder.

**Structure:**
- **Max nesting: 3 levels.** Use early returns/guard clauses to flatten logic.
- **Single responsibility.** Each function does one thing. If you can't name it
  without "and", split it.
- **No god functions.** Functions over ~40 lines are doing too much — split by
  responsibility (validation, transformation, I/O, presentation).
- **Clear data flow.** Inputs in, outputs out. Minimize side effects. Never hide
  state mutations inside getters or utility functions.
- **One-direction dependencies.** High-level modules import low-level, never the
  reverse. No circular imports — extract shared logic to a third module.
- **Don't abstract prematurely.** Three similar lines are better than an
  AbstractStrategyFactoryProvider. Extract only when the logic is genuinely the
  same concept repeated, not just similar-looking code.
- **Don't copy-paste.** When the same validation/transformation appears in 3+
  places with identical logic, extract it. But only when it's the same *concept*,
  not just coincidentally similar code.

**Performance:**
- **No N+1 queries.** Never query inside a loop. Batch with `IN`/`ANY` or use joins.
- **Right data structure.** Sets for membership checks, dicts for lookups — not lists.
  O(1) vs O(n) matters when n grows.
- **No string concatenation in loops.** Use `join()` or builders.
- **Compute once.** Don't recompute expensive results (regex compilation, config loading,
  API calls) inside loops when the result doesn't change.
- **No allocations in hot paths.** Constants at module level, not re-created per call.
- **Fetch only what you need.** No `SELECT *` when you need two columns. No loading
  entire files to read one line. Paginate unbounded queries.
- **Don't block.** No sync I/O on async event loops. No CPU-intensive work on the
  main thread. Offload to workers.
- **Bound your caches.** Unbounded `dict` caches grow forever → memory leak. Use
  `lru_cache(maxsize=N)` or equivalent.
- **Clean up listeners.** Event listeners and subscriptions that outlive their
  component are memory leaks.
- **Index your queries.** Every `WHERE` clause on a column used in production
  should have an index. Flag missing indexes.

**Container / build dependency hygiene:**
- **Single source of truth for dependencies.** Never hardcode package lists in a
  Dockerfile (`pip install pkg1 pkg2`, `npm install pkg1 pkg2`). Use a dependency
  file (`requirements.txt`, `package.json`, `Pipfile`, `pyproject.toml`) and
  install from it (`pip install -r requirements.txt`, `npm ci`).
- **Imports must match declared dependencies.** When code adds a new import, the
  corresponding package must appear in the dependency file AND the build must
  install it. A missing dependency compiles locally (installed in the dev venv)
  but crashes in a fresh container. After any feature that adds an import, verify
  the package is in the dependency file.
- **Dockerfile installs from the dependency file, not around it.** If a Dockerfile
  has its own `pip install` or `npm install` line with package names, those packages
  drift from the real dependency file. Flag any Dockerfile that installs packages
  by name instead of from the project's dependency file.

---

## Deep nesting — flatten with early returns

```python
# bad — 4 levels deep, hard to follow
def process_order(order):
    if order:
        if order.is_valid():
            if order.has_stock():
                if order.payment_cleared():
                    ship(order)
                else:
                    raise PaymentError("Payment not cleared")
            else:
                raise StockError("Out of stock")
        else:
            raise ValidationError("Invalid order")
    else:
        raise ValueError("No order")

# good — flat, each guard exits early
def process_order(order):
    if not order:
        raise ValueError("No order")
    if not order.is_valid():
        raise ValidationError("Invalid order")
    if not order.has_stock():
        raise StockError("Out of stock")
    if not order.payment_cleared():
        raise PaymentError("Payment not cleared")
    ship(order)
```

---

## God functions — split by responsibility

```python
# bad — one function does validation, transformation, DB, email, logging
def handle_signup(request):
    name = request.form["name"].strip()
    if len(name) < 2:
        return error("Name too short")
    email = request.form["email"].lower()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return error("Invalid email")
    password = request.form["password"]
    if len(password) < 8:
        return error("Password too short")
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    user_id = db.execute("INSERT INTO users ...", (name, email, hashed))
    token = secrets.token_urlsafe(32)
    db.execute("INSERT INTO tokens ...", (user_id, token))
    send_email(email, f"Welcome {name}", f"Verify: /verify?token={token}")
    logger.info("User %s signed up", user_id)
    return redirect("/welcome")

# good — each function has one job
def validate_signup(form: dict) -> SignupData:
    name = form["name"].strip()
    if len(name) < 2:
        raise ValidationError("Name too short")
    email = form["email"].lower()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise ValidationError("Invalid email")
    if len(form["password"]) < 8:
        raise ValidationError("Password too short")
    return SignupData(name=name, email=email, password=form["password"])

def create_user(data: SignupData) -> int:
    hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt())
    return db.execute("INSERT INTO users ...", (data.name, data.email, hashed))

def send_verification(user_id: int, email: str) -> None:
    token = secrets.token_urlsafe(32)
    db.execute("INSERT INTO tokens ...", (user_id, token))
    send_email(email, "Welcome", f"Verify: /verify?token={token}")

def handle_signup(request):
    data = validate_signup(request.form)
    user_id = create_user(data)
    send_verification(user_id, data.email)
    return redirect("/welcome")
```

---

## N+1 queries — batch instead of loop

```python
# bad — 1 query per user, 100 users = 101 queries
users = db.query("SELECT * FROM users LIMIT 100")
for user in users:
    orders = db.query("SELECT * FROM orders WHERE user_id = %s", (user.id,))
    user.orders = orders

# good — 2 queries total regardless of count
users = db.query("SELECT * FROM users LIMIT 100")
user_ids = [u.id for u in users]
orders = db.query("SELECT * FROM orders WHERE user_id = ANY(%s)", (user_ids,))
orders_by_user = defaultdict(list)
for order in orders:
    orders_by_user[order.user_id].append(order)
for user in users:
    user.orders = orders_by_user[user.id]
```

```javascript
// bad — N+1 in async code
const users = await db.query("SELECT * FROM users LIMIT 100");
for (const user of users) {
  user.orders = await db.query("SELECT * FROM orders WHERE user_id = $1", [user.id]);
}

// good — single join or batch
const rows = await db.query(`
  SELECT u.*, o.id as order_id, o.total
  FROM users u LEFT JOIN orders o ON u.id = o.user_id
  LIMIT 100
`);
```

---

## Wrong data structure for the job

```python
# bad — linear scan on every check, O(n) per lookup
allowed_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
if user_id in allowed_ids:  # O(n)
    ...

# bad — scanning a list to find duplicates, O(n²)
seen = []
for item in items:
    if item in seen:
        duplicates.append(item)
    seen.append(item)

# good — O(1) lookups
allowed_ids = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
if user_id in allowed_ids:  # O(1)
    ...

# good — set for dedup, O(n) total
seen = set()
for item in items:
    if item in seen:
        duplicates.append(item)
    seen.add(item)
```

---

## String concatenation in loops

```python
# bad — creates a new string object every iteration, O(n²) total
result = ""
for line in lines:
    result += line + "\n"

# good — O(n) total
result = "\n".join(lines)

# bad — f-string in a loop building HTML
html = ""
for item in items:
    html += f"<li>{item.name}</li>"

# good
html = "".join(f"<li>{item.name}</li>" for item in items)
```

```javascript
// bad
let csv = "";
for (const row of rows) {
  csv += row.join(",") + "\n";
}

// good
const csv = rows.map(row => row.join(",")).join("\n");
```

---

## Recomputing in loops

```python
# bad — compiles regex 10,000 times
for line in lines:
    match = re.match(r"^ERROR:\s+(.+)$", line)

# good — compile once
error_pattern = re.compile(r"^ERROR:\s+(.+)$")
for line in lines:
    match = error_pattern.match(line)

# bad — calling expensive function repeatedly with same args
for item in items:
    config = load_config_from_disk()  # same result every time
    process(item, config)

# good — compute once
config = load_config_from_disk()
for item in items:
    process(item, config)
```

---

## Allocations in hot paths

```python
# bad — creates a new list and dict every call, called thousands of times
def get_user_permissions(user_id: int) -> list[str]:
    defaults = ["read"]  # new list every call
    overrides = {"admin": ["read", "write", "delete"]}  # new dict every call
    role = get_role(user_id)
    return overrides.get(role, defaults)

# good — module-level constants
_DEFAULT_PERMS = ("read",)
_ROLE_PERMS = {
    "admin": ("read", "write", "delete"),
}

def get_user_permissions(user_id: int) -> tuple[str, ...]:
    role = get_role(user_id)
    return _ROLE_PERMS.get(role, _DEFAULT_PERMS)
```

---

## Loading everything when you need a subset

```python
# bad — loads all columns and all rows into memory
users = db.query("SELECT * FROM users")
names = [u.name for u in users]

# good — fetch only what's needed
names = db.query("SELECT name FROM users")

# bad — reads entire file to check first line
with open("large_file.csv", "r", encoding="utf-8") as f:
    content = f.read()
    first_line = content.split("\n")[0]

# good — reads only the first line
with open("large_file.csv", "r", encoding="utf-8") as f:
    first_line = f.readline()
```

```javascript
// bad — fetches all fields from API then uses two
const response = await fetch("/api/users");
const users = await response.json();
const names = users.map(u => u.name);

// good — ask for only what you need (if API supports it)
const response = await fetch("/api/users?fields=id,name");
```

---

## Blocking the event loop / main thread

```javascript
// bad — blocks the event loop with sync I/O
const data = fs.readFileSync("large-file.json", "utf-8");

// good — non-blocking
const data = await fs.promises.readFile("large-file.json", "utf-8");

// bad — CPU-intensive work on the event loop
app.get("/report", (req, res) => {
  const result = generateMassiveReport(); // blocks all other requests
  res.json(result);
});

// good — offload to worker
app.get("/report", async (req, res) => {
  const result = await runInWorker(generateMassiveReport);
  res.json(result);
});
```

```python
# bad — sync HTTP call inside async handler
async def handle_request(request):
    resp = requests.get("https://api.example.com/data")  # blocks the loop
    return resp.json()

# good — use async HTTP client
async def handle_request(request):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/data") as resp:
            return await resp.json()
```

---

## Circular dependencies / tangled imports

```python
# bad — models.py imports from views.py, views.py imports from models.py
# models.py
from views import format_user_display  # circular!

# good — dependency flows one direction
# models.py — pure data, no presentation knowledge
# views.py — imports from models, never the reverse
# If both need shared logic, extract to a third module (utils, formatters)
```

---

## Side effects hidden in unexpected places

```python
# bad — getter modifies state
class UserCache:
    def get_user(self, user_id: int) -> User:
        user = self._cache.get(user_id)
        if not user:
            user = db.query("SELECT * FROM users WHERE id = %s", (user_id,))
            self._cache[user_id] = user
            self._log_access(user_id)  # side effect in a "get"
            self._update_stats()       # another hidden side effect
        return user

# good — name reflects the side effect, or separate the concerns
class UserCache:
    def get_user(self, user_id: int) -> User:
        return self._cache.get(user_id)

    def fetch_and_cache_user(self, user_id: int) -> User:
        user = db.query("SELECT * FROM users WHERE id = %s", (user_id,))
        self._cache[user_id] = user
        return user
```

---

## Database: missing indexes and unbounded queries

```sql
-- bad — full table scan on every login
SELECT * FROM users WHERE email = 'user@example.com';
-- (no index on email column)

-- good — add the index
CREATE INDEX idx_users_email ON users(email);

-- bad — unbounded query, could return millions of rows
SELECT * FROM logs WHERE level = 'ERROR';

-- good — always limit, paginate
SELECT * FROM logs WHERE level = 'ERROR' ORDER BY created_at DESC LIMIT 100;
```

---

## Unnecessary abstraction / premature generalization

```python
# bad — AbstractStrategyFactoryProvider for a two-case if statement
class NotificationStrategy(ABC):
    @abstractmethod
    def send(self, message: str) -> None: ...

class EmailStrategy(NotificationStrategy):
    def send(self, message: str) -> None:
        send_email(message)

class SlackStrategy(NotificationStrategy):
    def send(self, message: str) -> None:
        send_slack(message)

class NotificationFactory:
    @staticmethod
    def create(channel: str) -> NotificationStrategy:
        if channel == "email":
            return EmailStrategy()
        return SlackStrategy()

# good — it's two cases, just branch
def send_notification(channel: str, message: str) -> None:
    if channel == "email":
        send_email(message)
    else:
        send_slack(message)
```

---

## Memory leaks: unbounded caches and listeners

```python
# bad — cache grows forever
_cache = {}

def get_data(key: str) -> Data:
    if key not in _cache:
        _cache[key] = expensive_fetch(key)
    return _cache[key]

# good — bounded cache
from functools import lru_cache

@lru_cache(maxsize=1024)
def get_data(key: str) -> Data:
    return expensive_fetch(key)
```

```javascript
// bad — event listeners never removed
function setupComponent() {
  window.addEventListener("resize", handleResize);
  document.addEventListener("scroll", handleScroll);
  // component destroyed, listeners persist → memory leak
}

// good — cleanup on teardown
function setupComponent() {
  window.addEventListener("resize", handleResize);
  return () => {
    window.removeEventListener("resize", handleResize);
  };
}
```

---

## Copy-paste code that should share logic

```python
# bad — same validation repeated in 3 handlers
def create_user(request):
    email = request.form["email"].strip().lower()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return error("Invalid email")
    ...

def update_user(request):
    email = request.form["email"].strip().lower()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return error("Invalid email")
    ...

def invite_user(request):
    email = request.form["email"].strip().lower()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return error("Invalid email")
    ...

# good — extract when the logic is genuinely the same concept
def validate_email(raw: str) -> str:
    email = raw.strip().lower()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise ValidationError("Invalid email")
    return email
```

---

## Container dependency drift — single source of truth

```dockerfile
# bad — hardcoded pip install list in Dockerfile drifts from requirements.txt
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install flask requests
CMD ["python", "app.py"]
# developer adds "import pyotp" → works locally (installed in venv)
# → container crashes: ModuleNotFoundError: No module named 'pyotp'

# good — install from the dependency file
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

```dockerfile
# bad — npm packages listed inline instead of from package.json
FROM node:20-slim
WORKDIR /app
COPY . .
RUN npm install express cors
CMD ["node", "server.js"]
# developer adds "const jwt = require('jsonwebtoken')" → works locally
# → container crashes: Cannot find module 'jsonwebtoken'

# good — install from package.json lockfile
FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY . .
CMD ["node", "server.js"]
```

```python
# bad — requirements.txt exists but Dockerfile ignores it
# Dockerfile has: RUN pip install flask requests pyotp
# requirements.txt has: flask, requests, pyotp, qrcode
# → qrcode missing from container, crash on the code path that uses it

# good — one source of truth, Dockerfile always reads it
# requirements.txt is the authority, Dockerfile installs from it:
#   COPY requirements.txt .
#   RUN pip install --no-cache-dir -r requirements.txt
# Adding a dependency = one edit to requirements.txt, no Dockerfile change
```

### How to catch this during review

When reviewing code that adds a new import or require:
1. Check whether the package is in the project's dependency file
2. Check whether the Dockerfile installs from that file or hardcodes its own list
3. If the Dockerfile hardcodes packages, flag both the missing package AND the
   antipattern — the fix is to switch to installing from the dependency file
