"""
Unit & Integration Tests for Ingestion Pipeline and Shared Connectors
Verifies connector normalization, deduplication, diagnostic funnel, and live API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app import app
from core.models import NormalizedJob, CompanyInfo
from core.deduplicator import deduplicate_jobs
from core.source_registry import source_registry
from ingestion.shared_connectors import ArbeitnowConnector, GreenhouseConnector

client = TestClient(app)

def test_sources_health_api_endpoint():
    response = client.get("/api/sources/health")
    assert response.status_code == 200
    data = response.json()
    assert data["total_registered_sources"] >= 70
    assert data["active_sources_count"] >= 30
    assert "by_category" in data
    assert "sources" in data
    assert len(data["sources"]) >= 70

def test_jobs_global_search_api_with_diagnostics():
    response = client.get("/api/jobs/global?q=Software+Engineer&country=Worldwide")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert "search_diagnostics" in data
    diag = data["search_diagnostics"]
    assert diag["sources_queried"] >= 30
    assert diag["total_evaluated"] > 0
    assert diag["matching_title_or_skills"] > 0

def test_zero_results_diagnostics_funnel():
    # Non-existent role to test diagnostic funnel
    response = client.get("/api/jobs/global?q=QuantumAstronautUnderwaterWelder999")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert "search_diagnostics" in data
    diag = data["search_diagnostics"]
    assert diag["matching_title_or_skills"] == 0
    assert diag["sources_queried"] >= 30
    assert "No matching jobs found" in diag["explanation"]

def test_deduplication_engine():
    job_a = NormalizedJob(
        id="job-1",
        title="Senior Python Engineer",
        company=CompanyInfo(name="Stripe Inc.", tier="MNC", verified=True),
        country="United States",
        location="Remote, USA",
        apply_url="https://stripe.com/jobs/1",
        source="Greenhouse",
        source_reliability="official_career_page"
    )
    job_b = NormalizedJob(
        id="job-2",
        title="Python Engineer, Senior",
        company=CompanyInfo(name="Stripe", tier="MNC", verified=True),
        country="United States",
        location="Remote, United States",
        apply_url="https://linkedin.com/jobs/view/2",
        source="LinkedIn",
        source_reliability="major_board"
    )

    deduped = deduplicate_jobs([job_a, job_b])
    assert len(deduped) == 1
    assert deduped[0].source == "Greenhouse"
    assert "LinkedIn" in deduped[0].alternate_sources

def test_greenhouse_connector_initialization():
    conn = GreenhouseConnector("stripe", "Stripe", "MNC")
    assert conn.board_token == "stripe"
    assert conn.company_name == "Stripe"
    assert "stripe" in conn.endpoint

def test_arbeitnow_connector_initialization():
    conn = ArbeitnowConnector()
    assert "arbeitnow.com" in conn.ENDPOINT
