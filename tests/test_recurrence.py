from datetime import date

from conftest import make_page

from family_tasks import recurrence

A, B = "user-a", "user-b"
TODAY = date(2026, 10, 28)


class FakeNotion:
    def __init__(self, pages, existing=()):
        self.pages, self.existing = pages, list(existing)
        self.created, self.updated = [], []

    def query(self, data_source_id, filter):
        conditions = filter["and"]
        if any(c.get("property") == "Task" for c in conditions):
            return self.existing
        if any(c.get("property") == "Completed" for c in conditions):
            return [p for p in self.pages if not p["properties"]["Completed"]["date"]]
        return [p for p in self.pages
                if not p["properties"]["Next created"]["checkbox"]
                and (p["properties"]["Repeats"]["select"] or {}).get("name") not in (None, "none")]

    def create_page(self, parent, properties, description, children=None):
        self.created.append(properties)

    def update_page(self, page_id, properties, description):
        self.updated.append((page_id, properties))


def test_weekly_repeat_creates_one_copy_and_marks_original():
    page = make_page("Bins", done=True, repeats="weekly", due="2026-10-26", owners=[A], category="Home",
                     effort="10 min", next_step="Wheel bins to curb", completed="2026-10-26")
    notion = FakeNotion([page])
    recurrence.run(notion, [A, B], TODAY)

    assert len(notion.created) == 1
    copy = notion.created[0]
    assert copy["Due"] == {"date": {"start": "2026-11-02"}}
    assert copy["Owner"] == {"people": [{"id": A}]}
    assert copy["Category"] == {"select": {"name": "Home"}}
    assert "Done" not in copy
    assert notion.updated == [("page-1", {"Next created": {"checkbox": True}})]


def test_rerun_after_marking_creates_nothing():
    page = make_page("Bins", done=True, repeats="weekly", due="2026-10-26", completed="2026-10-26", next_created=True)
    notion = FakeNotion([page])
    recurrence.run(notion, [A, B], TODAY)
    assert notion.created == [] and notion.updated == []


def test_existing_copy_is_not_duplicated():
    page = make_page("Bins", done=True, repeats="weekly", due="2026-10-26", completed="2026-10-26")
    notion = FakeNotion([page], existing=[make_page("Bins", id="copy", due="2026-11-02")])
    recurrence.run(notion, [A, B], TODAY)
    assert notion.created == []
    assert notion.updated == [("page-1", {"Next created": {"checkbox": True}})]


def test_rotation_and_month_and_stamp():
    page = make_page("Pay rent", done=True, repeats="monthly", due="2026-10-31", rotates=True, owners=[A],
                     last_edited="2026-10-27T14:00:00.000Z")
    notion = FakeNotion([page])
    recurrence.run(notion, [A, B], TODAY)
    copy = notion.created[0]
    assert copy["Due"] == {"date": {"start": "2026-11-30"}}
    assert copy["Owner"] == {"people": [{"id": B}]}
    assert notion.updated[0][1]["Completed"] == {"date": {"start": "2026-10-27"}}


def test_rotation_needs_two_people():
    page = make_page("Pay rent", done=True, repeats="weekly", due="2026-10-31", rotates=True, owners=[A])
    task = recurrence.tasks.from_page(page)
    assert recurrence.next_owners(task, [A]) == [A]


def test_undated_repeat_counts_from_completion():
    page = make_page("Water plants", done=True, repeats="every 2 weeks", completed="2026-10-20")
    notion = FakeNotion([page])
    recurrence.run(notion, [A, B], TODAY)
    assert notion.created[0]["Due"] == {"date": {"start": "2026-11-03"}}


def test_non_repeating_done_task_only_gets_stamped():
    page = make_page("Call plumber", done=True, repeats="none", last_edited="2026-10-27T14:00:00.000Z")
    notion = FakeNotion([page])
    recurrence.run(notion, [A, B], TODAY)
    assert notion.created == []
    assert notion.updated == [("page-1", {"Completed": {"date": {"start": "2026-10-27"}}})]
