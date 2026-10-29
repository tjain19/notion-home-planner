"""Set Term from the Due date on every open task that has one."""

from datetime import date

from . import dates, tasks
from .config import DATA_SOURCE_ID
from .notion import Notion


def run(notion: Notion, today: date) -> None:
    pages = notion.query(DATA_SOURCE_ID, {"and": [
        {"property": "Done", "checkbox": {"equals": False}},
        {"property": "Due", "date": {"is_not_empty": True}},
    ]})
    print(f"Terms: {len(pages)} open dated task(s)")
    for page in pages:
        task = tasks.from_page(page)
        term = dates.term_for(task.due_date, today)
        if term != task.term:
            notion.update_page(task.id, {"Term": tasks.select(term)}, tasks.describe(task, {"Term": (task.term, term)}))
