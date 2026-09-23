import pytest
from core.models import NormalizedJob, CompanyInfo
from core.deduplicator import deduplicate_jobs, compute_canonical_id

def test_deduplication_merges_sources():
    job1 = NormalizedJob(
        id="linkedin-101",
        source="LinkedIn",
        title="Senior Software Engineer",
        company=CompanyInfo(name="Google", tier="MNC", verified=True),
        country="United States",
        location="Mountain View, CA",
        apply_url="https://linkedin.com/jobs/view/101",
        source_reliability="major_board"
    )
    job2 = NormalizedJob(
        id="careers-102",
        source="CompanyCareerPage",
        title="Software Engineer, Senior",
        company=CompanyInfo(name="Google LLC", tier="MNC", verified=True),
        country="United States",
        location="Mountain View, CA, USA",
        apply_url="https://careers.google.com/jobs/results/102",
        source_reliability="official_career_page"
    )
    
    merged = deduplicate_jobs([job1, job2])
    assert len(merged) == 1
    winner = merged[0]
    # Official career page should win over LinkedIn
    assert winner.source == "CompanyCareerPage"
    assert "LinkedIn" in winner.alternate_sources
