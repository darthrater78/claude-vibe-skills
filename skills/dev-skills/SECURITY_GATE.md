# Security & Quality Gate Reference — Gate 3 🔒

Loaded on demand by the dev-skills skill, when **Gate 3 is about to run, pass,
or be marked ➖ N/A**, and whenever a finding needs resolving. It is a separate
file from the other gates because it is the largest of gates 1–5 and already
pulls two more references of its own; gates 1, 2, 4 and 5 have no use for it.

It holds the security scan, the quality review, the **finding lifecycle** —
fixed, waived by the user, or withdrawn, and nothing else clears a finding —
and the combined gate output.

Gate 3 additionally loads `SECURITY_REFERENCE.md` and `QUALITY_REFERENCE.md`,
plus the platform files that project environment detection matches. Gates 1, 2,
4 and 5 are in `GATE_REFERENCE.md`; Gate 6 is in `SHIP_REFERENCE.md`.

Section numbers referenced here (Section 1, 2, 4.7, …) point at `SKILL.md`.

---

### Gate 3 — Security & Quality 🔒

**Mandatory after every build.** Two steps, both must pass: security scan and
quality review.

**Before scanning, load reference files from this skill's base directory**
(shown when the skill loaded, e.g. "Base directory for this skill: ..."):
1. Read `SECURITY_REFERENCE.md` — bad/good code examples for cross-platform
   and language-general security patterns.
2. Read `QUALITY_REFERENCE.md` — bad/good code examples for cross-platform
   structure and performance anti-patterns.
3. Detect the project's platform(s) using the same signal table as
   `WORKFLOW_REFERENCE.md` Step 1 (Docker/Windows/Linux/Android/etc). For each
   match, also read that platform's file: `SECURITY_WINDOWS.md` for Windows,
   `SECURITY_LINUX.md` for Linux or Docker/container projects,
   `SECURITY_ANDROID.md` **and** `QUALITY_ANDROID.md` for Android. A project
   can match more than one (e.g. a Dockerfile targeting a Windows base image)
   — load every file that applies. If nothing matches confidently, skip the
   platform files but say so in the scan output rather than silently omitting
   the check.
Use these examples to pattern-match against the code being reviewed.

#### Step 1 — Security scan

Run a full scan of all source files. Check for every pattern category in
Sections 4.1–4.3 and the full rule checklists in `SECURITY_REFERENCE.md` plus
whichever platform file(s) matched (loaded above).

**Then audit the dependencies — this part is not optional and not limited to
packages the session touched.** Run the ecosystem's audit tool against the
current lockfile:

| Ecosystem | Command |
|---|---|
| Node | `npm audit` / `pnpm audit` / `yarn npm audit` (Berry; classic is `yarn audit`) |
| Python | `pip-audit` (note the hyphen — there is no `pip audit` subcommand) |
| Rust | `cargo audit` |
| Go | `govulncheck ./...` |
| .NET | `dotnet list package --vulnerable --include-transitive` |
| Java | `mvn org.owasp:dependency-check-maven:check` / `gradle dependencyCheckAnalyse` |
| Any | `osv-scanner scan source .` |

If no audit tool is available for the ecosystem, say so explicitly rather than
passing the step in silence — an unaudited dependency tree is an unknown, and
unknown is never "passed" (Section 2).

Report dependency findings with the advisory ID, the package, the installed
version, and the fixed version:

> 🚨 `lodash@4.17.15` — GHSA-35jh-r3h4-6jhm (Critical, prototype pollution)
>    Fixed in 4.17.21 — bump the pin
> ⚠️ `urllib3@1.26.5` — transitive via `requests` — CVE-2023-43804 (High)
>    Fixed in 1.26.17 — bump `requests` to pull the fixed range

**Hard stops (must fix before proceeding):**
- 🚨 Critical: hardcoded secrets, SQL injection, `shell=True` with user input,
  disabled TLS, `pickle` on untrusted data, RCE vectors
- ⚠️ High: path traversal, missing auth, `debug=True` in prod, weak crypto for
  passwords, `random` for tokens, no input validation on endpoints
- 🚨⚠️ **Any dependency — direct or transitive — carrying a Critical or High
  advisory** (Section 4.1). A pinned version is not a safe version; pinning
  fixes *which* CVEs the project has, not *whether* it has any. Bump to the
  fixed release and re-run the audit. Where no fixed release exists upstream,
  the gate does not pass silently: surface the advisory and the options
  (patch, vendor, replace, or accept with a documented reason) and let the
  user decide on the record

**Fixing a Critical or High — three checks, every time, not just "patch and
move on":**
1. **Reproduce before writing the fix.** A fix written from reading the code
   is a guess about the bug shape; a fix written after triggering the actual
   failure is a fix for the actual bug. Once it's fixed, look for sibling
   paths into the same bad state — the same class of bug rarely has exactly
   one entry point, and a fix that closes only the one you found leaves the
   others live.
2. **Flag any existing test whose assertions encode the insecure behavior as
   correct.** A test isn't proof of correctness just because it's green — a
   test that asserts "a locked resource returns 'no key found'" instead of
   "access denied" is a bug wearing a passing test as camouflage. Read what
   the test actually asserts, not just whether it passes.
3. **Confirm every new regression test fails without the fix.** Revert the
   fix (or comment it out) and re-run the new test — if it still passes, the
   test isn't testing the vulnerability, and shipping it as "covered" is
   false confidence. Put the fix back before committing.

**Surface immediately, and they stay open until they reach a terminal state
(below):**
- 📝 Medium: bare `except`, no type hints, mutable defaults, `assert` for validation,
  logging sensitive data, unpinned deps, dependencies with a Medium/Low advisory,
  dependencies several majors behind current with no advisory yet
- 💡 Low: missing `encoding=` on `open()`, string paths, missing static analysis in CI

#### Project standards check (`SKILL.md` §10)

Part of every scan. Read the tracker's `Standards:` row, and check the code
against it:

- **Encryption at rest:** the project's security section names what is
  stored and whether each store is encrypted at rest. A missing statement is
  a 📝 Medium finding. Sensitive data (credentials, TOTP secrets, tokens,
  personal data) stored in plaintext with no recorded decision is ⚠️ High.
- **Login projects:** TOTP, 30-day trusted device, and unlock/rescue each
  read *accepted* or *declined* on the row. An item never offered is a
  📝 Medium finding: offer it now. An accepted item is checked like any other
  auth code: TOTP secrets encrypted, trust tokens signed with a hard 30-day
  expiry and revoked on credential change, recovery codes hashed and
  single-use, the admin unlock logged.
- **Docker projects:** Apprise reads offered, *accepted* or *declined*. An
  accepted `APPRISE_URLS` is a secret: never logged, never in the image.

A declined item is not a finding. The user decided on the record.

### Finding lifecycle — nothing releases with an open finding

**Severity decides how urgent the conversation is. It does not decide whether
the finding can be carried.** Critical and High are an immediate hard stop: no
commit, no build, no anything until resolved. Medium and Low do not stop a work
commit — you must be able to save progress — but **no finding of any severity
may be open when the release track runs.** Gate 5 (PR), Gate 6 (merge, tag,
publish) are all blocked while anything is open.

A finding leaves the open state in exactly three ways:

| Terminal state | What it means | Who can do it |
|---|---|---|
| **fixed** | the code changed and the fix was re-verified against the *current* diff | Claude, then shown to the user |
| **waived** | the user explicitly waived *this specific finding*, with a reason | **only the user** |
| **withdrawn** | the finding was wrong; say why it was wrong | Claude, then shown to the user |

**Anything else is open, and open blocks the release.** "It's pre-existing",
"it's not related to this change", "it's only a Medium", "we'll get it next
release" are not terminal states. They are the sentences that carried a real
finding across two releases of this very repo while every gate read ✅.

**"Pre-existing" is a provenance note, not a status.** A finding that predates
this change is still a finding. Record where it came from if it helps; it does
not change what has to happen before the next tag.

**Only the user waives, and only one finding at a time.** Claude never waives
its own finding, and a blanket instruction — "ignore Mediums", "stop flagging
that" — is not a waiver: it is a request to suppress a category, which this
skill does not do. Ask for the specific finding. Record it on the tracker with
the date and the user's reason, on its own line:

```
🔕 waived 2026-09-19 by user: shellcheck unavailable in this container —
   re-check when a linter is present
```

A waiver covers the finding as it stands. If the finding's context changes —
the code it concerns is edited, the severity rises, the dependency it names
gets an advisory — it re-opens and needs a fresh decision.

**The tracker's SECURITY row carries the open count on its first line**, because
that is the line the enforcement checks read (`ENFORCEMENT.md`, A4):

```
🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High
              ✅ fixed 2026-09-19: no dependabot.yml → added (github-actions)
              🔕 waived 2026-09-19 by user: <reason>
```

**A ✅ SECURITY row that does not say `0 open` on its first line is an illegal
state**, and the checks deny the operation rather than trusting the ✅. Do not
resolve that denial by editing the count — resolve the findings.

Security step passes at zero Critical, zero High, **and zero open findings of
any severity** — in the code and in the dependency tree. Both halves are
reported, so a clean scan of hand-written code can never stand in for an
unaudited manifest:

> ✅ **Security scan passed** — 0 open, 0 Critical, 0 High
> Code: 0 Critical, 0 High | Medium: N (all fixed or waived) | Low: N
> Dependencies: `npm audit` clean — 0 Critical, 0 High | Medium: N | Low: N

If the project has no dependency-update automation, this is a finding like any
other — raise it, and it blocks the release until it is fixed or waived. It is
not a suggestion to leave on the table:

> 📝 **Medium — no `.github/dependabot.yml`.** Nothing watches these packages
> between security gates. This is open and blocks the release track. Want me to
> add one (`WORKFLOW_REFERENCE.md`), or do you want to waive it with a reason?

#### Enabling Dependabot alerts — hand the user these steps, not a menu path

Alerts and security updates are **repository settings, not a file**, so Claude
cannot turn them on and adding `dependabot.yml` does not turn them on either.
When the alerts endpoint returns `403`, or no credential in the session can
reach it at all, that is an open finding — and an open finding blocks the
release, so the user needs steps they can actually follow, not "Settings →
Code security". Give them this, filled in with the real owner and repo:

> **Enable Dependabot so the scan can run** — about a minute.
>
> 1. Open `https://github.com/<OWNER>/<REPO>/settings/security_analysis`
>    (or: repo → **Settings** → **Advanced Security**, previously
>    **Code security and analysis**).
> 2. **Dependency graph** — if there is an *Enable* button, press it first.
>    Everything below reads from it. It is already on and not switchable for
>    public repos; private repos must turn it on explicitly.
> 3. **Dependabot alerts** → **Enable**. This is the half that finds CVEs.
> 4. **Dependabot security updates** → **Enable**. This opens a PR that fixes
>    an alert, rather than only telling you about it.
> 5. Check **Security** tab → **Dependabot** — it should list alerts, or say
>    there are none. A message that the feature is disabled means step 3 did
>    not take.
>
> Then tell me and I will re-run the check.

**Three cases that make this fail, and what to say about each:**

- **The toggle is greyed out** — the repo is owned by an organization whose
  settings control it. An org owner enables it at
  `https://github.com/organizations/<ORG>/settings/security_analysis`, which
  can apply to all repositories at once. The user may not be that person; say
  so rather than sending them round the loop again.
- **A private repo with no dependency graph** — step 2 is mandatory there.
  Alerts will silently find nothing until it is on.
- **"We have no dependencies, so this does not matter"** — check before
  agreeing. The dependency graph covers **GitHub Actions workflows**, so a
  repo with no package manifest at all still gets real advisory coverage for
  the actions it pins. A repo with a `.github/workflows/` directory has
  something to watch.

**Verify rather than take "done" for an answer.** Re-run
`GET /repos/{owner}/{repo}/dependabot/alerts`: `200` (even with an empty
array) means alerts are on, `403` means they are not. If no credential in the
session can reach that endpoint, say that plainly — the finding stays open on
the user's word alone, or they waive it. Do not mark it fixed from an
unverified "I turned it on".

#### Step 2 — Quality review

Scan the changed code for every quality pattern in `QUALITY_REFERENCE.md`, plus
`QUALITY_ANDROID.md` if Android matched (loaded above), and the checklist
below:

**Structure issues (flag and fix):**
- Deep nesting (>3 levels) — flatten with early returns
- God functions (>~40 lines or multiple responsibilities) — split
- Circular dependencies — restructure
- Hidden side effects in getters or utility functions — rename or separate
- Copy-pasted logic that should be shared — extract

**Performance issues (flag and fix):**
- N+1 queries — batch with IN/ANY or joins
- Wrong data structures (lists for lookups instead of sets/dicts)
- String concatenation in loops — use join/builders
- Recomputation in loops (regex, config, API calls) — compute once
- Allocations in hot paths — move constants to module level
- Loading everything when a subset is needed — SELECT specific columns, paginate
- Blocking I/O on async event loops — use async alternatives
- Unbounded caches — use lru_cache with maxsize
- Missing database indexes on queried columns
- Event listeners never cleaned up — add teardown

**Container / build issues (flag and fix):**
- Dockerfile hardcodes package names instead of installing from dependency file — switch to `pip install -r requirements.txt` / `npm ci`
- New import added but package missing from dependency file — add it
- Dockerfile and dependency file list different packages — reconcile to one source of truth

Report quality findings separately from security:

> **Quality review — changed code:**
> ⚠️ `app.py:45` — N+1 query inside loop (fetches orders per user)
>    Fix: batch with `WHERE user_id = ANY(%s)`
> ⚠️ `utils.py:120` — function is 80 lines with 5 responsibilities
>    Fix: split into validate_input, transform_data, save_result
> ✅ No deep nesting issues
> ✅ No circular dependencies

Quality issues don't hard-block the gate (they're not security vulnerabilities),
but they must be surfaced and the user must acknowledge them. Fix what's
reasonable within the current scope — flag the rest as known technical debt.

#### Gate 3 combined output

Both steps must complete before the gate passes:

> ✅ **SECURITY & QUALITY GATE PASSED**
> Security: **0 open** | 0 Critical, 0 High | Medium: N | Low: N
> Quality: **0 open** | N structure issues, N performance issues
> Resolved this gate: N fixed, N waived by the user, N withdrawn

Quality findings follow the same lifecycle as security findings — fixed,
waived by the user, or withdrawn. A quality finding left open blocks the
release track too. "Known technical debt" is a description, not a terminal
state; if it is genuinely accepted, it is a waiver and the user records it.

If the user says "skip security" or "we can do security later":

> 🚫 **SECURITY GATE BLOCKED**
> Security scan is mandatory after every build. Running now.

Then run it. Do not ask again.
