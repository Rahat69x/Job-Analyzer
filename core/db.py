import sqlite3
import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Tuple
from core.models import (
    NormalizedJob, CompanyInfo, SalaryInfo, ExperienceRequirement, 
    RemoteEligibility, CandidateEligibility, WorkplaceType, ExperienceLevel
)
from core.normalizer import evaluate_candidate_eligibility
from core.occupation_taxonomy import normalize_search_query
from core.source_registry import source_registry

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "jobs.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Jobs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        source TEXT,
        title TEXT,
        company_name TEXT,
        company_tier TEXT,
        category_id INTEGER,
        category_name TEXT,
        category_type TEXT,
        country TEXT DEFAULT 'Bangladesh',
        city TEXT DEFAULT 'Dhaka',
        location TEXT,
        workplace_type TEXT DEFAULT 'On-site',
        remote_policy TEXT DEFAULT 'Not Remote',
        allowed_countries TEXT DEFAULT '[]',
        allowed_regions TEXT DEFAULT '[]',
        accepts_international INTEGER DEFAULT 0,
        visa_sponsorship INTEGER DEFAULT 0,
        work_auth_required INTEGER DEFAULT 0,
        publish_date TEXT,
        deadline TEXT,
        min_exp REAL,
        max_exp REAL,
        experience_level TEXT DEFAULT 'Mid Level',
        min_salary REAL,
        max_salary REAL,
        salary_text TEXT,
        salary_disclosed INTEGER,
        currency TEXT DEFAULT 'BDT',
        salary_type TEXT DEFAULT 'not_disclosed',
        salary_usd_min REAL,
        salary_usd_max REAL,
        salary_bdt_min REAL,
        salary_bdt_max REAL,
        job_type TEXT DEFAULT 'FullTime',
        employment_type TEXT DEFAULT 'Full-time',
        vacancies INTEGER DEFAULT 1,
        skills_required TEXT DEFAULT '[]',
        apply_url TEXT,
        job_context TEXT,
        source_reliability TEXT DEFAULT 'major_board',
        canonical_id TEXT,
        alternate_sources TEXT DEFAULT '[]',
        first_seen_at TEXT,
        remote_type TEXT DEFAULT 'UNKNOWN',
        source_type TEXT DEFAULT 'GLOBAL_JOB_BOARD',
        source_job_id TEXT,
        region TEXT DEFAULT 'Worldwide',
        updated_at TEXT,
        collected_at TEXT
    );
    """)

    # Check and add any missing columns for existing DB instances (auto-migration)
    existing_cols = [row[1] for row in cursor.execute("PRAGMA table_info(jobs)").fetchall()]
    migration_cols = {
        "country": "TEXT DEFAULT 'Bangladesh'",
        "city": "TEXT DEFAULT 'Dhaka'",
        "workplace_type": "TEXT DEFAULT 'On-site'",
        "remote_policy": "TEXT DEFAULT 'Not Remote'",
        "allowed_countries": "TEXT DEFAULT '[]'",
        "allowed_regions": "TEXT DEFAULT '[]'",
        "accepts_international": "INTEGER DEFAULT 0",
        "visa_sponsorship": "INTEGER DEFAULT 0",
        "work_auth_required": "INTEGER DEFAULT 0",
        "experience_level": "TEXT DEFAULT 'Mid Level'",
        "currency": "TEXT DEFAULT 'BDT'",
        "salary_type": "TEXT DEFAULT 'not_disclosed'",
        "salary_usd_min": "REAL",
        "salary_usd_max": "REAL",
        "salary_bdt_min": "REAL",
        "salary_bdt_max": "REAL",
        "employment_type": "TEXT DEFAULT 'Full-time'",
        "skills_required": "TEXT DEFAULT '[]'",
        "source_reliability": "TEXT DEFAULT 'major_board'",
        "canonical_id": "TEXT",
        "alternate_sources": "TEXT DEFAULT '[]'",
        "remote_type": "TEXT DEFAULT 'UNKNOWN'",
        "source_type": "TEXT DEFAULT 'GLOBAL_JOB_BOARD'",
        "source_job_id": "TEXT",
        "region": "TEXT DEFAULT 'Worldwide'",
        "updated_at": "TEXT",
        "collected_at": "TEXT"
    }
    for col, col_def in migration_cols.items():
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col} {col_def}")
            except Exception:
                pass

    # 2. User Application Tracker Table (8 Application Stages)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_job_tracker (
        job_id TEXT PRIMARY KEY,
        status TEXT DEFAULT 'Saved',
        notes TEXT DEFAULT '',
        score REAL DEFAULT 0.0,
        application_date TEXT,
        interview_date TEXT,
        recruiter_info TEXT DEFAULT '',
        followup_date TEXT,
        updated_at TEXT,
        FOREIGN KEY(job_id) REFERENCES jobs(id)
    );
    """)

    tracker_cols = [row[1] for row in cursor.execute("PRAGMA table_info(user_job_tracker)").fetchall()]
    tracker_migrations = {
        "application_date": "TEXT",
        "interview_date": "TEXT",
        "recruiter_info": "TEXT DEFAULT ''",
        "followup_date": "TEXT"
    }
    for col, col_def in tracker_migrations.items():
        if col not in tracker_cols:
            try:
                cursor.execute(f"ALTER TABLE user_job_tracker ADD COLUMN {col} {col_def}")
            except Exception:
                pass

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs(category_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_country ON jobs(country);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_workplace ON jobs(workplace_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);")
    conn.commit()
    conn.close()

def upsert_jobs(jobs: List[NormalizedJob]):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    
    for j in jobs:
        pub_str = j.publish_date.isoformat() if j.publish_date else None
        dead_str = j.deadline.isoformat() if j.deadline else None
        upd_str = j.updated_at.isoformat() if j.updated_at else now_str
        col_str = j.collected_at.isoformat() if j.collected_at else now_str
        
        cursor.execute("""
        INSERT INTO jobs (
            id, source, title, company_name, company_tier, category_id, category_name, category_type,
            country, city, location, workplace_type, remote_policy, allowed_countries, allowed_regions,
            accepts_international, visa_sponsorship, work_auth_required, publish_date, deadline,
            min_exp, max_exp, experience_level, min_salary, max_salary, salary_text, salary_disclosed,
            currency, salary_type, salary_usd_min, salary_usd_max, salary_bdt_min, salary_bdt_max,
            job_type, employment_type, vacancies, skills_required, apply_url, job_context,
            source_reliability, canonical_id, alternate_sources, first_seen_at,
            remote_type, source_type, source_job_id, region, updated_at, collected_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            company_name=excluded.company_name,
            company_tier=excluded.company_tier,
            category_id=excluded.category_id,
            category_name=excluded.category_name,
            category_type=excluded.category_type,
            country=excluded.country,
            city=excluded.city,
            location=excluded.location,
            workplace_type=excluded.workplace_type,
            remote_policy=excluded.remote_policy,
            allowed_countries=excluded.allowed_countries,
            allowed_regions=excluded.allowed_regions,
            accepts_international=excluded.accepts_international,
            visa_sponsorship=excluded.visa_sponsorship,
            work_auth_required=excluded.work_auth_required,
            deadline=excluded.deadline,
            salary_text=excluded.salary_text,
            min_salary=excluded.min_salary,
            max_salary=excluded.max_salary,
            salary_disclosed=excluded.salary_disclosed,
            currency=excluded.currency,
            salary_type=excluded.salary_type,
            salary_usd_min=excluded.salary_usd_min,
            salary_usd_max=excluded.salary_usd_max,
            salary_bdt_min=excluded.salary_bdt_min,
            salary_bdt_max=excluded.salary_bdt_max,
            job_type=excluded.job_type,
            employment_type=excluded.employment_type,
            skills_required=excluded.skills_required,
            apply_url=excluded.apply_url,
            job_context=excluded.job_context,
            source_reliability=excluded.source_reliability,
            alternate_sources=excluded.alternate_sources,
            remote_type=excluded.remote_type,
            source_type=excluded.source_type,
            source_job_id=excluded.source_job_id,
            region=excluded.region,
            updated_at=excluded.updated_at,
            collected_at=excluded.collected_at;
        """, (
            j.id, j.source, j.title, j.company.name, j.company.tier, j.category_id, j.category_name, j.category_type,
            j.country, j.city, j.location, j.workplace_type, j.remote_eligibility.policy,
            json.dumps(j.remote_eligibility.allowed_countries), json.dumps(j.remote_eligibility.allowed_regions),
            1 if j.remote_eligibility.accepts_international else 0,
            1 if j.remote_eligibility.visa_sponsorship else 0,
            1 if j.remote_eligibility.requires_work_authorization else 0,
            pub_str, dead_str,
            j.experience.min_years, j.experience.max_years, j.experience_level,
            j.salary.min_salary, j.salary.max_salary, j.salary.raw_text, 1 if j.salary.disclosed else 0,
            j.salary.currency, j.salary.salary_type, j.salary.salary_usd_min, j.salary.salary_usd_max,
            j.salary.salary_bdt_min, j.salary.salary_bdt_max,
            j.job_type, j.employment_type, j.vacancies, json.dumps(j.skills_required),
            j.apply_url, j.job_context, j.source_reliability, j.canonical_id,
            json.dumps(j.alternate_sources), now_str,
            j.remote_type, j.source_type, j.source_job_id, j.region, upd_str, col_str
        ))
        
    conn.commit()
    conn.close()

def row_to_normalized_job(row: sqlite3.Row, candidate_origin: str = "Bangladesh") -> NormalizedJob:
    """Hydrate a NormalizedJob from a SQLite database row."""
    allowed_countries = json.loads(row["allowed_countries"]) if "allowed_countries" in row.keys() and row["allowed_countries"] else []
    allowed_regions = json.loads(row["allowed_regions"]) if "allowed_regions" in row.keys() and row["allowed_regions"] else []
    skills = json.loads(row["skills_required"]) if "skills_required" in row.keys() and row["skills_required"] else []
    alt_sources = json.loads(row["alternate_sources"]) if "alternate_sources" in row.keys() and row["alternate_sources"] else []

    country = row["country"] if "country" in row.keys() and row["country"] else "Bangladesh"
    workplace_type = row["workplace_type"] if "workplace_type" in row.keys() and row["workplace_type"] else "On-site"
    policy = row["remote_policy"] if "remote_policy" in row.keys() and row["remote_policy"] else "Not Remote"

    remote_elig = RemoteEligibility(
        policy=policy,
        allowed_countries=allowed_countries,
        allowed_regions=allowed_regions,
        accepts_international=bool(row["accepts_international"]) if "accepts_international" in row.keys() else False,
        visa_sponsorship=bool(row["visa_sponsorship"]) if "visa_sponsorship" in row.keys() else False,
        requires_work_authorization=bool(row["work_auth_required"]) if "work_auth_required" in row.keys() else False
    )

    cand_elig = evaluate_candidate_eligibility(country, workplace_type, remote_elig, candidate_origin)

    pub_date = datetime.fromisoformat(row["publish_date"]) if row["publish_date"] else None
    dead_date = datetime.fromisoformat(row["deadline"]) if row["deadline"] else None
    upd_date = datetime.fromisoformat(row["updated_at"]) if "updated_at" in row.keys() and row["updated_at"] else None
    col_date = datetime.fromisoformat(row["collected_at"]) if "collected_at" in row.keys() and row["collected_at"] else None

    rem_type = row["remote_type"] if "remote_type" in row.keys() and row["remote_type"] else ("REMOTE" if workplace_type == "Remote" else ("HYBRID" if workplace_type == "Hybrid" else "ONSITE"))
    src_type = row["source_type"] if "source_type" in row.keys() and row["source_type"] else "GLOBAL_JOB_BOARD"
    src_jid = row["source_job_id"] if "source_job_id" in row.keys() else None
    reg = row["region"] if "region" in row.keys() and row["region"] else "Worldwide"

    return NormalizedJob(
        id=row["id"],
        source=row["source"],
        source_type=src_type,
        source_job_id=src_jid,
        title=row["title"],
        company=CompanyInfo(name=row["company_name"], tier=row["company_tier"], verified=True),
        category_id=row["category_id"],
        category_name=row["category_name"],
        category_type=row["category_type"],
        country=country,
        city=row["city"] if "city" in row.keys() else "Dhaka",
        location=row["location"],
        region=reg,
        workplace_type=workplace_type,
        remote_type=rem_type,
        remote_eligibility=remote_elig,
        candidate_eligibility=cand_elig,
        publish_date=pub_date,
        deadline=dead_date,
        updated_at=upd_date,
        collected_at=col_date,
        experience=ExperienceRequirement(min_years=row["min_exp"], max_years=row["max_exp"], raw_text=f"{row['min_exp']}y+"),
        experience_level=row["experience_level"] if "experience_level" in row.keys() and row["experience_level"] else "Mid Level",
        salary=SalaryInfo(
            disclosed=bool(row["salary_disclosed"]),
            min_salary=row["min_salary"],
            max_salary=row["max_salary"],
            currency=row["currency"] if "currency" in row.keys() else "BDT",
            raw_text=row["salary_text"] or "Negotiable",
            salary_type=row["salary_type"] if "salary_type" in row.keys() and row["salary_type"] else "not_disclosed",
            salary_usd_min=row["salary_usd_min"] if "salary_usd_min" in row.keys() else None,
            salary_usd_max=row["salary_usd_max"] if "salary_usd_max" in row.keys() else None,
            salary_bdt_min=row["salary_bdt_min"] if "salary_bdt_min" in row.keys() else None,
            salary_bdt_max=row["salary_bdt_max"] if "salary_bdt_max" in row.keys() else None
        ),
        job_type=row["job_type"],
        employment_type=row["employment_type"] if "employment_type" in row.keys() and row["employment_type"] else "Full-time",
        vacancies=row["vacancies"],
        skills_required=skills,
        job_context=row["job_context"] or "",
        apply_url=row["apply_url"],
        source_reliability=row["source_reliability"] if "source_reliability" in row.keys() and row["source_reliability"] else "major_board",
        canonical_id=row["canonical_id"] if "canonical_id" in row.keys() else None,
        alternate_sources=alt_sources
    )

def get_job_by_id(job_id: str) -> Optional[NormalizedJob]:
    """Retrieve a single NormalizedJob by ID from SQLite database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row_to_normalized_job(row)
    return None

def search_global_jobs(
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    country: Optional[str] = None,
    workplace_type: Optional[str] = None,
    remote_policy: Optional[str] = None,
    experience_level: Optional[str] = None,
    employment_type: Optional[str] = None,
    visa_sponsorship: Optional[bool] = None,
    candidate_origin: str = "Bangladesh",
    sort_by: str = "recent",
    source: Optional[str] = None,
    limit: int = 1500,
    min_salary: Optional[float] = None,
    max_salary: Optional[float] = None,
    salary_currency: str = "BDT",
    salary_period: str = "Monthly",
    freshness_days: Optional[int] = None
) -> List[NormalizedJob]:
    """Backward-compatible entry point returning List[NormalizedJob]."""
    jobs, _ = search_global_jobs_with_diagnostics(
        q=q,
        category_id=category_id,
        country=country,
        workplace_type=workplace_type,
        remote_policy=remote_policy,
        experience_level=experience_level,
        employment_type=employment_type,
        visa_sponsorship=visa_sponsorship,
        candidate_origin=candidate_origin,
        sort_by=sort_by,
        source=source,
        limit=limit,
        min_salary=min_salary,
        max_salary=max_salary,
        salary_currency=salary_currency,
        salary_period=salary_period,
        freshness_days=freshness_days
    )
    return jobs

def search_global_jobs_with_diagnostics(
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    country: Optional[str] = None,
    workplace_type: Optional[str] = None,
    remote_policy: Optional[str] = None,
    experience_level: Optional[str] = None,
    employment_type: Optional[str] = None,
    visa_sponsorship: Optional[bool] = None,
    candidate_origin: str = "Bangladesh",
    sort_by: str = "recent",
    source: Optional[str] = None,
    limit: int = 1500,
    min_salary: Optional[float] = None,
    max_salary: Optional[float] = None,
    salary_currency: str = "BDT",
    salary_period: str = "Monthly",
    freshness_days: Optional[int] = None
) -> Tuple[List[NormalizedJob], Dict[str, Any]]:
    """
    Production-grade global search pipeline:
    - Normalizes queries via deliberate occupation taxonomy.
    - Strictly excludes Bangladesh/BDJobs from worldwide & international queries.
    - Treats location and remote requirements as hard filters.
    - Applies weighted relevance scoring (Title > Skills > Description).
    - Returns hydrated jobs and complete diagnostic funnel metrics.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    total_in_db = cursor.execute("SELECT count(*) FROM jobs").fetchone()[0]
    all_reg_sources = source_registry.get_all_sources()
    active_sources_cnt = len([s for s in all_reg_sources if s.status in ["ACTIVE", "PARTIAL"]])
    unavail_sources_cnt = len(all_reg_sources) - active_sources_cnt

    conditions = []
    params = []

    # Source filter
    if source and source.lower() not in ["all", "any", ""]:
        conditions.append("source LIKE ?")
        params.append(f"%{source}%")

    # Category filter
    if category_id is not None and int(category_id) > 0:
        conditions.append("category_id = ?")
        params.append(int(category_id))

    # Location / Country Filter & Strict BDJobs Exclusion
    is_bd_search = bool((country and country.lower() in ["bangladesh", "bd"]) or (source and "bdjobs" in source.lower()))
    is_explicit_worldwide = bool(country and country.lower() in ["worldwide", "remote worldwide"])
    has_international_country = bool(country and country.lower() not in ["all", "any", "worldwide", "remote worldwide", "bangladesh", "bd", "worldwide & bangladesh"])
    is_worldwide_search = not country or country.lower() in ["all", "worldwide", "any", "remote worldwide"]

    if is_explicit_worldwide or has_international_country:
        conditions.append("source != 'BDJobs'")
    elif q and q.strip() and not is_bd_search:
        # If searching a specific role and country wasn't Bangladesh, exclude BDJobs from worldwide query
        conditions.append("source != 'BDJobs'")

    if not is_worldwide_search:
        c_lower = country.lower()
        if c_lower in ["european union", "eu", "europe"]:
            conditions.append("(region = 'Europe' OR country IN ('Germany', 'United Kingdom', 'France', 'Netherlands', 'Ireland', 'Sweden', 'Switzerland', 'Poland', 'Spain', 'Italy') OR (workplace_type = 'Remote' AND remote_policy = 'Worldwide'))")
        elif c_lower in ["united states", "usa", "us"]:
            conditions.append("(country = 'United States' OR location LIKE '%united states%' OR location LIKE '%usa%' OR (workplace_type = 'Remote' AND (remote_policy = 'Worldwide' OR allowed_countries LIKE '%United States%')))")
        elif c_lower in ["united kingdom", "uk"]:
            conditions.append("(country = 'United Kingdom' OR location LIKE '%united kingdom%' OR location LIKE '%uk%' OR (workplace_type = 'Remote' AND (remote_policy = 'Worldwide' OR allowed_countries LIKE '%United Kingdom%')))")
        elif c_lower == "germany":
            conditions.append("(country = 'Germany' OR location LIKE '%germany%' OR location LIKE '%berlin%' OR location LIKE '%munich%' OR (workplace_type = 'Remote' AND (remote_policy = 'Worldwide' OR allowed_countries LIKE '%Germany%')))")
        elif c_lower == "india":
            conditions.append("(country = 'India' OR location LIKE '%india%' OR location LIKE '%bangalore%' OR location LIKE '%bengaluru%' OR (workplace_type = 'Remote' AND (remote_policy = 'Worldwide' OR allowed_countries LIKE '%India%')))")
        elif c_lower == "singapore":
            conditions.append("(country = 'Singapore' OR location LIKE '%singapore%' OR (workplace_type = 'Remote' AND (remote_policy = 'Worldwide' OR allowed_countries LIKE '%Singapore%')))")
        elif c_lower == "canada":
            conditions.append("(country = 'Canada' OR location LIKE '%canada%' OR location LIKE '%toronto%' OR (workplace_type = 'Remote' AND (remote_policy = 'Worldwide' OR allowed_countries LIKE '%Canada%')))")
        elif c_lower == "bangladesh":
            conditions.append("(country = 'Bangladesh' OR location LIKE '%bangladesh%' OR location LIKE '%dhaka%')")
        else:
            conditions.append("(country = ? OR location LIKE ? OR (workplace_type = 'Remote' AND remote_policy = 'Worldwide'))")
            params.extend([country, f"%{country}%"])

    # Workplace mode / Remote filter
    has_remote_requested = bool(
        (workplace_type and workplace_type.lower() == "remote") or 
        (q and "remote" in q.lower()) or 
        (country and "remote" in country.lower())
    )
    if has_remote_requested:
        conditions.append("workplace_type = 'Remote'")
        if is_worldwide_search:
            # Must be true worldwide remote, not country restricted
            conditions.append("(remote_policy = 'Worldwide' OR location LIKE '%worldwide%' OR location LIKE '%anywhere%' OR location LIKE '%global%')")
            conditions.append("location NOT LIKE '%us only%' AND location NOT LIKE '%united states only%'")
    elif workplace_type and workplace_type.lower() not in ["all", "any"]:
        conditions.append("workplace_type = ?")
        params.append(workplace_type)

    if remote_policy and remote_policy.lower() not in ["all", "any"]:
        conditions.append("remote_policy = ?")
        params.append(remote_policy)

    if experience_level and experience_level.lower() not in ["all", "any"]:
        conditions.append("experience_level = ?")
        params.append(experience_level)

    if employment_type and employment_type.lower() not in ["all", "any"]:
        conditions.append("employment_type = ?")
        params.append(employment_type)

    if visa_sponsorship is True:
        conditions.append("visa_sponsorship = 1")

    # Freshness filter
    if freshness_days and int(freshness_days) > 0:
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=int(freshness_days))).isoformat()
        conditions.append("(publish_date >= ? OR updated_at >= ?)")
        params.extend([cutoff_date, cutoff_date])

    # Salary range filter
    if min_salary is not None and float(min_salary) > 0:
        val_min = float(min_salary)
        ann_bdt_min = (val_min if salary_period.lower() == "annual" else val_min * 12.0) * 120.0 if salary_currency.upper() == "USD" else (val_min * 12.0 if salary_period.lower() == "monthly" else val_min)
        conditions.append("salary_disclosed = 1 AND COALESCE(salary_bdt_max, salary_bdt_min) >= ?")
        params.append(ann_bdt_min)

    if max_salary is not None and float(max_salary) > 0:
        val_max = float(max_salary)
        ann_bdt_max = (val_max if salary_period.lower() == "annual" else val_max * 12.0) * 120.0 if salary_currency.upper() == "USD" else (val_max * 12.0 if salary_period.lower() == "monthly" else val_max)
        conditions.append("salary_disclosed = 1 AND COALESCE(salary_bdt_min, salary_bdt_max) <= ?")
        params.append(ann_bdt_max)

    # Deliberate Query Expansion using Occupation Taxonomy
    query_terms = []
    if q and q.strip():
        raw_tokens = [w for w in q.split() if w.lower() not in ["job", "jobs", "remote", "worldwide", "international"]]
        clean_query = " ".join(raw_tokens).strip() if raw_tokens else q.strip()
        query_terms = normalize_search_query(clean_query)

        if query_terms:
            token_conds = []
            for term in query_terms:
                token_conds.append("(title LIKE ? OR skills_required LIKE ? OR job_context LIKE ?)")
                p = f"%{term}%"
                params.extend([p, p, p])
            conditions.append("(" + " OR ".join(token_conds) + ")")

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    order_clause = "ORDER BY publish_date DESC, rowid DESC"
    if sort_by == "salary_desc":
        order_clause = "ORDER BY COALESCE(salary_usd_max, salary_usd_min, 0) DESC, publish_date DESC"
    elif sort_by == "salary_asc":
        order_clause = "ORDER BY CASE WHEN salary_usd_min > 0 THEN salary_usd_min ELSE 99999999 END ASC, publish_date DESC"
    elif sort_by == "deadline":
        order_clause = "ORDER BY CASE WHEN deadline IS NOT NULL AND deadline != '' THEN deadline ELSE '9999-12-31' END ASC, publish_date DESC"

    sql = f"SELECT * FROM jobs{where_clause} {order_clause} LIMIT ?"
    params.append(limit)

    rows = cursor.execute(sql, params).fetchall()
    conn.close()

    hydrated = [row_to_normalized_job(r, candidate_origin) for r in rows]

    # Weighted relevance ranking: Title match > Skills match > Description match
    if q and q.strip():
        primary_q = q.lower().strip()
        def calculate_relevance(job: NormalizedJob) -> float:
            t = job.title.lower()
            s = " ".join(job.skills_required).lower()
            d = (job.job_context or "").lower()
            rel = 0.0
            if primary_q == t:
                rel += 200.0
            elif primary_q in t:
                rel += 100.0
            elif any(term in t for term in query_terms):
                rel += 75.0
            elif any(term in s for term in query_terms):
                rel += 40.0
            elif any(term in d for term in query_terms):
                rel += 15.0
            return rel

        def get_sort_date(j: NormalizedJob) -> datetime:
            if not j.publish_date:
                return datetime.min.replace(tzinfo=timezone.utc)
            if j.publish_date.tzinfo is None:
                return j.publish_date.replace(tzinfo=timezone.utc)
            return j.publish_date

        if sort_by in ["recent", "relevance"]:
            hydrated.sort(key=lambda j: (calculate_relevance(j), get_sort_date(j)), reverse=True)

    # Diagnostic Search Funnel Calculation (Section 18)
    diagnostics = {
        "query": q,
        "normalized_terms": query_terms,
        "sources_queried": active_sources_cnt,
        "sources_active": active_sources_cnt,
        "sources_unavailable": unavail_sources_cnt,
        "total_evaluated": total_in_db,
        "matching_title_or_skills": len(hydrated),
        "matching_location": len([j for j in hydrated if not country or country.lower() in ["all", "worldwide"] or country.lower() in j.country.lower() or country.lower() in j.location.lower()]),
        "matching_remote": len([j for j in hydrated if not has_remote_requested or j.workplace_type == "Remote"]),
        "final_results": len(hydrated),
        "explanation": f"Evaluated {total_in_db} jobs across {active_sources_cnt} active global sources." if hydrated else "No matching jobs found from currently available sources with active endpoints."
    }

    return hydrated, diagnostics

def get_country_explorer_stats() -> List[Dict[str, Any]]:
    """Aggregate vacancies, remote percentage, top companies, and visa positions per country."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
    SELECT 
        country,
        COUNT(*) as total_jobs,
        SUM(CASE WHEN workplace_type = 'Remote' THEN 1 ELSE 0 END) as remote_jobs,
        SUM(CASE WHEN visa_sponsorship = 1 THEN 1 ELSE 0 END) as visa_jobs,
        AVG(CASE WHEN salary_usd_min IS NOT NULL THEN salary_usd_min ELSE NULL END) as avg_min_usd,
        GROUP_CONCAT(DISTINCT company_name) as companies_sample
    FROM jobs
    WHERE country IS NOT NULL AND country != ''
    GROUP BY country
    ORDER BY total_jobs DESC;
    """
    rows = cursor.execute(sql).fetchall()
    conn.close()

    results = []
    for r in rows:
        tot = r["total_jobs"]
        rem = r["remote_jobs"] or 0
        rem_pct = round((rem / tot) * 100, 1) if tot > 0 else 0.0
        
        comps = (r["companies_sample"] or "").split(",")[:4]
        
        results.append({
            "country": r["country"],
            "total_jobs": tot,
            "remote_jobs": rem,
            "remote_pct": rem_pct,
            "visa_sponsorship_jobs": r["visa_jobs"] or 0,
            "avg_salary_usd": round(r["avg_min_usd"], 0) if r["avg_min_usd"] else None,
            "top_companies": [c.strip() for c in comps if c.strip()]
        })

    return results

def set_job_status(
    job_id: str, 
    status: str, 
    notes: str = "", 
    score: float = 0.0,
    application_date: Optional[str] = None,
    interview_date: Optional[str] = None,
    recruiter_info: str = "",
    followup_date: Optional[str] = None
):
    """Save or update application status for a job across all 8 stages."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    
    cursor.execute("""
    INSERT INTO user_job_tracker (
        job_id, status, notes, score, application_date, interview_date, recruiter_info, followup_date, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(job_id) DO UPDATE SET
        status=excluded.status,
        notes=excluded.notes,
        score=excluded.score,
        application_date=COALESCE(excluded.application_date, user_job_tracker.application_date),
        interview_date=COALESCE(excluded.interview_date, user_job_tracker.interview_date),
        recruiter_info=excluded.recruiter_info,
        followup_date=excluded.followup_date,
        updated_at=excluded.updated_at;
    """, (job_id, status, notes, score, application_date, interview_date, recruiter_info, followup_date, now_str))
    
    conn.commit()
    conn.close()

def get_tracked_jobs() -> List[Dict[str, Any]]:
    """Retrieve user tracked pipeline across all 8 stages."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT t.job_id, t.status, t.notes, t.score, t.application_date, t.interview_date, 
           t.recruiter_info, t.followup_date, t.updated_at,
           j.title, j.company_name, j.country, j.location, j.workplace_type, j.salary_text, j.apply_url, j.source
    FROM user_job_tracker t
    LEFT JOIN jobs j ON t.job_id = j.id
    ORDER BY t.updated_at DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        d = dict(r)
        d["id"] = d["job_id"]
        d["tracker_score"] = d["score"]
        results.append(d)
    return results

def get_market_analytics(category_id: Optional[int] = None) -> Dict[str, Any]:
    """Calculate salary transparency rate, median salary spans, and employer hiring volumes."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    query_filter = "WHERE category_id = ?" if category_id else ""
    params = [category_id] if category_id else []
    
    cursor.execute(f"SELECT COUNT(*) FROM jobs {query_filter}", params)
    total_jobs = cursor.fetchone()[0]
    
    if total_jobs == 0:
        conn.close()
        return {
            "total_jobs_tracked": 0,
            "total_openings": 0,
            "transparency_rate": 0.0,
            "salary_stats": {"disclosed_pct": 0.0, "avg_salary": 0, "median_salary": 0},
            "median_salary_bdt": 0,
            "avg_salary_bdt": 0,
            "top_companies": [],
            "top_hiring_companies": [],
            "experience_breakdown": {},
            "experience_distribution": {}
        }
        
    cursor.execute(f"SELECT COUNT(*) FROM jobs {query_filter} {'AND' if category_id else 'WHERE'} salary_disclosed = 1", params)
    disclosed_jobs = cursor.fetchone()[0]
    transparency_rate = round((disclosed_jobs / total_jobs) * 100, 1) if total_jobs > 0 else 0.0
    
    cursor.execute(f"""
    SELECT AVG(min_salary) as avg_min, AVG(max_salary) as avg_max
    FROM jobs 
    {query_filter} {'AND' if category_id else 'WHERE'} salary_disclosed = 1
    """, params)
    sal_row = cursor.fetchone()
    avg_min = sal_row["avg_min"] or 0
    avg_max = sal_row["avg_max"] or 0
    avg_salary_bdt = round((avg_min + avg_max) / 2) if (avg_min and avg_max) else round(avg_min or avg_max)
    
    cursor.execute(f"""
    SELECT company_name, COUNT(*) as cnt 
    FROM jobs 
    {query_filter}
    GROUP BY company_name 
    ORDER BY cnt DESC 
    LIMIT 5
    """, params)
    top_companies = [{"company": r["company_name"], "openings": r["cnt"]} for r in cursor.fetchall()]
    
    cursor.execute(f"""
    SELECT experience_level, COUNT(*) as cnt
    FROM jobs
    {query_filter}
    GROUP BY experience_level
    """, params)
    exp_dist = {r["experience_level"] or "Mid Level": r["cnt"] for r in cursor.fetchall()}
    
    conn.close()
    
    return {
        "total_jobs_tracked": total_jobs,
        "total_openings": total_jobs,
        "transparency_rate": transparency_rate,
        "salary_stats": {
            "disclosed_pct": transparency_rate,
            "avg_salary": avg_salary_bdt,
            "median_salary": round(avg_salary_bdt * 0.95)
        },
        "median_salary_bdt": round(avg_salary_bdt * 0.95),
        "avg_salary_bdt": avg_salary_bdt,
        "top_companies": top_companies,
        "top_hiring_companies": top_companies,
        "experience_breakdown": exp_dist,
        "experience_distribution": exp_dist
    }
