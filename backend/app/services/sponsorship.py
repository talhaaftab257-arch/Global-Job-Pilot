import re
from datetime import datetime, timezone

CONFIRMED = re.compile(
    r"\b("
    r"visa sponsorship|"
    r"sponsor(?:ship)? (?:is )?(?:available|provided|offered|considered)|"
    r"we (?:can |will |do |offer )?sponsor (?:visas?|work permits?)?|"
    r"work permit (?:support|sponsorship|assistance)|"
    r"relocation (?:support|assistance|package|budget|allowance)|"
    r"international applicants? welcome|visa assistance"
    r")\b",
    re.I
)

UNAVAILABLE = re.compile(
    r"\b("
    r"no visa sponsorship|"
    r"unable to (?:provide |offer )?sponsor(?:ship)?|"
    r"not sponsor(?:ing)?|"
    r"cannot (?:offer |provide )?sponsor(?:ship)?|"
    r"without (?:visa )?sponsorship|"
    r"must (?:already )?(?:have|hold) (?:the )?(?:valid )?(?:right to work|work authorization)|"
    r"requires? existing work authorization|"
    r"no relocation (?:support|assistance)"
    r")\b",
    re.I
)

LIKELY = re.compile(
    r"\b("
    r"visa sponsor\b|"
    r"licensed sponsor|"
    r"sponsorship history|"
    r"global relocation|"
    r"sponsorship may be considered"
    r")\b",
    re.I
)

RELOCATION = re.compile(
    r"\b(relocation (?:support|assistance|package|allowance|bonus|stipend)|relocate to|relocation provided)\b",
    re.I
)

def classify(text: str) -> dict:
    """
    Classify visa sponsorship status strictly from vacancy text.
    Company-level registers are not vacancy evidence without vacancy text support.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", text or "") if s.strip()]

    denied_sentence = next((s for s in sentences if UNAVAILABLE.search(s)), None)
    confirmed_sentence = next(
        (s for s in sentences if CONFIRMED.search(s) and not UNAVAILABLE.search(s)),
        None
    )
    likely_sentence = next((s for s in sentences if LIKELY.search(s)), None)

    if denied_sentence:
        status = "unavailable"
        evidence = denied_sentence
    elif confirmed_sentence:
        status = "confirmed"
        evidence = confirmed_sentence
    elif likely_sentence:
        status = "likely"
        evidence = likely_sentence
    else:
        status = "unverified"
        evidence = None

    reloc_match = next((s for s in sentences if RELOCATION.search(s)), None)

    is_denied = status == "unavailable"
    work_auth_req = (
        "Existing domestic work authorization required"
        if is_denied and re.search(r"right to work|work authorization|citizenship", denied_sentence or "", re.I)
        else None
    )

    return {
        "sponsorship_status": status,
        "sponsorship_evidence": evidence,
        "sponsorship_source_url": None,
        "employer_sponsor_verified": False,
        "relocation_support": bool(reloc_match) if reloc_match else None,
        "relocation_evidence": reloc_match,
        "work_authorization_requirement": work_auth_req,
        "candidate_eligibility": "not_eligible_without_sponsorship" if is_denied else "eligible_with_sponsorship" if status == "confirmed" else "unknown",
        "verification_timestamp": datetime.now(timezone.utc).isoformat()
    }
