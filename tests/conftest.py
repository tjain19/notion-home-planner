import pytest

from family_tasks import tasks


def make_page(title="Task", *, id="page-1", category=None, term=None, owners=(), due=None, repeats=None,
              rotates=False, quick=False, reviewed=False, done=False, effort=None, next_step="", list=None,
              completed=None, next_created=False, body_double=False, last_edited="2026-10-25T15:00:00.000Z"):
    def sel(v):
        return {"type": "select", "select": {"name": v} if v else None}

    def rich(kind, v):
        return {"type": kind, kind: [{"plain_text": v}] if v else []}

    def dt(v):
        return {"type": "date", "date": {"start": v} if v else None}

    def cb(v):
        return {"type": "checkbox", "checkbox": v}

    return {
        "id": id,
        "url": f"https://www.notion.so/{id}",
        "last_edited_time": last_edited,
        "properties": {
            "Task": rich("title", title),
            "Category": sel(category),
            "Term": sel(term),
            "Owner": {"type": "people", "people": [{"id": o} for o in owners]},
            "Due": dt(due),
            "Repeats": sel(repeats),
            "Rotates": cb(rotates),
            "Quick": cb(quick),
            "Reviewed": cb(reviewed),
            "Done": cb(done),
            "Effort": sel(effort),
            "Next step": rich("rich_text", next_step),
            "List": sel(list),
            "Completed": dt(completed),
            "Next created": cb(next_created),
            "Body double": cb(body_double),
        },
    }


@pytest.fixture
def task():
    return lambda *a, **kw: tasks.from_page(make_page(*a, **kw))
