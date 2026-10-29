"""Small Notion API client. In dry-run mode, writes are printed instead of sent."""

import json
import time

import requests

API = "https://api.notion.com/v1"
VERSION = "2025-09-03"
RETRIES = 4


class NotionError(Exception):
    pass


class Notion:
    def __init__(self, token: str, dry_run: bool, session: requests.Session | None = None):
        self.dry_run = dry_run
        self.session = session or requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Notion-Version": VERSION,
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, body: dict | None = None, params: dict | None = None) -> dict:
        for attempt in range(RETRIES + 1):
            try:
                response = self.session.request(method, API + path, json=body, params=params, timeout=30)
            except requests.RequestException as error:
                if attempt == RETRIES:
                    raise NotionError(f"Could not reach Notion ({method} {path}): {error}") from error
                time.sleep(2 ** attempt)
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == RETRIES:
                    break
                time.sleep(float(response.headers.get("Retry-After", 2 ** attempt)))
                continue
            if not response.ok:
                break
            return response.json()
        raise NotionError(f"Notion {method} {path} failed with {response.status_code}: {response.text[:500]}")

    def _paginate(self, method: str, path: str, body: dict | None = None) -> list[dict]:
        results, cursor = [], None
        while True:
            if method == "GET":
                page = self._request(method, path, params={"page_size": 100, **({"start_cursor": cursor} if cursor else {})})
            else:
                page = self._request(method, path, body={**(body or {}), "page_size": 100, **({"start_cursor": cursor} if cursor else {})})
            results.extend(page["results"])
            if not page.get("has_more"):
                return results
            cursor = page["next_cursor"]

    # Reads

    def check_data_source(self, data_source_id: str) -> None:
        self._request("GET", f"/data_sources/{data_source_id}")

    def query(self, data_source_id: str, filter: dict | None = None) -> list[dict]:
        return self._paginate("POST", f"/data_sources/{data_source_id}/query", {"filter": filter} if filter else {})

    def people(self) -> list[dict]:
        """Workspace members (not bots), as {"id", "name"}, sorted by name."""
        users = self._paginate("GET", "/users")
        people = [{"id": u["id"], "name": u.get("name") or "Someone"} for u in users if u.get("type") == "person"]
        return sorted(people, key=lambda p: p["name"].lower())

    def child_page_titles(self, page_id: str) -> list[str]:
        blocks = self._paginate("GET", f"/blocks/{page_id}/children")
        return [b["child_page"]["title"] for b in blocks if b.get("type") == "child_page"]

    # Writes

    def update_page(self, page_id: str, properties: dict, description: str) -> None:
        print(f"{'[dry-run] would update' if self.dry_run else 'update'}: {description}")
        if not self.dry_run:
            self._request("PATCH", f"/pages/{page_id}", {"properties": properties})

    def create_page(self, parent: dict, properties: dict, description: str, children: list[dict] | None = None) -> None:
        print(f"{'[dry-run] would create' if self.dry_run else 'create'}: {description}")
        if self.dry_run:
            if children:
                print(json.dumps(children, indent=2, ensure_ascii=False))
            return
        body = {"parent": parent, "properties": properties}
        if children:
            body["children"] = children
        self._request("POST", "/pages", body)
