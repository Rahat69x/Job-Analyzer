"""
Unit & Integration Tests for Central Source Registry
Verifies structured metadata, 7 UI categories, Bdjobs isolation, and health summary telemetry.
"""

import pytest
from core.source_registry import source_registry, SOURCE_CATEGORIES, SOURCE_TYPES

def test_source_registry_initialization():
    sources = source_registry.get_all_sources()
    assert len(sources) >= 70  # At least 70 registered legitimate sources

def test_all_sources_have_valid_metadata():
    sources = source_registry.get_all_sources()
    for s in sources:
        assert s.id
        assert s.name
        assert s.type in SOURCE_TYPES
        assert s.category in SOURCE_CATEGORIES
        assert s.access_method in ["PUBLIC_API", "RSS_FEED", "ATS_CONNECTOR", "STRUCTURED_FEED", "DIRECT_CAREER"]
        assert s.status in ["ACTIVE", "PARTIAL", "UNAVAILABLE", "ERROR"]
        assert s.endpoint.startswith("http://") or s.endpoint.startswith("https://")
        assert s.jobs_found >= 0
        assert s.jobs_deduped >= 0

def test_bdjobs_strict_isolation():
    sources = source_registry.get_all_sources()
    bdjobs_sources = [s for s in sources if "bdjobs" in s.id.lower() or "bdjobs" in s.name.lower()]
    assert len(bdjobs_sources) >= 1
    for bds in bdjobs_sources:
        assert bds.category == "Bangladesh Sources"
        assert bds.region == "Bangladesh"
        assert bds.category != "Global Job Boards"
        assert bds.category != "Remote Job Boards"

def test_ats_platforms_registered():
    sources = source_registry.get_all_sources()
    ats_sources = [s for s in sources if s.type == "ATS"]
    assert len(ats_sources) >= 15
    parsers = set(s.parser for s in ats_sources)
    assert "greenhouse" in parsers
    assert "lever" in parsers
    assert "ashby" in parsers
    assert "smartrecruiters" in parsers

def test_health_summary_structure():
    summary = source_registry.get_health_summary()
    assert summary["total_registered_sources"] >= 70
    assert summary["active_sources_count"] >= 1
    assert "by_category" in summary
    for cat in SOURCE_CATEGORIES:
        assert cat in summary["by_category"]
        assert "total" in summary["by_category"][cat]
        assert "active" in summary["by_category"][cat]
        assert "jobs_found" in summary["by_category"][cat]

def test_source_status_update():
    test_src = "arbeitnow"
    source_registry.update_source_status(
        source_id=test_src,
        status="ACTIVE",
        jobs_found=25,
        jobs_deduped=25,
        http_status=200
    )
    src = source_registry.get_source(test_src)
    assert src is not None
    assert src.status == "ACTIVE"
    assert src.jobs_found == 25
    assert src.http_status == 200
    assert src.last_success is not None
