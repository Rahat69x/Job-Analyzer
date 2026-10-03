"""
Unit and integration tests for Universal Job Application Resolver,
ATS Detection, Redirect Unwrapping, and Bangladesh Platform Exclusion.
"""

import pytest
from fastapi.testclient import TestClient
from app import app
from core.apply_resolver import JobApplicationResolver, apply_resolver
from core.db import init_db, upsert_jobs
from core.models import NormalizedJob, CompanyInfo, SalaryInfo

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

# ==================== ATS SYSTEM DETECTION TESTS ====================

def test_greenhouse_ats_detection():
    resolver = JobApplicationResolver()
    url = "https://boards.greenhouse.io/anthropic/jobs/4028192001?gh_jid=4028192001"
    res = resolver.resolve_application(
        job_id="test_gh_1",
        apply_url=url,
        job_title="Senior AI Research Engineer",
        company_name="Anthropic",
        location="San Francisco, CA"
    )
    assert res.application_type == "EXTERNAL_ATS"
    assert res.platform_name == "Greenhouse"
    assert res.auth_requirement == "NONE"
    assert "boards.greenhouse.io" in res.canonical_url
    assert "gh_jid=4028192001" in res.canonical_url
    assert res.is_bangladesh_excluded is True
    assert len(res.steps) >= 3

def test_workday_ats_detection_with_auth_requirement():
    resolver = JobApplicationResolver()
    url = "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/USA-CA-Santa-Clara/Deep-Learning-Software-Engineer_JR198200"
    res = resolver.resolve_application(
        job_id="test_wd_1",
        apply_url=url,
        job_title="Deep Learning Software Engineer",
        company_name="NVIDIA",
        location="Santa Clara, CA"
    )
    assert res.application_type == "EXTERNAL_ATS"
    assert res.platform_name == "Workday"
    assert res.auth_requirement == "AUTH_REQUIRED"
    assert "Workday requires candidate account sign-in" in res.auth_details
    assert any("Sign in" in s or "account" in s.lower() for s in res.steps)

def test_lever_ats_detection():
    resolver = JobApplicationResolver()
    url = "https://jobs.lever.co/spotify/e2b34a6c-7f89-4d0a-9d2a-112233445566"
    res = resolver.resolve_application(
        job_id="test_lever_1",
        apply_url=url,
        job_title="Backend Engineer",
        company_name="Spotify",
        location="Stockholm, Sweden"
    )
    assert res.application_type == "EXTERNAL_ATS"
    assert res.platform_name == "Lever"
    assert res.auth_requirement == "NONE"

def test_smartrecruiters_and_ashby():
    resolver = JobApplicationResolver()
    # SmartRecruiters
    sr_res = resolver.resolve_application(
        job_id="test_sr_1",
        apply_url="https://jobs.smartrecruiters.com/Visa/743999991234567-software-engineer",
        job_title="Software Engineer",
        company_name="Visa"
    )
    assert sr_res.application_type == "EXTERNAL_ATS"
    assert sr_res.platform_name == "SmartRecruiters"

    # Ashby
    ashby_res = resolver.resolve_application(
        job_id="test_ashby_1",
        apply_url="https://jobs.ashbyhq.com/openai/1a2b3c4d-5e6f-7a8b",
        job_title="Research Scientist",
        company_name="OpenAI"
    )
    assert ashby_res.application_type == "EXTERNAL_ATS"
    assert ashby_res.platform_name == "Ashby"

# ==================== GLOBAL JOB BOARD DETECTION TESTS ====================

def test_linkedin_jobs_detection():
    resolver = JobApplicationResolver()
    url = "https://www.linkedin.com/jobs/view/3920192840/?refId=abcd1234&trackingId=xyz"
    res = resolver.resolve_application(
        job_id="test_li_1",
        apply_url=url,
        job_title="Machine Learning Lead",
        company_name="Meta"
    )
    assert res.application_type == "DIRECT_JOB_BOARD"
    assert res.platform_name == "LinkedIn"
    assert res.auth_requirement == "AUTH_REQUIRED"
    # Tracking parameters stripped in canonical URL
    assert "refId" not in res.canonical_url
    assert "trackingId" not in res.canonical_url

def test_indeed_and_wellfound_detection():
    resolver = JobApplicationResolver()
    # Indeed
    indeed_res = resolver.resolve_application(
        job_id="test_indeed_1",
        apply_url="https://www.indeed.com/viewjob?jk=abcdef0123456789",
        job_title="Data Scientist",
        company_name="Uber"
    )
    assert indeed_res.application_type == "DIRECT_JOB_BOARD"
    assert indeed_res.platform_name == "Indeed"

    # Wellfound
    wf_res = resolver.resolve_application(
        job_id="test_wf_1",
        apply_url="https://wellfound.com/jobs/2901234-senior-full-stack-engineer",
        job_title="Senior Full Stack Engineer",
        company_name="YC Startup"
    )
    assert wf_res.application_type == "DIRECT_JOB_BOARD"
    assert wf_res.platform_name == "Wellfound"
    assert wf_res.auth_requirement == "AUTH_REQUIRED"

# ==================== QUICK APPLY / EMAIL APPLICATION ====================

def test_quick_email_apply():
    resolver = JobApplicationResolver()
    url = "mailto:careers@techscale.io?subject=Application"
    res = resolver.resolve_application(
        job_id="test_mail_1",
        apply_url=url,
        job_title="DevOps Lead",
        company_name="TechScale"
    )
    assert res.application_type == "QUICK_APPLY"
    assert res.platform_name == "Direct Email Apply"
    assert "careers@techscale.io" in res.auth_details
    assert res.canonical_url.startswith("mailto:")

# ==================== DYNAMIC & EXTENSIBLE HEURISTICS ====================

def test_dynamic_international_ats_subdomain_heuristic():
    resolver = JobApplicationResolver()
    # Arbitrary company ATS not in the fixed list
    url = "https://careers.stripe.com/jobs/5918234-systems-engineer"
    res = resolver.resolve_application(
        job_id="test_stripe_1",
        apply_url=url,
        job_title="Systems Engineer",
        company_name="Stripe"
    )
    assert res.application_type == "EXTERNAL_ATS"
    assert "Careers (Applicant Tracking System)" in res.platform_name
    assert res.auth_requirement == "MANUAL_STEP_REQUIRED"

def test_generic_company_career_portal():
    resolver = JobApplicationResolver()
    url = "https://acme-global.org/about-us/careers"
    res = resolver.resolve_application(
        job_id="test_acme_1",
        apply_url=url,
        job_title="Product Manager",
        company_name="Acme Global"
    )
    assert res.application_type == "COMPANY_CAREER_SITE"
    assert res.platform_name == "Acme Global Official Portal"

# ==================== REDIRECT UNWRAPPING & TELEMETRY STRIPPING ====================

def test_unwrap_nested_redirect():
    resolver = JobApplicationResolver()
    # Aggregator wrapping a direct greenhouse URL with telemetry
    nested_url = (
        "https://aggregator.net/click?redirectUrl="
        "https%3A%2F%2Fboards.greenhouse.io%2Ffigma%2Fjobs%2F987654%3Fgh_jid%3D987654%26utm_source%3Daggregator%26utm_medium%3Dcpc"
    )
    unwrapped = resolver.unwrap_redirect(nested_url)
    assert "boards.greenhouse.io/figma/jobs/987654" in unwrapped
    assert "gh_jid=987654" in unwrapped
    assert "utm_source" not in unwrapped
    assert "utm_medium" not in unwrapped

# ==================== STRICT BDJOBS EXCLUSION RULE ====================

def test_bdjobs_exclusion_and_canonical_reroute():
    resolver = JobApplicationResolver()
    # International job mistakenly pointing to BDJobs
    bd_url = "https://jobs.bdjobs.com/jobdetails.asp?id=1234567"
    res = resolver.resolve_application(
        job_id="test_bd_leak_1",
        apply_url=bd_url,
        job_title="Principal AI Scientist",
        company_name="DeepMind",
        location="London, UK",
        job_source="BDJobs"
    )
    assert res.is_bangladesh_excluded is True
    assert "bdjobs.com" not in res.canonical_url
    assert "google.com/search" in res.canonical_url
    assert "DeepMind" in res.canonical_url
    assert res.notice is not None
    assert "BDJobs" in res.notice
    assert "excluded" in res.notice.lower()

def test_is_bangladesh_url_detector():
    resolver = JobApplicationResolver()
    assert resolver.is_bangladesh_url("https://jobs.bdjobs.com/jobdetails.asp?id=1") is True
    assert resolver.is_bangladesh_url("https://mybdjobs.bdjobs.com/applicant") is True
    assert resolver.is_bangladesh_url("https://corporate3.bdjobs.com/cv") is True
    assert resolver.is_bangladesh_url("https://www.chakri.com/jobs/123") is True
    assert resolver.is_bangladesh_url("https://boards.greenhouse.io/stripe/jobs/1") is False
    assert resolver.is_bangladesh_url("https://www.linkedin.com/jobs/view/1") is False

# ==================== PRESERVED PAYLOAD TESTS ====================

def test_preserved_payload_generation():
    resolver = JobApplicationResolver()
    res = resolver.resolve_application(
        job_id="test_payload_1",
        apply_url="https://jobs.lever.co/databricks/123",
        job_title="Data Platform Engineer",
        company_name="Databricks",
        location="Amsterdam, Netherlands",
        skills=["Python", "Apache Spark", "Kubernetes", "SQL"]
    )
    payload = res.preserved_payload
    assert payload["job_id"] == "test_payload_1"
    assert payload["job_title"] == "Data Platform Engineer"
    assert payload["company_name"] == "Databricks"
    assert "Python, Apache Spark" in payload["tailored_pitch"]
    assert "Dear Hiring Team at Databricks" in payload["tailored_pitch"]
    assert payload["skills"] == ["Python", "Apache Spark", "Kubernetes", "SQL"]

# ==================== API ENDPOINT TESTS ====================

def test_api_resolve_application_endpoint():
    req_body = {
        "job_id": "test_api_job_1",
        "apply_url": "https://boards.greenhouse.io/figma/jobs/123456",
        "title": "Senior Product Designer",
        "company": "Figma",
        "location": "Remote, Global",
        "skills": ["Figma", "UI/UX", "Design Systems"],
        "source": "Global"
    }
    response = client.post("/api/apply/resolve", json=req_body)
    assert response.status_code == 200
    data = response.json()
    assert data["application_type"] == "EXTERNAL_ATS"
    assert data["platform_name"] == "Greenhouse"
    assert data["is_bangladesh_excluded"] is True
    assert data["preserved_payload"]["company_name"] == "Figma"

def test_api_resolve_bdjobs_reroute_endpoint():
    req_body = {
        "job_id": "test_api_bd_1",
        "apply_url": "https://jobs.bdjobs.com/jobdetails.asp?id=999",
        "title": "Cloud Architect",
        "company": "Amazon Web Services",
        "location": "Global Remote",
        "skills": ["AWS", "Terraform", "Python"],
        "source": "BDJobs"
    }
    response = client.post("/api/apply/resolve", json=req_body)
    assert response.status_code == 200
    data = response.json()
    assert "bdjobs.com" not in data["canonical_url"]
    assert data["notice"] is not None
    assert "BDJobs" in data["notice"]

def test_api_get_job_application_flow_catalog():
    # Insert a test job into DB
    job = NormalizedJob(
        id="catalog_test_job_1",
        source="Global",
        external_id="ext_cat_1",
        title="Senior Security Architect",
        company=CompanyInfo(name="Cloudflare", website="https://cloudflare.com"),
        country="United States",
        location="Remote, Worldwide",
        is_remote=True,
        category_id=1,
        category_name="Engineering",
        salary=SalaryInfo(min=180000, max=220000, currency="USD", period="yearly", raw_text="$180,000 - $220,000/yr"),
        skills_required=["Cybersecurity", "Zero Trust", "Cloudflare Workers"],
        apply_url="https://boards.greenhouse.io/cloudflare/jobs/889900"
    )
    upsert_jobs([job])

    response = client.get(f"/api/apply/job/{job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["application_type"] == "EXTERNAL_ATS"
    assert data["platform_name"] == "Greenhouse"
    assert "cloudflare" in data["canonical_url"]
    assert "Zero Trust" in data["preserved_payload"]["tailored_pitch"]

def test_api_get_job_application_flow_not_found():
    response = client.get("/api/apply/job/non_existent_job_id_xyz")
    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]
