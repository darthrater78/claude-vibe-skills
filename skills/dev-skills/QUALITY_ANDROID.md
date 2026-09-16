# Code Quality Pattern Reference — Android

Loaded alongside `QUALITY_REFERENCE.md` during Gate 3 and quality review when
project environment detection (`WORKFLOW_REFERENCE.md`, Step 1) matches
Android. Contains Android-only structure and performance patterns —
cross-platform patterns are in `QUALITY_REFERENCE.md`.

---

## Rules — apply as code is written

**Android-specific:**
- **Never block the main thread.** Network calls, database queries, file I/O, and
  heavy computation on the main (UI) thread cause ANRs. Use coroutines, `WorkManager`,
  or background threads.
- **Leak-proof lifecycles.** Never hold Activity/Fragment references in long-lived
  objects (singletons, static fields, background threads). Use `WeakReference` or
  lifecycle-aware components (`ViewModel`, `LiveData`).
- **RecyclerView over ListView.** ListView creates views for every item; RecyclerView
  recycles them. Use `DiffUtil` for efficient updates instead of `notifyDataSetChanged()`.
- **Avoid overdraw.** Remove unnecessary backgrounds, flatten view hierarchies, use
  `ConstraintLayout` over nested `LinearLayout`s.

---

## Android — main thread blocking

```kotlin
// bad — network call on the main thread → ANR
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val response = URL("https://api.example.com/data").readText()  // blocks UI
        textView.text = response
    }
}

// good — coroutine on IO dispatcher
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        lifecycleScope.launch {
            val response = withContext(Dispatchers.IO) {
                URL("https://api.example.com/data").readText()
            }
            textView.text = response
        }
    }
}
```

---

## Android — Activity/Fragment lifecycle leaks

```kotlin
// bad — singleton holds Activity reference → leaked after rotation/finish
object DataCache {
    var callback: MainActivity? = null  // Activity never GC'd
}

// bad — static field holds Fragment context
companion object {
    var context: Context? = null  // leaks the Activity
}

// good — ViewModel survives configuration changes, no Activity reference
class DataViewModel : ViewModel() {
    val data = MutableLiveData<String>()

    fun loadData() {
        viewModelScope.launch {
            data.value = repository.fetch()
        }
    }
}

// good — if a reference is needed, use WeakReference
class MyTask(activity: MainActivity) {
    private val activityRef = WeakReference(activity)

    fun onComplete(result: String) {
        activityRef.get()?.updateUI(result)
    }
}
```
