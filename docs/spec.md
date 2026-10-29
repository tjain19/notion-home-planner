# Spec

## Problem

Two adults share a household task list in Notion. One of them works best when tasks arrive as prompts that are already broken down. The goal: the list sorts itself, repeats what needs repeating, and comes to both people, so neither has to be the reminder.

## Data model

One Notion database. Properties:

| Property | Type | Values / notes |
|---|---|---|
| Task | title | |
| Category | select | Home, Work, Health, Childcare, Admin, Finances, Travel, Social/Entertainment |
| Term | select | This week, This month, This quarter, Long term |
| Owner | people | |
| Due | date | |
| Repeats | select | none, weekly, every 2 weeks, monthly |
| Effort | select | 2 min, 10 min, 30 min, 1 hour+ |
| Next step | text | One line, 12 words max |
| List | select | Household, Personal (blank counts as Household) |
| Done, Quick, Reviewed, Rotates, Frog, Quick win, Body double | checkbox | |
| Completed | date | Set by the nightly job |
| Next created | checkbox | Set by the nightly job; prevents duplicate repeats |

People are read from the Notion workspace, never hardcoded.

## P0 (built)

**Nightly, about 2am US Eastern, plus a manual run button**

1. **Sorter.** For tasks not Done and not Reviewed, fill only blank fields:
   - Category
   - Term (undated tasks only)
   - Effort
   - Quick (true when Effort is 2 min)
   - Next step

   Never overwrite a field that already has a value. Skip tasks with an empty title.
2. **Term from dates.** For every open task with a Due date:
   - overdue or due by this Sunday: This week
   - due by the end of the month: This month
   - due by the end of the quarter: This quarter
   - later: Long term

   The date wins over a hand-set Term.
3. **Recurrence.** When a repeating task is Done:
   - Create exactly one next copy, with Due moved forward 7 days, 14 days or 1 month. Done is unchecked and the other fields are copied.
   - If Rotates is checked, the owner switches to the other person.
   - Re-running never creates duplicates.

**Sunday, 7pm US Eastern (handles daylight saving; GitHub cron is UTC)**

4. Create a "Week of <Monday>" child page with:
   - a recap line: "You two finished X of Y this week."
   - one toggle per person, headed by an @mention and a task count, listing their This week Household tasks (Quick tasks first, Next step in gray)
   - Unclaimed, then Overdue with due dates
   - a divider and a Personal section per person
   - at most 20 tasks, then "and N more"

   The @mentions notify both people. If GitHub starts the run late, the summary still posts that Sunday evening.

**Reliability**

5. Any error fails the run with a non-zero exit, so GitHub sends an email. A missing key or unreachable Notion counts as an error.
6. A dry-run mode prints every change it would make without writing to Notion. Scheduled runs stay dry until a `LIVE` repo variable is set.

## P1 (planned)

- **Frog and Quick win.** Each night, pick one Frog (hardest task) and one Quick win (easiest quick task) per person, and clear yesterday's picks.
  - Candidates are the person's open tasks due today or overdue. If there are none, fall back to their This week tasks.
  - The Frog and the Quick win must be different tasks.
- **iPhone Shortcut for capture.** "Hey Siri, family task" creates a task with just a title through the Notion API, and the nightly sorter fills in the rest. It uses a separate insert-only Notion integration.
- **Copy page content on repeat.** The next copy of a repeating task also gets the notes and checklist inside the page.
