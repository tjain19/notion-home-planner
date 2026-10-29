from datetime import date, datetime, timezone

from family_tasks import dates, summary

A, B = "user-a", "user-b"
PEOPLE = [{"id": A, "name": "Alex"}, {"id": B, "name": "Sam"}]
SUNDAY = date(2026, 11, 1)


def plain(block):
    kind = block["type"]
    return "".join(r["text"]["content"] if r["type"] == "text" else f"@{r['mention']['user']['id']}"
                   for r in block[kind].get("rich_text", []))


def eastern(*args):
    return datetime(*args, tzinfo=timezone.utc).astimezone(dates.TZ)


def test_window_handles_daylight_saving():
    # Summer: 23:00 UTC Sunday is 7pm EDT. Winter: 00:00 UTC Monday is 7pm EST.
    assert summary.in_window(eastern(2026, 7, 12, 23, 0))
    assert summary.in_window(eastern(2026, 11, 2, 0, 0))
    # In winter the 23:00 UTC cron is 6pm Eastern, before the window opens.
    assert not summary.in_window(eastern(2026, 11, 1, 23, 0))


def test_window_covers_late_runs_until_midnight():
    # A run delayed to 11:40pm Eastern on Sunday still posts.
    assert summary.in_window(eastern(2026, 11, 2, 4, 40))
    # Once it's Monday in New York, it's too late.
    assert not summary.in_window(eastern(2026, 11, 2, 5, 5))
    assert not summary.in_window(eastern(2026, 7, 13, 4, 0))  # midnight EDT, Monday


def test_title_uses_next_monday():
    assert summary.page_title(summary.next_monday(SUNDAY)) == "Week of Nov 2, 2026"


def test_layout(task):
    open_tasks = [
        task("Book dentist", id="a", owners=[B], term="This week", category="Health", next_step="Call office"),
        task("Text sitter", id="b", owners=[B], term="This week", quick=True),
        task("Fix gate", id="c", term="This week"),
        task("Renew passport", id="d", owners=[A], due="2026-10-20"),
        task("Plan party", id="e", owners=[A], due="2026-11-05"),  # due next week
        task("Long project", id="f", owners=[A], term="Long term"),
        task("Journal", id="g", owners=[B], term="This week", list="Personal"),
    ]
    done = [task("Bins", id="h", done=True, completed="2026-10-28"),
            task("Old", id="i", done=True, completed="2026-10-01")]
    blocks = summary.build(open_tasks, done, PEOPLE, SUNDAY)
    lines = [plain(b) for b in blocks]

    # Finished 1; still open this week: a, b, c, d (overdue). e is due next week.
    assert lines[0] == "You two finished 1 of 5 this week."
    assert lines[1] == f"@{A} · 1 task"
    assert [plain(c) for c in blocks[1]["toggle"]["children"]] == ["Plan party"]
    assert lines[2] == f"@{B} · 2 tasks"
    assert [plain(c).split(" ·")[0].split(" —")[0] for c in blocks[2]["toggle"]["children"]] == ["Text sitter", "Book dentist"]
    assert "— Call office" in plain(blocks[2]["toggle"]["children"][1])
    assert lines[3] == "Unclaimed · 1 task"
    assert lines[4] == "Overdue · 1 task"
    assert plain(blocks[4]["toggle"]["children"][0]) == "Renew passport · due Oct 20"
    assert blocks[5]["type"] == "divider"
    assert lines[6] == "Personal"
    assert lines[7] == "Alex — No personal tasks this week"
    assert lines[8] == "Sam · 1 task"


def test_cap_at_twenty(task):
    open_tasks = [task(f"Task {i}", id=str(i), owners=[B], term="This week") for i in range(25)]
    blocks = summary.build(open_tasks, [], PEOPLE, SUNDAY)
    t_children = blocks[2]["toggle"]["children"]
    assert sum(c["type"] == "to_do" for c in t_children) == 20
    assert plain(t_children[-1]) == "and 5 more"
