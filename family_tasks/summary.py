"""The Sunday evening "Week of ..." page under Family Planner."""

from datetime import date, datetime, time, timedelta

from . import dates, tasks
from .config import DATA_SOURCE_ID, PLANNER_PAGE_ID, SUMMARY_MAX_TASKS
from .notion import Notion
from .tasks import Task

WINDOW_START = time(18, 30)


def in_window(moment: datetime) -> bool:
    """Sunday from 6:30pm to midnight Eastern. Cron tries hourly from 7pm, so a late GitHub run still posts."""
    return moment.weekday() == 6 and moment.time() >= WINDOW_START


def next_monday(today: date) -> date:
    return today + timedelta(days=7 - today.weekday())


def page_title(monday: date) -> str:
    return f"Week of {dates.short(monday)}, {monday.year}"


def effective_term(task: Task, on: date) -> str | None:
    return dates.term_for(task.due_date, on) if task.due_date else task.term


def _sort_key(task: Task):
    return (not task.quick, task.due_date or date.max, task.title.lower())


# Block helpers

def _text(content: str, *, gray: bool = False, bold: bool = False, link: str | None = None) -> dict:
    item = {"type": "text", "text": {"content": content}}
    if link:
        item["text"]["link"] = {"url": link}
    if gray or bold:
        item["annotations"] = {"color": "gray" if gray else "default", "bold": bold}
    return item


def _mention(user_id: str) -> dict:
    return {"type": "mention", "mention": {"type": "user", "user": {"id": user_id}}}


def _paragraph(rich: list[dict]) -> dict:
    return {"type": "paragraph", "paragraph": {"rich_text": rich}}


def _toggle(rich: list[dict], children: list[dict]) -> dict:
    return {"type": "toggle", "toggle": {"rich_text": rich, "children": children}}


def _todo(task: Task, show_due: bool = False) -> dict:
    rich = [_text(task.title, link=task.url)]
    if task.category:
        rich.append(_text(f" · {task.category}"))
    if show_due and task.due_date:
        rich.append(_text(f" · due {dates.short(task.due_date)}"))
    if task.next_step:
        rich.append(_text(f" — {task.next_step}", gray=True))
    return {"type": "to_do", "to_do": {"rich_text": rich, "checked": False}}


def _count(n: int) -> str:
    return f"{n} task" if n == 1 else f"{n} tasks"


class Budget:
    """At most SUMMARY_MAX_TASKS task lines on the page; each section notes what it left out."""

    def __init__(self, limit: int = SUMMARY_MAX_TASKS):
        self.left = limit

    def items(self, task_list: list[Task], show_due: bool = False) -> list[dict]:
        shown, hidden = task_list[:self.left], len(task_list) - min(len(task_list), self.left)
        self.left -= len(shown)
        blocks = [_todo(t, show_due) for t in shown]
        if hidden:
            blocks.append(_paragraph([_text(f"and {hidden} more", gray=True)]))
        return blocks


def build(open_tasks: list[Task], done_tasks: list[Task], people: list[dict], today: date) -> list[dict]:
    monday = next_monday(today)
    start = dates.week_start(today)
    household = [t for t in open_tasks if t.household]

    finished = [t for t in done_tasks if t.household and start <= t.completed_on() <= today]
    still_open = [t for t in household if effective_term(t, today) == "This week"]
    blocks = [_paragraph([_text(f"You two finished {len(finished)} of {len(finished) + len(still_open)} this week.")])]

    overdue = sorted((t for t in household if t.due_date and t.due_date < today), key=_sort_key)
    overdue_ids = {t.id for t in overdue}
    upcoming = sorted((t for t in household if effective_term(t, monday) == "This week" and t.id not in overdue_ids),
                      key=_sort_key)
    budget = Budget()

    for person in people:
        mine = [t for t in upcoming if person["id"] in t.owners]
        children = budget.items(mine) or [_paragraph([_text("Nothing this week", gray=True)])]
        blocks.append(_toggle([_mention(person["id"]), _text(f" · {_count(len(mine))}")], children))

    unclaimed = [t for t in upcoming if not t.owners]
    if unclaimed:
        blocks.append(_toggle([_text(f"Unclaimed · {_count(len(unclaimed))}", bold=True)], budget.items(unclaimed)))
    if overdue:
        blocks.append(_toggle([_text(f"Overdue · {_count(len(overdue))}", bold=True)],
                              budget.items(overdue, show_due=True)))

    blocks.append({"type": "divider", "divider": {}})
    blocks.append({"type": "heading_3", "heading_3": {"rich_text": [_text("Personal")]}})
    personal = sorted((t for t in open_tasks if not t.household and effective_term(t, monday) == "This week"),
                      key=_sort_key)
    for person in people:
        mine = [t for t in personal if person["id"] in t.owners]
        if mine:
            blocks.append(_toggle([_text(person["name"], bold=True), _text(f" · {_count(len(mine))}")],
                                  budget.items(mine)))
        else:
            blocks.append(_paragraph([_text(person["name"], bold=True),
                                      _text(" — No personal tasks this week", gray=True)]))
    return blocks


def run(notion: Notion, people: list[dict], moment: datetime, force: bool) -> None:
    if not force and not in_window(moment):
        print(f"Summary: {moment:%a %H:%M} Eastern is outside the Sunday window; nothing to do")
        return
    today = moment.date()
    title = page_title(next_monday(today))
    if not force and title in notion.child_page_titles(PLANNER_PAGE_ID):
        print(f"Summary: {title!r} already exists; nothing to do")
        return

    open_tasks = [tasks.from_page(p) for p in notion.query(DATA_SOURCE_ID, {"property": "Done", "checkbox": {"equals": False}})]
    done_tasks = [tasks.from_page(p) for p in notion.query(DATA_SOURCE_ID, {"and": [
        {"property": "Done", "checkbox": {"equals": True}},
        {"or": [
            {"property": "Completed", "date": {"on_or_after": dates.week_start(today).isoformat()}},
            {"property": "Completed", "date": {"is_empty": True}},
        ]},
    ]})]
    open_tasks = [t for t in open_tasks if t.title]

    blocks = build(open_tasks, done_tasks, people, today)
    notion.create_page({"type": "page_id", "page_id": PLANNER_PAGE_ID}, tasks.title(title), f"summary page {title!r}", blocks)
