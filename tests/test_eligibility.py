import pytest
from core.normalizer import (
    parse_salary, parse_experience, classify_experience_level,
    normalize_location, classify_remote_policy, evaluate_candidate_eligibility
)
from core.models import RemoteEligibility

def test_remote_india_only_ineligible_for_bangladesh():
    workplace_type, remote_eligibility = classify_remote_policy(
        title="Senior Backend Engineer (Remote - India only)",
        location="Bangalore, India",
        context="We are looking for Python developers residing in India. Remote - India only."
    )
    assert workplace_type == "Remote"
    assert "India" in remote_eligibility.allowed_countries
    
    # Candidate from Bangladesh
    eligibility_bd = evaluate_candidate_eligibility(
        job_country="India",
        workplace_type=workplace_type,
        remote_eligibility=remote_eligibility,
        candidate_origin_country="Bangladesh"
    )
    assert eligibility_bd.is_eligible is False
    assert eligibility_bd.status == "ineligible"
    assert "India" in eligibility_bd.reason

    # Candidate from India
    eligibility_in = evaluate_candidate_eligibility(
        job_country="India",
        workplace_type=workplace_type,
        remote_eligibility=remote_eligibility,
        candidate_origin_country="India"
    )
    assert eligibility_in.is_eligible is True
    assert eligibility_in.status == "eligible"

def test_worldwide_remote_eligible_for_all():
    workplace_type, remote_eligibility = classify_remote_policy(
        title="Full Stack Software Engineer",
        location="Worldwide Remote",
        context="This is a 100% remote (worldwide) position. Work from anywhere."
    )
    assert workplace_type == "Remote"
    assert remote_eligibility.policy == "Worldwide"
    
    eligibility = evaluate_candidate_eligibility(
        job_country="United States",
        workplace_type=workplace_type,
        remote_eligibility=remote_eligibility,
        candidate_origin_country="Bangladesh"
    )
    assert eligibility.is_eligible is True
    assert eligibility.status == "eligible"
    assert "Worldwide remote" in eligibility.reason

def test_visa_sponsorship_eligible_for_international():
    workplace_type, remote_eligibility = classify_remote_policy(
        title="Site Reliability Engineer",
        location="Munich, Germany",
        context="Full-time role in Munich. Visa sponsorship and relocation assistance provided."
    )
    assert workplace_type == "On-site"
    assert remote_eligibility.visa_sponsorship is True
    
    eligibility = evaluate_candidate_eligibility(
        job_country="Germany",
        workplace_type=workplace_type,
        remote_eligibility=remote_eligibility,
        candidate_origin_country="Bangladesh"
    )
    assert eligibility.is_eligible is True
    assert eligibility.status == "eligible"
    assert "Visa Sponsorship" in eligibility.reason

def test_currency_conversion_usd_and_bdt():
    salary = parse_salary("$120,000 - $160,000 (Annual)")
    assert salary.disclosed is True
    assert salary.currency == "USD"
    assert salary.min_salary == 120000.0
    assert salary.max_salary == 160000.0
    assert salary.salary_usd_min == 120000.0
    assert salary.salary_bdt_min == 120000.0 * 120.0
    assert salary.period == "Annual"

def test_location_normalization_global():
    city, country, region = normalize_location("San Francisco, CA, USA")
    assert country == "United States"
    assert region == "North America"

    city2, country2, region2 = normalize_location("Tokyo, Japan")
    assert country2 == "Japan"
    assert region2 == "Asia-Pacific"

    city3, country3, region3 = normalize_location("London, United Kingdom")
    assert country3 == "United Kingdom"
    assert region3 == "Europe"
