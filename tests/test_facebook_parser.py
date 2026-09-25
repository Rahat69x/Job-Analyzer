import pytest
from ingestion.facebook_parser import parse_pasted_facebook_text

def test_parse_facebook_post_full():
    sample_text = """
    We are hiring!
    Position: Full Stack Engineer
    Company: Acme Tech Solutions
    Location: Dhaka, Bangladesh
    Salary: 100,000 - 150,000 BDT
    Experience: 4+ years
    Requirements:
    - Proficiency with Python, React, PostgreSQL
    - Strong problem solving skills
    How to apply:
    Send CV to jobs@acmetech.com or visit https://acmetech.com/careers
    """
    job = parse_pasted_facebook_text(sample_text)
    assert job is not None
    assert job.source == "Facebook"
    assert "Full Stack Engineer" in job.title
    assert "Acme Tech Solutions" in job.company.name
    assert "acmetech.com" in job.apply_url
    assert job.salary.min_salary == 100000

def test_parse_facebook_remote():
    sample_text = """
    Looking for a Remote Flutter Developer
    Company: Global Apps Inc
    Location: Remote (Worldwide)
    Salary: $2000 - $3500 / month
    Apply here: https://forms.gle/sampleform
    """
    job = parse_pasted_facebook_text(sample_text)
    assert job is not None
    assert "Flutter Developer" in job.title
    assert job.workplace_type == "Remote"
    assert job.remote_eligibility.policy == "Worldwide"
    assert "forms.gle" in job.apply_url

def test_parse_facebook_empty():
    job = parse_pasted_facebook_text("")
    assert job is None
