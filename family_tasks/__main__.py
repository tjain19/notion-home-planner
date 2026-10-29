"""Entry point: python -m family_tasks nightly|weekly [--dry-run] [--force]."""

import argparse
import os
import sys
import traceback

from . import config, dates, recurrence, sorter, summary, terms
from .notion import Notion


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="family_tasks")
    parser.add_argument("job", choices=["nightly", "weekly"])
    parser.add_argument("--dry-run", action="store_true", help="print every change instead of writing to Notion")
    parser.add_argument("--force", action="store_true", help="weekly: post now, even outside Sunday 7pm or if this week's page exists")
    args = parser.parse_args(argv)
    dry_run = args.dry_run or os.environ.get("DRY_RUN", "").lower() == "true"

    cfg = config.load(dry_run)
    notion = Notion(cfg.notion_token, cfg.dry_run)
    notion.check_data_source(config.DATA_SOURCE_ID)
    people = notion.people()
    if not people:
        raise RuntimeError("No people found in the Notion workspace; check the integration's user access")
    moment = dates.now()
    print(f"{args.job} run at {moment:%Y-%m-%d %H:%M %Z}{' (dry run)' if dry_run else ''}; "
          f"people: {', '.join(p['name'] for p in people)}")

    if args.job == "weekly":
        summary.run(notion, people, moment, args.force)
        return 0

    # Each step runs even if an earlier one failed; any failure fails the run.
    today = moment.date()
    classifier = sorter.Classifier(cfg.anthropic_api_key)
    steps = [
        ("recurrence", lambda: recurrence.run(notion, [p["id"] for p in people], today)),
        ("terms", lambda: terms.run(notion, today)),
        ("sorter", lambda: sorter.run(notion, classifier)),
    ]
    failed = []
    for name, step in steps:
        try:
            step()
        except Exception:
            traceback.print_exc()
            failed.append(name)
    if failed:
        print(f"FAILED steps: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
