import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_healthz_endpoint():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_ai_market_analytics_endpoint():
    response = client.get("/api/analytics/ai-market")
    assert response.status_code == 200
    data = response.json()
    assert "overview" in data
    assert "role_analysis" in data
    assert "skills_analysis" in data
    assert "salary_analysis" in data
    assert "section_9_key_answers" in data
    
    overview = data["overview"]
    assert overview["total_job_postings_analyzed"] >= 30000
    assert overview["median_salary_usd"] > 100000
    assert overview["remote_jobs_percentage"] > 5.0

def test_download_assets():
    # Notebook download
    res_nb = client.get("/api/analytics/download/notebook")
    assert res_nb.status_code == 200
    assert len(res_nb.content) > 10000

    # SQL queries download
    res_sql = client.get("/api/analytics/download/sql")
    assert res_sql.status_code == 200
    assert b"standardized_title" in res_sql.content

    # DAX measures download
    res_dax = client.get("/api/analytics/download/dax")
    assert res_dax.status_code == 200
    assert b"COUNTROWS" in res_dax.content

    # Power BI pbix download
    res_pbix = client.get("/api/analytics/download/powerbi")
    assert res_pbix.status_code == 200

    # CSV dataset download
    res_csv = client.get("/api/analytics/download/csv")
    assert res_csv.status_code == 200
    assert b"job_id" in res_csv.content
