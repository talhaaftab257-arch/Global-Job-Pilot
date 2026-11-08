import hashlib
import html
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
import httpx
from app.services.sponsorship import classify
from app.services.matching import score

SKIP = re.compile(
    r"\b(data analyst|business intelligence analyst|reporting analyst|administrative assistant|hr coordinator|sales representative)\b",
    re.I
)

COUNTRIES = {
    "United States": [
        "united states", "usa", "u.s.", "u.s.a", "san francisco", "seattle", "new york",
        "boston", "austin", "chicago", "los angeles", "mountain view", "sunnyvale",
        "palo alto", "san jose", "california", "washington", "texas", "new york",
        "remote, us", "remote - us", "us remote", "remote (us)"
    ],
    "United Kingdom": [
        "united kingdom", "uk", "u.k.", "london", "england", "scotland", "wales",
        "cambridge", "oxford", "manchester", "edinburgh", "bristol",
        "remote, uk", "remote - uk", "uk remote", "remote (uk)"
    ],
    "Germany": [
        "germany", "berlin", "munich", "münchen", "hamburg", "frankfurt", "cologne",
        "köln", "stuttgart", "düsseldorf", "deutschland"
    ],
    "Canada": [
        "canada", "toronto", "vancouver", "montreal", "montréal", "ottawa", "waterloo",
        "calgary", "ontario", "british columbia", "quebec"
    ],
    "Netherlands": [
        "netherlands", "amsterdam", "rotterdam", "utrecht", "eindhoven", "the hague",
        "den haag", "holland"
    ],
    "Ireland": ["ireland", "dublin", "cork", "galway", "limerick"],
    "Switzerland": ["switzerland", "zurich", "zürich", "geneva", "genève", "lausanne", "basel"],
    "France": ["france", "paris", "lyon", "toulouse", "bordeaux"],
    "Sweden": ["sweden", "stockholm", "gothenburg", "malmö"],
    "Norway": ["norway", "oslo", "bergen", "trondheim"],
    "Denmark": ["denmark", "copenhagen", "aarhus"],
    "Finland": ["finland", "helsinki", "espoo", "tampere"],
    "Australia": ["australia", "sydney", "melbourne", "brisbane", "perth", "canberra"],
    "New Zealand": ["new zealand", "auckland", "wellington", "christchurch"],
    "Singapore": ["singapore"],
    "Japan": ["japan", "tokyo", "osaka", "kyoto"],
    "South Korea": ["south korea", "seoul"],
    "United Arab Emirates": ["united arab emirates", "uae", "u.a.e.", "dubai", "abu dhabi"],
    "Saudi Arabia": ["saudi arabia", "ksa", "riyadh", "jeddah"],
    "Qatar": ["qatar", "doha"],
    "Poland": ["poland", "warsaw", "krakow", "wroclaw"],
    "Spain": ["spain", "madrid", "barcelona", "valencia"],
    "Pakistan": ["pakistan", "islamabad", "rawalpindi", "karachi", "lahore"],
    "Worldwide": ["anywhere", "worldwide", "global remote", "remote - global", "remote worldwide", "remote - anywhere"]
}

def clean_html(value: str) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def country_from_location(location: str) -> str | None:
    text = (location or "").lower()
    for country, aliases in COUNTRIES.items():
        if any(re.search(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", text) for alias in aliases):
            return country
    return None

def detect_remote_type(location: str, description: str) -> str:
    combined = f"{location} {description[:300]}".lower()
    if re.search(r"\b(remote|work from home|telecommute|distributed)\b", combined):
        return "remote"
    elif re.search(r"\b(hybrid|flexible)\b", combined):
        return "hybrid"
    return "onsite"

def canonical(url: str) -> str:
    if not url:
        return ""
    p = urlsplit(url)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", ""))

def normalize(title: str, company: str, location: str, description: str, url: str,
              external_id: str, posted_at=None, salary=None, source="") -> dict | None:
    # Filter out pure data analysts/admin unless explicit AI/ML engineering
    body = clean_html(description)
    if SKIP.search(title) and not re.search(r"\b(ai engineer|machine learning|llm|deep learning|rag)\b", f"{title} {body}", re.I):
        return None

    country = country_from_location(location)
    remote_type = detect_remote_type(location, body)

    # Classify sponsorship and relocation
    sponsorship_info = classify(body)

    # Deterministic external_id fallback
    ext_id = str(external_id).strip()
    if not ext_id:
        ext_id = hashlib.sha256(f"{company}|{title}|{location}".lower().encode()).hexdigest()[:24]

    canonical_url = canonical(url)
    if not canonical_url:
        canonical_url = f"https://jobs.jobpilot.internal/{company}/{ext_id}".lower()

    job = {
        "title": title.strip(),
        "company": company.strip(),
        "location": location.strip() if location else None,
        "country": country,
        "description": body,
        "application_url": url.strip() or canonical_url,
        "canonical_url": canonical_url,
        "external_id": ext_id,
        "posted_at": posted_at,
        "salary_text": salary.strip() if salary else None,
        "source_name": source,
        "remote_type": remote_type,
        "status": "open",
        **sponsorship_info
    }

    # Calculate match score & explanation
    match_data = score(job)
    job.update(match_data)
    return job

async def collect_greenhouse(board: str) -> list[dict]:
    headers = {"User-Agent": "GlobalAIJobPilot/1.0 (+https://github.com)"}
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as c:
        r = await c.get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")
        r.raise_for_status()
        data = r.json()

    out = []
    company_name = board.replace("-", " ").title()
    for x in data.get("jobs", []):
        loc = (x.get("location") or {}).get("name", "")
        posted = x.get("updated_at")
        j = normalize(
            title=x.get("title", ""),
            company=company_name,
            location=loc,
            description=x.get("content", ""),
            url=x.get("absolute_url", ""),
            external_id=x.get("id", ""),
            posted_at=posted,
            source=f"greenhouse:{board}"
        )
        if j:
            out.append(j)
    return out

async def collect_lever(board: str) -> list[dict]:
    headers = {"User-Agent": "GlobalAIJobPilot/1.0 (+https://github.com)"}
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as c:
        r = await c.get(f"https://api.lever.co/v0/postings/{board}?mode=json")
        r.raise_for_status()
        data = r.json()

    out = []
    company_name = board.replace("-", " ").title()
    for x in data:
        desc = x.get("descriptionPlain") or clean_html(x.get("description", ""))
        cats = x.get("categories") or {}
        loc = cats.get("location", "")
        created_at = None
        if x.get("createdAt"):
            created_at = datetime.fromtimestamp(x["createdAt"] / 1000, timezone.utc).isoformat()

        salary = None
        if x.get("salaryRange"):
            sr = x["salaryRange"]
            salary = f"{sr.get('currency', '$')} {sr.get('min', '')}-{sr.get('max', '')} {sr.get('interval', 'per year')}"

        j = normalize(
            title=x.get("text", ""),
            company=company_name,
            location=loc,
            description=desc,
            url=x.get("hostedUrl", "") or x.get("applyUrl", ""),
            external_id=x.get("id", ""),
            posted_at=created_at,
            salary=salary,
            source=f"lever:{board}"
        )
        if j:
            out.append(j)
    return out

async def collect_ashby(board: str) -> list[dict]:
    headers = {"User-Agent": "GlobalAIJobPilot/1.0 (+https://github.com)"}
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as c:
        r = await c.get(f"https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true")
        r.raise_for_status()
        data = r.json()

    out = []
    company_name = board.replace("-", " ").title()
    for x in data.get("jobs", []):
        comp = x.get("compensation") or {}
        salary = comp.get("compensationTierSummary")
        j = normalize(
            title=x.get("title", ""),
            company=company_name,
            location=x.get("location", ""),
            description=x.get("descriptionPlain") or x.get("descriptionHtml", ""),
            url=x.get("jobUrl", ""),
            external_id=x.get("id", ""),
            posted_at=x.get("publishedAt"),
            salary=salary,
            source=f"ashby:{board}"
        )
        if j:
            out.append(j)
    return out

COLLECTORS = {
    "greenhouse": collect_greenhouse,
    "lever": collect_lever,
    "ashby": collect_ashby
}
