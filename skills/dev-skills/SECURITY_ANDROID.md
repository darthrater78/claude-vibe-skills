# Security Pattern Reference — Android

Loaded alongside `SECURITY_REFERENCE.md` during Gate 3 and audit mode when
project environment detection (`WORKFLOW_REFERENCE.md`, Step 1) matches
Android. Contains Android-only security patterns — cross-platform and
language-general patterns are in `SECURITY_REFERENCE.md`.

---

## Rules — flag on sight during any coding session

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
