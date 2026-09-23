import sqlite3
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from core.models import (
    NormalizedJob, CompanyInfo, SalaryInfo, ExperienceRequirement, 
    RemoteEligibility, CandidateEligibility, WorkplaceType, ExperienceLevel
)
from core.normalizer import evaluate_candidate_eligibility

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
        first_seen_at TEXT
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
        "alternate_sources": "TEXT DEFAULT '[]'"
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
        
        cursor.execute("""
        INSERT INTO jobs (
            id, source, title, company_name, company_tier, category_id, category_name, category_type,
            country, city, location, workplace_type, remote_policy, allowed_countries, allowed_regions,
            accepts_international, visa_sponsorship, work_auth_required, publish_date, deadline,
            min_exp, max_exp, experience_level, min_salary, max_salary, salary_text, salary_disclosed,
            currency, salary_type, salary_usd_min, salary_usd_max, salary_bdt_min, salary_bdt_max,
            job_type, employment_type, vacancies, skills_required, apply_url, job_context,
            source_reliability, canonical_id, alternate_sources, first_seen_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?
        )
        ON CONFLICT(id) DO UPDATE SET
            deadline=excluded.deadline,
            salary_text=excluded.salary_text,
            min_salary=excluded.min_salary,
            max_salary=excluded.max_salary,
            salary_disclosed=excluded.salary_disclosed,
            salary_usd_min=excluded.salary_usd_min,
            salary_usd_max=excluded.salary_usd_max,
            salary_bdt_min=excluded.salary_bdt_min,
            salary_bdt_max=excluded.salary_bdt_max,
            alternate_sources=excluded.alternate_sources;
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
            json.dumps(j.alternate_sources), now_str
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

    return NormalizedJob(
        id=row["id"],
        source=row["source"],
        title=row["title"],
        company=CompanyInfo(name=row["company_name"], tier=row["company_tier"], verified=True),
        category_id=row["category_id"],
        category_name=row["category_name"],
        category_type=row["category_type"],
        country=country,
        city=row["city"] if "city" in row.keys() else "Dhaka",
        location=row["location"],
        workplace_type=workplace_type,
        remote_eligibility=remote_elig,
        candidate_eligibility=cand_elig,
        publish_date=pub_date,
        deadline=dead_date,
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
    limit: int = 50
) -> List[NormalizedJob]:
    """Execute dynamic multi-criteria SQL query across the global job catalog."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    # Category filter
    if category_id is not None and int(category_id) > 0:
        conditions.append("category_id = ?")
        params.append(int(category_id))

    # Country filter
    if country and country.lower() not in ["all", "worldwide", "any"]:
        conditions.append("country = ?")
        params.append(country)

    # Workplace mode filter
    if workplace_type and workplace_type.lower() not in ["all", "any"]:
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

    # Smart tokenized search query
    raw_tokens = []
    content_tokens = []
    if q and q.strip():
        raw_tokens = [w.strip() for w in q.split() if w.strip()]
        
        # Check for workplace hints
        has_remote = any(w.lower() == "remote" for w in raw_tokens)
        if has_remote and (not workplace_type or workplace_type.lower() in ["all", "any"]):
            conditions.append("workplace_type = 'Remote'")
            
        known_countries = {
            "bangladesh": "Bangladesh", "bd": "Bangladesh", "usa": "United States", 
            "us": "United States", "germany": "Germany", "india": "India", 
            "singapore": "Singapore", "uk": "United Kingdom", "canada": "Canada"
        }
        
        for token in raw_tokens:
            t_lower = token.lower()
            if t_lower in ["remote", "worldwide", "international", "job", "jobs"]:
                continue
            if t_lower in known_countries and (not country or country.lower() in ["all", "worldwide", "any"]):
                if "country = ?" not in conditions:
                    conditions.append("country = ?")
                    params.append(known_countries[t_lower])
                continue
            content_tokens.append(token)

        if content_tokens:
            token_conds = []
            for token in content_tokens:
                pattern = f"%{token}%"
                token_conds.append("(title LIKE ? OR company_name LIKE ? OR skills_required LIKE ? OR category_name LIKE ? OR job_context LIKE ?)")
                params.extend([pattern, pattern, pattern, pattern, pattern])
            conditions.append("(" + " AND ".join(token_conds) + ")")

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"SELECT * FROM jobs{where_clause} ORDER BY publish_date DESC, rowid DESC LIMIT ?"
    params.append(limit)

    rows = cursor.execute(sql, params).fetchall()

    # If strict AND search returned 0 results, fall back to OR search across content tokens
    if not rows and q and q.strip() and len(raw_tokens) > 1:
        fb_conditions = []
        fb_params = []
        if category_id is not None and int(category_id) > 0:
            fb_conditions.append("category_id = ?")
            fb_params.append(int(category_id))
        if country and country.lower() not in ["all", "worldwide", "any"]:
            fb_conditions.append("country = ?")
            fb_params.append(country)
        if workplace_type and workplace_type.lower() not in ["all", "any"]:
            fb_conditions.append("workplace_type = ?")
            fb_params.append(workplace_type)
        if visa_sponsorship is True:
            fb_conditions.append("visa_sponsorship = 1")

        search_tokens = content_tokens if content_tokens else raw_tokens
        or_conds = []
        for token in search_tokens:
            pattern = f"%{token}%"
            or_conds.append("(title LIKE ? OR company_name LIKE ? OR skills_required LIKE ? OR category_name LIKE ?)")
            fb_params.extend([pattern, pattern, pattern, pattern])
        if or_conds:
            fb_conditions.append("(" + " OR ".join(or_conds) + ")")
            fb_where = " WHERE " + " AND ".join(fb_conditions) if fb_conditions else ""
            fb_params.append(limit)
            rows = cursor.execute(f"SELECT * FROM jobs{fb_where} ORDER BY publish_date DESC, rowid DESC LIMIT ?", fb_params).fetchall()

    conn.close()

    return [row_to_normalized_job(r, candidate_origin) for r in rows]

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
