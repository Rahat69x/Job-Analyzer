import pytest
from datetime import datetime, timezone, timedelta
from core.models import NormalizedJob, CompanyInfo, SalaryInfo, ExperienceRequirement, UserProfile
from scoring.scorer import JobScorer

def test_recency_scoring_decay():
    scorer = JobScorer()
    now = datetime.now(timezone.utc)
    
    fresh_score = scorer.calculate_recency_score(now - timedelta(hours=2), now + timedelta(days=10))
    week_old_score = scorer.calculate_recency_score(now - timedelta(days=7), now + timedelta(days=10))
    month_old_score = scorer.calculate_recency_score(now - timedelta(days=30), now + timedelta(days=10))
    expired_score = scorer.calculate_recency_score(now - timedelta(days=2), now - timedelta(days=1))
    
    assert fresh_score > week_old_score
    assert week_old_score > month_old_score
    assert expired_score == 0.05

def test_salary_transparency_scoring():
    scorer = JobScorer()
    
    job_disclosed = NormalizedJob(
        id="test-1",
        title="Software Engineer",
        company=CompanyInfo(name="Test Co"),
        category_id=8,
        category_name="IT/Telecommunication",
        apply_url="https://example.com",
        salary=SalaryInfo(disclosed=True, min_salary=80000, max_salary=100000, raw_text="Tk. 80,000 - 100,000")
    )
    
    job_negotiable = NormalizedJob(
        id="test-2",
        title="Software Engineer",
        company=CompanyInfo(name="Test Co"),
        category_id=8,
        category_name="IT/Telecommunication",
        apply_url="https://example.com",
        salary=SalaryInfo(disclosed=False, raw_text="Negotiable")
    )
    
    score_disclosed = scorer.calculate_salary_score(job_disclosed)
    score_negotiable = scorer.calculate_salary_score(job_negotiable)
    
    assert score_disclosed > score_negotiable
    assert score_negotiable == 0.35
    assert score_disclosed >= 0.70

def test_profile_skill_match():
    scorer = JobScorer()
    profile = UserProfile(
        target_category_ids=[8],
        skills=["Python", "FastAPI", "PostgreSQL"],
        experience_years=4.0
    )
    
    job_matching = NormalizedJob(
        id="match-1",
        title="Senior Python & FastAPI Engineer",
        company=CompanyInfo(name="Brain Station 23"),
        category_id=8,
        category_name="IT/Telecommunication",
        experience=ExperienceRequirement(min_years=3.0, max_years=6.0),
        job_context="Requires strong Python, FastAPI, and PostgreSQL database optimization.",
        apply_url="https://example.com"
    )
    
    job_irrelevant = NormalizedJob(
        id="match-2",
        title="Java & Spring Boot Developer",
        company=CompanyInfo(name="Other Co"),
        category_id=8,
        category_name="IT/Telecommunication",
        experience=ExperienceRequirement(min_years=8.0, max_years=12.0),
        job_context="Requires 10 years of Java, Oracle, and enterprise Spring framework.",
        apply_url="https://example.com"
    )
    
    score_match = scorer.calculate_profile_match(job_matching, profile)
    score_irrelevant = scorer.calculate_profile_match(job_irrelevant, profile)
    
    assert score_match > score_irrelevant
