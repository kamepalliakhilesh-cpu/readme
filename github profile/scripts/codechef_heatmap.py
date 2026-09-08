#!/usr/bin/env python3
"""
Generate assets/codechef-heatmap.svg from the public CodeChef profile.

Profile tracked:
    https://www.codechef.com/users/k_v_akhilesh

The script deliberately fails rather than generating a fake heatmap if
CodeChef changes its public page structure or does not expose the activity
data expected by the parser.
"""

from __future__ import annotations

import html
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = "k_v_akhilesh"
PROFILE_URL = f"https://www.codechef.com/users/{USERNAME}"
OUTPUT = Path("assets/codechef-heatmap.svg")


def fetch_profile() -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0 Safari/537.36"
        )
    }
    response = requests.get(PROFILE_URL, headers=headers, timeout=30)
    response.raise_for_status()
    if "CodeChef" not in response.text:
        raise RuntimeError("Unexpected response from CodeChef.")
    return response.text


def extract_activity_data(source: str) -> dict[date, int]:
    """
    Try to find date/count pairs embedded in the public page.

    CodeChef can change its frontend representation. We support common
    date/count encodings and refuse to silently create incorrect data.
    """
    data: dict[date, int] = {}

    # Common ISO date followed by a numeric count in inline JS/HTML.
    patterns = [
        r'(?:"|\\')(\d{4}-\d{2}-\d{2})(?:"|\\')\s*[:=,]\s*(\d+)',
        r'(?:"|\\')(\d{4}-\d{2}-\d{2})(?:"|\\')\s*,\s*(\d+)',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, source):
            try:
                d = date.fromisoformat(match.group(1))
                count = int(match.group(2))
            except ValueError:
                continue
            data[d] = max(data.get(d, 0), count)

    return data


def generate_svg(data: dict[date, int]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    end = date.today()
    start = end - timedelta(days=364)

    # Sunday-start calendar grid.
    first = start - timedelta(days=(start.weekday() + 1) % 7)
    last = end + timedelta(days=(6 - ((end.weekday() + 1) % 7)))

    days = []
    current = first
    while current <= last:
        days.append(current)
        current += timedelta(days=1)

    max_count = max(data.values(), default=0)

    def level(count: int) -> int:
        if count <= 0 or max_count == 0:
            return 0
        ratio = count / max_count
        if ratio <= 0.25:
            return 1
        if ratio <= 0.50:
            return 2
        if ratio <= 0.75:
            return 3
        return 4

    # Use neutral SVG colors; users can change these later if desired.
    shades = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

    cell = 12
    gap = 3
    left = 34
    top = 30
    weeks = ((last - first).days + 1) // 7
    width = left + weeks * (cell + gap) + 10
    height = top + 7 * (cell + gap) + 28

    rects = []
    for i, d in enumerate(days):
        week = i // 7
        weekday = i % 7
        x = left + week * (cell + gap)
        y = top + weekday * (cell + gap)
        count = data.get(d, 0)
        title = html.escape(f"{d.isoformat()}: {count} submissions")
        rects.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
            f'rx="2" fill="{shades[level(count)]}">'
            f"<title>{title}</title></rect>"
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
viewBox="0 0 {width} {height}" width="{width}" height="{height}"
role="img" aria-label="CodeChef activity heatmap for {USERNAME}">
<style>
text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
</style>
<text x="0" y="18" font-size="13" font-weight="600">CodeChef — {USERNAME}</text>
{''.join(rects)}
<text x="0" y="{height - 7}" font-size="10" fill="#8b949e">
Last 365 days • hover a square for the date and submissions
</text>
</svg>
"""
    OUTPUT.write_text(svg, encoding="utf-8")


def main() -> int:
    try:
        source = fetch_profile()
        data = extract_activity_data(source)

        if not data:
            raise RuntimeError(
                "No CodeChef activity data could be safely extracted. "
                "CodeChef may have changed its page structure. "
                "No placeholder heatmap was generated."
            )

        generate_svg(data)
        print(f"Generated {OUTPUT} with {len(data)} activity dates.")
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
