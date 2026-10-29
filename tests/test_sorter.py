from family_tasks import sorter

ANSWER = sorter.Sorting(category="Home", term="This month", effort="2 min",
                        next_step="Find the filter size printed on the old one, then order online now")


def test_fills_only_blank_fields(task):
    t = task("Replace furnace filter", category="Finances", next_step="Already set")
    updates, changes = sorter.plan(t, ANSWER)
    assert set(updates) == {"Term", "Effort", "Quick"}
    assert updates["Term"] == {"select": {"name": "This month"}}


def test_dated_task_term_left_to_date_rules(task):
    t = task("Replace furnace filter", due="2026-11-20")
    assert "Term" not in sorter.blank_fields(t)
    updates, _ = sorter.plan(t, ANSWER)
    assert "Term" not in updates


def test_next_step_cut_to_twelve_words(task):
    updates, _ = sorter.plan(task("Replace furnace filter"), ANSWER)
    words = updates["Next step"]["rich_text"][0]["text"]["content"].split()
    assert len(words) == 12


def test_quick_from_person_set_effort_without_model(task):
    t = task("Text sitter", category="Childcare", term="This week", effort="2 min", next_step="Text her")
    assert sorter.blank_fields(t) == []
    updates, _ = sorter.plan(t, None)
    assert updates == {"Quick": {"checkbox": True}}


def test_nothing_to_do_when_complete(task):
    t = task("Text sitter", category="Childcare", term="This week", effort="10 min", next_step="Text her")
    assert sorter.plan(t, None) == ({}, {})


class FakeNotion:
    def __init__(self, pages):
        self.pages, self.updated = pages, []

    def query(self, data_source_id, filter):
        return self.pages

    def update_page(self, page_id, properties, description):
        self.updated.append(page_id)


class FakeClassifier:
    def __init__(self):
        self.calls = []

    def sort(self, t):
        self.calls.append(t.title)
        return ANSWER


def test_run_skips_untitled_and_complete_tasks():
    from conftest import make_page
    notion = FakeNotion([
        make_page("", id="blank"),
        make_page("Done already", id="full", category="Home", term="This week", effort="10 min", next_step="Go"),
        make_page("Book dentist", id="new"),
    ])
    classifier = FakeClassifier()
    sorter.run(notion, classifier)
    assert classifier.calls == ["Book dentist"]
    assert notion.updated == ["new"]
