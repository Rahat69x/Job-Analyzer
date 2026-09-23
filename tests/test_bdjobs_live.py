import pytest
from ingestion.bdjobs_client import BDJobsClient

def test_bdjobs_live_it_category():
    client = BDJobsClient()
    jobs = client.fetch_jobs_by_category(category_id=8, page=1, rpp=10)
    assert len(jobs) > 0
    first = jobs[0]
    assert first.source == "BDJobs"
    assert first.category_id == 8
    assert first.category_name == "IT/Telecommunication"
    assert first.apply_url.startswith("https://jobs.bdjobs.com/")

def test_bdjobs_live_accounting_category():
    client = BDJobsClient()
    jobs = client.fetch_jobs_by_category(category_id=1, page=1, rpp=10)
    assert len(jobs) > 0
    first = jobs[0]
    assert first.category_id == 1
    assert first.category_name == "Accounting/Finance"
