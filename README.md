# Job Analyzer — Global Job Discovery & Remote Job Platform

> Real-time global job discovery, remote opportunity aggregator, candidate eligibility engine, and objective scoring platform covering Bangladesh and major international markets.
>
> **Live Web Application**: [https://job-analyzer-s3wi.onrender.com](https://job-analyzer-s3wi.onrender.com)

---

## Key Features

1. **Global & Bangladesh Discovery**:
   - Covers Bangladesh (BDJobs live API, Chakri, Skill.jobs) and major international tech hubs (USA, Germany, UK, India, Singapore, Worldwide Remote).
   - Real-time country, workplace, and remote eligibility filters with direct application links.
2. **Strict ToS Compliance for Social & Professional Networks**:
   - **LinkedIn & Facebook**: Both platforms strictly prohibit automated web scraping in their Terms of Service.
   - **Compliant Ingestion**: Job Analyzer never runs unauthorized crawlers on either network. It ingests opportunities exclusively via:
     - **Manual-Paste Ingestion**: Intelligent text & JSON-LD parsing for copied job descriptions, groups, and posts.
     - **Official APIs**: Official LinkedIn Partner API and Facebook Graph API for managed pages.
     - **1-Click Bookmarklet**: Client-side single-click capture tool for active browser sessions.
3. **Objective "Best Jobs" Scoring Engine**:
   - **Recency ($w_1 = 0.20$)**: Half-life exponential decay ($e^{-\Delta t / 7}$).
   - **Salary Transparency ($w_2 = 0.30$)**: Penalizes opaque "Negotiable" listings; rewards disclosed packages normalized to USD and BDT.
   - **Candidate Profile Match ($w_3 = 0.35$)**: Multi-factor keyword overlap + experience bracket alignment.
   - **Employer Credibility ($w_4 = 0.15$)**: Tiered rating for MNCs, Top Conglomerates, Financial Institutions, and verified enterprises.
4. **Circadian Timezone Feasibility**:
   - Computes daylight/graveyard shift impact, core hour overlap, and feasibility tiers across timezones.

---

## 🚀 Quick Start

### 1. Command-Line Interface (CLI)

```bash
# Query top openings for IT/Telecommunication (Category 8)
python cli.py --category 8 --skills "Python, React, Docker" --experience 4 --limit 10

# Query top openings for Accounting/Finance (Category 1)
python cli.py --category 1 --skills "Audit, Tax, ACCA" --experience 5 --limit 10

# List all 64 verified categories with live vacancy counts
python cli.py --list-categories
```

### 2. Interactive Web Dashboard

Launch the FastAPI dev server:

```bash
python app.py
```
Then navigate to: **`http://127.0.0.1:8000`** in your browser.

---

## 📐 Scoring Formula

The composite score ($0.00$ to $1.00$) evaluates each job opening:

$$\text{Score} = (w_1 \cdot S_{\text{recency}}) + (w_2 \cdot S_{\text{salary}}) + (w_3 \cdot S_{\text{profile\_match}}) + (w_4 \cdot S_{\text{employer\_cred}})$$

| Component | Weight | Logic |
| :--- | :---: | :--- |
| **Recency ($S_{\text{recency}}$)** | 20% | $e^{-\Delta t / 7}$. Jobs posted within 24h score $\sim 1.0$; 7-day-old jobs score $0.37$. Expired jobs drop to $0.05$. |
| **Salary ($S_{\text{salary}}$)** | 30% | "Negotiable" / undisclosed receives base penalty ($0.35$). Disclosed packages receive $0.70$ base $+ 0.30 \cdot \min(1.0, \text{Midpoint} / \text{Benchmark})$. |
| **Profile Match ($S_{\text{profile}}$)** | 35% | Jaccard skill keyword match $(45\%) +$ Experience fit bracket $(35\%) +$ Category target fit $(20\%)$. |
| **Employer Tier ($S_{\text{employer}}$)** | 15% | MNC ($1.00$), Financial Inst. ($0.95$), Conglomerate ($0.90$), Verified Corporate ($0.80$), SME ($0.60$), Confidential ($0.25$). |

---

## 🧪 Automated Tests

Run the test suite with `pytest`:

```bash
python -m pytest tests/ -v
```

---

## 📁 Project Structure

```
├── data/
│   └── taxonomy.json          # 64 verified BDJobs categories & 28 industries
├── core/
│   ├── models.py              # Pydantic schemas (NormalizedJob, UserProfile, etc.)
│   └── normalizer.py          # Salary, experience, date, and tier parsers
├── ingestion/
│   ├── bdjobs_client.py       # Live REST API connector for api.bdjobs.com
│   ├── linkedin_parser.py     # Compliant structured paste parser
│   └── public_portals.py      # Skill.jobs & Chakri connectors
├── scoring/
│   └── scorer.py              # Multi-factor mathematical ranking engine
├── static/
│   ├── index.html             # Glassmorphic responsive dashboard
│   ├── styles.css             # Vanilla CSS design tokens & dark theme
│   └── app.js                 # Interactive controller & CSV exporter
├── tests/
│   ├── test_normalizer.py     # Parser unit tests
│   ├── test_scoring.py        # Algorithm tests
│   └── test_bdjobs_live.py    # Production REST API integration tests
├── app.py                     # FastAPI application
├── cli.py                     # Terminal tool
└── README.md
```
