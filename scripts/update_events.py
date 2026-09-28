#!/usr/bin/env python3
"""Render the portfolio event lists from the canonical JSON data."""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = ROOT / "data" / "events.json"
INDEX_PATH = ROOT / "index.html"
START_MARKER = "<!-- EVENTS:START -->"
END_MARKER = "<!-- EVENTS:END -->"

ATTENDANCE_TYPES = {
    "attendee": ("Attendee", "bi bi-person-badge"),
    "poster": ("Poster", "bi bi-easel"),
    "speaker": ("Speaker", "bi bi-mic"),
    "lecturer": ("Lecturer", "bi bi-mic"),
    "exhibitor": ("Exhibitor", "bi bi-briefcase"),
    "keynote_speaker": ("Keynote Speaker", "bi bi-star-fill"),
}

LINK_TYPES = {
    "youtube": ("YouTube", "fa-brands fa-youtube"),
    "spotify": ("Spotify", "fa-brands fa-spotify"),
    "website": ("Website", "bi bi-globe"),
}

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def parse_iso_date(value: Any, field: str, event_id: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{event_id}: {field} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{event_id}: invalid {field}: {value!r}") from error


def nonempty_string(value: Any, field: str, event_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{event_id}: {field} must be a non-empty string")
    return value.strip()


def load_events() -> list[dict[str, Any]]:
    payload = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(
        payload.get("events"), list
    ):
        raise ValueError(
            "events.json must contain schema_version 1 and an events array"
        )

    events: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw_event in payload["events"]:
        if not isinstance(raw_event, dict):
            raise ValueError("Every event must be a JSON object")

        event_id = nonempty_string(raw_event.get("id"), "id", "event")
        if event_id in seen_ids:
            raise ValueError(f"Duplicate event id: {event_id}")
        seen_ids.add(event_id)

        name = nonempty_string(raw_event.get("name"), "name", event_id)
        start_date = parse_iso_date(raw_event.get("start_date"), "start_date", event_id)
        end_date = parse_iso_date(raw_event.get("end_date"), "end_date", event_id)
        if end_date < start_date:
            raise ValueError(f"{event_id}: end_date cannot precede start_date")

        attendance_type = nonempty_string(
            raw_event.get("attendance_type"), "attendance_type", event_id
        )
        if attendance_type not in ATTENDANCE_TYPES:
            allowed = ", ".join(ATTENDANCE_TYPES)
            raise ValueError(f"{event_id}: attendance_type must be one of {allowed}")

        location = raw_event.get("location")
        if not isinstance(location, dict):
            raise ValueError(f"{event_id}: location must be an object")
        place = nonempty_string(location.get("place"), "location.place", event_id)
        country = nonempty_string(location.get("country"), "location.country", event_id)

        name_html = raw_event.get("name_html")
        if name_html is not None:
            name_html = nonempty_string(name_html, "name_html", event_id)
            if re.fullmatch(r"(?:[^<>]|<sup>|</sup>)+", name_html) is None:
                raise ValueError(f"{event_id}: name_html may contain only <sup> tags")

        links = raw_event.get("links", [])
        if not isinstance(links, list):
            raise ValueError(f"{event_id}: links must be an array")
        validated_links = []
        for link in links:
            if not isinstance(link, dict):
                raise ValueError(f"{event_id}: every link must be an object")
            link_type = nonempty_string(link.get("type"), "links.type", event_id)
            if link_type not in LINK_TYPES:
                allowed = ", ".join(LINK_TYPES)
                raise ValueError(f"{event_id}: link type must be one of {allowed}")
            url = nonempty_string(link.get("url"), "links.url", event_id)
            if urlparse(url).scheme != "https":
                raise ValueError(f"{event_id}: link URLs must use HTTPS")
            validated_links.append({"type": link_type, "url": url})

        events.append(
            {
                "id": event_id,
                "name": name,
                "name_html": name_html,
                "start_date": start_date,
                "end_date": end_date,
                "place": place,
                "country": country,
                "attendance_type": attendance_type,
                "links": validated_links,
            }
        )

    return events


def render_event(event: dict[str, Any], indent: str) -> str:
    name = event["name_html"] or html.escape(event["name"])
    start_date: date = event["start_date"]
    date_label = f"{MONTHS[start_date.month - 1]} {start_date.year}"
    location = html.escape(f"{event['place']}, {event['country']}")
    role_label, role_icon = ATTENDANCE_TYPES[event["attendance_type"]]

    metadata = [
        f'<time datetime="{start_date.isoformat()}">{date_label}</time>',
        f'<i class="bi bi-geo-alt" style="color: #149ddd;"></i> {location}',
        f'<i class="{role_icon}" style="color: #149ddd;"></i> <strong>{role_label}</strong>',
    ]
    for link in event["links"]:
        label, icon = LINK_TYPES[link["type"]]
        url = html.escape(link["url"], quote=True)
        metadata.append(
            f'<a href="{url}" target="_blank" rel="noopener noreferrer">'
            f'<i class="{icon}" style="color: #149ddd;"></i> '
            f"<strong>{label}</strong></a>"
        )

    continuation = f" &nbsp;|&nbsp;\n{indent}        "
    return "\n".join(
        (
            f'{indent}<li style="margin-bottom: 10px;">',
            f'{indent}    <strong style="font-size: 1.05rem; color: #173b6c;">{name}</strong><br>',
            f'{indent}    <span style="color: #666; font-size: 0.95rem;">',
            f"{indent}        {continuation.join(metadata)}",
            f"{indent}    </span>",
            f"{indent}</li>",
        )
    )


def render_lists(events: list[dict[str, Any]], today: date) -> str:
    upcoming = sorted(
        (event for event in events if event["end_date"] >= today),
        key=lambda event: (event["start_date"], event["end_date"]),
    )
    past = sorted(
        (event for event in events if event["end_date"] < today),
        key=lambda event: (event["end_date"], event["start_date"]),
        reverse=True,
    )

    lines = [
        "                    <h5><b>Where we'll meet</b></h5>",
        '                    <ul style="list-style-type: none; padding-left: 30px; padding-top: 10px;">',
    ]
    if upcoming:
        lines.extend(
            render_event(event, "                        ") for event in upcoming
        )
    else:
        lines.append(
            '                        <li style="margin-bottom: 10px; color: #666;">'
            "No upcoming events currently scheduled.</li>"
        )
    lines.extend(
        (
            "                    </ul>",
            "",
            "                    <br>",
            "                    <h5><b>Where we've met</b></h5>",
            "",
        )
    )

    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in past:
        by_year[event["end_date"].year].append(event)

    for index, year in enumerate(sorted(by_year, reverse=True)):
        open_attribute = " open" if year == today.year else ""
        lines.extend(
            (
                f"                    <details{open_attribute}>",
                f"                        <summary><strong>{year}</strong></summary>",
                '                        <ul style="list-style-type: none; padding-left: 30px; padding-top: 10px;">',
            )
        )
        lines.extend(
            render_event(event, "                            ")
            for event in by_year[year]
        )
        lines.extend(
            ("                        </ul>", "                    </details>")
        )
        if index != len(by_year) - 1:
            lines.append("")

    return "\n".join(lines)


def update_index(rendered: str, *, check: bool) -> bool:
    markup = INDEX_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(?P<start>^[ \t]*{re.escape(START_MARKER)}[ \t]*$).*?"
        rf"(?P<end>^[ \t]*{re.escape(END_MARKER)}[ \t]*$)",
        flags=re.DOTALL | re.MULTILINE,
    )
    replacement = (
        f"                    {START_MARKER}\n"
        f"{rendered}\n"
        f"                    {END_MARKER}"
    )
    updated, replacements = pattern.subn(replacement, markup, count=1)
    if replacements != 1:
        raise RuntimeError("Could not find the event markers in index.html")
    if updated == markup:
        return False
    if check:
        raise RuntimeError("index.html event lists are out of date")
    INDEX_PATH.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--today", type=date.fromisoformat, help="Override today's date"
    )
    parser.add_argument("--check", action="store_true", help="Validate without writing")
    args = parser.parse_args()

    today = args.today or date.today()
    events = load_events()
    rendered = render_lists(events, today)
    changed = update_index(rendered, check=args.check)
    upcoming = sum(event["end_date"] >= today for event in events)
    print(
        f"Validated {len(events)} events for {today.isoformat()}: "
        f"{upcoming} upcoming, {len(events) - upcoming} past; "
        f"index.html {'updated' if changed else 'already current'}."
    )


if __name__ == "__main__":
    main()
