"""Stamp Completed on finished tasks and create the next copy of repeating ones."""

from datetime import date, datetime, timedelta

from . import dates, tasks
from .config import DATA_SOURCE_ID
from .notion import Notion
from .tasks import Task

DONE = {"property": "Done", "checkbox": {"equals": True}}


def next_due(task: Task, repeats: str) -> date | datetime:
    base = task.due or task.completed_on()
    if repeats == "weekly":
        return base + timedelta(days=7)
    if repeats == "every 2 weeks":
        return base + timedelta(days=14)
    if repeats == "monthly":
        return dates.add_months(base, 1)
    raise ValueError(f"Unknown Repeats value {repeats!r} on task {task.title!r}")


def next_owners(task: Task, people_ids: list[str]) -> list[str]:
    """Hand a rotating task to the other person; needs one owner and two people."""
    if task.rotates and len(task.owners) == 1 and len(people_ids) == 2 and task.owners[0] in people_ids:
        return [p for p in people_ids if p != task.owners[0]]
    return task.owners


def repeats(task: Task) -> bool:
    return bool(task.repeats) and task.repeats != "none"


def next_instance(task: Task, people_ids: list[str], today: date) -> dict:
    """Properties for the next copy: same fields, new Due, not done."""
    due = next_due(task, task.repeats)
    return {
        "Task": tasks.title(task.title),
        "Category": tasks.select(task.category),
        "Term": tasks.select(dates.term_for(dates.local_date(due), today)),
        "Owner": tasks.people(next_owners(task, people_ids)),
        "Due": tasks.date_value(due),
        "Repeats": tasks.select(task.repeats),
        "Rotates": tasks.checkbox(task.rotates),
        "Quick": tasks.checkbox(task.quick),
        "Reviewed": tasks.checkbox(task.reviewed),
        "Effort": tasks.select(task.effort),
        "Next step": tasks.text(task.next_step),
        "List": tasks.select(task.list),
        "Body double": tasks.checkbox(task.body_double),
    }


def _already_exists(notion: Notion, task: Task, due: date | datetime) -> bool:
    """Guard against a duplicate if an earlier run created the copy but failed before marking."""
    matches = notion.query(DATA_SOURCE_ID, {"and": [
        {"property": "Task", "title": {"equals": task.title}},
        {"property": "Due", "date": {"equals": dates.local_date(due).isoformat()}},
        {"property": "Done", "checkbox": {"equals": False}},
    ]})
    return bool(matches)


def run(notion: Notion, people_ids: list[str], today: date) -> None:
    unstamped = notion.query(DATA_SOURCE_ID, {"and": [DONE, {"property": "Completed", "date": {"is_empty": True}}]})
    pending = notion.query(DATA_SOURCE_ID, {"and": [
        DONE,
        {"property": "Next created", "checkbox": {"equals": False}},
        {"property": "Repeats", "select": {"is_not_empty": True}},
        {"property": "Repeats", "select": {"does_not_equal": "none"}},
    ]})
    pages = {page["id"]: page for page in unstamped + pending}
    print(f"Recurrence: {len(pages)} finished task(s) to process")

    for page in pages.values():
        task = tasks.from_page(page)
        updates, changes = {}, {}

        if task.completed is None:
            stamp = task.completed_on()
            updates["Completed"] = tasks.date_value(stamp)
            changes["Completed"] = (None, stamp)

        if repeats(task) and not task.next_created and task.title:
            properties = next_instance(task, people_ids, today)
            due = next_due(task, task.repeats)
            if _already_exists(notion, task, due):
                print(f"Recurrence: next copy of {task.title!r} due {due} already exists")
            else:
                notion.create_page(
                    {"type": "data_source_id", "data_source_id": DATA_SOURCE_ID},
                    properties,
                    f"next {task.repeats} copy of {task.title!r}, due {dates.format_notion(due)}"
                    + (" (owner rotated)" if properties["Owner"]["people"] != tasks.people(task.owners)["people"] else ""),
                )
            updates["Next created"] = tasks.checkbox(True)
            changes["Next created"] = (False, True)

        if updates:
            notion.update_page(task.id, updates, tasks.describe(task, changes))
