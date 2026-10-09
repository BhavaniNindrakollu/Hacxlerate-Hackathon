# ImpostorRadar — System Architecture & Technical Specifications

**ImpostorRadar** is an automated Digital Risk Protection (DRP) platform specifically engineered for **Social Media and App Store Impersonation Monitoring**. Designed for high accuracy, explainable scoring, and rapid incident takedown enforcement.

---

## 1. High-Level Architecture

The platform operates as a unified single-service application where FastAPI handles REST operations, detection pipelines, forensic PDF generation, and directly serves the compiled React production frontend.

```mermaid
flowchart TD
    subgraph Data Sources & Ingestion
        S1[Realistic Social Seed JSON<br/>40 candidates] --> C1[Social Connector]
        S2[Realistic App Store Seed JSON<br/>30 candidates] --> C2[App Store Connector]
        S3[Live API Interface<br/>Stub with Try/Except Fallback] --> C1
        S3 --> C2
    end

    subgraph Normalization Pipeline
        C1 --> N1[Unicode NFKC & Lowercase]
        C2 --> N1
        N1 --> N2[Homoglyph Map: Cyrillic/Confusables]
        N2 --> N3[Leetspeak Normalizer: 0->o, 1->l, rn->m]
        N3 --> N4[Noise & Punctuation Stripper]
    end

    subgraph Brand Profile & Official Allowlist
        BP[Brand Registry Profile<br/>Name, Logo, Keywords] --> EX{Official Asset<br/>Exclusion Filter}
        O1[Official Social Handles] --> EX
        O2[Official App Package IDs & Devs] --> EX
    end

    subgraph Forensic Detection Engine
        N4 --> EX
        EX -- Matches Allowlist --> SAFE[Mark as Official Asset<br/>Score = 0.0 • Verdict: Safe]
        EX -- Non-Official Candidate --> DET[Multi-Signal Scoring Engine]

        DET --> SIG1[Name Lexical Similarity<br/>Rapidfuzz Damerau-Levenshtein • W=35]
        DET --> SIG2[Look-alike Technique Detection<br/>Swaps, Homoglyphs, Spacing, Added Words • W=15]
        DET --> SIG3[Logo Perceptual Hash<br/>64-bit pHash Hamming Distance • W=20]
        DET --> SIG4[Text Cosine Similarity<br/>TF-IDF Vectorizer vs Brand Keywords • W=10]
        DET --> SIG5[Publisher Mismatch<br/>Unverified Dev / Support Claim • W=10]
        DET --> SIG6[Scam Indicators<br/>Phishing triggers, low followers, age • W=10]
    end

    subgraph Persistence & API Layer
        SIG1 & SIG2 & SIG3 & SIG4 & SIG5 & SIG6 --> AGG[Score Aggregator 0-100<br/>High >=75 | Med 50-74 | Low 30-49]
        SAFE --> AGG
        AGG --> DB[(SQLite Database<br/>SQLAlchemy ORM)]
        DB --> API[FastAPI Endpoints<br/>CORS • Lifespan • Background Auto-seed]
    end

    subgraph Presentation & Enforcement
        API --> UI[React 18 + Vite + Tailwind UI]
        UI --> TR[Trust Radar Dashboard<br/>Brand Exposure Score & Recharts]
        UI --> TC[Explainable Threat Cards<br/>Side-by-side Logo & Evidence]
        UI --> LAB[Look-alike Lab<br/>Interactive Typo Permutations]
        UI --> TKD[One-Click Takedown Pack<br/>ReportLab PDF Dossier & Legal Text]
    end
```

---

## 2. Multi-Signal Detection & Scoring Matrix

Threat scores range from **0 to 100**, calculated as a weighted sum of independent forensic signals:

$$\text{Threat Score} = \sum_{i=1}^{6} w_i \cdot s_i$$

| Signal Component | Weight ($w_i$) | Analytical Methodology | Forensic Evidence Output |
| :--- | :---: | :--- | :--- |
| **Name Similarity** | **35** | RapidFuzz token and lexical ratio between normalized brand name and candidate identifier. Special generic compounds (e.g. *Paytm Valley Farms*) are discounted to avoid over-flagging normal businesses. | `"High name lexical similarity (80%) to brand 'Paytm' on candidate 'Paytn Official Care'"` |
| **Look-alike Technique** | **15** | Categorization into character swaps, Cyrillic homoglyphs (`а` for `a`), leetspeak (`0` for `o`, `rn` for `m`), spacing insertions (`Pay tm`), punctuation delimiters (`Pay.tm`), and added bait words (`official`, `care`, `rewards`). | `"Look-alike technique [swap]: Character transposition / swap identified ('Paytm' vs 'Paytn Official Care')"` |
| **Logo Perceptual Hash** | **20** | 64-bit perceptual hash (`imagehash.phash`) on normalized RGB images. Hamming distance $\le 2$ indicates near-identical clone; distance $\le 12$ indicates deceptive imitation. | `"Perceptual logo hash distance 0/64: Near-identical clone of official logo"` |
| **Bio / Description TF-IDF** | **10** | Scikit-learn TF-IDF Vectorizer calculating cosine similarity between brand core keywords and candidate bio/description. | `"Bio / description contains significant brand-relevant terminology (TF-IDF similarity: 0.65)"` |
| **Publisher / Dev Mismatch** | **10** | For apps: flags publishers not registered in the brand's authorized developer allowlist. For social: flags unverified accounts claiming official authority. | `"Publisher mismatch: Developed by unverified entity 'FastTech Solutions' instead of official publisher"` |
| **Scam Indicators** | **10** | Pattern matching for phishing triggers (*DM to claim*, *instant loan*, *urgent KYC*, *wallet freeze*, *bit.ly*, *enter OTP*), combined with account age and follower count anomalies. | `"Scam phrases / deceptive bait detected: dm us, bit.ly, urgent kyc"` |

### Verdict Bands
- **HIGH THREAT ($\ge 75$):** Active impersonator, immediate takedown required.
- **MEDIUM THREAT ($50 - 74$):** Suspicious look-alike, unofficial reseller, or high-risk fan entity.
- **LOW THREAT ($30 - 49$):** Weak resemblance or borderline community mention.
- **SAFE ($< 30$):** Legitimate entities, innocent business compounds, or verified official assets.

---

## 3. Strict Official Asset Exclusion Filter

To eliminate false positives on the brand's own digital assets:
1. Candidate handles are checked against the brand's registered social handles with platform matching and `@` normalization.
2. Candidate apps are checked against the brand's official package IDs and official developer names.
3. Matching assets bypass threat scoring entirely, receiving **Score = 0.0**, **Verdict = "Safe"**, and an explicit allowlist citation.

---

## 4. Fault-Tolerant Connector Architecture

All data connectors inherit from `BaseConnector` and encapsulate ingestion inside robust error handling:
- `SocialSampleConnector` & `AppStoreSampleConnector` load realistic seed datasets (~40 social + ~30 app candidates).
- `LiveSocialConnector` & `LiveAppStoreConnector` provide pluggable hooks for live social and store scraping APIs, falling back to cached seed data if network drops or rate limits occur.
- When an upstream source is unavailable, the UI presents an informative status banner while continuing uninterrupted operation.

---

## 5. Unique Differentiating Features

### A. Explainable Threat Card
Every detection item displays:
- Side-by-side logo visualizer comparing the official logo against candidate avatar.
- 6-segment score breakdown bar showing exact point contributions.
- Numbered forensic evidence log explaining human-readable reasons.

### B. Look-alike Lab
An interactive permutation laboratory where security analysts can type any brand name and immediately inspect generated typos, homoglyphs, spacing tricks, and added words—with real-time cross-referencing indicating if any variant exists in current monitored feeds.

### C. One-Click Takedown Pack
Instantly produces:
1. **Platform-Tailored Copy-Paste Notice:** Formatted legal complaints referencing DMCA, Trademark, and specific policies for Twitter/X, Meta, Google Play, Apple App Store, and Telegram.
2. **Official PDF Evidence Dossier:** High-resolution ReportLab document containing executive summaries, forensic signal tables, evidence logs, and verification timestamps ready for submission to platform legal teams.

### D. Trust Radar Dashboard
Features organizational **Brand Exposure Score** (0–100 risk index), severity distribution donut chart, cross-channel threat counts, and top technique frequency metrics powered by Recharts.
