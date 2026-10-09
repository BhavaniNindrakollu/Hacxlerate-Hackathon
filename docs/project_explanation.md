# ImpostorRadar — Complete Project Explanation (Beginner Friendly)

> Read this if you are new to the project. Every section describes **what actually exists in the code today**.
> No feature is described that has not been implemented and verified.

---

## 1. What is ImpostorRadar?

ImpostorRadar is a **Digital Risk Protection (DRP)** prototype with one narrow focus: finding **fake brand accounts on social media** and **fake apps in app stores**.

Companies like Paytm, PhonePe, or a local bank are constantly copied: scammers create `@paytm_official_care` on Twitter, or publish an app with a nearly identical logo and a different developer name. ImpostorRadar demonstrates how such impostors can be **detected, scored, explained, and acted on** — ending with a ready-to-send takedown notice (text + PDF) that a brand-protection team could file with the platform.

## 2. The problem it solves

- Brand support handles impersonate official help desks to phish OTPs and wallets.
- App-store clones copy a logo and name to steal installs and data.
- Manual monitoring does not scale — and both false negatives (missed clones) and false positives (flagging innocent businesses) are costly.

ImpostorRadar approaches this with **explainable scoring**: every candidate gets a 0–100 risk score, a severity verdict, and a list of human-readable evidence reasons. Nothing is a black box.

## 3. How a scan works, end to end

1. **Brand profile** — a user defines the company name, keywords, official social handles, and official app package IDs (the *allowlist*).
2. **Ingestion** — a connector collects candidate profiles/apps. Today this reads bundled sample JSON files; live-API stubs exist but are not wired to real service yet.
3. **Normalization** — names are normalized (Unicode NFKC, Cyrillic homoglyphs, leetspeak, spacing tricks) so `Pаytm` (Cyrillic `а`) and `Paytm` can be compared fairly.
4. **Official-asset exclusion** — candidates that match the official handle/package allowlist are marked official **before scoring** and can never be flagged. (This is the zero-false-positive invariant.)
5. **Scoring** — up to six weighted signals are computed locally: name similarity (35), look-alike technique (15), logo perceptual hash (20), bio/description similarity (10), publisher/authorization mismatch (10), scam/phishing bait (10).
6. **Verdict** — score bands: **High ≥ 75**, **Medium 50–74**, **Low 30–49**, **Safe < 30**.
7. **Storage** — the scan run and every detection (with its evidence + score breakdown) are saved to SQLite.
8. **Action** — the analyst opens a detection dossier and generates a **takedown pack**: platform-specific notice text and a PDF dossier.

## 4. Technology stack

| Layer | Technology |
| :--- | :--- |
| Backend | Python 3.11+, FastAPI, SQLAlchemy ORM, Pydantic v2 |
| Database | SQLite (file-based; path configurable via `DATABASE_URL`) |
| Detection engine | rapidfuzz (name similarity), imagehash (perceptual hashing), scikit-learn TF-IDF (text similarity), Pillow |
| Auth | bcrypt password hashing (cost 12), opaque server-side sessions, httpOnly cookies |
| Reports | ReportLab (PDF takedown dossiers) |
| Frontend | React 18, Vite 6, Tailwind CSS 3.4, React Router 6, Recharts, lucide-react |
| Tests | pytest (TestClient + per-test isolated database) |

## 5. Folder structure (current)

```
Imposter Rader/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, lifespan (init DB, bootstrap admin, first-run demo seed), SPA hosting
│   │   ├── config.py          # Settings (env-driven): DB URL, CORS, session hours, signup policy, paths
│   │   ├── db.py              # Engine/session factory, init_db, initial-admin bootstrap
│   │   ├── models.py          # users, auth_sessions, audit_logs, brands, official_assets, scan_runs, detections, app_settings
│   │   ├── schemas.py         # Pydantic request/response models + validators
│   │   ├── security.py        # bcrypt hashing, session cookies, CSRF check, role guards, audit writer
│   │   ├── connectors/        # base, factory, social_sample, appstore_sample, live_connector (fallback stubs)
│   │   ├── data/              # social_candidates.json (40), app_candidates.json (30), common_words.txt (980)
│   │   ├── routers/           # auth, users, audit, brand, social, apps, detections, lookalike, takedown, dashboard, sources, health
│   │   └── services/          # normalize, scoring, imagesim, textsim, lookalike, takedown engine
│   ├── tests/                 # conftest.py + test_auth, test_api, test_detection, test_retention, test_smoke
│   ├── uploads/               # uploaded brand logos + candidate images (served auth-only via /uploads)
│   └── backups/               # manual/pre-deletion DB backups + JSON detection exports
├── frontend/
│   └── src/
│       ├── api/client.js      # fetch wrapper: credentials, CSRF header, 401 → session-expired event
│       ├── auth/AuthContext.jsx  # session state, login/logout/signup, `can()` permission helper
│       ├── components/        # ThreatCard, SeverityBadge, SourceBanner, ConfirmDialog, AccessDenied, UserMenu
│       └── pages/             # Login, Signup, Dashboard, BrandProfile, SocialMonitoring, AppStoreMonitoring,
│                              # LookalikeLab, DetectionDetail, Settings, Users
├── docs/                      # architecture.md, data_sources.md, project_explanation.md (this file), pitch_and_demo.md
├── .env.example               # documented configuration template (placeholders only, no secrets)
├── .gitignore                 # excludes .env, local DBs, backups, uploaded private files
└── render.yaml                # single-service deployment spec with persistent-disk guidance
```

## 6. Architecture diagram

```mermaid
flowchart TB
    subgraph Browser["Browser (React SPA)"]
        UI[Pages: Dashboard, Brand, Social, Apps, Lab, Detection Detail, Settings, Users]
        AC[AuthContext + client.js<br/>credentials: include, CSRF header]
    end

    subgraph FastAPI["FastAPI (single service)"]
        MW[CORS allowlist + cookie session]
        SEC[security.py<br/>session validation · CSRF double-submit · role guards · audit]
        ROUTERS[/api routers:<br/>auth · users · audit · brand · social · apps ·<br/>detections · lookalike · takedown · dashboard · sources/]
        STATIC[Static hosting:<br/>frontend/dist SPA + /uploads (auth-only)]
    end

    subgraph Engine["Detection Engine (local)"]
        CONN[Connectors<br/>sample JSON now / live fallback stubs]
        NORM[Normalizer<br/>NFKC · homoglyphs · leetspeak · spacing]
        EXCL{Official-asset<br/>exclusion}
        SCORE[6 weighted signals<br/>→ score + evidence + verdict]
    end

    DB[(SQLite<br/>users · sessions · audit · brands · assets ·<br/>scan_runs · detections · settings)]

    UI --> AC --> MW --> SEC --> ROUTERS
    ROUTERS --> CONN --> NORM --> EXCL
    EXCL -- allowlisted --> SAFE[Official / Safe, score 0]
    EXCL -- candidate --> SCORE
    SCORE --> DB
    SAFE --> DB
    ROUTERS --> DB
    SEC --> STATIC
    SCORE -->|takedown pack| ROUTERS
```

## 7. Authentication — how login actually works

- **Signup** (`POST /api/auth/signup`): validates name/email/password server-side. Password policy: at least 10 characters, not all digits, not all letters, different from the email. Passwords are hashed with **bcrypt (cost 12)** and never stored or logged in plaintext. The **first account ever created becomes the Administrator**; every later self-registration gets the **Analyst** role (self-registration can never grant administrator).
- **Login** (`POST /api/auth/login`): verifies the bcrypt hash; wrong email or password returns the same generic message ("Invalid email or password") so attackers cannot enumerate accounts; failures are written to the audit log.
- **Sessions**: the server stores session rows (`auth_sessions`) with an expiry (default **12 hours**, `SESSION_HOURS` env). The browser receives two cookies: `ir_session` (httpOnly — JavaScript can never read it, so it cannot be stolen by XSS) and `ir_csrf` (readable, used for CSRF protection). No tokens are kept in `localStorage`.
- **Every request** re-validates the session server-side. Expired or missing sessions get `401` with a clear message; the frontend shows the message and redirects to the login page.
- **Logout** (`POST /api/auth/logout`): deletes the session row server-side and clears both cookies — a copied cookie is dead immediately.
- **CSRF protection**: because auth rides on cookies, every non-GET request must echo the `ir_csrf` cookie value in the `X-CSRF-Token` header; the server rejects mismatches with `403`.
- **Protected routing**: the React app wraps all pages in an auth guard — unauthenticated visitors are redirected to `/login`, and a 401 anywhere triggers a global "session expired" redirect.
- **Admin bootstrap**: optionally set `INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_PASSWORD` env vars to create the first admin on an empty database. Never hardcode credentials; leave blank to let the first registered user become admin in development.

## 8. Roles and permissions

Three roles, enforced **on the backend** (the UI merely hides what you cannot do — hiding buttons is never the security boundary).

| Capability | Viewer | Analyst | Administrator |
| :--- | :---: | :---: | :---: |
| View dashboard, brand, detections, dossiers | ✅ | ✅ | ✅ |
| Run scans (social / apps / full) | — | ✅ | ✅ |
| Edit brand profile, upload logo, load demo data | — | ✅ | ✅ |
| Generate/copy/download takedown packs | — | ✅ | ✅ |
| Delete a single detection | — | ✅ | ✅ |
| Delete detection **history** (bulk) | — | — | ✅ |
| Manage data sources / simulate outage | — | — | ✅ |
| Manage users & roles | — | — | ✅ |
| View security audit log | — | — | ✅ |

- Role changes and admin actions are written to the **audit log** (`audit_logs`): signup, login, login_failed, logout, user_role_update, delete_detection, delete_detection_history, toggle_sources, brand changes, and more.
- The last active administrator cannot be demoted or disabled — the system refuses, so you can never lock yourself out.
- This deployment uses a **shared single-brand workspace**: all authenticated users see the same brand's data (documented simplification for the single-brand hackathon demo). Accounts, credentials, and sessions are still strictly personal.

## 9. Data storage & retention

- Everything durable lives in **SQLite** (`backend/impostorradar.db` by default; change `DATABASE_URL`). Tables: `users`, `auth_sessions`, `audit_logs`, `brands`, `official_assets`, `scan_runs`, `detections`, `app_settings`.
- **Scans add/update** rows. **Restart, logout, page changes, and brand switching never delete data.** Restarting the backend simply opens the existing database.
- **Startup never resets the database.** The only automatic write is a one-time demo seed that runs **only when the `brands` table is completely empty** (first launch).
- **Deleting detection history** is an Administrator-only action that requires typing the exact confirmation phrase `DELETE_DETECTION_HISTORY` in a dialog that spells out what will and will not be deleted. It can create a **backup first** (a JSON export of every detection + a full copy of the SQLite file into `backend/backups/`), deletes `detections` and `scan_runs` **inside one transaction** (a failure rolls everything back — no partial state), then verifies brand/asset counts are unchanged, and finally writes an audit entry with the counts.
- **Brand profile, official assets, uploaded logos, user accounts, and audit logs are never touched** by history deletion. Loading the demo brand (with its own overwrite confirmation) replaces only the brand + allowlists, never the detection history.

## 10. Data sources — what is real vs simulated

All scanning is **local computation on bundled sample data**. There is **no live connection** to Twitter/X, Meta, Telegram, YouTube, Google Play, or Apple — and the app never claims continuous real-time monitoring. If a source is unavailable (or an admin simulates an outage from Settings), scans still complete using cached/sample data, and the UI shows a friendly source-unavailable banner.

Full details: **`docs/data_sources.md`**.

## 11. Security protections present today

- bcrypt password hashing; no plaintext passwords anywhere (DB, logs, or API responses).
- httpOnly + SameSite=Lax session cookies; short session lifetime; server-side session invalidation on logout.
- CSRF double-submit token required on every state-changing request.
- CORS restricted to an explicit origin allowlist configured via env (wildcard `*` is stripped; credentials are only allowed to those origins).
- **Every** `/api` endpoint requires authentication; each action additionally requires its role. Verified by tests that a viewer hitting scan/delete endpoints gets `403` even when bypassing the UI.
- No IDOR: detection/detail endpoints are scoped and validated; user management endpoints are admin-only; uploaded files are served only to authenticated users with a path-traversal guard.
- Input validation on both ends (Pydantic schemas server-side, form checks client-side): duplicate emails, invalid credentials, weak passwords, bad confirmations, malformed IDs.
- Login failures and all admin actions are audit-logged; generic error messages prevent account enumeration.
- Uploaded logos limited by size (`MAX_LOGO_BYTES`, default 2 MB) and validated as images.
- Secrets are environment-driven; `.env` is git-ignored and `.env.example` contains placeholders only.

## 12. Honest limitations (what this project is NOT)

- **Not a live monitoring system** — no real social/app-store APIs are connected; sample data only.
- **No background scheduler** — scans run when a user presses a button, not continuously.
- **SQLite on ephemeral hosting** — on platforms without a persistent disk, the DB and uploads are lost on redeploy; `render.yaml` documents the persistent-disk configuration.
- **Single shared workspace** — no per-team multi-tenancy; documented simplification.
- **Demo scale** — 40 social candidates + 30 app candidates + your own brand data.
- Takedown packs are generated drafts; sending them is the operator's responsibility.

---

## Quick start (Windows PowerShell)

```powershell
# 1. Clone / open the project, then set up the backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..

# 2. (Optional) create your env file — defaults work for local dev
Copy-Item .env.example .env

# 3. Build the frontend
cd frontend
npm install
npm run build
cd ..

# 4. Run the single production service from the project root
backend\.venv\Scripts\uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` → you land on the login page.
First visit? Click **Create one** — the first account becomes the Administrator. The first startup pre-seeds the demo brand "Paytm" and one scan, so the dashboard already shows real detection data.

For frontend development with hot reload run `npm run dev` in `frontend/` instead (it proxies `/api` and `/uploads` to `127.0.0.1:8000`).
