"""Small PostgREST/Auth client that supports both legacy JWT and opaque API keys."""

from types import SimpleNamespace
from urllib.parse import quote

import httpx


class RestResult:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class RestQuery:
    def __init__(self, client, table: str):
        self.client = client
        self.table_name = table
        self.method = "GET"
        self.columns = "*"
        self.params = {}
        self.filters = []
        self.headers = {}
        self.body = None
        self.single_optional = False
        self.preferences = []

    def select(self, columns="*", count=None):
        self.columns = columns
        if count:
            self.preferences.append(f"count={count}")
        if self.method != "GET":
            self.preferences.append("return=representation")
        return self

    def eq(self, column, value):
        self.filters.append((column, f"eq.{value}"))
        return self

    def order(self, column, desc=False):
        direction = "desc" if desc else "asc"
        self.params["order"] = f"{column}.{direction}"
        return self

    def range(self, start, end):
        self.headers["Range"] = f"{start}-{end}"
        return self

    def limit(self, value):
        self.params["limit"] = str(value)
        return self

    def maybe_single(self):
        self.single_optional = True
        self.params["limit"] = "1"
        return self

    def upsert(self, values, on_conflict=None):
        self.method = "POST"
        self.body = values
        self.preferences.append("resolution=merge-duplicates")
        if on_conflict:
            self.params["on_conflict"] = on_conflict
        return self

    def insert(self, values):
        self.method = "POST"
        self.body = values
        return self

    def update(self, values):
        self.method = "PATCH"
        self.body = values
        return self

    def execute(self):
        self.params.setdefault("select", self.columns)
        self.params.update(self.filters)
        headers = dict(self.headers)
        if self.preferences:
            headers["Prefer"] = ",".join(dict.fromkeys(self.preferences))
        response = self.client.http.request(
            self.method,
            f"{self.client.rest_url}/{quote(self.table_name, safe='')}",
            params=self.params,
            headers=headers,
            json=self.body,
        )
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            data = None
        if self.single_optional:
            data = (data[0] if data else None) if isinstance(data, list) else data
        content_range = response.headers.get("content-range", "")
        count = None
        if "/" in content_range:
            total = content_range.rsplit("/", 1)[1]
            if total.isdigit():
                count = int(total)
        return RestResult(data=data, count=count)


class RestAuth:
    def __init__(self, client):
        self.client = client

    def get_user(self, access_token):
        response = self.client.http.get(
            f"{self.client.base_url}/auth/v1/user",
            headers={
                "apikey": self.client.api_key,
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "GlobalAIJobPilot/1.0",
            },
        )
        response.raise_for_status()
        user = response.json()
        return SimpleNamespace(user=SimpleNamespace(id=user.get("id")))


class SupabaseRestClient:
    def __init__(self, url: str, api_key: str):
        self.base_url = url.rstrip("/")
        self.rest_url = f"{self.base_url}/rest/v1"
        self.api_key = api_key
        headers = {
            "apikey": api_key,
            "Content-Type": "application/json",
            "User-Agent": "GlobalAIJobPilot/1.0",
        }
        if not api_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {api_key}"
        self.http = httpx.Client(headers=headers, timeout=30)
        self.auth = RestAuth(self)

    def table(self, name: str) -> RestQuery:
        return RestQuery(self, name)
