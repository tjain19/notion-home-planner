"""Settings, plus Notion IDs and secrets read from the environment."""

import os
from dataclasses import dataclass

# Which Notion database to manage and which page gets the weekly summaries.
DATA_SOURCE_ID = os.environ.get("NOTION_DATA_SOURCE_ID", "").strip()
PLANNER_PAGE_ID = os.environ.get("NOTION_SUMMARY_PAGE_ID", "").strip()
MODEL = "claude-haiku-5-5"
TIMEZONE = "America/New_York"

CATEGORIES = ["Home", "Work", "Health", "Childcare", "Admin", "Finances", "Travel", "Social/Entertainment"]
TERMS = ["This week", "This month", "This quarter", "Long term"]
EFFORTS = ["2 min", "10 min", "30 min", "1 hour+"]

SUMMARY_MAX_TASKS = 20


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    notion_token: str
    anthropic_api_key: str
    dry_run: bool


def load(dry_run: bool) -> Config:
    required = ("NOTION_TOKEN", "ANTHROPIC_API_KEY", "NOTION_DATA_SOURCE_ID", "NOTION_SUMMARY_PAGE_ID")
    values = {name: os.environ.get(name, "").strip() for name in required}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ConfigError(f"Missing required environment variable(s): {', '.join(missing)}")
    return Config(values["NOTION_TOKEN"], values["ANTHROPIC_API_KEY"], dry_run)
