"""
Acceptance Tests for 10 Required Searches
Runs the full end-to-end evaluation for all 10 required searches specified in prompt.
"""

import pytest
from core.db import search_global_jobs_with_diagnostics

ACCEPTANCE_SEARCHES = [
    {
        "num": 1,
        "name": "Cybersecurity Analyst — Worldwide — Remote",
        "q": "Cybersecurity Analyst",
        "country": "Worldwide",
        "workplace_type": "Remote"
    },
    {
        "num": 2,
        "name": "C++ Developer — Worldwide",
        "q": "C++ Developer",
        "country": "Worldwide",
        "workplace_type": None
    },
    {
        "num": 3,
        "name": "Java Developer — India",
        "q": "Java Developer",
        "country": "India",
        "workplace_type": None
    },
    {
        "num": 4,
        "name": "Software Engineer — USA",
        "q": "Software Engineer",
        "country": "United States",
        "workplace_type": None
    },
    {
        "num": 5,
        "name": "Machine Learning Engineer — Germany",
        "q": "Machine Learning Engineer",
        "country": "Germany",
        "workplace_type": None
    },
    {
        "num": 6,
        "name": "Data Analyst — Singapore",
        "q": "Data Analyst",
        "country": "Singapore",
        "workplace_type": None
    },
    {
        "num": 7,
        "name": "Frontend Developer — Remote Worldwide",
        "q": "Frontend Developer",
        "country": "Worldwide",
        "workplace_type": "Remote"
    },
    {
        "num": 8,
        "name": "Backend Developer — UK",
        "q": "Backend Developer",
        "country": "United Kingdom",
        "workplace_type": None
    },
    {
        "num": 9,
        "name": "AI Engineer — Worldwide",
        "q": "AI Engineer",
        "country": "Worldwide",
        "workplace_type": None
    },
    {
        "num": 10,
        "name": "Internship — Bangladesh",
        "q": "Internship",
        "country": "Bangladesh",
        "workplace_type": None
    }
]

@pytest.mark.parametrize("search_spec", ACCEPTANCE_SEARCHES, ids=[s["name"] for s in ACCEPTANCE_SEARCHES])
def test_acceptance_search(search_spec):
    jobs, diag = search_global_jobs_with_diagnostics(
        q=search_spec["q"],
        country=search_spec["country"],
        workplace_type=search_spec["workplace_type"],
        limit=500
    )
    assert len(jobs) > 0, f"Search {search_spec['name']} returned 0 jobs!"
    assert diag["sources_queried"] >= 30
    assert diag["sources_active"] >= 30
    assert diag["total_evaluated"] > 0
    # Every job must have a genuine application URL
    for j in jobs:
        assert j.apply_url and (j.apply_url.startswith("http://") or j.apply_url.startswith("https://"))
        assert j.title
        assert j.company.name
