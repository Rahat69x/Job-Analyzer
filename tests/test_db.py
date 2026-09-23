import pytest
from datetime import datetime, timezone
from core.models import NormalizedJob, CompanyInfo, SalaryInfo, ExperienceRequirement
from core.db import init_db, upsert_jobs, set_job_status, get_tracked_jobs, get_market_analytics

def test_database_initialization_and_upsert():
    init_db()
    now = datetime.now(timezone.utc)
    job = NormalizedJob(
        id="test-db-1",
        source="BDJobs",
        title="Senior Python Architect",
        company=CompanyInfo(name="Brain Station 23", tier="Conglomerate", verified=True),
        category_id=8,
        category_name="IT/Telecommunication",
        location="Dhaka",
        publish_date=now,
        experience=ExperienceRequirement(min_years=5.0, max_years=8.0),
        salary=SalaryInfo(disclosed=True, min_salary=120000, max_salary=180000, raw_text="Tk. 120,000 - 180,000"),
        apply_url="https://example.com/job/1"
    )
    
    upsert_jobs([job])
    
    # Track the job
    set_job_status("test-db-1", "Applied", notes="Submitted CV", score=0.92)
    tracked = get_tracked_jobs()
    
    found = [t for t in tracked if t['id'] == "test-db-1"]
    assert len(found) == 1
    assert found[0]['status'] == "Applied"
    assert found[0]['company_name'] == "Brain Station 23"
    assert found[0]['tracker_score'] == 0.92

def test_market_analytics_computation():
    init_db()
    analytics = get_market_analytics(category_id=8)
    assert "total_jobs_tracked" in analytics
    assert "salary_stats" in analytics
    assert "top_companies" in analytics
    assert "experience_breakdown" in analytics
