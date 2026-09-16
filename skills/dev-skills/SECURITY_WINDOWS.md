# Security Pattern Reference — Windows

Loaded alongside `SECURITY_REFERENCE.md` during Gate 3 and audit mode when
project environment detection (`WORKFLOW_REFERENCE.md`, Step 1) matches
Windows. Contains Windows-only security patterns — cross-platform and
language-general patterns are in `SECURITY_REFERENCE.md`.

---

## Rules — flag on sight during any coding session

**Windows-specific:**
- Elevation: default the app manifest to `asInvoker` — `requireAdministrator` hands the
  admin token to *every* process the app launches, so a "just open the docs" call opens an
  elevated browser; re-launch user-facing targets via `explorer.exe` to drop back to the
  shell's integrity level, and elevate a separate helper (`Verb = "runas"`) for the one
  operation that needs it
- PowerShell injection: no `Invoke-Expression`/`iex`/`& $userInput` — use parameter arrays
- UNC path injection: reject `\\` and `//` prefixed paths from user input (NTLM hash leak)
- DLL hijacking: use absolute paths for `LoadLibrary`/`ctypes.CDLL`, call `SetDllDirectory("")`
- Credential storage: use DPAPI/Credential Manager/`keyring` — never plaintext in registry or config
- Registry: use `HKCU` not `HKLM` unless needed, set restrictive ACLs, validate data read back
- Services: never run as `SYSTEM` — use dedicated service accounts, gMSA where available;
  always quote `binPath=` (an unquoted `C:\Program Files\...` path is a privesc)
- Code signing: sign with Authenticode, never bypass execution policy
- Path hazards: reject reserved names (`CON`, `PRN`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`),
  handle MAX_PATH, account for case insensitivity

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

## Windows — UAC and process elevation

```xml
<!-- app.manifest — bad: every process this app launches inherits the admin token -->
<requestedExecutionLevel level="requireAdministrator" uiAccess="false" />

<!-- good: run unelevated, elevate one helper for the operation that actually needs it -->
<requestedExecutionLevel level="asInvoker" uiAccess="false" />
```

```csharp
// bad — from a requireAdministrator process this opens the browser AS ADMIN
Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });

// good — explorer.exe re-launches the target at the shell's (unelevated) integrity level.
// Validate the scheme first: explorer.exe will just as happily run a file path or an .exe.
if (!Uri.TryCreate(url, UriKind.Absolute, out var uri) ||
    (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps))
    throw new ArgumentException("http/https only");
Process.Start(new ProcessStartInfo("explorer.exe", $"\"{uri.AbsoluteUri}\"") { UseShellExecute = false });

// good — elevate only the privileged step, as its own process, from an asInvoker app
Process.Start(new ProcessStartInfo("helper.exe", args) { UseShellExecute = true, Verb = "runas" });
```

---

## Windows — DLL search-order hijacking

```python
# bad — searches the current directory and PATH; a planted helper.dll wins
import ctypes
ctypes.CDLL("helper.dll")

# good — drop the cwd from the search order, then load by absolute path
ctypes.windll.kernel32.SetDllDirectoryW("")
ctypes.CDLL(r"C:\Program Files\MyApp\helper.dll")
```

```csharp
// good — restrict P/Invoke resolution to System32 and the app's own directory
[assembly: DefaultDllImportSearchPaths(
    DllImportSearchPath.System32 | DllImportSearchPath.AssemblyDirectory)]
```

---

## Windows — registry security

```csharp
// bad — machine-wide key with a default ACL, and the value is trusted on read:
// anyone who can write it gets code execution inside this (possibly elevated) process
Registry.LocalMachine.CreateSubKey(@"SOFTWARE\MyApp").SetValue("HelperPath", path);
Process.Start((string)Registry.LocalMachine.OpenSubKey(@"SOFTWARE\MyApp").GetValue("HelperPath"));

// good — per-user hive, and validate anything read back before acting on it
using var key = Registry.CurrentUser.CreateSubKey(@"SOFTWARE\MyApp");
key.SetValue("HelperPath", path);
var helper = key.GetValue("HelperPath") as string;
if (helper is null ||
    !helper.StartsWith(AppContext.BaseDirectory, StringComparison.OrdinalIgnoreCase))
    throw new SecurityException("helper path outside the install directory");
```

---

## Windows — service configuration

```bat
:: bad — LocalSystem, and an unquoted path: C:\Program.exe runs instead if anyone can drop it there
sc.exe create MyService binPath= C:\Program Files\MyApp\svc.exe obj= LocalSystem start= auto

:: good — least-privileged virtual account, quoted binary path
sc.exe create MyService binPath= "\"C:\Program Files\MyApp\svc.exe\"" obj= "NT SERVICE\MyService" start= auto
sc.exe sdshow MyService   :: confirm no unprivileged principal can reconfigure the service
```

---

## Windows — code signing and execution policy

```powershell
# bad — turns the protection off instead of signing the thing
Set-ExecutionPolicy Bypass -Scope LocalMachine
powershell.exe -ExecutionPolicy Bypass -File .\deploy.ps1

# good — sign with a timestamp, so signatures outlive the signing certificate
Set-AuthenticodeSignature -FilePath .\deploy.ps1 -Certificate $cert `
    -TimestampServer http://timestamp.digicert.com

# good — verify what you are about to ship
signtool verify /pa /v .\MyApp.exe
(Get-AuthenticodeSignature .\MyApp.exe).Status   # must be 'Valid', not 'NotSigned'/'UnknownError'
```

---

## Windows — reserved names and path limits

```python
# bad — CON, NUL, COM1..COM9 are devices with or without an extension, and Win32
# strips trailing dots and spaces, so "secret.txt. " resolves onto "secret.txt"
Path(upload_dir, user_filename).write_bytes(data)

# good
RESERVED = {"CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
name = PurePath(user_filename).name
if (PurePath(name).stem.upper() in RESERVED
        or name != name.rstrip(" .")
        or set(name) & set(r'<>:"/\|?*')):
    raise ValueError("reserved or malformed Windows filename")
# paths compare case-insensitively — normalize before matching against an allowlist
```
