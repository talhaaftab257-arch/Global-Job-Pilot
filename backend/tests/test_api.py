import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.collectors.public_ats import normalize
from app.database import save_job

client = TestClient(app)

@pytest.fixture(autouse=True)
def seed_sample_job():
    job = normalize(
        title="Senior AI Agent Engineer",
        company="Anthropic AI Test",
        location="London, United Kingdom",
        description="We are building multi-agent systems using Python, FastAPI, LangGraph, and Claude. We offer visa sponsorship for qualified international candidates. Relocation assistance provided.",
        url="https://jobs.example.com/ai-engineer",
        external_id="test-job-001",
        salary="£90,000 - £120,000",
        source="greenhouse:anthropic"
    )
    save_job(None, "greenhouse", "anthropic", job)

def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "sources_configured" in data
    assert "total_jobs" in data

def test_api_jobs_list_and_filter():
    res = client.get("/api/jobs?query=test-job-001")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 1
    found = [j for j in data["items"] if j["external_id"] == "test-job-001"]
    assert len(found) == 1
    assert found[0]["sponsorship_status"] == "confirmed"
    assert found[0]["match_score"] >= 70

def test_api_jobs_sponsorship_filter():
    res = client.get("/api/jobs?sponsorship=confirmed&limit=20")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) > 0
    for item in data["items"]:
        assert item["sponsorship_status"] == "confirmed"

def test_api_featured_jobs():
    res = client.get("/api/jobs/featured")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) <= 30

def test_api_analytics_overview():
    res = client.get("/api/analytics/overview")
    assert res.status_code == 200
    data = res.json()
    assert "total_jobs" in data
    assert "matching_jobs" in data
    assert "average_match" in data
    assert "sponsorship" in data

def test_api_analytics_countries():
    res = client.get("/api/analytics/countries")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    uk = next((c for c in data if c["country"] == "United Kingdom"), None)
    assert uk is not None
    assert uk["jobs"] >= 1

def test_api_sources():
    res = client.get("/api/sources")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) > 0

def test_api_preferences_get_and_put():
    res = client.get("/api/preferences")
    assert res.status_code == 200
    data = res.json()
    assert "target_titles" in data

    update_payload = {
        "target_titles": ["Staff AI Engineer", "Lead AI Engineer"],
        "target_countries": ["United Kingdom", "Germany"],
        "target_regions": ["Europe"],
        "skills": ["Python", "LangGraph", "FastAPI"],
        "minimum_match_score": 75,
        "sponsorship_priority": True,
        "daily_notification_limit": 25
    }
    put_res = client.put("/api/preferences", json=update_payload)
    assert put_res.status_code == 200

    verify_res = client.get("/api/preferences")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert "Staff AI Engineer" in v_data["target_titles"]
    assert v_data["minimum_match_score"] == 75

def test_api_applications_workflow():
    jobs_res = client.get("/api/jobs?limit=5")
    job_id = jobs_res.json()["items"][0]["id"]

    post_res = client.post("/api/applications", json={
        "job_id": job_id,
        "status": "applied",
        "notes": "Applied via employer career site with portfolio link."
    })
    assert post_res.status_code == 200
    app_data = post_res.json()
    app_id = app_data["id"]

    list_res = client.get("/api/applications")
    assert list_res.status_code == 200
    apps = list_res.json()["items"]
    assert any(a["id"] == app_id for a in apps)

    patch_res = client.patch(f"/api/applications/{app_id}", json={
        "status": "interview",
        "notes": "Interview scheduled for technical round."
    })
    assert patch_res.status_code == 200
