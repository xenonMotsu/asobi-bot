from __future__ import annotations

"""Main entry point for Asobi Store and Asobi Ticket deadline alerts.

This module fetches data from the target websites, filters items based on
remaining days until their deadlines, and sends notifications to Discord.

Parsing logic for the target pages is intentionally left unimplemented and
marked as TODO because it depends on the websites' DOM structures.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

import requests
from dateutil import tz

ASOBISTORE_URL = (
    "https://shop.asobistore.jp/product/catalog/s/simekiri/sime/1/cf113/118/n/120#a1"
)
ASOBITICKET_BASE = "https://asobiticket2.asobistore.jp"
ASOBITICKET_EVENTS_URL = f"{ASOBITICKET_BASE}/booths"


@dataclass
class DeadlineEntry:
    """Simple structure representing an item/event with a deadline."""

    title: str
    url: str
    deadline: datetime


def load_alert_days() -> List[int]:
    """Load alert days from the environment variable.

    Returns
    -------
    list[int]
        Sorted list of days before the deadline when notifications should
        be sent.
    """

    value = os.getenv("ALERT_DAYS")
    if value:
        try:
            days = sorted({int(v.strip()) for v in value.split(",") if v.strip()})
            return days
        except ValueError:
            pass
    return [0, 1, 7]


def send_discord(webhook_url: str, content: str) -> None:
    """Send a message to Discord via webhook."""

    requests.post(webhook_url, json={"content": content}, timeout=10)


# ---------------------------------------------------------------------------
# Parsing helpers (to be implemented)
# ---------------------------------------------------------------------------

def parse_asobistore_items(html: str) -> List[DeadlineEntry]:
    """Parse Asobi Store HTML and return a list of items with deadlines.

    TODO: Implement the actual parsing logic based on the website's structure.
    """

    raise NotImplementedError


def parse_ticket_event_list(html: str) -> List[str]:
    """Parse the event list page and return URLs for each event.

    TODO: Implement based on the website's structure.
    """

    raise NotImplementedError


def parse_ticket_event(html: str) -> List[DeadlineEntry]:
    """Parse a single event page and return available receptions with deadlines.

    TODO: Implement based on the website's structure.
    """

    raise NotImplementedError


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------

def get_asobistore_items() -> List[DeadlineEntry]:
    """Fetch and parse items from Asobi Store."""

    response = requests.get(ASOBISTORE_URL, timeout=10)
    response.raise_for_status()
    return parse_asobistore_items(response.text)


def get_ticket_events() -> List[DeadlineEntry]:
    """Fetch and parse events from Asobi Ticket."""

    response = requests.get(ASOBITICKET_EVENTS_URL, timeout=10)
    response.raise_for_status()

    event_urls = parse_ticket_event_list(response.text)

    entries: List[DeadlineEntry] = []
    for url in event_urls:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        entries.extend(parse_ticket_event(resp.text))
    return entries


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def filter_entries(
    entries: Iterable[DeadlineEntry], alert_days: Iterable[int], now: datetime
) -> List[DeadlineEntry]:
    """Filter entries that match the given alert days."""

    alert_set = set(alert_days)
    result: List[DeadlineEntry] = []
    for entry in entries:
        delta = (entry.deadline.date() - now.date()).days
        if delta in alert_set:
            result.append(entry)
    return result


def format_message(section: str, entries: Iterable[DeadlineEntry]) -> str:
    """Create a Discord-friendly message for a list of entries."""

    lines = [f"**{section}**"]
    for e in entries:
        deadline = e.deadline.strftime("%Y-%m-%d %H:%M")
        lines.append(f"- {e.title} | 締切: {deadline} | <{e.url}>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main routine
# ---------------------------------------------------------------------------

def main() -> None:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL is not set")

    alert_days = load_alert_days()

    jst = tz.gettz("Asia/Tokyo")
    now = datetime.now(tz=jst)

    messages: List[str] = []

    try:
        store_items = filter_entries(get_asobistore_items(), alert_days, now)
        if store_items:
            messages.append(format_message("アソビストア 締切間近", store_items))
    except NotImplementedError:
        messages.append("アソビストアのパースは未実装です。")

    try:
        ticket_items = filter_entries(get_ticket_events(), alert_days, now)
        if ticket_items:
            messages.append(format_message("アソビチケット 締切間近", ticket_items))
    except NotImplementedError:
        messages.append("アソビチケットのパースは未実装です。")

    if messages:
        send_discord(webhook_url, "\n\n".join(messages))


if __name__ == "__main__":
    main()
