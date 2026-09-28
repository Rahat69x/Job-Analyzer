import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_global_search_api():
    response = client.get("/api/global/search?q=engineer")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "results" in data
    assert data["total"] > 0
    # Check that job has candidate eligibility
    first_res = data["results"][0]
    assert "job" in first_res
    assert "candidate_eligibility" in first_res["job"]
    assert "is_eligible" in first_res["job"]["candidate_eligibility"]
    assert "apply_url" in first_res["job"]

def test_global_remote_api():
    response = client.get("/api/global/remote?region=Worldwide")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    for item in data["results"]:
        assert item["job"]["workplace_type"] == "Remote"

def test_country_explorer_api():
    response = client.get("/api/global/countries")
    assert response.status_code == 200
    data = response.json()
    assert "countries" in data
    assert len(data["countries"]) > 0
    first_c = data["countries"][0]
    assert "country" in first_c
    assert "total_jobs" in first_c
    assert "remote_jobs" in first_c

def test_recommendations_api():
    response = client.get("/api/global/recommendations?skills=Python,React&education=CSE+Student&experience=0.5")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0

def test_currency_conversion_api():
    response = client.get("/api/global/currencies")
    assert response.status_code == 200
    data = response.json()
    assert "rates" in data
    assert "USD" in data["rates"]
    assert "BDT" in data["rates"]
    assert data["bdt_per_usd"] == 120.0

def test_source_filtering():
    response = client.get("/api/global/search?source=Remote%20OK")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for r in data["results"]:
        assert "remote ok" in r["job"]["source"].lower()

def test_taxonomy_counts():
    response = client.get("/api/taxonomy")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    func = [c for c in data["categories"] if c["type"] == "Functional"]
    spec = [c for c in data["categories"] if c["type"] == "Special Skilled"]
    assert len(func) == 31
    assert len(spec) == 33

def test_salary_filtering_bdt():
    response = client.get("/api/global/search?min_salary=50000&salary_currency=BDT&salary_period=Monthly")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for r in data["results"]:
        job = r["job"]
        assert job["salary"]["disclosed"] is True
        # Annualized BDT should be at least 50,000 * 12 = 600,000
        bdt_high = job["salary"]["salary_bdt_max"] or job["salary"]["salary_bdt_min"]
        assert bdt_high >= 600000

def test_salary_filtering_usd():
    response = client.get("/api/global/search?min_salary=50000&salary_currency=USD&salary_period=Annual")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for r in data["results"]:
        job = r["job"]
        assert job["salary"]["disclosed"] is True
        usd_high = job["salary"]["salary_usd_max"] or job["salary"]["salary_usd_min"]
        assert usd_high >= 50000

def test_category_and_salary_filtering_alone():
    # Category 11 = Healthcare/Medical with min_salary 50,000 BDT/mo alone
    response = client.get("/api/global/search?category_id=11&min_salary=50000&salary_currency=BDT&salary_period=Monthly")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for r in data["results"]:
        job = r["job"]
        assert job["category_id"] == 11
        assert job["salary"]["disclosed"] is True
        bdt_high = job["salary"]["salary_bdt_max"] or job["salary"]["salary_bdt_min"]
        assert bdt_high >= 600000


