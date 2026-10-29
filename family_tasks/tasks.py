"""Reading task pages into plain objects and building Notion property values."""

from dataclasses import dataclass
from datetime import date, datetime

from . import dates


@dataclass
class Task:
    id: str
    url: str
    title: str
    category: str | None
    term: str | None
    owners: list[str]
    due: date | datetime | None
    repeats: str | None
    rotates: bool
    quick: bool
    reviewed: bool
    done: bool
    effort: str | None
    next_step: str
    list: str
    completed: date | None
    next_created: bool
    body_double: bool
    last_edited: datetime

    @property
    def due_date(self) -> date | None:
        return dates.local_date(self.due) if self.due else None

    @property
    def household(self) -> bool:
        return self.list != "Personal"

    def completed_on(self) -> date:
        """When the task was finished: the stamp if set, else its last edit."""
        return self.completed or dates.local_date(self.last_edited)


def _text(prop: dict) -> str:
    return "".join(part["plain_text"] for part in prop.get(prop["type"], [])).strip()


def _select(prop: dict) -> str | None:
    return prop["select"]["name"] if prop.get("select") else None


def _date(prop: dict) -> date | datetime | None:
    return dates.parse(prop["date"]["start"]) if prop.get("date") else None


def from_page(page: dict) -> Task:
    p = page["properties"]
    completed = _date(p["Completed"])
    return Task(
        id=page["id"],
        url=page["url"],
        title=_text(p["Task"]),
        category=_select(p["Category"]),
        term=_select(p["Term"]),
        owners=[person["id"] for person in p["Owner"]["people"]],
        due=_date(p["Due"]),
        repeats=_select(p["Repeats"]),
        rotates=p["Rotates"]["checkbox"],
        quick=p["Quick"]["checkbox"],
        reviewed=p["Reviewed"]["checkbox"],
        done=p["Done"]["checkbox"],
        effort=_select(p["Effort"]),
        next_step=_text(p["Next step"]),
        list=_select(p["List"]) or "Household",
        completed=dates.local_date(completed) if completed else None,
        next_created=p["Next created"]["checkbox"],
        body_double=p["Body double"]["checkbox"],
        last_edited=datetime.fromisoformat(page["last_edited_time"]),
    )


def title(value: str) -> dict:
    return {"title": [{"type": "text", "text": {"content": value}}]}


def text(value: str) -> dict:
    return {"rich_text": [{"type": "text", "text": {"content": value}}] if value else []}


def select(value: str | None) -> dict:
    return {"select": {"name": value} if value else None}


def checkbox(value: bool) -> dict:
    return {"checkbox": value}


def date_value(value: date | datetime | None) -> dict:
    return {"date": {"start": dates.format_notion(value)} if value else None}


def people(ids: list[str]) -> dict:
    return {"people": [{"id": i} for i in ids]}


def describe(task: Task, changes: dict[str, tuple]) -> str:
    """One line per page: 'Title | Field: old -> new; ...'."""
    parts = [f"{field}: {_show(old)} -> {_show(new)}" for field, (old, new) in changes.items()]
    return f"{task.title or '(untitled)'} | " + "; ".join(parts)


def _show(value) -> str:
    if value is None or value == "":
        return "(blank)"
    return str(value)
