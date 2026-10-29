# Notion Home Planner

[![Tests](https://github.com/tjain19/notion-home-planner/actions/workflows/tests.yml/badge.svg)](https://github.com/tjain19/notion-home-planner/actions/workflows/tests.yml)

A shared household task list in Notion that sorts itself, repeats what needs repeating, and brings each week's plan to both people, so neither of them has to be the reminder.

> **Status: functional, in active development.** The P0 features below run every night and every Sunday against a real household's Notion workspace. P1 features are specced but not built yet. See [docs/spec.md](docs/spec.md).

## What it does

**Every night**
- **Sorts new tasks.** Type only a title. Claude (Haiku) fills in Category, Term, Effort, a Quick flag and a one-line *Next step*, e.g. "Open the pediatrician's site and book a checkup slot". It only fills blank fields; anything a person sets is never changed.
- **Keeps timing honest.** Tasks with a due date get their Term (This week, This month, This quarter, Long term) recalculated from the date, so the list stays accurate as weeks pass.
- **Repeats chores.** When a weekly, every-2-weeks or monthly task is checked off, exactly one next copy is created with the due date moved forward. If the task is set to rotate, the owner switches to the other person.

**Every Sunday evening**
- **Posts a weekly summary page** that @mentions each person:
  - a recap: "You two finished X of Y this week"
  - each person's tasks for the coming week, quick ones first, with their next steps
  - unclaimed and overdue tasks
  - personal tasks, in their own section

  It's capped to fit on a phone screen.

## How it works

```
GitHub Actions (cron, UTC)
  ├─ nightly.yml ──► python -m family_tasks nightly
  │                    1. recurrence.py  stamp Completed, create next copies (idempotent)
  │                    2. terms.py       Term from Due date
  │                    3. sorter.py      Claude fills blank fields (structured output)
  └─ weekly.yml  ──► python -m family_tasks weekly
                       summary.py        build the "Week of …" page and @mentions
                           │
                           ▼
                     Notion API (2025-09-03, data sources)
```

- `notion.py` is a small client with retries on 429 and 5xx responses, pagination, and a dry-run mode that prints every write instead of sending it.
- `dates.py` holds all calendar rules in US Eastern time: week, month and quarter boundaries, and month math that clamps Jan 31 + 1 month to Feb 28.
- `tasks.py` maps Notion pages to plain dataclasses and back.

## Design decisions

- **People's edits always win.** The sorter only writes to blank fields and skips any task marked *Reviewed*. The one deliberate exception is Term on dated tasks, where the due date is the source of truth.
- **Safe re-runs.** Recurrence marks the finished task with *Next created* and also checks for an existing copy before creating one. A run that crashes halfway can't double up when it runs again.
- **Constrained model output.** The sorter uses structured outputs with enum-typed fields, so Claude can only return valid Notion options. Next steps are trimmed to 12 words.
- **Daylight saving without two configs.** GitHub cron is UTC only, so the Sunday job is scheduled hourly across both offsets. The script posts only inside the Sunday evening window, and only if that week's page doesn't exist yet. This also covers GitHub starting scheduled runs late, which happens.
- **Fail loudly.** Any error, missing key or unreachable Notion exits non-zero, so GitHub emails the owner. Each nightly step runs even if an earlier one failed, and the run is still marked failed.
- **Dry run by default.** Manual runs default to dry run. Scheduled runs only write once the `LIVE` repo variable is set to `true`.

## Tech

Python 3.12 · Notion API · Anthropic API (Claude Haiku, structured outputs) · GitHub Actions · pytest

## Setup

1. **Create a Notion database** with the properties listed in [docs/spec.md](docs/spec.md#data-model), and a page to hold the weekly summaries.
2. **Create a Notion internal integration** with read, update and insert content permissions, plus *read user information*. Connect it to the database and the summary page.
3. **Add repository secrets:** `NOTION_TOKEN`, `ANTHROPIC_API_KEY`.
4. **Add repository variables:**
   - `NOTION_DATA_SOURCE_ID`: the database's data source ID
   - `NOTION_SUMMARY_PAGE_ID`: the summary page's ID

   The scheduled jobs skip quietly until these are set.
5. **Dry-run both workflows** from the Actions tab, then set the variable `LIVE` = `true`.

**Run locally**
```
pip install -r requirements.txt -r requirements-dev.txt
pytest
export NOTION_TOKEN=... ANTHROPIC_API_KEY=... NOTION_DATA_SOURCE_ID=... NOTION_SUMMARY_PAGE_ID=...
python -m family_tasks nightly --dry-run
python -m family_tasks weekly --dry-run --force
```

## Roadmap

- **Frog and Quick win:** each person gets one hard task and one easy task picked from today's list every morning.
- **iPhone Shortcut** for capturing a task by voice.
- **Copy page content** (notes, checklists) when a task repeats.

## Notes

Built with AI pair programming (Claude Code). I wrote the spec, made the product decisions, and tested against my own workspace.

## License

MIT
