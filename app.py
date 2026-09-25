import os
import json
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from core.models import UserProfile, ScoringWeights, ScoredJob, NormalizedJob
from core.db import (
    init_db, upsert_jobs, set_job_status, get_tracked_jobs, get_market_analytics,
    search_global_jobs, get_country_explorer_stats, get_connection, row_to_normalized_job
)
from core.normalizer import EXCHANGE_RATES_TO_USD, evaluate_candidate_eligibility
from core.timezone_engine import feasibility_engine, FlexibilityTier
from ingestion.bdjobs_client import BDJobsClient
from ingestion.public_portals import fetch_sample_partner_jobs
from ingestion.linkedin_parser import parse_pasted_linkedin_text
from ingestion.aggregator import global_aggregator
from scoring.scorer import JobScorer

app = FastAPI(title="Job Analyzer - Global Job Discovery & Remote Job Platform", version="3.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TAXONOMY_PATH = os.path.join(BASE_DIR, "data", "taxonomy.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")
ALERTS_PATH = os.path.join(BASE_DIR, "data", "alerts.json")
JOB_ROLES_PATH = os.path.join(BASE_DIR, "data", "job_roles.json")

# Initialize database, client & scorer
init_db()
bdjobs_client = BDJobsClient(TAXONOMY_PATH)
scorer = JobScorer()

# Pre-populate global catalog in DB on boot
try:
    initial_jobs = global_aggregator.fetch_all(limit_per_source=15)
    if initial_jobs:
        upsert_jobs(initial_jobs)
except Exception as e:
    pass

class LinkedInIngestRequest(BaseModel):
    text: str
    target_category_id: int = 8
    user_skills: List[str] = []
    user_experience: float = 3.0

class TrackJobRequest(BaseModel):
    job_id: str
    status: str = "Saved" # Saved, Planning to Apply, Applied, Interview, Technical Test, Offer, Rejected, Withdrawn
    notes: str = ""
    score: float = 0.0
    application_date: Optional[str] = None
    interview_date: Optional[str] = None
    recruiter_info: str = ""
    followup_date: Optional[str] = None

class CreateAlertRequest(BaseModel):
    title: str
    query: str = ""
    country: str = "Worldwide"
    remote_only: bool = True
    international_only: bool = False
    experience_level: str = "Any"

class TimezoneFeasibilityRequest(BaseModel):
    candidate_timezone: str = "Asia/Dhaka"
    candidate_utc_offset: Optional[str] = None
    preferred_working_window: List[str] = ["09:00", "18:00"]
    flexibility_tier: str = "MODERATE_EVENING" # STRICT_DAYLIGHT, MODERATE_EVENING, NIGHT_OWL
    employer_timezone: str = "America/New_York"
    employer_core_window: List[str] = ["09:00", "17:00"]
    required_overlap_hours: float = 4.0
    job_description_text: Optional[str] = None

# ==================== TIME-ZONE FEASIBILITY ENDPOINTS ====================

@app.post("/api/feasibility/timezone")
def evaluate_timezone_feasibility(payload: TimezoneFeasibilityRequest):
    """
    Evaluates circadian feasibility, time-zone offset math, and overlap windows.
    Adheres strictly to the requested JSON schema.
    """
    try:
        flex_tier = FlexibilityTier(payload.flexibility_tier)
    except Exception:
        flex_tier = FlexibilityTier.MODERATE_EVENING

    cand_win = (payload.preferred_working_window[0], payload.preferred_working_window[1]) if len(payload.preferred_working_window) >= 2 else ("09:00", "18:00")
    emp_win = (payload.employer_core_window[0], payload.employer_core_window[1]) if len(payload.employer_core_window) >= 2 else ("09:00", "17:00")

    return feasibility_engine.evaluate(
        candidate_timezone=payload.candidate_timezone,
        candidate_preferred_window=cand_win,
        flexibility_tier=flex_tier,
        employer_timezone=payload.employer_timezone,
        employer_core_window=emp_win,
        required_overlap_hours=payload.required_overlap_hours,
        job_description_text=payload.job_description_text
    )

@app.get("/api/feasibility/job/{job_id}")
def evaluate_job_timezone_feasibility(
    job_id: str,
    candidate_timezone: str = Query("Asia/Dhaka"),
    flexibility_tier: str = Query("MODERATE_EVENING"),
    required_overlap: float = Query(4.0)
):
    """Evaluate time-zone feasibility for a specific job in the catalog against candidate timezone."""
    init_db()
    conn = get_connection()
    row = conn.cursor().execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    job = row_to_normalized_job(row, "Bangladesh")
    
    country_to_tz = {
        "United States": "America/New_York",
        "Germany": "Europe/Berlin",
        "United Kingdom": "Europe/London",
        "India": "Asia/Kolkata",
        "Singapore": "Asia/Singapore",
        "Japan": "Asia/Tokyo",
        "Australia": "Australia/Sydney",
        "Canada": "America/Toronto",
        "United Arab Emirates": "Asia/Dubai",
        "Bangladesh": "Asia/Dhaka"
    }
    emp_tz = country_to_tz.get(job.country, "America/New_York")
    if job.workplace_type == "Remote" and job.country == "Bangladesh":
        # Check if job context mentions US/UK hours
        ctx_lower = f"{job.title} {job.job_context}".lower()
        if "us" in ctx_lower or "night shift" in ctx_lower or "est" in ctx_lower or "edt" in ctx_lower:
            emp_tz = "America/New_York"
    
    try:
        flex_enum = FlexibilityTier(flexibility_tier)
    except Exception:
        flex_enum = FlexibilityTier.MODERATE_EVENING

    return feasibility_engine.evaluate(
        candidate_timezone=candidate_timezone,
        flexibility_tier=flex_enum,
        employer_timezone=emp_tz,
        required_overlap_hours=required_overlap,
        job_description_text=f"{job.title} {job.job_context}"
    )

# ==================== GLOBAL DISCOVERY ENDPOINTS ====================

@app.get("/api/global/search")
def search_jobs(
    q: Optional[str] = Query(None, description="Keywords: title, skills, or company"),
    category_id: Optional[int] = Query(None, description="BDJobs Category ID"),
    country: Optional[str] = Query(None, description="Target country e.g. Bangladesh, Germany, United States, India"),
    workplace_type: Optional[str] = Query(None, description="Remote, Hybrid, On-site"),
    remote_policy: Optional[str] = Query(None, description="Worldwide, Regional, Country-Restricted"),
    experience_level: Optional[str] = Query(None, description="Internship, Entry Level, Junior, Mid Level, Senior, Lead"),
    employment_type: Optional[str] = Query(None, description="Full-time, Part-time, Contract, Freelance, Internship"),
    visa_sponsorship: Optional[bool] = Query(None, description="True if visa sponsorship required"),
    candidate_origin: str = Query("Bangladesh", description="Applicant home country"),
    skills: Optional[str] = Query(None, description="Comma-separated skills"),
    experience: float = Query(3.0, description="Applicant experience years"),
    refresh_live: bool = Query(False, description="Force refresh from live sources"),
    limit: int = Query(50, description="Results limit")
):
    """
    Comprehensive global multi-criteria search.
    Intelligently scores and evaluates candidate eligibility.
    """
    results = search_global_jobs(
        q=q,
        category_id=category_id,
        country=country,
        workplace_type=workplace_type,
        remote_policy=remote_policy,
        experience_level=experience_level,
        employment_type=employment_type,
        visa_sponsorship=visa_sponsorship,
        candidate_origin=candidate_origin,
        limit=limit
    )

    # If category_id requested and DB has few results, or refresh_live is requested: fetch from BDJobs API
    if category_id and (len(results) < 5 or refresh_live):
        try:
            live_cat_jobs = bdjobs_client.fetch_jobs_by_category(category_id, page=1, rpp=50)
            if live_cat_jobs:
                upsert_jobs(live_cat_jobs)
                results = search_global_jobs(
                    q=q,
                    category_id=category_id,
                    country=country,
                    workplace_type=workplace_type,
                    remote_policy=remote_policy,
                    experience_level=experience_level,
                    employment_type=employment_type,
                    visa_sponsorship=visa_sponsorship,
                    candidate_origin=candidate_origin,
                    limit=limit
                )
        except Exception as e:
            print(f"[SearchAPI] Error fetching live category: {e}")
    # If general query has insufficient results, fetch live from aggregator
    elif q and len(results) < 5:
        try:
            live_jobs = global_aggregator.fetch_all(query=q, country=country, limit_per_source=15)
            if live_jobs:
                upsert_jobs(live_jobs)
                results = search_global_jobs(
                    q=q,
                    category_id=category_id,
                    country=country,
                    workplace_type=workplace_type,
                    remote_policy=remote_policy,
                    experience_level=experience_level,
                    employment_type=employment_type,
                    visa_sponsorship=visa_sponsorship,
                    candidate_origin=candidate_origin,
                    limit=limit
                )
        except Exception:
            pass

    # Score and rank against candidate profile
    skills_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else []
    profile = UserProfile(
        candidate_origin_country=candidate_origin,
        target_category_ids=[category_id] if category_id else [],
        skills=skills_list,
        experience_years=experience,
        preferred_countries=[country] if country and country != "Worldwide" else [],
        preferred_workplace_type=[workplace_type] if workplace_type else ["Remote", "Hybrid", "On-site"]
    )

    ranked = scorer.rank_jobs(results, profile)
    return {
        "total": len(ranked),
        "query": q,
        "category_id": category_id,
        "country": country or "All Countries",
        "candidate_origin": candidate_origin,
        "results": [r.model_dump() for r in ranked]
    }

@app.get("/api/global/remote")
def get_remote_jobs(
    region: Optional[str] = Query("Worldwide", description="Worldwide, Asia-Pacific, Europe, North America"),
    candidate_origin: str = Query("Bangladesh", description="Applicant home country"),
    q: Optional[str] = Query(None, description="Keywords"),
    limit: int = Query(50)
):
    """Dedicated Remote-First endpoint delivering international and regional remote opportunities."""
    all_remote = search_global_jobs(
        q=q,
        workplace_type="Remote",
        candidate_origin=candidate_origin,
        limit=limit
    )

    if region and region != "All":
        if region == "Worldwide":
            all_remote = [j for j in all_remote if j.remote_eligibility.policy == "Worldwide"]
        elif region == "Bangladesh Eligible":
            all_remote = [j for j in all_remote if j.candidate_eligibility.is_eligible]
        else:
            all_remote = [j for j in all_remote if region in j.remote_eligibility.allowed_regions or j.remote_eligibility.policy == "Worldwide"]

    profile = UserProfile(
        candidate_origin_country=candidate_origin,
        preferred_workplace_type=["Remote"]
    )
    ranked = scorer.rank_jobs(all_remote, profile)
    return {
        "total": len(ranked),
        "region_filter": region,
        "candidate_origin": candidate_origin,
        "results": [r.model_dump() for r in ranked]
    }

@app.get("/api/global/countries")
def get_country_explorer():
    """Country Explorer directory aggregating metrics for major worldwide job markets."""
    stats = get_country_explorer_stats()
    return {"countries": stats}

@app.get("/api/global/recommendations")
def get_recommendations(
    skills: str = Query("Python, React", description="Candidate skills"),
    experience: float = Query(2.0, description="Years of experience"),
    education: str = Query("CSE Student", description="Education level"),
    candidate_origin: str = Query("Bangladesh", description="Candidate home country"),
    remote_preferred: bool = Query(True)
):
    """Personalized job recommendations tailoring student, entry-level, or senior positions."""
    skills_list = [s.strip() for s in skills.split(",") if s.strip()]
    
    # Query database
    all_jobs = search_global_jobs(candidate_origin=candidate_origin, limit=60)
    
    profile = UserProfile(
        candidate_origin_country=candidate_origin,
        skills=skills_list,
        experience_years=experience,
        education_level=education,
        preferred_workplace_type=["Remote", "Hybrid", "On-site"] if not remote_preferred else ["Remote"]
    )
    
    ranked = scorer.rank_jobs(all_jobs, profile)
    
    # Boost student / internship opportunities if experience is low or education mentions student
    is_student_or_fresher = experience <= 1.0 or any(k in education.lower() for k in ["student", "fresh", "beginner", "intern"])
    if is_student_or_fresher:
        ranked.sort(key=lambda x: (
            1 if x.job.experience_level in ["Internship", "Entry Level"] else 0,
            x.score.final_score
        ), reverse=True)

    return {
        "candidate_profile": {
            "origin": candidate_origin,
            "skills": skills_list,
            "experience": experience,
            "education": education
        },
        "total_recommendations": len(ranked),
        "results": [r.model_dump() for r in ranked[:25]]
    }

@app.get("/api/global/tracker")
def list_global_tracked_jobs():
    """Retrieve all jobs across the 8 application pipeline stages."""
    return {"tracked_jobs": get_tracked_jobs()}

@app.post("/api/global/tracker")
def update_global_tracked_job(payload: TrackJobRequest):
    """Update pipeline stage, notes, dates, and recruiter contact for a job."""
    set_job_status(
        job_id=payload.job_id,
        status=payload.status,
        notes=payload.notes,
        score=payload.score,
        application_date=payload.application_date,
        interview_date=payload.interview_date,
        recruiter_info=payload.recruiter_info,
        followup_date=payload.followup_date
    )
    return {"status": "success", "job_id": payload.job_id, "new_status": payload.status}

@app.get("/api/global/alerts")
def get_global_alerts():
    """Retrieve active multi-criteria alerts."""
    if os.path.exists(ALERTS_PATH):
        try:
            with open(ALERTS_PATH, "r", encoding="utf-8") as f:
                return {"alerts": json.load(f)}
        except Exception:
            pass
    # Default template alerts
    return {"alerts": [
        {"title": "Remote Java Jobs - International", "query": "Java", "country": "Worldwide", "remote_only": True, "created_at": "Today"},
        {"title": "Bangladesh CSE Internships", "query": "Intern", "country": "Bangladesh", "remote_only": False, "created_at": "Yesterday"},
        {"title": "Germany Software Engineering Jobs", "query": "Software Engineer", "country": "Germany", "remote_only": False, "created_at": "3 days ago"},
        {"title": "Worldwide Remote SWE", "query": "Software Engineer", "country": "Worldwide", "remote_only": True, "created_at": "1 week ago"}
    ]}

@app.post("/api/global/alerts")
def create_global_alert(payload: CreateAlertRequest):
    """Save a new user-defined job alert."""
    alerts = []
    if os.path.exists(ALERTS_PATH):
        try:
            with open(ALERTS_PATH, "r", encoding="utf-8") as f:
                alerts = json.load(f)
        except Exception:
            alerts = []
    
    new_alert = payload.model_dump()
    new_alert["created_at"] = "Just now"
    alerts.insert(0, new_alert)
    
    with open(ALERTS_PATH, "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2)
        
    return {"status": "success", "alert": new_alert}

@app.get("/api/global/currencies")
def get_currencies():
    """Exchange rates and conversion table relative to USD and BDT."""
    return {
        "base_currency": "USD",
        "rates": EXCHANGE_RATES_TO_USD,
        "bdt_per_usd": 120.0
    }

# ==================== LEGACY & CORE ENDPOINTS ====================

@app.get("/api/job-roles")
def get_job_roles(q: Optional[str] = None):
    """Return structured job roles and skills for intelligent autocomplete."""
    if os.path.exists(JOB_ROLES_PATH):
        with open(JOB_ROLES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if q:
                query = q.strip().lower()
                data = [item for item in data if query in item['title'].lower() or query in item.get('category', '').lower()]
            return {"roles": data}
    return {"roles": []}

@app.get("/api/taxonomy")
def get_taxonomy():
    """Return all 64 verified categories and industries."""
    if os.path.exists(TAXONOMY_PATH):
        with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"categories": [], "industries": []}

@app.get("/api/jobs")
def get_ranked_jobs(
    category_id: int = Query(8, description="BDJobs Category ID"),
    skills: str = Query("", description="Comma-separated skills"),
    experience: float = Query(3.0, description="Years of experience"),
    w_recency: float = Query(0.20, description="Weight for recency"),
    w_salary: float = Query(0.30, description="Weight for salary"),
    w_profile: float = Query(0.35, description="Weight for profile match"),
    w_employer: float = Query(0.15, description="Weight for employer credibility"),
    include_partners: bool = Query(True, description="Include cross-portal public listings")
):
    """Fetch, normalize, score, and rank jobs for a specified category."""
    cat_info = bdjobs_client.get_category_info(category_id)
    skills_list = [s.strip() for s in skills.split(",") if s.strip()]
    
    profile = UserProfile(
        target_category_ids=[category_id],
        skills=skills_list,
        experience_years=experience
    )
    
    custom_scorer = JobScorer(ScoringWeights(
        w_recency=w_recency,
        w_salary=w_salary,
        w_profile=w_profile,
        w_employer=w_employer
    ))
    
    jobs = bdjobs_client.fetch_jobs_by_category(category_id, page=1, rpp=50)
    
    if include_partners:
        partner_jobs = fetch_sample_partner_jobs(category_id, cat_info['name'])
        jobs.extend(partner_jobs)
        
    if jobs:
        upsert_jobs(jobs)
    else:
        # Fallback to local cached DB jobs for this category so users never get 0
        jobs = search_global_jobs(category_id=category_id, limit=50)
        
    ranked = custom_scorer.rank_jobs(jobs, profile)
    
    return {
        "category": cat_info,
        "total_evaluated": len(ranked),
        "results": [r.model_dump() for r in ranked]
    }

@app.post("/api/ingest/linkedin")
def ingest_linkedin_job(payload: LinkedInIngestRequest):
    """ToS-Compliant structured paste parser for LinkedIn listings."""
    cat_info = bdjobs_client.get_category_info(payload.target_category_id)
    job = parse_pasted_linkedin_text(payload.text, payload.target_category_id, cat_info['name'])
    
    if not job:
        raise HTTPException(status_code=400, detail="Could not parse job from pasted text.")
        
    profile = UserProfile(
        target_category_ids=[payload.target_category_id],
        skills=payload.user_skills,
        experience_years=payload.user_experience
    )
    
    upsert_jobs([job])
    scored = scorer.score_job(job, profile)
    return scored.model_dump()

@app.get("/api/analytics")
def get_analytics(category_id: Optional[int] = None):
    return get_market_analytics(category_id)

@app.get("/api/tracker")
def list_tracked_jobs():
    return {"tracked_jobs": get_tracked_jobs()}

@app.post("/api/tracker")
def update_tracked_job(payload: TrackJobRequest):
    set_job_status(payload.job_id, payload.status, payload.notes, payload.score)
    return {"status": "success", "job_id": payload.job_id, "new_status": payload.status}

@app.get("/api/alerts")
def get_alerts():
    return get_global_alerts()

# Serve static files
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_dashboard():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"status": "Global Job Discovery API active."})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    uvicorn.run("app:app", host=host, port=port, reload=False if os.environ.get("PORT") else True)

