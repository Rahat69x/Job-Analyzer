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
