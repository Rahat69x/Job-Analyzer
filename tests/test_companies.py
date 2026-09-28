import pytest
import json
import sqlite3
from fastapi.testclient import TestClient
from app import app
from ingestion.global_connectors import CuratedCompaniesConnector
from core.db import search_global_jobs

client = TestClient(app)

USER_COMPANIES = [
    "10up", "15Five", "17hats", "18F", "1Password", "42 Technologies", "Abiturma",
    "Ably", "Abstract API", "Acct", "Acivilate", "Acquia", "ActiveCampaign", "Ad Hoc",
    "Adaface", "AddStructure", "Adeventa", "Adzuna", "AE Studio", "Aerolab", "AgFlow",
    "Aha!", "Aim India", "Airbank", "Algorand", "Algorithmia", "Alight Solutions",
    "Alley", "AllyDVM", "AlphaSights", "Amazon", "Ambaum", "Andela", "Animalz",
    "Annertech", "Anomali", "Apartment Therapy", "Appinio", "Applaudo",
    "Appstractor Corporation", "Appwrite", "Argyle", "ARK", "Arkency", "Art & Logic",
    "Artefactual Systems", "ALICE", "Articulate", "Airbyte", "AirGarage", "AirTreks",
    "Aivitex", "Alami", "Alan", "Automatic", "Axelerant", "Axios", "Bairesdev",
    "Baleng", "Balsamiq", "Bandcamp", "BandLab", "Bandzoogle", "Baarrametric",
    "Basecamp", "Bear Group", "BeBanjo", "BeenVerified", "Betalab", "BetaPeak",
    "BetterUp", "Beyond Company"
]

def test_companies_json_integrity():
    with open("data/companies.json", "r", encoding="utf-8") as f:
        comps = json.load(f)
    assert len(comps) == 72
    comp_names = [c["name"] for c in comps]
    assert comp_names == USER_COMPANIES
    for c in comps:
        assert "name" in c and c["name"]
        assert "website" in c and c["website"]
        assert "careers_url" in c
        assert "industry" in c
        assert "typical_roles" in c and isinstance(c["typical_roles"], list)
        assert "location" in c
        assert "workplace_type" in c
        assert "remote_policy" in c
        assert "salary_range" in c
        assert "tier" in c

def test_api_companies_endpoint():
    res = client.get("/api/companies")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 72
    assert len(data["companies"]) == 72

    # Test filtering by query
    res_filter = client.get("/api/companies?q=Basecamp")
    assert res_filter.status_code == 200
    d_filter = res_filter.json()
    assert d_filter["total"] == 1
    assert d_filter["companies"][0]["name"] == "Basecamp"
    assert "https://basecamp.com" in d_filter["companies"][0]["website"]

def test_curated_companies_connector():
    connector = CuratedCompaniesConnector()
    jobs = connector.fetch_jobs(limit=100)
    assert len(jobs) >= 70
    job_companies = set(j.company.name for j in jobs)
    assert "10up" in job_companies
    assert "Basecamp" in job_companies
    assert "Bairesdev" in job_companies

def test_database_has_all_user_companies():
    conn = sqlite3.connect("data/jobs.db")
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT company_name FROM jobs")
    db_companies = set(r[0] for r in cur.fetchall())
    conn.close()

    for comp in USER_COMPANIES:
        assert comp in db_companies, f"Company {comp} missing from jobs database!"

def test_global_search_sort_by_salary():
    res = client.get("/api/global/search?sort_by=salary_desc&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    # First item should have high salary
    first_job = data["results"][0]["job"]
    assert first_job["salary"]["salary_usd_max"] is not None
