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

    safe_url = re.sub(r"([?&]api_key=)[^&]+", r"\1***", url)
    raise RuntimeError(f"Unable to fetch {safe_url}: {last_error}") from last_error


def request_json(url: str, *, headers: dict[str, str] | None = None) -> Any:
    return json.loads(request_text(url, headers=headers))


def parse_number(value: str) -> int:
    """Parse Scholar numbers, including thousands separators and non-breaking spaces."""
    digits = re.sub(r"\D", "", html.unescape(value))
    if not digits:
        raise ValueError(f"Expected a number, received {value!r}")
    return int(digits)


def format_compact_number(value: int) -> str:
    """Format a KPI with at most one decimal and a compact suffix."""
    for divisor, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "k")):
        if abs(value) >= divisor:
            compact = f"{value / divisor:.1f}".rstrip("0").rstrip(".")
            return f"{compact}{suffix}"
    return f"{value:,}"


def scholar_metrics() -> dict[str, int]:
    """Read paper and citation totals through SerpApi's Scholar Author API."""
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_KEY is not configured")

    page_size = 100
    paper_count = 0
    citations: int | None = None

    for start in range(0, 10_000, page_size):
        query = urlencode(
            {
                "engine": "google_scholar_author",
                "author_id": SCHOLAR_ID,
                "hl": "en",
                "num": page_size,
                "start": start,
                "api_key": api_key,
            }
        )
        payload = request_json(f"https://serpapi.com/search.json?{query}")
        if not isinstance(payload, dict):
            raise RuntimeError("SerpApi returned an unexpected response")
        if payload.get("error"):
            raise RuntimeError(f"SerpApi error: {payload['error']}")

        articles = payload.get("articles", [])
        if not isinstance(articles, list):
            raise RuntimeError("SerpApi returned an invalid articles list")

        if citations is None:
            try:
                raw_citations = payload["cited_by"]["table"][0]["citations"]["all"]
                citations = int(raw_citations)
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise RuntimeError(
                    "SerpApi returned no total citation count"
                ) from error

        paper_count += len(articles)
        if len(articles) < page_size:
            break
    else:
        raise RuntimeError("SerpApi pagination exceeded the safety limit")

    if paper_count == 0 or citations is None:
        raise RuntimeError("SerpApi returned no Scholar publications")

    return {"papers": paper_count, "citations": citations}


def load_existing_metrics() -> dict[str, Any]:
    """Load the last committed snapshot for per-source fallbacks."""
    try:
        payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def collect_with_fallback(
    source_name: str,
    metric_names: tuple[str, ...],
    fetcher: Any,
    existing: dict[str, Any],
) -> tuple[dict[str, int], bool]:
    """Collect one source, retaining its previous values on transient failure."""
    try:
        fresh = fetcher()
        if isinstance(fresh, int):
            fresh = {metric_names[0]: fresh}
        if not isinstance(fresh, dict):
            raise TypeError("collector returned an unexpected value")
        return {name: int(fresh[name]) for name in metric_names}, False
    except Exception as error:
        fallback = {
            name: existing[name]
            for name in metric_names
            if isinstance(existing.get(name), int)
        }
        if len(fallback) != len(metric_names):
            raise RuntimeError(
                f"{source_name} failed and no complete previous values are available"
            ) from error

        message = str(error).replace("\n", " ")
        print(
            f"::warning title={source_name} metrics stale::"
            f"Using the last committed values because collection failed: {message}"
        )
        return fallback, True


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
        value = int(metrics[metric_name])
        display_value = (
            format_compact_number(value)
            if metric_name == "pypi_downloads"
            else f"{value:,}"
        )
        markup, replacements = pattern.subn(
            rf"\g<1>{display_value}\g<2>", markup, count=1
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
    existing = load_existing_metrics()
    scholar, scholar_stale = collect_with_fallback(
        "Google Scholar", ("papers", "citations"), scholar_metrics, existing
    )
    github, github_stale = collect_with_fallback(
        "GitHub", ("github_stars",), github_stars, existing
    )
    pypi, pypi_stale = collect_with_fallback(
        "PyPI", ("pypi_downloads",), pypi_downloads, existing
    )

    stale_sources = [
        name
        for name, is_stale in (
            ("google_scholar", scholar_stale),
            ("github", github_stale),
            ("pypi", pypi_stale),
        )
        if is_stale
    ]
    now = (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    metrics = {
        **scholar,
        **github,
        **pypi,
        "conferences": conference_count(),
        "updated_at": existing.get("updated_at", now) if stale_sources else now,
    }
    if stale_sources:
        metrics["stale_sources"] = stale_sources

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    update_html_fallbacks(metrics)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
