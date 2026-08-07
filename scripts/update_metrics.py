#!/usr/bin/env python3
"""Collect the public metrics displayed on the portfolio homepage."""

from __future__ import annotations

import html
import json
import os
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "metrics.json"
INDEX_PATH = ROOT / "index.html"

SCHOLAR_ID = "_9OzwqMAAAAJ"
GITHUB_USER = "viventriglia"
PYPI_PACKAGE = "pytecgg"
CONFERENCE_OFFSET = 11  # 2 talk PyData Roma + 1 SIF + 8 fra PyData e altro

USER_AGENT = (
    "portfolio-metrics/1.0 "
    "(+https://github.com/viventriglia/portfolio; weekly public-metrics refresh)"
)


def request_text(url: str, *, headers: dict[str, str] | None = None) -> str:
    """Fetch a UTF-8 response, retrying short-lived network and server errors."""
    request_headers = {
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": USER_AGENT,
    }
    if headers:
        request_headers.update(headers)

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            request = Request(url, headers=request_headers)
            with urlopen(request, timeout=30) as response:
                encoding = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(encoding, errors="replace")
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(2**attempt)

    raise RuntimeError(f"Unable to fetch {url}: {last_error}") from last_error


def request_json(url: str, *, headers: dict[str, str] | None = None) -> Any:
    return json.loads(request_text(url, headers=headers))


def parse_number(value: str) -> int:
    """Parse Scholar numbers, including thousands separators and non-breaking spaces."""
    digits = re.sub(r"\D", "", html.unescape(value))
    if not digits:
        raise ValueError(f"Expected a number, received {value!r}")
    return int(digits)


def scholar_metrics() -> dict[str, int]:
    """Read publication and citation totals from a public Scholar profile."""
    page_size = 100
    paper_count = 0
    stats: list[int] | None = None

    for start in range(0, 2_000, page_size):
        query = urlencode(
            {
                "user": SCHOLAR_ID,
                "hl": "en",
                "cstart": start,
                "pagesize": page_size,
            }
        )
        page = request_text(f"https://scholar.google.com/citations?{query}")

        if "gsc_prf_in" not in page or "gsc_rsb_std" not in page:
            raise RuntimeError(
                "Google Scholar returned an unexpected page or a bot check"
            )

        if stats is None:
            raw_stats = re.findall(
                r'<td[^>]*class=["\'][^"\']*\bgsc_rsb_std\b[^"\']*["\'][^>]*>'
                r"(.*?)</td>",
                page,
                flags=re.DOTALL,
            )
            stats = [parse_number(re.sub(r"<[^>]+>", "", value)) for value in raw_stats]
            if not stats:
                raise RuntimeError("Could not find Scholar citation statistics")

        rows_on_page = len(
            re.findall(r'class=["\'][^"\']*\bgsc_a_tr\b[^"\']*["\']', page)
        )
        paper_count += rows_on_page

        if rows_on_page < page_size:
            break
    else:
        raise RuntimeError("Scholar profile pagination exceeded the safety limit")

    if paper_count == 0 or stats is None:
        raise RuntimeError("Could not find publications in the Scholar profile")

    return {
        "papers": paper_count,
        "citations": stats[0],
    }


def github_stars() -> int:
    """Sum stars across repositories owned by the public GitHub account."""
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"

    total = 0
    for page_number in range(1, 101):
        query = urlencode(
            {"type": "owner", "per_page": 100, "page": page_number, "sort": "full_name"}
        )
        repositories = request_json(
            f"https://api.github.com/users/{GITHUB_USER}/repos?{query}",
            headers=headers,
        )
        if not isinstance(repositories, list):
            raise RuntimeError("GitHub returned an unexpected response")

        total += sum(int(repository["stargazers_count"]) for repository in repositories)
        if len(repositories) < 100:
            return total

    raise RuntimeError("GitHub pagination exceeded the safety limit")


def pypi_downloads() -> int:
    """Return the package's all-time downloads from pepy.tech's public badge."""
    query = urlencode(
        {
            "period": "TOTAL",
            "units": "NONE",
            "left_text": "Downloads",
        }
    )
    badge = request_text(
        f"https://api.pepy.tech/personalized-badge/{PYPI_PACKAGE}?{query}"
    )
    text_values = re.findall(r"<text\b[^>]*>([^<]+)</text>", badge)
    numeric_values = {
        parse_number(value)
        for value in text_values
        if re.fullmatch(r"\s*[\d,.]+\s*", html.unescape(value))
    }
    if len(numeric_values) != 1:
        raise RuntimeError("pepy.tech returned an unexpected total-downloads badge")
    return numeric_values.pop()


def conference_count(today: date | None = None) -> int:
    """Count dated, past conference entries in index.html, then add the agreed offset."""
    markup = INDEX_PATH.read_text(encoding="utf-8")
    section = re.search(
        r'<section\b[^>]*\bid=["\']conferences["\'][^>]*>(.*?)</section>',
        markup,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if section is None:
        raise RuntimeError("Could not find the Conferences section in index.html")

    reference_date = today or datetime.now(timezone.utc).date()
    event_dates = re.findall(
        r'<time\b[^>]*\bdatetime=["\'](\d{4}-\d{2}-\d{2})["\']',
        section.group(1),
        flags=re.IGNORECASE,
    )
    past_events = sum(
        date.fromisoformat(event_date) < reference_date for event_date in event_dates
    )
    return past_events + CONFERENCE_OFFSET


def update_html_fallbacks(metrics: dict[str, int | str]) -> None:
    """Keep no-fetch fallbacks current for file:// and no-JavaScript viewing."""
    markup = INDEX_PATH.read_text(encoding="utf-8")

    for metric_name in (
        "papers",
        "citations",
        "github_stars",
        "pypi_downloads",
        "conferences",
    ):
        pattern = re.compile(
            rf'(<[^>]+\bdata-metric="{metric_name}"[^>]*>)[^<]*(</[^>]+>)'
        )
        markup, replacements = pattern.subn(
            rf"\g<1>{int(metrics[metric_name]):,}\g<2>", markup, count=1
        )
        if replacements != 1:
            raise RuntimeError(f"Could not update the {metric_name} HTML fallback")

    updated_at = datetime.fromisoformat(
        str(metrics["updated_at"]).replace("Z", "+00:00")
    )
    display_date = f"{updated_at.day} {updated_at.strftime('%b %Y')}"
    date_pattern = re.compile(r"(<span data-metrics-updated>)[^<]*(</span>)")
    markup, replacements = date_pattern.subn(
        rf"\g<1>{display_date}\g<2>", markup, count=1
    )
    if replacements != 1:
        raise RuntimeError("Could not update the metrics date HTML fallback")

    INDEX_PATH.write_text(markup, encoding="utf-8")


def main() -> None:
    metrics = {
        **scholar_metrics(),
        "github_stars": github_stars(),
        "pypi_downloads": pypi_downloads(),
        "conferences": conference_count(),
        "updated_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    update_html_fallbacks(metrics)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
