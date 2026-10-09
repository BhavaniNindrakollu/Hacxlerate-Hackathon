# ImpostorRadar — 6-Slide Pitch Outline & 2-Minute Demo Script

*Built for the Kampus.VC Hackathon Challenge: Digital Risk Protection for Social & App Monitoring*

> **Demo credentials (local demo only — never reuse for any deployed instance):**
> - Administrator: `admin@kampus.vc` / `ImpostorRadar#2026`
> - Viewer: `priya@kampus.vc` / `PriyaDemo#2026`

---

## Part 1: 6-Slide Presentation Outline

### Slide 1: The Problem — The Digital Blindspot
- **Headline:** Brands are under assault where customers look first: Social & App Stores.
- **The Reality:** Threat actors exploit character swaps (`Paytn`), Cyrillic homoglyphs (`pаytm`), and fake customer care portals (`paytm_care_india`) to defraud consumers before brands even know they exist.
- **The Core Flaw in Existing DRP Tools:**
  1. Over-flagging innocent companies (e.g. *Paytm Valley Farms* flagged as critical).
  2. Flagging the brand's own official assets.
  3. Black-box risk scores without explainable legal evidence.
  4. Manual, slow takedown process taking hours per incident.

---

### Slide 2: The Approach — Forensic, Explainable, Automated
- **Headline:** Automated intelligence tailored strictly for Social & App ecosystem risk.
- **Zero False-Positive Invariant:** Strict allowlist filtering protects official assets *before* scoring.
- **Compound Word Intelligence:** Lexical disambiguation protects legitimate businesses (*Valley Farms*, *News Daily*) while catching deceptive bait keywords (*support*, *rewards*, *login*, *urgent KYC*).
- **Multi-Modal Detection Matrix:** Evaluates Name (35%) + Look-alike Technique (15%) + Logo Perceptual Hash (20%) + Bio TF-IDF (10%) + Publisher Mismatch (10%) + Scam Signals (10%).

---

### Slide 3: Architecture — Robust, Fast, Secure, Single Deployable Service
- **Headline:** Modular, fault-tolerant Python & React architecture with account security built in.
- **Architecture Flow:**
  `Ingestion Connectors -> Normalizer (NFKC + Homoglyphs + Leetspeak) -> Official Asset Exclusion -> Multi-Signal Scoring Engine -> SQLite / SQLAlchemy -> FastAPI API (session auth + roles + CSRF) -> React UI`
- **Access Control:** Every API endpoint is authenticated; destructive actions (delete history, source toggles, user management) are administrator-only — enforced on the backend, not just hidden in the UI.
- **Connector Resilience:** Graceful fallbacks for social and app store feeds; if an external API experiences downtime or rate limits, the system seamlessly displays cached feeds with clear user messaging—scans *never* crash.
- **Production Packaging:** Single service where FastAPI directly serves the compiled Vite React frontend on any cloud host.

---

### Slide 4: Unique Differentiating Features
- **1. Explainable Threat Card:**
  - Every threat shows a side-by-side logo comparison, exact pHash distance, and a 6-signal breakdown bar.
- **2. Look-alike Lab:**
  - Real-time permutation playground: type any brand and inspect swaps, homoglyphs, spacing, and added words cross-referenced against live feeds.
- **3. One-Click Takedown Pack:**
  - Generates platform-tailored legal notices (Twitter, Meta, Google Play, Apple) and an executive ReportLab PDF dossier in 1 click.
- **4. Trust Radar Dashboard:**
  - Real-time **Brand Exposure Score** (0–100 risk index) with Recharts analytics.
- **5. Secure Multi-User Workspace:**
  - Signup/login with bcrypt hashing, httpOnly cookie sessions with CSRF protection, three roles (Administrator / Analyst / Viewer) enforced across UI *and* API, and an audit log of every sensitive action.

---

### Slide 5: The Demo Flow (10-Second Judge Experience)
- **Step 1:** Log in as Administrator (`admin@kampus.vc`) — the app starts locked; protected routes require a session.
- **Step 2:** Click **"Load Demo Brand"** on the Brand Profile page (pre-configures *Paytm*, official logos, handles, and official app identifiers — existing data is preserved).
- **Step 3:** Inspect **Trust Radar Dashboard** (Exposure Score 100/100 CRITICAL, 110 monitored candidates, 21 high-severity threats, distribution charts).
- **Step 4:** Examine **Social Monitoring Feed** (show *Paytm Official Support Desk* @paytm_official_care flagged High at 87.8, while official `@paytm` is marked Safe/Excluded and *Paytm Valley Farms* is marked Safe).
- **Step 5:** Inspect **App Store Monitoring** (clone app *Paytn Fast Wallet & Cashback* with publisher mismatch and logo clone detected).
- **Step 6:** Generate **One-Click Takedown Pack** (download official PDF evidence dossier and copy platform notice).
- **Step 7:** Open **Look-alike Lab** (live permutations cross-matched with active feeds).
- **Step 8 (optional):** Log in as Viewer (`priya@kampus.vc`) to show role-restricted navigation and backend 403s; Settings outage toggle is Administrator-only.

---

### Slide 6: Results & Hackathon Deliverables
- **100% Test Suite Pass Rate:** 57/57 pytest tests covering authentication, role enforcement, safe data retention, official-asset exclusion, and lookalike detection.
- **Production Ready:** Single unified container / web service deployable via `render.yaml`.
- **Extensible:** Plug-and-play connector interface ready for production Twitter / Google Play API keys.

---

## Part 2: 2-Minute Demo Video Script

*Target duration: 120 seconds | Delivery: confident, energetic, concise*

| Time | Visual on Screen | Spoken Script |
| :---: | :--- | :--- |
| **0:00 - 0:15** | **Login page** → sign in as `admin@kampus.vc` → **Home Dashboard** appears. | "Hello judges! This is **ImpostorRadar**, an explainable Digital Risk Protection platform for Social Media and App Stores. First, notice the app ships secure by default: every route is behind authentication, passwords are bcrypt-hashed, and the first registered account becomes the system administrator. Signing in, our **Trust Radar Dashboard** shows our **Brand Exposure Score**—an aggregated 0-100 risk index over all live candidates." |
| **0:15 - 0:35** | Navigate to **Brand Profile**, click **"Load Demo Brand"**. | "Let's head to the **Brand Profile**. With one click, judges can click **'Load Demo Brand'** to configure our demo brand, Paytm. Notice how official Twitter, Instagram, and YouTube handles, along with official Google Play and App Store package IDs, are registered. Our engine enforces a strict rule: official assets are checked against this allowlist and excluded *before* scoring, guaranteeing zero false positives—and loading the demo never wipes existing brand data or history." |
| **0:35 - 1:00** | Navigate to **Social Feeds**, scroll through Threat Cards. | "In **Social Monitoring**, our multi-signal engine flags `@paytm_official_care` — *Paytm Official Support Desk* — as **High Severity (87.8/100)**. Each **Explainable Threat Card** shows a side-by-side logo comparison with perceptual-hash matching, the added-word technique, and human-readable forensic reasons. Most importantly, `@paytm` itself is excluded and safe. And look at *Paytm Valley Farms* — our compound-word classifier knows it's an innocent farm business and scores it Safe, not critical!" |
| **1:00 - 1:20** | Open **Detection Detail** for `@paytm_official_care`, click **Download Dossier (PDF)** and **Copy Notice**. | "When security teams need to act, they click into the incident for our **One-Click Takedown Pack**. ImpostorRadar instantly generates a platform-tailored legal takedown notice ready to submit to the X Trust & Safety team, plus an executive, multi-page ReportLab PDF evidence dossier with forensic tables, timestamps, and signature blocks." |
| **1:20 - 1:40** | Navigate to **Look-alike Lab**, type `Paytm` and view generated variants. | "Next is our unique **Look-alike Lab**. Type any brand name, and our engine generates dozens of permutations—character swaps, Cyrillic homoglyphs, leetspeak, spacing, and bait keywords. Even better, it cross-references our active monitored feeds in real-time, highlighting which variants are already active in the wild." |
| **1:40 - 2:00** | Navigate to **Settings** (admin-only), toggle **Simulate Outage**, show resilience banner on feed, conclude. | "Finally, in **Settings**—visible only to administrators—we can simulate an upstream data outage. Notice how our feeds gracefully display a friendly cached-data banner without ever crashing. Hiding buttons isn't security, though: every admin action is enforced by the backend with role checks and CSRF protection. ImpostorRadar runs as a single deployable service with 57/57 passing automated tests. Thank you!" |
