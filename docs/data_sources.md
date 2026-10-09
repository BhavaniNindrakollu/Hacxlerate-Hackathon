# Data Sources — What Is Real, What Is Sample, and How It Flows

> Audience: developers, judges, and operators of ImpostorRadar.
> This document is intentionally explicit about what is real and what is simulated.
> **ImpostorRadar does NOT continuously monitor live social networks or app stores today.**

---

## 1. The four kinds of data in the system

| Kind | Where it lives | Created by | Lifecycle |
| :--- | :--- | :--- | :--- |
| **Bundled sample data** | `backend/app/data/social_candidates.json` (40 profiles), `backend/app/data/app_candidates.json` (30 apps), `backend/app/data/common_words.txt` (980 words) | Shipped with the repository | Read-only at runtime. Never modified, deleted, or overwritten by the app. |
| **User-created data** | SQLite: `brands`, `official_assets`; logo files in `backend/uploads/` | Admin/Analyst via the Brand Profile page (`POST /api/brand`), "Load Demo Brand", or logo upload | Survives restarts and detection-history deletion. Replaced only when the user explicitly loads new brand data. |
| **SQLite database** | `backend/impostorradar.db` (location configurable via `DATABASE_URL`) | Backend | All of the above plus users, sessions, scan history. Back it up before schema changes. |
| **Engine-generated data** | SQLite: `detections`, `scan_runs`; takedown packs generated on demand (not stored) | The detection engine on each scan | Added/updated by scans. Deleted **only** by the admin-only "Delete Detection History" action. |

### SQLite tables at a glance

| Table | Holds | Deleted by "Delete Detection History"? |
| :--- | :--- | :---: |
| `brands` | Brand profile (company name, logo path, keywords) | No |
| `official_assets` | Official social handles + app package IDs (the allowlist) | No |
| `detections` | Every scored candidate + evidence + score breakdown | **Yes** |
| `scan_runs` | One row per scan execution (source name/status/message) | **Yes** |
| `users`, `auth_sessions` | Accounts and active login sessions | No |
| `audit_logs` | Security-relevant events (login, logout, role change, deletions…) | No |
| `app_settings` | Toggles such as source-outage simulation | No |

---

## 2. Are any real external APIs connected?

**No.** As shipped:

- There is **no** connection to the X/Twitter API, Meta Graph API, Telegram, YouTube, Google Play, or the Apple App Store.
- There is **no** background scheduler and **no** webhook listener. Scans run **only** when a user presses a scan button (or when the very first startup pre-seeds the demo brand).
- The default connector mode is `CONNECTOR_MODE=sample`, which reads the bundled JSON files described above.

The `CONNECTOR_MODE=live` option exists as a **wiring point**, not a working integration: the live connector classes in `backend/app/connectors/live_connector.py` deliberately raise `NotImplementedError` and immediately fall back to sample data. This lets a future developer implement real `fetch()` methods without changing any other part of the system.

> **Honesty rule:** never describe this app as "continuously monitoring the internet" or "connected to Twitter/Google Play". It scans a bundled dataset, plus whatever a future live connector provides when implemented.

---

## 3. Real vs. local scanning

Everything that happens during a scan is **local computation on this machine**:

1. The connector loads candidate records (from JSON files today).
2. The detection engine normalizes names (NFKC, Cyrillic homoglyphs, leetspeak, spacing) and computes six weighted signals locally using open-source libraries (`rapidfuzz`, `imagehash`, `scikit-learn` TF-IDF).
3. Results are written to the local SQLite database.
4. Takedown packs (PDF/text) are generated locally with `reportlab`.

No candidate data, brand data, or user data leaves the machine. Nothing is uploaded anywhere. This means the app is fully functional **offline**.

---

## 4. How the sample / live connectors work

```
factory.get_social_connector() / get_app_connector()
        │  reads settings.connector_mode
        ├── "live"  → LiveSocialConnector / LiveAppStoreConnector
        │              └─ fetch() → NotImplementedError (today)
        │                 └─ caught → falls back to sample connector,
        │                    returns ConnectorResult(status="unavailable",
        │                    message="source unavailable, showing cached/sample data (…)", items=sample)
        └── anything else (default "sample")
               → SocialSampleConnector / AppStoreSampleConnector
                  └─ fetch() → reads backend/app/data/*.json
                     → ConnectorResult(status="ok", items=[…])
```

The connector contract (`backend/app/connectors/base.py`) is: **`fetch()` never raises** — it returns `status="ok"` with items or `status="unavailable"` with a friendly message (and, where possible, cached/sample items anyway).

Every scan records the connector outcome in the `scan_runs` table (`source_name`, `source_status`, `source_message`), so each detection batch is traceable to its source state.

---

## 5. What happens when a source is unavailable

Design principle: **an outage degrades, it never breaks.**

- The sample connectors catch file/parse errors and return `status="unavailable"` with empty or cached items.
- The live connectors catch any failure (missing keys, network error, rate limit) and fall back to sample data automatically.
- Scans complete successfully either way; the UI keeps working.
- Admins can additionally **simulate** an outage for demonstration: `POST /api/sources/toggle` (admin-only, audit-logged) flips `simulate_*_unavailable` flags stored in `app_settings`. The Sources status endpoint (`GET /api/sources`) then reports `unavailable`, and the UI shows the friendly banner — while scans still complete on cached/sample data.
- The pytest suite includes `test_smoke.py::test_connectors_never_raise` which proves the no-crash contract.

## 6. The friendly "source unavailable" banner

The React frontend renders a `SourceBanner` component on the Social Feeds and App Stores pages whenever the sources endpoint reports degraded state. The banner text is calm and explicit — for example:

> *"Source unavailable, showing cached/sample data"*

It never shows a raw stack trace, never blocks the page, and never prevents viewing existing detections. A "Check Connector Status" action lets the user refresh the status without running a scan.

---

## 7. Extending the datasets

You can grow the demo coverage without touching code:

1. **More social candidates** — append objects to `backend/app/data/social_candidates.json` with fields:
   `platform, handle, name, bio, avatar_url, profile_url, followers_count, is_verified, created_at, links`.
2. **More app listings** — append objects to `backend/app/data/app_candidates.json` with fields:
   `store, package_id, title, developer_name, description, icon_url, rating, downloads_count, app_url`.
3. **Fewer false positives on innocent companies** — add generic words to `common_words.txt` (one per line); they feed the compound-name discount that stops names like "Paytm Valley Farms" being flagged.
4. **Your own brand** — create it through the Brand Profile page (name, keywords, official handles, official package IDs, logo upload). No file editing needed.

Keep JSON valid (UTF-8, list of objects). The connectors validate structure and will report `unavailable` rather than crash if a file is malformed.

---

## 8. Integrating real APIs in the future

The intended extension point is `backend/app/connectors/live_connector.py`. A production integration should address:

- **Authentication** — API keys/OAuth tokens must be read from environment variables (`.env`), never hardcoded or committed. Use dedicated credentials per platform with least privilege.
- **Rate limits & quotas** — respect each platform's published limits; implement token buckets, exponential backoff on HTTP 429/5xx, request caching (ETags / TTL), and store cursors/pagination state so scans resume instead of restarting.
- **Terms of Service & legal** — X/Twitter, Meta, Telegram, Google, and Apple all restrict automated access. Use official APIs (X API v2, Meta Graph API, Google Play Developer API, Telegram Bot API) or licensed brand-protection data providers; scraping may violate ToS.
- **Data protection** — minimize PII collection; store only what is needed for evidence; consider regional regulations (GDPR/DPDP) for the candidates you persist.
- **Operational safety** — keep the graceful-fallback contract: a dead upstream API must still return `ConnectorResult(status="unavailable", message=…)` and never break a scan.
- **Attribution & freshness** — record per-source timestamps so detections can state how old the underlying data is.

Until such connectors are implemented and verified against real endpoints, this project must be described as **sample-data driven**, not live.

---

## 9. Demo data vs. generated detections — separate lifecycles

- **Demo/sample candidates** (JSON files) are never deleted by the application. Loading the demo brand overwrites only the brand profile + official allowlists (with an explicit confirmation dialog), never detection history.
- **Generated detections** (`detections`, `scan_runs`) accumulate as scans run, persist across restarts, and are removed only by the admin-only Delete Detection History action — which backs up first (when requested), operates inside a single transaction, and is audit-logged.
- **User and brand data** (users, brands, official assets, uploaded logos) are untouched by history deletion by design, with a post-deletion integrity check that verifies brand/asset counts are unchanged.

## 10. Startup behavior — no silent data loss

On every backend start the app opens the existing database and **never resets it**. The only automatic seed is a one-time convenience: *if and only if* the `brands` table is completely empty (first launch), it loads the Paytm demo brand and runs a first scan. Once any brand exists, startup touches no data.
