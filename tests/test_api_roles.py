import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_job_roles_endpoint_all():
    response = client.get("/api/job-roles")
    assert response.status_code == 200
    data = response.json()
    assert "roles" in data
    assert len(data["roles"]) > 50

def test_job_roles_c_query():
    response = client.get("/api/job-roles?q=c")
    assert response.status_code == 200
    data = response.json()
    titles = [r["title"] for r in data["roles"]]
    assert "C++ Developer" in titles
    assert "C Developer" in titles
    assert "C# Developer" in titles

def test_job_roles_python_query():
    response = client.get("/api/job-roles?q=python")
    assert response.status_code == 200
    data = response.json()
    titles = [r["title"] for r in data["roles"]]
    assert "Python Developer" in titles
    assert "Python Backend Developer" in titles

def test_job_roles_java_query():
    response = client.get("/api/job-roles?q=java")
    assert response.status_code == 200
    data = response.json()
    titles = [r["title"] for r in data["roles"]]
    assert "Java Developer" in titles
    assert "Java Software Engineer" in titles
