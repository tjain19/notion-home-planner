"""Fill blank Category, Term, Effort, Quick and Next step with Claude. Never overwrite."""

from typing import Literal

import anthropic
from pydantic import BaseModel, Field

from . import tasks
from .config import DATA_SOURCE_ID, MODEL
from .notion import Notion
from .tasks import Task

MAX_STEP_WORDS = 12

SYSTEM = """You sort tasks on a shared family to-do list for two adults.
For each task, pick:
- category: the best fit from the allowed list.
- term: when it realistically needs doing (This week, This month, This quarter, Long term).
- effort: a realistic estimate of the hands-on time.
- next_step: the very first physical action, as a short imperative prompt of at most 12 words.
  Make it concrete enough to start without thinking (e.g. "Open the pediatrician's site and book a checkup slot").
Use the fields that are already filled in as context."""


class Sorting(BaseModel):
    category: Literal["Home", "Work", "Health", "Childcare", "Admin", "Finances", "Travel", "Social/Entertainment"]
    term: Literal["This week", "This month", "This quarter", "Long term"]
    effort: Literal["2 min", "10 min", "30 min", "1 hour+"]
    next_step: str = Field(description="One line, at most 12 words")


class SorterError(Exception):
    pass


class Classifier:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=3)

    def sort(self, task: Task) -> Sorting:
        response = self.client.messages.parse(
            model=MODEL,
            max_tokens=2048,
            output_config={"effort": "low"},
            system=SYSTEM,
            messages=[{"role": "user", "content": _describe(task)}],
            output_format=Sorting,
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            raise SorterError(f"No usable answer for task {task.title!r} (stop_reason={response.stop_reason})")
        return response.parsed_output


def _describe(task: Task) -> str:
    lines = [f"Task: {task.title}", f"List: {task.list}"]
    for label, value in (("Category", task.category), ("Term", task.term), ("Effort", task.effort),
                         ("Next step", task.next_step), ("Due", task.due_date)):
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def one_line(step: str) -> str:
    words = " ".join(step.split()).split(" ")
    return " ".join(words[:MAX_STEP_WORDS]).strip()


def blank_fields(task: Task) -> list[str]:
    blanks = []
    if not task.category:
        blanks.append("Category")
    if not task.term and task.due is None:
        blanks.append("Term")
    if not task.effort:
        blanks.append("Effort")
    if not task.next_step:
        blanks.append("Next step")
    return blanks


def plan(task: Task, sorting: Sorting | None) -> tuple[dict, dict]:
    """The property updates for one task: only blank fields, plus Quick for 2-minute tasks."""
    updates, changes = {}, {}
    blanks = blank_fields(task)
    if sorting:
        values = {"Category": sorting.category, "Term": sorting.term, "Effort": sorting.effort,
                  "Next step": one_line(sorting.next_step)}
        for field in blanks:
            value = values[field]
            if not value:
                continue
            updates[field] = tasks.text(value) if field == "Next step" else tasks.select(value)
            changes[field] = (None, value)
    effort = task.effort or changes.get("Effort", (None, None))[1]
    if effort == "2 min" and not task.quick:
        updates["Quick"] = tasks.checkbox(True)
        changes["Quick"] = (False, True)
    return updates, changes


def run(notion: Notion, classifier: Classifier) -> None:
    pages = notion.query(DATA_SOURCE_ID, {"and": [
        {"property": "Done", "checkbox": {"equals": False}},
        {"property": "Reviewed", "checkbox": {"equals": False}},
    ]})
    print(f"Sorter: {len(pages)} open, unreviewed task(s)")
    for page in pages:
        task = tasks.from_page(page)
        if not task.title:
            continue
        sorting = classifier.sort(task) if blank_fields(task) else None
        updates, changes = plan(task, sorting)
        if updates:
            notion.update_page(task.id, updates, tasks.describe(task, changes))
