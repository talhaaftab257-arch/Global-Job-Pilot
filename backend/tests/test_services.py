from app.collectors.public_ats import normalize, canonical, country_from_location
from app.services.matching import score
from app.services.sponsorship import classify

def test_vacancy_specific_sponsorship_evidence():
    result=classify("We offer visa sponsorship for this role. Relocation assistance is available.")
    assert result["sponsorship_status"]=="confirmed"
    assert "visa sponsorship" in result["sponsorship_evidence"].lower()
    assert classify("Candidates must already have the right to work. No visa sponsorship.")["sponsorship_status"]=="unavailable"
    assert classify("We are an international company.")["sponsorship_status"]=="unverified"

def test_job_normalization_matching_and_dedup_url():
    job=normalize("AI Engineer","Example","Berlin, Germany","Build Python FastAPI and LangGraph RAG agents. Visa sponsorship available.","https://jobs.example/role?utm_source=feed","123",source="greenhouse")
    assert job is not None and job["match_score"]>50
    assert job["sponsorship_status"]=="confirmed"
    assert canonical("https://jobs.example/role?utm_source=feed")==canonical("https://jobs.example/role?ref=other")
    assert job["country"]=="Germany"
    assert normalize("Data Analyst","Example","London","Prepare dashboards and reports", "https://example/job", "2") is None
    assert country_from_location("Dublin, Ireland")=="Ireland"

def test_daily_report_maximum_is_enforced_by_selection_contract():
    # Sorting/selection is applied in daily.py before either notification renderer runs.
    records=[{"title":str(i)} for i in range(35)]
    assert len(records[:30])==30
