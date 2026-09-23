# bd-job-analyzer

> Bangladesh Multi-Portal Job Aggregator and "Best Jobs" Scoring Engine built on top of the verified 64-category BDJobs taxonomy.

---

## 🌟 Key Features

1. **Verified 64-Category Taxonomy**:
   - Covers all **31 Functional Categories** and **33 Special Skilled Categories** directly mapped to live production BDJobs IDs.
   - Includes 28 Industry classifications and candidate pool metrics.
2. **Multi-Portal Ingestion**:
   - **BDJobs**: Live integration with BDJobs production REST microservice (`https://api.bdjobs.com/Jobs/api/JobSearch/GetJobSearch`).
   - **LinkedIn**: ToS-compliant structured paste & JSON-LD parser that extracts title, company, experience, and salary without risky scraping.
   - **Partner Portals**: Cross-portal connectors for public listings (Skill.jobs, Chakri.com).
3. **Objective "Best Jobs" Scoring Engine**:
   - **Recency ($w_1 = 0.20$)**: Half-life exponential decay ($e^{-\Delta t / 7}$).
   - **Salary Transparency ($w_2 = 0.30$)**: Penalizes opaque "Negotiable" listings; rewards disclosed packages benchmarked against category medians.
   - **Candidate Profile Match ($w_3 = 0.35$)**: Multi-factor keyword overlap + experience bracket alignment.
   - **Employer Credibility ($w_4 = 0.15$)**: Tiered rating for MNCs, Top Conglomerates, Financial Institutions, and verified enterprises.
4. **Interfaces**:
   - **CLI Tool**: Instant terminal queries with tabulate formatted tables.
   - **Interactive Web Dashboard**: Modern, glassmorphic dark-mode web application with real-time category chips, experience sliders, LinkedIn paste modal, and CSV export.

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
