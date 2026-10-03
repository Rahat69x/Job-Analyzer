from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_static_and_root_assets():
    endpoints = [
        ('/', 200, 'text/html'),
        ('/styles.css', 200, 'text/css'),
        ('/app.js', 200, 'javascript'),
        ('/autocomplete.js', 200, 'javascript'),
        ('/bookmarklet.js', 200, 'javascript'),
        ('/static/styles.css', 200, 'text/css'),
        ('/static/app.js', 200, 'javascript'),
        ('/healthz', 200, 'application/json'),
        ('/reports/figures/fig1_top_ai_roles.png', 200, 'image/png')
    ]
    for path, expected_status, expected_mime in endpoints:
        resp = client.get(path)
        assert resp.status_code == expected_status, f"{path} returned {resp.status_code}"
        assert expected_mime in resp.headers.get("content-type", "")

def test_cors_headers_for_vercel():
    resp = client.get("/api/taxonomy", headers={"Origin": "https://job-analyzer-pi.vercel.app"})
    assert resp.status_code == 200
    allow_origin = resp.headers.get("access-control-allow-origin")
    assert allow_origin in ["*", "https://job-analyzer-pi.vercel.app"]
